"""تست مسیر کوتاه فروشنده: ثبت‌نام ۳ قدمی، فعال‌سازی فوری، اولین محصول، و ارسال سفارش با کمترین کلیک."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from telegram.ext import ConversationHandler

import config
from database.db import async_session
from database.models import Category, Order, OrderStatus, Product, Shop, ShopOwner, ShopSubscription, User
from handlers import order as order_h
from handlers import seller_registration as reg
from handlers.admin import products as products_h
from handlers.admin.orders import order_detail_keyboard
from services.order_service import transition_order
from utils.crypto import safe_decrypt, safe_encrypt

SELLER_ID = 7001
ADMIN_ID = 1


def make_context():
    bot = AsyncMock()
    bot.username = "testbot"
    bot.token = "123:TEST"
    return SimpleNamespace(user_data={}, bot=bot)


def message_update(text=None, contact=None, user_id=SELLER_ID):
    message = SimpleNamespace(text=text, contact=contact, photo=[], reply_text=AsyncMock())
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id, first_name="نرگس", username="narges"),
        effective_chat=SimpleNamespace(id=user_id),
        effective_message=message,
        message=message,
        callback_query=None,
    )


def callback_update(data, user_id=SELLER_ID):
    message = SimpleNamespace(chat_id=user_id, delete=AsyncMock(), reply_text=AsyncMock())
    query = SimpleNamespace(
        data=data, answer=AsyncMock(), edit_message_text=AsyncMock(),
        edit_message_reply_markup=AsyncMock(), message=message,
    )
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id, first_name="نرگس", username="narges"),
        effective_chat=SimpleNamespace(id=user_id),
        effective_message=message,
        message=None,
        callback_query=query,
    )


def buttons(markup):
    return [(b.text, b.callback_data) for row in markup.inline_keyboard for b in row]


async def register(ctx, with_card=True):
    assert await reg.seller_registration_start(callback_update("seller_reg:start"), ctx) == reg.ASK_NAME
    assert await reg.ask_name(message_update("گل‌فروشی نرگس"), ctx) == reg.ASK_PHONE
    assert await reg.ask_phone(message_update("۰۹۱۲۳۴۵۶۷۸۹"), ctx) == reg.ASK_CARD_NUMBER
    if with_card:
        assert await reg.ask_card_number(message_update("6037 9912 3456 7890"), ctx) == reg.ASK_CARD_HOLDER
        return await reg.ask_card_holder(message_update("نرگس احمدی"), ctx)
    return await reg.skip_card(callback_update("seller_reg:skip_card"), ctx)


async def get_shop():
    async with async_session() as session:
        owner = (await session.execute(select(ShopOwner).where(ShopOwner.user_id == SELLER_ID))).scalar_one()
        return await session.get(Shop, owner.shop_id)


# ─── ثبت‌نام ────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("09123456789", "09123456789"),
    ("۰۹۱۲۳۴۵۶۷۸۹", "09123456789"),
    ("+989123456789", "09123456789"),
    ("989123456789", "09123456789"),
    ("0912 345 6789", "09123456789"),
    ("9123456789", "09123456789"),
    ("02112345678", None),
    ("0912345678", None),
    ("سلام", None),
])
def test_normalize_phone(raw, expected):
    assert reg.normalize_phone(raw) == expected


async def test_registration_activates_shop_immediately_with_trial(monkeypatch):
    monkeypatch.setattr(config, "AUTO_APPROVE_SHOPS", True)
    monkeypatch.setattr(config, "ADMIN_IDS", {ADMIN_ID})
    ctx = make_context()

    assert await register(ctx) == ConversationHandler.END

    shop = await get_shop()
    assert (shop.status, shop.is_active, shop.phone) == ("active", True, "09123456789")
    assert safe_decrypt(shop.card_number) == "6037991234567890"
    assert safe_decrypt(shop.card_holder_name) == "نرگس احمدی"
    async with async_session() as session:
        sub = (await session.execute(select(ShopSubscription).where(ShopSubscription.shop_id == shop.id))).scalar_one()
    assert sub.is_trial and sub.is_active

    # فروشنده لینک فروشگاه و دکمه‌ی «اولین محصول» رو می‌گیره؛ ادمین فقط باخبر می‌شه
    sent = {c.args[0]: c for c in ctx.bot.send_message.await_args_list}
    seller_msg = sent[SELLER_ID]
    assert f"start=shop_{shop.id}" in seller_msg.args[1]
    assert ("➕ افزودن اولین محصول", "admin:products:add") in buttons(seller_msg.kwargs["reply_markup"])
    assert buttons(sent[ADMIN_ID].kwargs["reply_markup"]) == [
        ("🔎 مشاهده و مدیریت فروشگاه", f"admin:shops:edit:{shop.id}")
    ]
    assert ctx.user_data == {}


async def test_registration_without_card_points_seller_to_payment_settings(monkeypatch):
    monkeypatch.setattr(config, "AUTO_APPROVE_SHOPS", True)
    ctx = make_context()

    assert await register(ctx, with_card=False) == ConversationHandler.END

    shop = await get_shop()
    assert shop.status == "active" and shop.card_number is None
    seller_msg = next(c for c in ctx.bot.send_message.await_args_list if c.args[0] == SELLER_ID)
    assert ("💳 ثبت شماره کارت", "seller:payment_settings") in buttons(seller_msg.kwargs["reply_markup"])


async def test_registration_waits_for_admin_when_auto_approve_is_off(monkeypatch):
    monkeypatch.setattr(config, "AUTO_APPROVE_SHOPS", False)
    monkeypatch.setattr(config, "ADMIN_IDS", {ADMIN_ID})
    ctx = make_context()

    await register(ctx)

    shop = await get_shop()
    assert shop.status == "draft"
    async with async_session() as session:
        assert (await session.execute(select(ShopSubscription))).first() is None
    admin_msg = next(c for c in ctx.bot.send_message.await_args_list if c.args[0] == ADMIN_ID)
    assert (f"admin:seller:approve:{shop.id}" in [d for _, d in buttons(admin_msg.kwargs["reply_markup"])])


async def test_invalid_inputs_keep_the_same_step():
    ctx = make_context()
    assert await reg.ask_name(message_update("x"), ctx) == reg.ASK_NAME
    ctx.user_data["seller_shop_name"] = "فروشگاه"
    assert await reg.ask_phone(message_update("12345"), ctx) == reg.ASK_PHONE
    assert await reg.ask_card_number(message_update("1234"), ctx) == reg.ASK_CARD_NUMBER


async def test_existing_seller_is_not_registered_twice(monkeypatch):
    monkeypatch.setattr(config, "AUTO_APPROVE_SHOPS", True)
    await register(make_context())
    assert await reg.seller_registration_start(callback_update("seller_reg:start"), make_context()) == ConversationHandler.END
    async with async_session() as session:
        assert len((await session.execute(select(Shop))).all()) == 1


# ─── اولین محصول ───────────────────────────────────────────────

async def test_first_product_needs_no_category_setup(monkeypatch):
    monkeypatch.setattr(config, "AUTO_APPROVE_SHOPS", True)
    monkeypatch.setattr(products_h, "download_and_store_multiple", AsyncMock(return_value=[]))
    await register(make_context())
    shop = await get_shop()
    ctx = make_context()

    assert await products_h.start_add_product(callback_update("admin:products:add"), ctx) == products_h.ASK_NAME
    assert await products_h.add_name(message_update("دسته گل رز"), ctx) == products_h.ASK_DESC
    assert await products_h.add_desc(message_update("-"), ctx) == products_h.ASK_PRICE
    # تنها دسته‌بندی خودکار انتخاب می‌شه؛ قیمت با ارقام فارسی و جداکننده هم قبوله
    assert await products_h.add_price(message_update("۴۵۰٬۰۰۰"), ctx) == products_h.ASK_STOCK
    assert await products_h.add_stock(message_update("۱۰"), ctx) == products_h.ASK_PHOTO
    done = callback_update("admin:products:add:nophoto")
    assert await products_h.add_photo_button(done, ctx) == ConversationHandler.END

    async with async_session() as session:
        product = (await session.execute(select(Product).where(Product.shop_id == shop.id))).scalar_one()
        category = await session.get(Category, product.category_id)
    assert (product.name, product.price, product.stock, product.description) == ("دسته گل رز", 450000, 10, None)
    assert category.name == products_h.DEFAULT_CATEGORY_NAME
    assert f"start=product_{product.id}" in done.effective_message.reply_text.await_args.args[0]


# ─── سفارش با کمترین کلیک ──────────────────────────────────────

async def make_paid_order() -> int:
    async with async_session() as session:
        shop = Shop(name="فروشگاه", status="active", is_active=True, card_number=safe_encrypt("6037991234567890"))
        session.add(shop)
        await session.flush()
        session.add(User(user_id=5001, first_name="سارا"))
        order = Order(
            shop_id=shop.id, user_id=5001, tracking_code="T1", total_price=1000, status=OrderStatus.PAID,
            payment_method="cod", shipping_address="تهران", phone="0912",
        )
        session.add(order)
        await session.commit()
        return order.id


async def test_seller_can_ship_right_after_payment_is_approved():
    order_id = await make_paid_order()
    async with async_session() as session:
        order = await session.get(Order, order_id)

    actions = [d for _, d in buttons(order_detail_keyboard(order, "admin:orders:pending:0"))]
    assert f"admin:orders:status:{order_id}:shipped" in actions
    assert f"admin:orders:tracking:{order_id}" in actions
    assert actions.count(f"admin:orders:status:{order_id}:cancelled") == 1

    order = await transition_order(order_id, OrderStatus.SHIPPED, actor="seller")
    assert order.status == OrderStatus.SHIPPED


async def test_checkout_stops_early_when_shop_has_no_card(monkeypatch):
    async with async_session() as session:
        shop = Shop(name="بدون کارت", status="active", is_active=True)
        session.add(shop)
        await session.flush()
        session.add(ShopOwner(user_id=SELLER_ID, shop_id=shop.id))
        session.add(User(user_id=5001, first_name="سارا", current_shop_id=shop.id))
        await session.commit()
        shop_id = shop.id
    monkeypatch.setattr(order_h, "_check_blocked", AsyncMock(return_value=False))
    monkeypatch.setattr(order_h, "_check_abandoned_limit", AsyncMock(return_value=False))
    monkeypatch.setattr(order_h, "get_current_shop_id", AsyncMock(return_value=shop_id))
    notifier = SimpleNamespace(send_to_seller=AsyncMock())
    monkeypatch.setattr(order_h, "get_notification_service", lambda bot: notifier)
    update = callback_update("order:start", user_id=5001)

    start_checkout = getattr(order_h.start_checkout, "__wrapped__", order_h.start_checkout)
    assert await start_checkout(update, make_context()) == ConversationHandler.END

    assert "اطلاعات پرداخت" in update.callback_query.edit_message_text.await_args.args[0]
    assert notifier.send_to_seller.await_args.args[0] == shop_id


# ─── کاربر اول روی دیتابیس تازه ────────────────────────────────

async def test_first_user_can_start_on_a_fresh_database():
    """روی دیتابیس بدون هیچ فروشگاهی، /start نباید به‌خاطر فروشگاه پیش‌فرض (شماره ۱) بشکنه."""
    from handlers.start import register_user

    tg_user = SimpleNamespace(id=9001, first_name="سارا", last_name=None, username="sara")
    await register_user(tg_user)

    async with async_session() as session:
        user = await session.get(User, 9001)
    assert user is not None and user.current_shop_id is None


# ─── رسید متنی و جزئیات سفارش مشتری (باگ‌هایی که فقط روی سرور واقعی دیده شد) ───

async def test_text_receipt_without_photo_is_accepted(monkeypatch):
    """مشتری به‌جای عکس، شماره تراکنش می‌فرسته؛ نباید با UnboundLocalError بشکنه."""
    order_id = await make_paid_order()
    async with async_session() as session:
        order = await session.get(Order, order_id)
        order.status = OrderStatus.PENDING_PAYMENT
        order.payment_method = "card_to_card"
        await session.commit()
        shop_id = order.shop_id
    notify = AsyncMock()
    monkeypatch.setattr(order_h, "_notify_seller_receipt", notify)
    update = message_update("TX-884412", user_id=5001)
    update.message.caption = None
    update.message.photo = []
    context = make_context()
    context.user_data["card_order_id"] = order_id

    assert await order_h.handle_card_receipt(update, context) == ConversationHandler.END

    notify.assert_awaited_once()
    assert notify.await_args.args[1:3] == (order_id, shop_id)
    async with async_session() as session:
        assert (await session.get(Order, order_id)).payment_receipt_at is not None


async def test_customer_order_detail_shows_status_history(monkeypatch):
    order_id = await make_paid_order()
    await transition_order(order_id, OrderStatus.CONFIRMED, actor="seller")
    monkeypatch.setattr(order_h, "get_current_shop_id", AsyncMock(return_value=(await _shop_id_of(order_id))))
    update = callback_update(f"order:detail:{order_id}", user_id=5001)

    detail = getattr(order_h.order_detail_customer, "__wrapped__", order_h.order_detail_customer)
    await detail(update, make_context())

    shown = update.callback_query.edit_message_text.await_args.args[0]
    assert "تاریخچه وضعیت" in shown


async def _shop_id_of(order_id):
    async with async_session() as session:
        return (await session.get(Order, order_id)).shop_id


# ─── گالری عکس‌های وب‌محور (محصولاتی که عکسشون از سایت یا ایمپورت اومده) ───

async def test_gallery_shows_previews_not_file_paths(monkeypatch):
    from database.models import ProductImage

    await register(make_context())
    shop = await get_shop()
    async with async_session() as session:
        cat = Category(name="تیشرت", shop_id=shop.id)
        session.add(cat)
        await session.flush()
        product = Product(name="تیشرت تست", price=2000000, stock=3, category_id=cat.id, shop_id=shop.id)
        session.add(product)
        await session.flush()
        session.add(ProductImage(product_id=product.id, file_id="web_x.jpg", local_url="/api/product-image-file/x.jpg", sort_order=1))
        await session.commit()
        product_id = product.id
    monkeypatch.setattr(config, "WEBSITE_URL", "http://example.test")
    update = callback_update(f"admin:products:gallery:{product_id}")
    context = make_context()

    await products_h.gallery_list(update, context)

    shown = update.callback_query.edit_message_text.await_args.args[0]
    assert "/api/product-image-file" not in shown
    album = context.bot.send_media_group.await_args.kwargs["media"]
    assert [m.media for m in album] == ["http://example.test/api/product-image-file/x.jpg"]
