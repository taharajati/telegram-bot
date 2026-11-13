"""تست مسیر کوتاه فروشنده: ثبت‌نام ۳ قدمی، فعال‌سازی فوری، اولین محصول، و ارسال سفارش با کمترین کلیک."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from telegram.ext import ConversationHandler

import config
from database.db import async_session
from database.models import Category, Order, OrderItem, OrderStatus, Product, Shop, ShopOwner, ShopSubscription, User, utcnow
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
        effective_user=SimpleNamespace(id=user_id, first_name="نرگس", last_name=None, username="narges"),
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
        effective_user=SimpleNamespace(id=user_id, first_name="نرگس", last_name=None, username="narges"),
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


# ─── لینک‌های مستقیم (بایو اینستاگرام): start=product_N و start=category_N ───

async def _shop_with_product():
    await register(make_context())
    shop = await get_shop()
    async with async_session() as session:
        cat = Category(name="تیشرت", shop_id=shop.id)
        session.add(cat)
        await session.flush()
        product = Product(name="تیشرت تست", price=2000000, stock=3, category_id=cat.id, shop_id=shop.id)
        session.add(product)
        await session.commit()
        return shop.id, cat.id, product.id


async def test_product_deep_link_opens_the_product():
    from handlers import start as start_h

    _, _, product_id = await _shop_with_product()
    update = message_update(None, user_id=5555)
    ctx = make_context()
    ctx.args = [f"product_{product_id}"]

    await start_h.start_command(update, ctx)

    sent = ctx.bot.send_message.await_args.kwargs
    assert "تیشرت تست" in sent["text"]
    assert any(b.callback_data.startswith("cart:add:") for row in sent["reply_markup"].inline_keyboard for b in row)


async def test_category_deep_link_opens_the_category():
    from handlers import start as start_h

    _, category_id, _ = await _shop_with_product()
    update = message_update(None, user_id=5556)
    ctx = make_context()
    ctx.args = [f"category_{category_id}"]

    await start_h.start_command(update, ctx)

    assert update.message.reply_text.await_count >= 1


# ─── لیست محصولات و صفحه‌ی محصول ───

async def test_product_list_sort_and_stock_filter_do_not_crash():
    from handlers import menu as menu_h

    shop_id, category_id, _ = await _shop_with_product()
    async with async_session() as session:
        session.add(Product(name="کراپ تاپ ارزون", price=500000, stock=0, category_id=category_id, shop_id=shop_id))
        await session.commit()
    context = make_context()
    context.user_data["current_shop_id"] = shop_id

    async def open_list(action):
        update = callback_update(f"cat:{action}:{category_id}:0", user_id=5600)
        shown = getattr(menu_h.show_products, "__wrapped__", menu_h.show_products)
        from unittest.mock import patch
        with patch.object(menu_h, "get_current_shop_id", AsyncMock(return_value=shop_id)):
            await shown(update, context)
        return update.callback_query.edit_message_text.await_args

    first = await open_list("open")
    assert "ارزان‌ترین" not in first.args[0] and "جدیدترین" in first.args[0]
    second = await open_list("sort")
    assert "ارزان‌ترین" in second.args[0]
    labels = [b.text for row in second.kwargs["reply_markup"].inline_keyboard for b in row]
    assert any("تیشرت تست" in t for t in labels) and any(t.startswith("⛔") for t in labels)
    await open_list("stock")
    assert context.user_data["only_available"] is True


async def test_product_screen_is_one_photo_message_with_gallery_navigation():
    from database.models import ProductImage
    from handlers import menu as menu_h

    shop_id, category_id, product_id = await _shop_with_product()
    async with async_session() as session:
        product = await session.get(Product, product_id)
        product.image_file_id = "AgAC-main"
        session.add(ProductImage(product_id=product_id, file_id="AgAC-second", sort_order=1))
        await session.commit()

    screen = await menu_h.load_product_screen(product_id, 5700, category_id, 0)
    assert screen["photos"] == ["AgAC-main", "AgAC-second"]
    assert "تیشرت تست" in screen["caption"] and len(screen["caption"]) <= 1024
    data = [b.callback_data for row in screen["keyboard"].inline_keyboard for b in row]
    assert f"prod:img:{product_id}:1:{category_id}:0" in data and f"cart:add:{product_id}:{category_id}:0" in data

    bot = AsyncMock()
    await menu_h.send_product_screen(bot, 5700, screen)
    assert bot.send_photo.await_count == 1 and bot.send_media_group.await_count == 0

    update = callback_update(f"prod:img:{product_id}:1:{category_id}:0", user_id=5700)
    update.callback_query.edit_message_media = AsyncMock()
    await menu_h.show_product_photo(update, make_context())
    media = update.callback_query.edit_message_media.await_args.kwargs["media"]
    assert media.media == "AgAC-second"


async def test_add_to_cart_on_product_screen_only_updates_buttons():
    from handlers import cart as cart_h

    shop_id, category_id, product_id = await _shop_with_product()
    update = callback_update(f"cart:add:{product_id}:{category_id}:0", user_id=5800)
    update.callback_query.message.photo = ["x"]
    update.callback_query.edit_message_reply_markup = AsyncMock()
    from unittest.mock import patch
    add = getattr(cart_h.add_to_cart, "__wrapped__", cart_h.add_to_cart)
    with patch.object(cart_h, "get_current_shop_id", AsyncMock(return_value=shop_id)):
        await add(update, make_context())

    assert update.callback_query.answer.await_args.args[0].startswith("✅")
    update.callback_query.message.reply_text.assert_not_awaited()
    keyboard = update.callback_query.edit_message_reply_markup.await_args.kwargs["reply_markup"]
    assert any("سبد (" in b.text for row in keyboard.inline_keyboard for b in row)


# ─── پرداخت و رسید ───

async def _card_order(status=OrderStatus.PENDING_PAYMENT):
    order_id = await make_paid_order()
    async with async_session() as session:
        order = await session.get(Order, order_id)
        order.status = status
        order.payment_method = "card_to_card"
        await session.commit()
    return order_id


async def test_receipt_for_a_cancelled_order_is_refused_with_a_clear_message(monkeypatch):
    from services.order_service import attach_card_receipt

    order_id = await _card_order(OrderStatus.CANCELLED)
    with pytest.raises(ValueError) as error:
        await attach_card_receipt(order_id, receipt_file_id="", receipt_caption="TX-1234")
    assert "لغو شده" in str(error.value) and "سبدت سر جاشه" in str(error.value)


async def test_expired_unpaid_order_notifies_the_customer(monkeypatch):
    from datetime import timedelta
    from services import payment as payment_svc

    order_id = await _card_order()
    async with async_session() as session:
        order = await session.get(Order, order_id)
        order.created_at = utcnow() - timedelta(minutes=payment_svc.CARD_PAYMENT_MINUTES + 5)
        await session.commit()
    bot = AsyncMock()

    assert await payment_svc.auto_cancel_unpaid_orders(bot=bot) == 1

    assert bot.send_message.await_args.args[0] == 5001
    assert "مهلت پرداخت" in bot.send_message.await_args.args[1]


async def test_order_with_a_receipt_is_never_cancelled_for_missing_receipt():
    from datetime import timedelta
    from services import payment as payment_svc
    from services.order_service import attach_card_receipt

    order_id = await _card_order()
    await attach_card_receipt(order_id, receipt_file_id="", receipt_caption="TX-884412")
    async with async_session() as session:
        order = await session.get(Order, order_id)
        order.created_at = utcnow() - timedelta(hours=3)
        await session.commit()

    assert await payment_svc.auto_cancel_unpaid_orders() == 0
    async with async_session() as session:
        assert (await session.get(Order, order_id)).status == OrderStatus.PENDING_PAYMENT


async def test_retry_after_cancel_does_not_oversell():
    from services import payment as payment_svc

    order_id = await _card_order(OrderStatus.CANCELLED)
    async with async_session() as session:
        order = await session.get(Order, order_id)
        category = Category(name="تست", shop_id=order.shop_id)
        session.add(category)
        await session.flush()
        product = Product(name="تک‌عدد", price=1000, stock=0, category_id=category.id, shop_id=order.shop_id)
        session.add(product)
        await session.flush()
        session.add(OrderItem(order_id=order_id, product_id=product.id, product_name="تک‌عدد", quantity=2, unit_price=1000))
        await session.commit()

    assert await payment_svc.retry_card_receipt(order_id, receipt_text="TX-99999") is False
    async with async_session() as session:
        assert (await session.get(Order, order_id)).status == OrderStatus.CANCELLED


# ─── پنل فروشنده و ارسال سفارش ───

async def test_typing_a_tracking_code_ships_the_order_and_tells_the_customer():
    from handlers.admin import orders as admin_orders

    order_id = await make_paid_order()
    context = make_context()
    context.user_data["tracking_order_id"] = order_id
    save = getattr(admin_orders.save_tracking_number, "__wrapped__", admin_orders.save_tracking_number)

    await save(message_update("1234567890", user_id=SELLER_ID), context)

    async with async_session() as session:
        order = await session.get(Order, order_id)
    assert order.status == OrderStatus.SHIPPED and order.tracking_number == "1234567890"
    sent = context.bot.send_message.await_args.kwargs
    assert sent["chat_id"] == 5001 and "ارسال شد" in sent["text"] and "1234567890" in sent["text"]
    assert sent["reply_markup"].inline_keyboard[0][0].callback_data == f"customer:confirm_delivery:{order_id}"


async def test_seller_panel_has_few_buttons_and_counts_pending_orders():
    from handlers import seller_panel as panel_h

    await register(make_context())
    shop = await get_shop()
    async with async_session() as session:
        session.add(User(user_id=5001, first_name="سارا"))
        session.add(Order(shop_id=shop.id, user_id=5001, tracking_code="P1", total_price=1000, status=OrderStatus.PAID,
                          payment_method="card_to_card", shipping_address="تهران", phone="0912"))  # منتظر ارسال
        await session.commit()
    text, keyboard = await panel_h._build_seller_panel(SELLER_ID, "testbot")

    flat = [b for row in keyboard.inline_keyboard for b in row]
    assert len(keyboard.inline_keyboard) <= 5 and len(flat) <= 9
    assert any(b.callback_data == "seller:settings" for b in flat)
    assert any("(۱)" in b.text for b in flat) and "۱ سفارش منتظر اقدام" in text
    assert not any(b.callback_data == "seller:delete_shop" for b in flat)  # حذف فروشگاه ته تنظیماته


async def test_one_tap_sold_out_zeroes_available_stock():
    from handlers.admin import products as products_h

    await register(make_context())
    shop = await get_shop()
    async with async_session() as session:
        cat = Category(name="تیشرت", shop_id=shop.id)
        session.add(cat)
        await session.flush()
        product = Product(name="تیشرت", price=1000, stock=5, reserved_stock=2, category_id=cat.id, shop_id=shop.id)
        session.add(product)
        await session.commit()
        product_id = product.id
    update = callback_update(f"admin:products:soldout:{product_id}")
    soldout = getattr(products_h.product_soldout, "__wrapped__", products_h.product_soldout)

    await soldout(update, make_context())

    async with async_session() as session:
        product = await session.get(Product, product_id)
    assert product.available_stock == 0 and product.reserved_stock == 2


def test_short_price_formats_for_buttons():
    from utils.helpers import short_price

    assert short_price(2000000) == "۲ میلیون"
    assert short_price(1500000) == "۱٫۵ میلیون"
    assert short_price(450000) == "۴۵۰ هزار"
    assert short_price(900) == "۹۰۰ تومان"


# ─── لیست و کارت محصول برای فروشنده ───

async def _seller_with_products():
    await register(make_context())
    shop = await get_shop()
    async with async_session() as session:
        cat = Category(name="تیشرت", shop_id=shop.id)
        session.add(cat)
        await session.flush()
        session.add_all([
            Product(name="موجود", price=2000000, stock=10, category_id=cat.id, shop_id=shop.id),
            Product(name="ناموجود", price=450000, stock=0, category_id=cat.id, shop_id=shop.id),
            Product(name="مخفی", price=1000, stock=4, is_active=False, category_id=cat.id, shop_id=shop.id),
        ])
        await session.commit()
        ids = {p.name: p.id for p in (await session.execute(select(Product))).scalars()}
    return shop.id, ids


async def test_seller_product_list_shows_status_counts_and_filters():
    from handlers.admin import products as products_h

    _, ids = await _seller_with_products()
    context = make_context()

    update = callback_update("admin:products:list:0")
    await getattr(products_h.list_products, "__wrapped__", products_h.list_products)(update, context)
    shown = update.callback_query.edit_message_text.await_args
    assert "۳ محصول" in shown.args[0] and "۱ موجود" in shown.args[0] and "۱ ناموجود" in shown.args[0] and "۱ مخفی" in shown.args[0]
    labels = [b.text for row in shown.kwargs["reply_markup"].inline_keyboard for b in row]
    assert any(t.startswith("🟢") and "۲ میلیون" in t for t in labels)
    assert any(t.startswith("⛔") for t in labels) and any(t.startswith("🙈") for t in labels)

    cycle = getattr(products_h.cycle_products_filter, "__wrapped__", products_h.cycle_products_filter)
    update = callback_update("admin:products:filter")
    await cycle(update, context)  # all -> in
    shown = update.callback_query.edit_message_text.await_args
    rows = [b.text for row in shown.kwargs["reply_markup"].inline_keyboard for b in row if b.callback_data.startswith("admin:products:edit:")]
    assert len(rows) == 1 and rows[0].startswith("🟢") and "فیلتر: موجود" in shown.args[0]


async def test_seller_stock_stepper_respects_reserved_stock():
    from handlers.admin import products as products_h

    _, ids = await _seller_with_products()
    product_id = ids["موجود"]
    async with async_session() as session:
        product = await session.get(Product, product_id)
        product.stock, product.reserved_stock = 3, 3
        await session.commit()
    step = getattr(products_h.product_stock_step, "__wrapped__", products_h.product_stock_step)

    down = callback_update(f"admin:products:stk:{product_id}:-1")
    await step(down, make_context())
    async with async_session() as session:
        assert (await session.get(Product, product_id)).stock == 3  # زیر رزرو نمی‌ره
    assert "رزرو" in down.callback_query.answer.await_args.args[0]

    up = callback_update(f"admin:products:stk:{product_id}:1")
    up.callback_query.edit_message_text = AsyncMock()
    await step(up, make_context())
    async with async_session() as session:
        assert (await session.get(Product, product_id)).stock == 4
    card = up.callback_query.edit_message_text.await_args
    assert "<b>۴</b>" in card.args[0] and card.kwargs["parse_mode"] == "HTML"


async def test_product_card_has_photo_status_and_quick_actions():
    from handlers.admin import products as products_h

    _, ids = await _seller_with_products()
    async with async_session() as session:
        product = await session.get(Product, ids["موجود"])
        product.image_file_id = "AgAC-main"
        await session.commit()
    context = make_context()
    update = callback_update(f"admin:products:edit:{ids['موجود']}")
    update.callback_query.message.photo = []
    await getattr(products_h.open_product_edit, "__wrapped__", products_h.open_product_edit)(update, context)

    sent = context.bot.send_photo.await_args.kwargs
    assert sent["photo"] == "AgAC-main" and "🟢" in sent["caption"] and "۲,۰۰۰,۰۰۰" in sent["caption"]
    data = [b.callback_data for row in sent["reply_markup"].inline_keyboard for b in row]
    for expected in (f"admin:products:stk:{ids['موجود']}:1", f"admin:products:stk:{ids['موجود']}:-1",
                     f"admin:products:soldout:{ids['موجود']}", f"admin:products:toggle:{ids['موجود']}",
                     f"admin:products:preview:{ids['موجود']}"):
        assert expected in data
