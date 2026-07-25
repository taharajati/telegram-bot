"""
تست خودکار سیستم اشتراک — روی SQLite محلی، بدون نیاز به ربات.
اجرا: python -m pytest tests/test_subscription.py -v
"""
import pytest

from database.db import test_async_session, engine, async_session
from database.models import Base
from sqlalchemy import select


# ─── Fixtures ─────────────────────────────────────────────


@pytest.fixture(scope="module")
def setup_tables():
    """Create tables once for all tests in this module."""
    import asyncio
    loop = asyncio.new_event_loop()
    loop.run_until_complete(_create_tables())
    yield
    loop.run_until_complete(_drop_tables())
    loop.close()


async def _create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _drop_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ─── Test helpers ─────────────────────────────────────────


async def _seed_plans():
    from services.subscription import seed_subscription_plans
    async with async_session() as session:
        await seed_subscription_plans(session)
        await session.commit()


async def _make_shop() -> tuple[int, int]:
    from database.models import ShopOwner, User, Shop
    async with async_session() as session:
        user = User(user_id=999999, first_name="Test")
        session.add(user)
        await session.flush()

        shop = Shop(
            name="فروشگاه تست",
            description="تست اشتراک",
            phone="09120000000",
            is_active=True,
            status="active",
            shipping_cost=0,
        )
        session.add(shop)
        await session.flush()

        owner = ShopOwner(user_id=user.user_id, shop_id=shop.id)
        session.add(owner)
        await session.commit()

        return user.user_id, shop.id


async def _get_one_plan():
    async with async_session() as session:
        result = await session.execute(select(SubscriptionPlan))
        return result.scalars().first()


# ─── Tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_01_seed_plans(setup_tables):
    """4 پلن بعد از seed وجود داشته باشد."""
    from database.models import SubscriptionPlan
    await _seed_plans()
    async with async_session() as session:
        result = await session.execute(
            select(SubscriptionPlan).order_by(SubscriptionPlan.id)
        )
        plans = result.scalars().all()

    assert len(plans) == 4
    assert plans[0].name == "🥈 ماهانه"
    assert plans[0].duration_days == 30
    assert plans[0].price == 499000
    assert plans[3].name == "👑 سالانه"
    assert plans[3].duration_days == 365
    assert plans[3].price == 3499000


@pytest.mark.asyncio
async def test_02_create_trial(setup_tables):
    """ساخت ردیف trial و بررسی صحت آن."""
    from database.models import SubscriptionPlan
    from services.subscription import create_trial_subscription
    await _seed_plans()
    user_id, shop_id = await _make_shop()

    sub = await create_trial_subscription(shop_id, verified_by=user_id)
    assert sub is not None
    assert sub.shop_id == shop_id
    assert sub.is_trial is True
    assert sub.plan_id is None
    assert sub.price == 0
    assert sub.superseded_at is None
    assert sub.end_date > sub.start_date
    from datetime import timedelta
    expected_end = sub.start_date + timedelta(days=7)
    assert abs((sub.end_date - expected_end).total_seconds()) < 60


@pytest.mark.asyncio
async def test_03_has_active_subscription_trial(setup_tables):
    """تست has_active_subscription — trial باید active باشه."""
    from services.subscription import create_trial_subscription, has_active_subscription
    await _seed_plans()
    user_id, shop_id = await _make_shop()

    await create_trial_subscription(shop_id, verified_by=user_id)
    active = await has_active_subscription(shop_id)
    assert active is True


@pytest.mark.asyncio
async def test_04_create_paid_subscription(setup_tables):
    """ساخت ردیف اشتراک پولی."""
    from database.models import SubscriptionPlan
    from services.subscription import create_paid_subscription
    await _seed_plans()
    user_id, shop_id = await _make_shop()

    plan = await _get_one_plan()
    sub = await create_paid_subscription(
        shop_id=shop_id,
        plan_id=plan.id,
        price=plan.price,
        receipt_hash="abc123",
        user_id=user_id,
    )
    assert sub is not None
    assert sub.is_trial is False
    assert sub.plan_id == plan.id
    assert sub.price == 499000
    assert sub.approval_status == "pending"
    assert sub.receipt_hash == "abc123"
    assert sub.superseded_at is None


