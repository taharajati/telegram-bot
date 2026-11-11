"""
تست خودکار سیستم اشتراک — روی SQLite در حافظه، بدون نیاز به ربات.
اجرا: python -m pytest tests/test_subscription.py -v
"""
import pytest

from database.db import async_session
from database.models import (
    Base,
    Shop,
    ShopOwner,
    User,
    SubscriptionPlan,
    ShopSubscription,
)
from services.subscription import (
    seed_subscription_plans,
    create_trial_subscription,
    create_paid_subscription,
    get_current_subscription,
    has_active_subscription,
    verify_subscription,
    reject_subscription,
    get_subscription_display,
    receipt_hash,
)


# ─── Fixtures ─────────────────────────────────────────────


@pytest.fixture(autouse=True)
async def _create_and_drop_tables():
    """Create tables before each test, drop after."""
    from database.db import engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def _seed_plans():
    async with async_session() as session:
        await seed_subscription_plans(session)
        await session.commit()


@pytest.fixture
async def make_shop():
    """Fixture that returns a callable to create a shop and returns (user_id, shop_id)."""
    async def _make_shop():
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

    return _make_shop


async def _get_one_plan():
    from sqlalchemy import select

    async with async_session() as session:
        result = await session.execute(select(SubscriptionPlan))
        return result.scalars().first()


# ─── Tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_01_seed_plans(_create_and_drop_tables, _seed_plans):
    """۴ پلن بعد از seed وجود داشته باشد."""
    from database.models import SubscriptionPlan
    from sqlalchemy import select

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
async def test_02_create_trial(_create_and_drop_tables, _seed_plans, make_shop):
    """ساخت ردیف trial و بررسی صحت آن."""
    user_id, shop_id = await make_shop()

    async with async_session() as session:
        sub = await create_trial_subscription(shop_id, admin_user_id=user_id, session=session)
        await session.commit()

    assert sub is not None
    assert sub.shop_id == shop_id
    assert sub.is_trial is True
    assert sub.plan_id is None
    assert sub.approval_status == "approved"
    assert sub.superseded_at is None
    assert sub.end_date > sub.start_date
    from datetime import timedelta

    expected_end = sub.start_date + timedelta(days=13)
    assert abs((sub.end_date - expected_end).total_seconds()) < 60


@pytest.mark.asyncio
async def test_03_has_active_subscription_trial(_create_and_drop_tables, _seed_plans, make_shop):
    """تست has_active_subscription — trial باید active باشه."""
    user_id, shop_id = await make_shop()

    async with async_session() as session:
        await create_trial_subscription(shop_id, admin_user_id=user_id, session=session)
        await session.commit()

    async with async_session() as session:
        active = await has_active_subscription(shop_id, session)
    assert active is True


@pytest.mark.asyncio
async def test_04_create_paid_subscription(_create_and_drop_tables, _seed_plans, make_shop):
    """ساخت ردیف اشتراک پولی."""
    user_id, shop_id = await make_shop()

    plan = await _get_one_plan()

    async with async_session() as session:
        sub = await create_paid_subscription(
            shop_id=shop_id,
            plan_id=plan.id,
            session=session,
            receipt_file_id="test_receipt_file_id",
            receipt_caption="test caption",
        )
        await session.commit()

    assert sub is not None
    assert sub.is_trial is False
    assert sub.plan_id == plan.id
    assert sub.approval_status == "pending"
    assert sub.receipt_hash is not None
    assert sub.superseded_at is None


@pytest.mark.asyncio
async def test_05_subscription_supersede(_create_and_drop_tables, _seed_plans, make_shop):
    """ردیف قدیمی بعد از خرید جدید supersede بشه."""
    user_id, shop_id = await make_shop()

    async with async_session() as session:
        old = await create_trial_subscription(shop_id, admin_user_id=user_id, session=session)
        await session.commit()

    assert old.superseded_at is None

    plan = await _get_one_plan()

    async with async_session() as session:
        new = await create_paid_subscription(
            shop_id=shop_id,
            plan_id=plan.id,
            session=session,
            receipt_file_id="test_img_binary_001",
            receipt_caption="",
        )
        await session.commit()

    async with async_session() as session:
        current = await get_current_subscription(shop_id, session)
    assert current.id == new.id

    async with async_session() as session:
        old_row = await session.get(ShopSubscription, old.id)
        assert old_row.superseded_at is not None


@pytest.mark.asyncio
async def test_06_verify_subscription(_create_and_drop_tables, _seed_plans, make_shop):
    """تأیید ادمین روی اشتراک pending."""
    user_id, shop_id = await make_shop()

    plan = await _get_one_plan()

    async with async_session() as session:
        sub = await create_paid_subscription(
            shop_id=shop_id,
            plan_id=plan.id,
            session=session,
            receipt_file_id="verify_test",
            receipt_caption="",
        )
        await session.commit()

    assert sub.approval_status == "pending"

    async with async_session() as session:
        verified = await verify_subscription(sub.id, admin_user_id=user_id, session=session)
        await session.commit()

    assert verified is not None
    assert verified.approval_status == "approved"
    assert verified.verified_at is not None
    assert verified.verified_by == user_id


@pytest.mark.asyncio
async def test_07_reject_subscription(_create_and_drop_tables, _seed_plans, make_shop):
    """رد اشتراک توسط ادمین."""
    user_id, shop_id = await make_shop()

    plan = await _get_one_plan()

    async with async_session() as session:
        sub = await create_paid_subscription(
            shop_id=shop_id,
            plan_id=plan.id,
            session=session,
            receipt_file_id="reject_test",
            receipt_caption="",
        )
        await session.commit()

    async with async_session() as session:
        rejected = await reject_subscription(sub.id, admin_user_id=user_id, reason="مشکل در رسید", session=session)
        await session.commit()

    assert rejected is not None
    assert rejected.approval_status == "rejected"
    assert rejected.rejection_reason == "مشکل در رسید"


@pytest.mark.asyncio
async def test_08_get_subscription_display(_create_and_drop_tables, _seed_plans, make_shop):
    """get_subscription_display متن readable برگردونه."""
    user_id, shop_id = await make_shop()

    async with async_session() as session:
        await create_trial_subscription(shop_id, admin_user_id=user_id, session=session)
        await session.commit()

    async with async_session() as session:
        text = await get_subscription_display(shop_id, session)

    assert isinstance(text, str)
    assert len(text) > 5


@pytest.mark.asyncio
async def test_09_receipt_hash_function(_create_and_drop_tables):
    """تابع receipt_hash هش SHA-256 درست بده."""
    h1 = receipt_hash(b"test_image_bytes")
    h2 = receipt_hash(b"test_image_bytes")
    h3 = receipt_hash(b"different_bytes")

    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64
    assert isinstance(h1, str)


@pytest.mark.asyncio
async def test_10_receipt_dedup(_create_and_drop_tables, _seed_plans, make_shop):
    """receipt_hash یکتا — دوبار ثبت با هش تکراری reject بشه."""
    user_id, shop_id = await make_shop()

    plan = await _get_one_plan()

    async with async_session() as session:
        await create_paid_subscription(
            shop_id=shop_id,
            plan_id=plan.id,
            session=session,
            receipt_file_id="duplicate_hash",
            receipt_caption="",
        )
        await session.commit()

    with pytest.raises(Exception):
        async with async_session() as session:
            await create_paid_subscription(
                shop_id=shop_id,
                plan_id=plan.id,
                session=session,
                receipt_file_id="duplicate_hash",
                receipt_caption="",
            )
            await session.commit()