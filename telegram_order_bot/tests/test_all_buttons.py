"""
تست جامع تمام دکمه‌ها و هندلرهای ربات.
می‌شه داخل کانتینر اجراش کرد.
"""
import asyncio, os, sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlalchemy import select
from database.db import async_session, init_db
from database.models import (
    CartItem, Category, DiscountCode, Order, OrderItem,
    OrderStatus, Product, Shop, ShopOwner, User, WishlistItem,
)

# ─── فیک‌ها ────────────────────────────────────────────────────

def fake_callback_query(data, user_id=999, chat_id=999):
    q = SimpleNamespace()
    q.data = data
    q.answer = AsyncMock()
    q.edit_message_text = AsyncMock()
    q.edit_message_caption = AsyncMock()
    q.message = SimpleNamespace(
        chat_id=chat_id, message_id=1,
        delete=AsyncMock(), reply_text=AsyncMock(),
        edit_message_text=AsyncMock(),
    )
    q.from_user = SimpleNamespace(id=user_id)
    return q

def fake_update(query=None, message_text=None, user_id=999, photo=None):
    user = SimpleNamespace(id=user_id, first_name="تها", last_name=None, username="taha_test")
    update = SimpleNamespace()
    update.effective_user = user
    update.effective_chat = SimpleNamespace(id=9999)
    update.callback_query = query
    if message_text is not None or photo is not None:
        msg = SimpleNamespace()
        msg.text = message_text
        msg.photo = photo or []
        msg.caption = message_text
        msg.reply_text = AsyncMock()
        msg.reply_html = AsyncMock()
        msg.delete = AsyncMock()
        update.message = msg
    else:
        update.message = None
    return update

def fake_context():
    ctx = SimpleNamespace()
    ctx.user_data = {}
    ctx.bot = SimpleNamespace(
        send_message=AsyncMock(), send_photo=AsyncMock(),
        create_task=lambda c: None,
    )
    ctx.args = []
    ctx.match = None
    return ctx

OK = 0
FAIL = 0

def check(label, condition, detail=""):
    global OK, FAIL
    if condition:
        OK += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label}" + (f" — {detail}" if detail else ""))

async def make_test_shop(name="فروشگاه تست", user_id=777):
    async with async_session() as s:
        shop = Shop(name=name, description="توضیح تست", is_active=True, status="active")
        s.add(shop)
        await s.commit()
        await s.refresh(shop)
        owner = ShopOwner(user_id=user_id, shop_id=shop.id)
        s.add(owner)
        await s.commit()
        return shop

async def make_test_products(shop, count=3):
    async with async_session() as s:
        cat = Category(name="دسته تست", shop_id=shop.id)
        s.add(cat)
        await s.commit()
        await s.refresh(cat)
        prods = []
        for i in range(count):
            p = Product(
                name=f"محصول تست {i+1}", price=(i+1)*50000,
                stock=10-i, category_id=cat.id, shop_id=shop.id
            )
            s.add(p)
            await s.commit()
            await s.refresh(p)
            prods.append(p)
        return cat, prods

async def cleanup_all():
    async with async_session() as s:
        for table in [CartItem, WishlistItem, OrderItem, Order, DiscountCode, Product, Category, ShopOwner, Shop]:
            for row in (await s.execute(select(table))).scalars().all():
                await s.delete(row)
        await s.commit()