@pytest.mark.asyncio
async def test_05_subscription_supersede(setup_tables):
    """ردیف قدیمی بعد از خرید جدید supersede بشه."""
    from database.models import SubscriptionPlan
    from services.subscription import (
        create_trial_subscription,
        create_paid_subscription,
        get_current_subscription,
        receipt_hash,
    )
    await _seed_plans()
    user_id, shop_id = await _make_shop()

    old = await create_trial_subscription(shop_id, verified_by=user_id)
    assert old.superseded_at is None

    plan = await _get_one_plan()
    h = receipt_hash("test_img_binary_001")
    new = await create_paid_subscription(
        shop_id=shop_id,
        plan_id=plan.id,
        price=plan.price,
        receipt_hash=h,
        user_id=user_id,
    )

    current = await get_current_subscription(shop_id)
    assert current.id == new.id

    from database.models import ShopSubscription
    async with async_session() as session:
        old_row = await session.get(ShopSubscription, old.id)
        assert old_row.superseded_at is not None


@pytest.mark.asyncio
async def test_06_verify_subscription(setup_tables):
    """تأیید ادمین روی اشتراک pending."""
    from services.subscription import create_paid_subscription, verify_subscription
    await _seed_plans()
    user_id, shop_id = await _make_shop()

    plan = await _get_one_plan()
    sub = await create_paid_subscription(
        shop_id=shop_id, plan_id=plan.id, price=plan.price,
        receipt_hash="verify_test", user_id=user_id,
    )
    assert sub.approval_status == "pending"

    await verify_subscription(sub.id, user_id)
    from database.models import ShopSubscription
    async with async_session() as session:
        verified = await session.get(ShopSubscription, sub.id)
        assert verified.approval_status == "approved"
        assert verified.verified_at is not None
        assert verified.verified_by == user_id


@pytest.mark.asyncio
async def test_07_reject_subscription(setup_tables):
    """رد اشتراک توسط ادمین."""
    from services.subscription import create_paid_subscription, reject_subscription
    await _seed_plans()
    user_id, shop_id = await _make_shop()

    plan = await _get_one_plan()
    sub = await create_paid_subscription(
        shop_id=shop_id, plan_id=plan.id, price=plan.price,
        receipt_hash="reject_test", user_id=user_id,
    )

    await reject_subscription(sub.id, user_id, reason="مشکل در رسید")
    from database.models import ShopSubscription
    async with async_session() as session:
        rejected = await session.get(ShopSubscription, sub.id)
        assert rejected.approval_status == "rejected"
        assert rejected.rejected_reason == "مشکل در رسید"


@pytest.mark.asyncio
async def test_08_get_subscription_display(setup_tables):
    """get_subscription_display متن readable برگردونه."""
    from services.subscription import create_trial_subscription, get_subscription_display
    await _seed_plans()
    user_id, shop_id = await _make_shop()

    await create_trial_subscription(shop_id, verified_by=user_id)
    async with async_session() as session:
        text = await get_subscription_display(shop_id, session)

    assert isinstance(text, str)
    assert len(text) > 5


@pytest.mark.asyncio
async def test_09_receipt_hash_function():
    """تابع receipt_hash هش SHA-256 درست بده."""
    from services.subscription import receipt_hash

    h1 = receipt_hash(b"test_image_bytes")
    h2 = receipt_hash(b"test_image_bytes")
    h3 = receipt_hash(b"different_bytes")

    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64
    assert isinstance(h1, str)


@pytest.mark.asyncio
async def test_10_receipt_dedup(setup_tables):
    """receipt_hash یکتا — دوبار ثبت با هش تکراری reject بشه."""
    from services.subscription import create_paid_subscription
    from database.models import SubscriptionPlan
    await _seed_plans()
    user_id, shop_id = await _make_shop()

    plan = await _get_one_plan()
    await create_paid_subscription(
        shop_id=shop_id, plan_id=plan.id, price=plan.price,
        receipt_hash="duplicate_hash", user_id=user_id,
    )
    with pytest.raises(Exception):
        await create_paid_subscription(
            shop_id=shop_id, plan_id=plan.id, price=plan.price,
            receipt_hash="duplicate_hash", user_id=user_id,
        )
