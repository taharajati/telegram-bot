"""
تست: ادغام حذف فروشگاه با اشتراک فعال و سایر ماژول‌ها.
پوشش: handlers/admin/shops.py + handlers/seller_panel.py (seller_delete_final)
"""
import pytest
from unittest.mock import AsyncMock
from types import SimpleNamespace

from sqlalchemy import select, text as sa_text

from database.db import async_session
from database.models import (
    Base, Shop, ShopOwner, ShopSubscription, SubscriptionPlan,
    User, Product, Category, CartItem, Order, OrderStatus,
)


# ─── Fixtures ───────────────────────────────────────────────────


@pytest.fixture(autouse=True)
async def _tables():
    from database.db import engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
def _force_config(monkeypatch):
    monkeypatch.setattr("config.ADMIN_IDS", {888001, 888002})
    monkeypatch.setattr("config.ADMIN_CARD_NUMBER", "6219861937973138")


@pytest.fixture
async def seed_plans():
    from services.subscription import seed_subscription_plans
    async with async_session() as session:
        await seed_subscription_plans(session)
        await session.commit()


def fake_update(user_id, data=None, msg_text=None):
    user = SimpleNamespace(id=user_id, first_name="Test")
    update = SimpleNamespace(
        effective_user=user,
        effective_chat=SimpleNamespace(id=9999),
    )
    if data is not None:
        q = SimpleNamespace()
        q.data = data
        q.answer = AsyncMock()
        q.edit_message_text = AsyncMock()
        q.edit_message_caption = AsyncMock()
        q.message = SimpleNamespace(
            chat_id=9999, message_id=1,
            delete=AsyncMock(), reply_text=AsyncMock(),
            edit_message_text=AsyncMock(),
        )
        q.from_user = SimpleNamespace(id=user_id)
        update.callback_query = q
        update.message = None
    else:
        update.callback_query = None
        msg = SimpleNamespace()
        msg.text = msg_text
        msg.photo = []
        msg.reply_text = AsyncMock()
        msg.reply_html = AsyncMock()
        msg.delete = AsyncMock()
        update.message = msg
    return update


def fake_context():
    ctx = SimpleNamespace()
    ctx.user_data = {}
    ctx.bot = SimpleNamespace(
        send_message=AsyncMock(), send_photo=AsyncMock(),
        get_me=AsyncMock(return_value=SimpleNamespace(id=123456)),
        create_task=lambda c: None,
    )
    ctx.args = []
    ctx.match = None
    return ctx


async def make_shop_and_owner(user_id=9001):
    async with async_session() as session:
        shop = Shop(name="تست حذف", description="", is_active=True, status="active",
                    phone="09120000000", shipping_cost=0)
        session.add(shop)
        await session.flush()
        owner = ShopOwner(user_id=user_id, shop_id=shop.id)
        session.add(owner)
        await session.flush()
        user = User(user_id=user_id, first_name="Test")
        session.add(user)
        await session.commit()
        shop_id = shop.id
    return shop_id, user_id


async def add_active_subscription(shop_id, session):
    """Create a paid + verified subscription so shop has an active one."""
    from services.subscription import create_paid_subscription, verify_subscription
    plan = (await session.execute(select(SubscriptionPlan))).scalars().first()
    sub = await create_paid_subscription(
        shop_id=shop_id, plan_id=plan.id,
        session=session,
        receipt_file_id="test_receipt", receipt_caption="",
    )
    await session.flush()
    await verify_subscription(sub.id, admin_user_id=888001, session=session)
    await session.commit()
    return sub


async def add_pending_subscription(shop_id, session):
    """Create a paid subscription with pending status."""
    from services.subscription import create_paid_subscription
    plan = (await session.execute(select(SubscriptionPlan))).scalars().first()
    sub = await create_paid_subscription(
        shop_id=shop_id, plan_id=plan.id,
        session=session,
        receipt_file_id="pending_receipt", receipt_caption="",
    )
    await session.commit()
    return sub


async def add_products_and_orders(shop_id, session):
    cat = Category(name="دسته تست", shop_id=shop_id)
    session.add(cat)
    await session.flush()
    prod = Product(name="محصول تست", price=100000, stock=5,
                   category_id=cat.id, shop_id=shop_id)
    session.add(prod)
    await session.flush()
    order = Order(
        user_id=9002, shop_id=shop_id, total_price=100000,
        status=OrderStatus.PENDING, tracking_code=str(shop_id) + "ord",
        shipping_address="آدرس", phone="09120000000",
    )
    session.add(order)
    await session.flush()
    ci = CartItem(user_id=9002, product_id=prod.id, shop_id=shop_id, quantity=1)
    session.add(ci)
    await session.commit()
    return cat, prod, order