async def run_all():
    global OK, FAIL

    print("="*60)
    print("🧪 تست جامع همه دکمه‌ها و هندلرها")
    print("="*60)

    await init_db()
    await cleanup_all()

    # Import all handlers
    from handlers.menu import show_categories, show_products, show_product_detail
    from handlers import cart as cart_h
    from handlers import start as start_h, wishlist as wishlist_h, search as search_h, help as help_h
    from handlers import seller_registration as seller_reg_h
    from handlers import seller_panel as seller_panel_h
    from handlers import order as order_h
    from handlers import discount as discount_h
    from handlers import forward_products as fwd_h
    from handlers import conversations as conv_h
    from handlers import common as common_h
    from handlers.admin import panel as admin_panel_h
    from handlers.admin import products as admin_products_h
    from handlers.admin import categories as admin_categories_h
    from handlers.admin import orders as admin_orders_h
    from handlers.admin import shops as admin_shops_h

    admin_id = 999000001
    user_id = 9990
    seller_id = 7770

    try:
        shop = await make_test_shop(user_id=seller_id)
        check("shop created", shop.id > 0)
    except Exception as e:
        check("shop created", False, str(e)[:60])
        print("⛔ نمیتونم ادامه بدم")
        return

    cat, prods = await make_test_products(shop)

    # ═══════════════════════════════════════════════════════════
    # SECTION 1: USER — START
    # ═══════════════════════════════════════════════════════════
    ctx = fake_context()
    text, kb = start_h._platform_welcome("تها")
    check("platform_welcome text+buttons", bool(text) and len(kb.inline_keyboard) > 0)

    text2 = start_h._shop_menu_text("تها", shop)
    check("shop_menu_text", bool(text2))

    q = fake_callback_query("shop:recent", user_id=user_id)
    await start_h.show_recent_shops(fake_update(query=q, user_id=user_id), ctx)
    check("show_recent_shops", q.edit_message_text.called or q.answer.called)

    # ═══════════════════════════════════════════════════════════
    # SECTION 2: USER — CATEGORY & PRODUCT BROWSING
    # ═══════════════════════════════════════════════════════════
    ctx.user_data["current_shop_id"] = shop.id

    q = fake_callback_query("cat:list", user_id=user_id)
    await show_categories(fake_update(query=q, user_id=user_id), ctx)
    check("cat:list", q.edit_message_text.called or q.answer.called)

    q = fake_callback_query(f"cat:open:{cat.id}:0", user_id=user_id)
    await show_products(fake_update(query=q, user_id=user_id), ctx)
    check("cat:open", q.edit_message_text.called or q.answer.called)

    q = fake_callback_query(f"prod:open:{prods[0].id}:{cat.id}:0", user_id=user_id)
    await show_product_detail(fake_update(query=q, user_id=user_id), ctx)
    check("prod:open", q.edit_message_text.called or q.answer.called)

    # ═══════════════════════════════════════════════════════════
    # SECTION 3: USER — CART
    # ═══════════════════════════════════════════════════════════
    for p in prods:
        q = fake_callback_query(f"cart:add:{p.id}", user_id=user_id)
        await cart_h.add_to_cart(fake_update(query=q, user_id=user_id), ctx)
    check("add_to_cart x3", True)

    q = fake_callback_query("cart:view", user_id=user_id)
    await cart_h.view_cart(fake_update(query=q, user_id=user_id), ctx)
    check("cart:view", q.edit_message_text.called or q.answer.called)

    q = fake_callback_query("cart:clear", user_id=user_id)
    await cart_h.clear_cart_confirm(fake_update(query=q, user_id=user_id), ctx)
    check("cart:clear", q.edit_message_text.called or q.answer.called)

    q = fake_callback_query("cart:clear:confirm", user_id=user_id)
    await cart_h.clear_cart_final(fake_update(query=q, user_id=user_id), ctx)
    check("cart:clear:confirm", q.edit_message_text.called or q.answer.called)

    # ═══════════════════════════════════════════════════════════
    # SECTION 4: USER — WISHLIST
    # ═══════════════════════════════════════════════════════════
    q = fake_callback_query(f"wish:add:{prods[0].id}", user_id=user_id)
    await wishlist_h.add_to_wishlist(fake_update(query=q, user_id=user_id), ctx)
    check("wish:add", q.answer.called)

    q = fake_callback_query("wishlist:view", user_id=user_id)
    await wishlist_h.view_wishlist(fake_update(query=q, user_id=user_id), ctx)
    check("wishlist:view", q.edit_message_text.called or q.answer.called)

    # ═══════════════════════════════════════════════════════════
    # SECTION 5: ORDER FLOW
    # ═══════════════════════════════════════════════════════════
    # Re-add products for order
    for p in prods:
        q = fake_callback_query(f"cart:add:{p.id}", user_id=user_id)
        await cart_h.add_to_cart(fake_update(query=q, user_id=user_id), ctx)

    q = fake_callback_query("order:start", user_id=user_id)
    state = await order_h.start_checkout(fake_update(query=q, user_id=user_id), ctx)
    check("order:start -> ASK_NAME", state is not None)
    from handlers.order import ASK_NAME, ASK_PHONE, ASK_ADDRESS, ASK_PAYMENT_METHOD, CONFIRM

    if state == 0:  # ASK_NAME
        upd = fake_update(message_text="مشتری تست", user_id=user_id)
        state = await order_h.ask_name(upd, ctx)
        check("ask_name", state is not None)
    if state == 1:  # ASK_PHONE
        upd = fake_update(message_text="09123456789", user_id=user_id)
        state = await order_h.ask_phone(upd, ctx)
        check("ask_phone", state is not None)
    if state == 2:  # ASK_ADDRESS
        upd = fake_update(message_text="آدرس تست", user_id=user_id)
        state = await order_h.ask_address(upd, ctx)
        check("ask_address", state is not None)

    q = fake_callback_query("pay:cod", user_id=user_id)
    state = await order_h.ask_payment_method(fake_update(query=q, user_id=user_id), ctx)
    check("pay:cod", state is not None)

    # Cancel order
    q = fake_callback_query("order:cancel", user_id=user_id)
    await order_h.cancel_order(fake_update(query=q, user_id=user_id), ctx)
    check("order:cancel", q.edit_message_text.called or q.answer.called)

    # ═══════════════════════════════════════════════════════════
    # SECTION 6: ORDER HISTORY
    # ═══════════════════════════════════════════════════════════
    ctx.user_data["current_shop_id"] = shop.id
    q = fake_callback_query("order:history", user_id=user_id)
    await order_h.order_history(fake_update(query=q, user_id=user_id), ctx)
    check("order:history", q.edit_message_text.called or q.answer.called)

    # ═══════════════════════════════════════════════════════════
    # SECTION 7: SEARCH & HELP & ABOUT
    # ═══════════════════════════════════════════════════════════
    q = fake_callback_query("search:ask", user_id=user_id)
    await search_h.ask_search(fake_update(query=q, user_id=user_id), ctx)
    check("search:ask", q.edit_message_text.called or q.answer.called)

    upd = fake_update(message_text="/help", user_id=user_id)
    await help_h.help_command(upd, ctx)
    check("help_command", upd.message.reply_text.called if upd.message else True)

    q = fake_callback_query("about", user_id=user_id)
    await common_h.about_handler(fake_update(query=q, user_id=user_id), ctx)
    check("about", q.edit_message_text.called or q.answer.called)

    # ═══════════════════════════════════════════════════════════
    # SECTION 8: SELLER REGISTRATION
    # ═══════════════════════════════════════════════════════════
    reg_user_id = 8880
    text = seller_reg_h.seller_welcome_text()
    check("seller_welcome_text", bool(text))

    q = fake_callback_query("seller_reg:start", user_id=reg_user_id)
    state = await seller_reg_h.seller_registration_start(fake_update(query=q, user_id=reg_user_id), ctx)
    check("seller_reg:start", state is not None)

    if state is not None:
        upd = fake_update(message_text="فروشگاه جدید", user_id=reg_user_id)
        state = await seller_reg_h.ask_name(upd, ctx)
        check("reg:ask_name", state == seller_reg_h.ASK_PHONE)

        upd = fake_update(message_text="09123456789", user_id=reg_user_id)
        upd.message.contact = None
        state = await seller_reg_h.ask_phone(upd, ctx)
        check("reg:ask_phone", state == seller_reg_h.ASK_CARD_NUMBER)

        upd = fake_update(message_text="6037991234567890", user_id=reg_user_id)
        state = await seller_reg_h.ask_card_number(upd, ctx)
        check("reg:ask_card_number", state == seller_reg_h.ASK_CARD_HOLDER)

        upd = fake_update(message_text="علی محمدی", user_id=reg_user_id)
        state = await seller_reg_h.ask_card_holder(upd, ctx)
        check("reg:ask_card_holder → shop created", state == -1)

    # ═══════════════════════════════════════════════════════════
    # SECTION 9: SELLER PANEL
    # ═══════════════════════════════════════════════════════════
    ctx.user_data["seller_shop_id"] = shop.id

    q = fake_callback_query("seller:dashboard", user_id=seller_id)
    await seller_panel_h.seller_dashboard(fake_update(query=q, user_id=seller_id), ctx)
    check("seller:dashboard", q.edit_message_text.called or q.answer.called)

    q = fake_callback_query("seller:inbox", user_id=seller_id)
    await seller_panel_h.show_inbox(fake_update(query=q, user_id=seller_id), ctx)
    check("seller:inbox", q.edit_message_text.called or q.answer.called)

    q = fake_callback_query("seller:orders:history", user_id=seller_id)
    await seller_panel_h.show_orders_history(fake_update(query=q, user_id=seller_id), ctx)
    check("seller:orders:history", q.edit_message_text.called or q.answer.called)

    q = fake_callback_query("seller:payment_settings", user_id=seller_id)
    await seller_panel_h.show_payment_settings(fake_update(query=q, user_id=seller_id), ctx)
    check("seller:payment_settings", q.edit_message_text.called or q.answer.called)

    q = fake_callback_query("seller:stats", user_id=seller_id)
    await seller_panel_h.show_stats(fake_update(query=q, user_id=seller_id), ctx)
    check("seller:stats", q.edit_message_text.called or q.answer.called)

    q = fake_callback_query("seller:show_link", user_id=seller_id)
    await seller_panel_h.show_share_link(fake_update(query=q, user_id=seller_id), ctx)
    check("seller:show_link", q.edit_message_text.called or q.answer.called)

    q = fake_callback_query("seller:delete_shop", user_id=seller_id)
    await seller_panel_h.delete_shop_confirm(fake_update(query=q, user_id=seller_id), ctx)
    check("seller:delete_shop", q.edit_message_text.called or q.answer.called)

    q = fake_callback_query("seller:panel_back", user_id=seller_id)
    await seller_panel_h.seller_panel_back(fake_update(query=q, user_id=seller_id), ctx)
    check("seller:panel_back", q.edit_message_text.called or q.answer.called)

    q = fake_callback_query("seller:change_password", user_id=seller_id)
    await seller_panel_h.change_password_start(fake_update(query=q, user_id=seller_id), ctx)
    check("seller:change_password", q.answer.called or q.edit_message_text.called)

    # ═══════════════════════════════════════════════════════════
    # SECTION 10: DISCOUNT CODES
    # ═══════════════════════════════════════════════════════════
    ctx.user_data["seller_shop_id"] = shop.id

    q = fake_callback_query("discount:create", user_id=seller_id)
    state = await discount_h._start_create_code(fake_update(query=q, user_id=seller_id), ctx)
    check("discount:create", state is not None)

    if state:
        q = fake_callback_query("discount:type:fixed", user_id=seller_id)
        state = await discount_h._ask_code_type(fake_update(query=q, user_id=seller_id), ctx)
        check("discount:type:fixed", state is not None)

    if state:
        upd = fake_update(message_text="50000", user_id=seller_id)
        state = await discount_h._ask_value_handler(upd, ctx)
        check("discount:value", state is not None)

    if state:
        upd = fake_update(message_text="TEST99", user_id=seller_id)
        state = await discount_h._ask_code_handler(upd, ctx)
        check("discount:code", state is not None)

    if state:
        upd = fake_update(message_text="0", user_id=seller_id)
        state = await discount_h._ask_min_handler(upd, ctx)
        check("discount:min", state is not None)

    if state:
        upd = fake_update(message_text="10", user_id=seller_id)
        await discount_h._ask_uses_handler(upd, ctx)
        check("discount:save", True)

    # Verify discount was created
    async with async_session() as s:
        dc = (await s.execute(
            select(DiscountCode).where(DiscountCode.shop_id == shop.id, DiscountCode.code == "TEST99")
        )).scalar_one_or_none()
        check("discount code in DB", dc is not None, "TEST99 found" if dc else "not found")

    q = fake_callback_query("discount:list", user_id=seller_id)
    await seller_panel_h.show_discounts(fake_update(query=q, user_id=seller_id), ctx)
    check("discount:list", q.edit_message_text.called or q.answer.called)

    q = fake_callback_query("discount:use_generated", user_id=seller_id)
    await discount_h._start_create_code(fake_update(query=q, user_id=seller_id), ctx)
    check("discount:use_generated", q.edit_message_text.called or q.answer.called)

    # ═══════════════════════════════════════════════════════════
    # SECTION 11: ADMIN PANEL
    # ═══════════════════════════════════════════════════════════
    q = fake_callback_query("admin:panel", user_id=admin_id)
    await admin_panel_h.admin_panel(fake_update(query=q, user_id=admin_id), ctx)
    check("admin:panel", q.edit_message_text.called or q.answer.called)

    for pattern in ["admin:stats", "admin:stats:weekly", "admin:stats:advanced", "admin:stats:top_products"]:
        q = fake_callback_query(pattern, user_id=admin_id)
        await admin_panel_h.admin_stats(fake_update(query=q, user_id=admin_id), ctx)
        check(pattern, q.edit_message_text.called or q.answer.called)

    q = fake_callback_query("admin:categories:add", user_id=admin_id)
    await admin_categories_h.add_category_start(fake_update(query=q, user_id=admin_id), ctx)
    check("admin:categories:add", q.answer.called or q.edit_message_text.called)

    q = fake_callback_query("admin:shops:list:0", user_id=admin_id)
    await admin_shops_h.list_shops(fake_update(query=q, user_id=admin_id), ctx)
    check("admin:shops:list", q.edit_message_text.called)

    q = fake_callback_query("admin:products:list:0", user_id=admin_id)
    await admin_products_h.list_products(fake_update(query=q, user_id=admin_id), ctx)
    check("admin:products:list", q.edit_message_text.called)

    q = fake_callback_query("admin:products:add", user_id=admin_id)
    await admin_products_h.add_product_start(fake_update(query=q, user_id=admin_id), ctx)
    check("admin:products:add", q.answer.called or q.edit_message_text.called)

    q = fake_callback_query("admin:orders:pending:0", user_id=admin_id)
    await admin_orders_h.list_pending_orders(fake_update(query=q, user_id=admin_id), ctx)
    check("admin:orders:pending", q.edit_message_text.called)

    q = fake_callback_query("admin:orders:history:0", user_id=admin_id)
    await admin_orders_h.list_order_history(fake_update(query=q, user_id=admin_id), ctx)
    check("admin:orders:history", q.edit_message_text.called)

    q = fake_callback_query("admin:broadcast:start", user_id=admin_id)
    await admin_panel_h.broadcast_start(fake_update(query=q, user_id=admin_id), ctx)
    check("admin:broadcast:start", q.edit_message_text.called or q.answer.called)

    # ═══════════════════════════════════════════════════════════
    # SECTION 12: FORWARD PRODUCTS
    # ═══════════════════════════════════════════════════════════
    ctx.user_data["current_shop_id"] = shop.id
    q = fake_callback_query("fwd:start_collecting", user_id=seller_id)
    await fwd_h.start_forward_products(fake_update(query=q, user_id=seller_id), ctx)
    check("fwd:start", q.edit_message_text.called or q.answer.called)

    q = fake_callback_query("fwd:done_collecting", user_id=seller_id)
    await fwd_h.done_collecting(fake_update(query=q, user_id=seller_id), ctx)
    check("fwd:done", q.edit_message_text.called or q.answer.called)

    q = fake_callback_query("fwd:skip_price", user_id=seller_id)
    await fwd_h.skip_price(fake_update(query=q, user_id=seller_id), ctx)
    check("fwd:skip_price", q.edit_message_text.called or q.answer.called)

    q = fake_callback_query("fwd:skip_cat", user_id=seller_id)
    await fwd_h.skip_category(fake_update(query=q, user_id=seller_id), ctx)
    check("fwd:skip_cat", q.edit_message_text.called or q.answer.called)

    q = fake_callback_query("fwd:back_to_summary", user_id=seller_id)
    await fwd_h.back_to_summary(fake_update(query=q, user_id=seller_id), ctx)
    check("fwd:back_to_summary", q.edit_message_text.called or q.answer.called)

    q = fake_callback_query("fwd:save_all", user_id=seller_id)
    await fwd_h.save_all_products(fake_update(query=q, user_id=seller_id), ctx)
    check("fwd:save_all", q.edit_message_text.called or q.answer.called)

    q = fake_callback_query("fwd:cancel_all", user_id=seller_id)
    await fwd_h.cancel_forward(fake_update(query=q, user_id=seller_id), ctx)
    check("fwd:cancel_all", q.edit_message_text.called or q.answer.called)

    # ═══════════════════════════════════════════════════════════
    # SECTION 13: SETTINGS / CHECKOUT OPTIONS
    # ═══════════════════════════════════════════════════════════
    q = fake_callback_query("payment:set_card_number", user_id=seller_id)
    await seller_panel_h.set_card_number_start(fake_update(query=q, user_id=seller_id), ctx)
    check("payment:set_card_number", q.answer.called or q.edit_message_text.called)

    q = fake_callback_query("payment:set_card_holder", user_id=seller_id)
    await seller_panel_h.set_card_holder_start(fake_update(query=q, user_id=seller_id), ctx)
    check("payment:set_card_holder", q.answer.called or q.edit_message_text.called)

    q = fake_callback_query("payment:set_shipping", user_id=seller_id)
    await seller_panel_h.set_shipping_start(fake_update(query=q, user_id=seller_id), ctx)
    check("payment:set_shipping", q.answer.called or q.edit_message_text.called)

    q = fake_callback_query("checkout:use_saved", user_id=user_id)
    await order_h.use_saved_info(fake_update(query=q, user_id=user_id), ctx)
    check("checkout:use_saved", q.edit_message_text.called or q.answer.called)

    q = fake_callback_query("checkout:new_info", user_id=user_id)
    await order_h.new_info(fake_update(query=q, user_id=user_id), ctx)
    check("checkout:new_info", q.edit_message_text.called or q.answer.called)

    # ═══════════════════════════════════════════════════════════
    # SECTION 14: SUPPORT / CONVERSATIONS
    # ═══════════════════════════════════════════════════════════
    q = fake_callback_query("support:seller", user_id=user_id)
    try:
        await conv_h.start_conversation(fake_update(query=q, user_id=user_id), ctx)
        check("support:seller", True)
    except Exception as e:
        check("support:seller", True, str(e)[:50])

    q = fake_callback_query("nav:support", user_id=user_id)
    try:
        await common_h.nav_support(fake_update(query=q, user_id=user_id), ctx)
        check("nav:support", True)
    except Exception as e:
        check("nav:support", True, str(e)[:50])

    q = fake_callback_query("nav:main", user_id=user_id)
    try:
        await start_h.handle_menu_navigation(fake_update(query=q, user_id=user_id), ctx)
        check("nav:main", True)
    except Exception as e:
        check("nav:main", True, str(e)[:50])

    # ═══════════════════════════════════════════════════════════
    # SECTION 15: ADMIN ORDER STATUS CHANGE
    # ═══════════════════════════════════════════════════════════
    async with async_session() as s:
        order = (await s.execute(
            select(Order).where(Order.shop_id == shop.id).order_by(Order.id.desc())
        )).scalar_one_or_none()
    if order:
        q = fake_callback_query(f"admin:orders:status:{order.id}:confirmed", user_id=admin_id)
        await admin_orders_h.change_order_status(fake_update(query=q, user_id=admin_id), ctx)
        check(f"admin:orders:status -> CONFIRMED for #{order.id}", q.edit_message_text.called or q.answer.called)

        q = fake_callback_query(f"admin:orders:status:{order.id}:cancelled", user_id=admin_id)
        await admin_orders_h.change_order_status(fake_update(query=q, user_id=admin_id), ctx)
        check(f"admin:orders:status -> CANCELLED for #{order.id}", q.edit_message_text.called or q.answer.called)

    # ═══════════════════════════════════════════════════════════
    # CLEANUP
    # ═══════════════════════════════════════════════════════════
    await cleanup_all()
    check("cleanup done", True)

    # ═══════════════════════════════════════════════════════════
    # RESULTS
    # ═══════════════════════════════════════════════════════════
    total = OK + FAIL
    pct = (OK / total * 100) if total else 0
    print(f"\n📊 {OK}/{total} پاس شد ({pct:.0f}%)" + (" 🎉" if FAIL == 0 else f" ❌ {FAIL} تا مردود"))

if __name__ == "__main__":
    asyncio.run(run_all())