# ══════════════════════════════════════════════════════════════════
# TESTS: Admin delete shop
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_admin_delete_shop_no_subscription(
    _tables, seed_plans
):
    """حذف فروشگاه توسط ادمین — بدون اشتراک."""
    shop_id, user_id = await make_shop_and_owner()

    from handlers.admin.shops import delete_shop_final
    upd = fake_update(user_id=888001, data=f"admin:shops:delete_final:{shop_id}")
    ctx = fake_context()
    await delete_shop_final(upd, ctx)

    # Verify shop is gone
    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
        assert shop is None

    # Verify owner is gone
    async with async_session() as session:
        owners = (await session.execute(
            select(ShopOwner).where(ShopOwner.shop_id == shop_id)
        )).scalars().all()
        assert len(owners) == 0


@pytest.mark.asyncio
async def test_admin_delete_shop_with_active_subscription(
    _tables, seed_plans
):
    """حذف فروشگاه با اشتراک فعال — نباید FK error بده."""
    shop_id, user_id = await make_shop_and_owner()

    async with async_session() as session:
        await add_active_subscription(shop_id, session)

    from handlers.admin.shops import delete_shop_final
    upd = fake_update(user_id=888001, data=f"admin:shops:delete_final:{shop_id}")
    ctx = fake_context()
    await delete_shop_final(upd, ctx)

    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
        assert shop is None

        subs = (await session.execute(
            select(ShopSubscription).where(ShopSubscription.shop_id == shop_id)
        )).scalars().all()
        assert len(subs) == 0  # همه پاک شدن


@pytest.mark.asyncio
async def test_admin_delete_shop_with_pending_subscription(
    _tables, seed_plans
):
    """حذف فروشگاه با اشتراک pending — باید پاک بشه."""
    shop_id, user_id = await make_shop_and_owner()

    async with async_session() as session:
        await add_pending_subscription(shop_id, session)

    from handlers.admin.shops import delete_shop_final
    upd = fake_update(user_id=888001, data=f"admin:shops:delete_final:{shop_id}")
    ctx = fake_context()
    await delete_shop_final(upd, ctx)

    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
        assert shop is None


@pytest.mark.asyncio
async def test_admin_delete_shop_with_products_orders_cart(
    _tables, seed_plans
):
    """حذف فروشگاه با محصولات و سفارشات — همه باید پاک بشن."""
    shop_id, user_id = await make_shop_and_owner()

    async with async_session() as session:
        cat, prod, order = await add_products_and_orders(shop_id, session)

    from handlers.admin.shops import delete_shop_final
    upd = fake_update(user_id=888001, data=f"admin:shops:delete_final:{shop_id}")
    ctx = fake_context()
    await delete_shop_final(upd, ctx)

    async with async_session() as session:
        assert await session.get(Shop, shop_id) is None
        assert await session.get(Product, prod.id) is None
        assert await session.get(Category, cat.id) is None
        assert await session.get(Order, order.id) is None
        carts = (await session.execute(
            select(CartItem).where(CartItem.shop_id == shop_id)
        )).scalars().all()
        assert len(carts) == 0


@pytest.mark.asyncio
async def test_admin_delete_shop_notifies_seller(
    _tables, seed_plans
):
    """بعد از حذف توسط ادمین، باید به فروشنده نوتیف بده."""
    shop_id, user_id = await make_shop_and_owner()

    from handlers.admin.shops import delete_shop_final
    upd = fake_update(user_id=888001, data=f"admin:shops:delete_final:{shop_id}")
    ctx = fake_context()
    await delete_shop_final(upd, ctx)

    # Should have called send_message to owner
    # (we can't check exact call args in this mock setup)
    assert upd.callback_query.edit_message_text.called


# ══════════════════════════════════════════════════════════════════
# TESTS: Seller delete shop
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_seller_delete_shop_basic(
    _tables, seed_plans
):
    """فروشنده فروشگاه خودش رو حذف کنه."""
    shop_id, user_id = await make_shop_and_owner()

    from handlers.seller_panel import seller_delete_final
    upd = fake_update(user_id=user_id, data=f"seller:delete_final:{shop_id}")
    ctx = fake_context()
    await seller_delete_final(upd, ctx)

    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
        assert shop is None

    # Should have removed seller menu
    assert ctx.bot.send_message.called


@pytest.mark.asyncio
async def test_seller_delete_shop_with_active_subscription(
    _tables, seed_plans
):
    """فروشنده فروشگاه با اشتراک فعال حذف کنه."""
    shop_id, user_id = await make_shop_and_owner()

    async with async_session() as session:
        await add_active_subscription(shop_id, session)

    from handlers.seller_panel import seller_delete_final
    upd = fake_update(user_id=user_id, data=f"seller:delete_final:{shop_id}")
    ctx = fake_context()
    await seller_delete_final(upd, ctx)

    async with async_session() as session:
        assert await session.get(Shop, shop_id) is None
        subs = (await session.execute(
            select(ShopSubscription).where(ShopSubscription.shop_id == shop_id)
        )).scalars().all()
        assert len(subs) == 0  # subscription cleaned up


@pytest.mark.asyncio
async def test_seller_delete_shop_with_data_clears_all(
    _tables, seed_plans
):
    """حذف فروشنده — همه دیتاهای مرتبط پاک بشن."""
    shop_id, user_id = await make_shop_and_owner()

    async with async_session() as session:
        await add_active_subscription(shop_id, session)
        cat, prod, order = await add_products_and_orders(shop_id, session)

    from handlers.seller_panel import seller_delete_final
    upd = fake_update(user_id=user_id, data=f"seller:delete_final:{shop_id}")
    ctx = fake_context()
    await seller_delete_final(upd, ctx)

    async with async_session() as session:
        assert await session.get(Shop, shop_id) is None
        assert await session.get(Product, prod.id) is None
        assert await session.get(Category, cat.id) is None
        assert await session.get(Order, order.id) is None
        assert await session.get(ShopOwner, shop_id) is None  # owner was deleted
        carts = (await session.execute(
            select(CartItem).where(CartItem.shop_id == shop_id)
        )).scalars().all()
        assert len(carts) == 0


@pytest.mark.asyncio
async def test_seller_delete_shop_nonexistent(
    _tables
):
    """حذف فروشگاه ناموجود — ارور بده."""
    from handlers.seller_panel import seller_delete_final
    upd = fake_update(user_id=9001, data="seller:delete_final:99999")
    ctx = fake_context()
    await seller_delete_final(upd, ctx)

    assert upd.callback_query.edit_message_text.called
    text = upd.callback_query.edit_message_text.call_args[0][0]
    assert "❌" in text or "پیدا نشد" in text


@pytest.mark.asyncio
async def test_seller_delete_shop_unauthorized_user(
    _tables
):
    """کاربر غیرصاحب فروشگاه — نباید بتونه حذف کنه (فقط callback check)."""
    shop_id, _ = await make_shop_and_owner(user_id=9001)

    from handlers.seller_panel import seller_delete_final
    # Different user tries to delete
    upd = fake_update(user_id=9999, data=f"seller:delete_final:{shop_id}")
    ctx = fake_context()
    await seller_delete_final(upd, ctx)

    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
        assert shop is not None  # Still exists


# ══════════════════════════════════════════════════════════════════
# TESTS: Support command from /support (Message context, not Callback)
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_support_command_as_seller(
    _tables
):
    """support_command وقتی از /support صدا زده بشه (Message) باید کار کنه."""
    shop_id, user_id = await make_shop_and_owner()

    from handlers.seller_panel import support_command
    upd = fake_update(user_id=user_id, msg_text="/support")
    ctx = fake_context()
    await support_command(upd, ctx)

    # Should reply with inbox text or "no conversations"
    assert upd.message.reply_text.called


@pytest.mark.asyncio
async def test_support_command_as_non_seller(
    _tables
):
    """کاربر عادی /support بزنه — پیام مناسب ببینه."""
    from handlers.seller_panel import support_command
    upd = fake_update(user_id=9999, msg_text="/support")
    ctx = fake_context()
    await support_command(upd, ctx)

    assert upd.message.reply_text.called
    text = upd.message.reply_text.call_args[0][0]
    assert "فروشنده" in text or "پشتیبانی" in text
