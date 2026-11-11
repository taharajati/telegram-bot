"""
تست جامع تمام هندلرها و دکمه‌ها — هر callback ثبت‌شده رو صدا می‌زنه
و مطمئن می‌شه که خطای مدیریت‌نشده (Exception) نمی‌ده.

⚠️  این تست از TEST_DATABASE_URL استفاده می‌کند. اگر ست نشده باشد،
    از DATABASE_URL استفاده می‌شود. هیچ‌وقت روی دیتابیس پروداکشن اجرا نشود.
"""
import os
import sys

# ─── CRITICAL: force test database before any project import ─────
# This ensures handlers and services all use the test DB, not production.
_test_db_url = os.environ.get("TEST_DATABASE_URL", "").strip()
if _test_db_url:
    os.environ["DATABASE_URL"] = _test_db_url
else:
    print("⚠️  WARNING: TEST_DATABASE_URL not set — tests use DATABASE_URL (production?)", file=sys.stderr)

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlalchemy import select
from database.db import async_session, init_db
from database.models import (
    CartItem, Category, DiscountCode, Order, OrderItem,
    OrderStatus, Product, Shop, ShopOwner, User, WishlistItem,
    Conversation, Message,
)

# ─── Fakes ────────────────────────────────────────────────────

OK = 0
FAIL = 0
SKIP = 0

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
        get_me=AsyncMock(return_value=SimpleNamespace(id=123456, username="testbot", first_name="TestBot")),
        username="testbot",
    )
    ctx.args = []
    ctx.match = None
    return ctx

def check(label, condition, detail=""):
    global OK, FAIL
    if condition:
        OK += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label}" + (f" — {detail}" if detail else ""))

# ─── DB helpers ────────────────────────────────────────────────

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

async def make_conv(shop_id, buyer_id=888):
    async with async_session() as s:
        c = Conversation(buyer_id=buyer_id, shop_id=shop_id, order_id=None, status="open")
        s.add(c)
        await s.commit()
        await s.refresh(c)
        return c

async def make_message(conv_id, sender_role="buyer", content="سلام"):
    async with async_session() as s:
        m = Message(conversation_id=conv_id, sender_role=sender_role, content=content)
        s.add(m)
        await s.commit()
        return m

async def cleanup_all():
    async with async_session() as s:
        # Clear user foreign keys referencing shops first
        from database.models import User
        for u in (await s.execute(select(User))).scalars().all():
            u.current_shop_id = None
            u.last_shop_id = None
        await s.flush()

        for table in [Message, Conversation, CartItem, WishlistItem, OrderItem, Order,
                      DiscountCode, Product, Category, ShopOwner, Shop]:
            for row in (await s.execute(select(table))).scalars().all():
                await s.delete(row)
        await s.commit()

# ─── Smoke test runner ───────────────────────────────────────

async def safe_call(label, fn, *args, **kwargs):
    """Call a handler and assert it doesn't throw any Exception."""
    global OK, FAIL
    try:
        result = await fn(*args, **kwargs)
        check(label, True)
        return result
    except Exception as e:
        FAIL += 1
        import traceback
        tb = "".join(traceback.format_exception_only(type(e), e)).strip()
        print(f"  ❌ {label} — {tb}")
        return None

async def run_all():
    global OK, FAIL, SKIP

    print("="*60)
    print("🧪 اسمیک تست جامع — همه دکمه‌ها و هندلرها")
    print("="*60)

    await init_db()
    await cleanup_all()

    # ── Import all handlers ──
    from handlers.menu import show_categories, show_products, show_product_detail
    from handlers import cart as cart_h
    from handlers import start as start_h, wishlist as wishlist_h, search as search_h, help as help_h
    from handlers import seller_registration as seller_reg_h
    from handlers import seller_panel as seller_panel_h
    from handlers import order as order_h
    from handlers import discount as discount_h
    from handlers import support as support_h
    from handlers import forward_products as fwd_h
    from handlers import conversations as conv_h
    from handlers import common as common_h
    from handlers.admin import panel as admin_panel_h
    from handlers.admin import products as admin_products_h
    from handlers.admin import categories as admin_categories_h
    from handlers.admin import orders as admin_orders_h
    from handlers.admin import shops as admin_shops_h

    # ── Create test data ──
    admin_id = 9000000
    seller_id = 9000001
    buyer_id = 9000002

    shop = await make_test_shop("فروشگاه اسمیک تست", user_id=seller_id)
    cat, prods = await make_test_products(shop)
    conv = await make_conv(shop.id, buyer_id=buyer_id)
    msg = await make_message(conv.id, sender_role="buyer", content="سلام تست")

    async with async_session() as s:
        u = User(user_id=seller_id, first_name="فروشنده", username="seller", current_shop_id=shop.id, last_shop_id=shop.id)
        await s.merge(u)
        u2 = User(user_id=buyer_id, first_name="مشتری", username="customer", current_shop_id=shop.id, last_shop_id=shop.id)
        await s.merge(u2)
        u3 = User(user_id=admin_id, first_name="ادمین", username="admin", current_shop_id=shop.id, last_shop_id=shop.id)
        await s.merge(u3)
        await s.commit()

    print(f"\n📦 فروشگاه ID={shop.id} | دسته ID={cat.id} | محصولات: {[p.id for p in prods]}")
    print(f"   فروشنده ID={seller_id} | خریدار ID={buyer_id} | مکالمه ID={conv.id}\n")

    # ══════════════════════════════════════════════════════════
    # TEST: Support / Two-way messaging
    # ══════════════════════════════════════════════════════════
    print("───── پشتیبانی و پیام ─────")

    ctx = fake_context()
    ctx.user_data["support_shop_id"] = shop.id
    ctx.user_data["shop_id"] = shop.id

    # support:seller — entry
    q = fake_callback_query("support:seller", user_id=buyer_id)
    upd = fake_update(query=q)
    await safe_call("support:seller → seller_support_start",
                    support_h.seller_support_start, upd, ctx)

    # seller:inbox — list conversations
    ctx2 = fake_context()
    q2 = fake_callback_query("seller:inbox", user_id=seller_id)
    upd2 = fake_update(query=q2)
    await safe_call("seller:inbox → seller_inbox",
                    conv_h.seller_inbox, upd2, ctx2)

    # msg:open — seller opens conversation
    ctx3 = fake_context()
    q3 = fake_callback_query(f"msg:open:{conv.id}", user_id=seller_id)
    upd3 = fake_update(query=q3)
    await safe_call(f"msg:open:{conv.id} → seller_open_conv",
                    conv_h.seller_open_conv, upd3, ctx3)

    # msg:reply — seller starts replying
    ctx4 = fake_context()
    q4 = fake_callback_query(f"msg:reply:{conv.id}", user_id=seller_id)
    upd4 = fake_update(query=q4)
    await safe_call(f"msg:reply:{conv.id} → start_send_message",
                    conv_h.start_send_message, upd4, ctx4)

    # seller sends a text reply
    ctx5 = fake_context()
    ctx5.user_data["conv_id_writing"] = conv.id
    upd5 = fake_update(message_text="پاسخ فروشنده", user_id=seller_id)
    await safe_call("seller text reply → save_message (seller role)",
                    conv_h.save_message, upd5, ctx5)

    # support:seller — cancel
    ctx6 = fake_context()
    ctx6.user_data["support_mode"] = True
    ctx6.user_data["support_shop_id"] = shop.id
    upd6 = fake_update(message_text="/cancel", user_id=buyer_id)
    await safe_call("seller_support_cancel",
                    support_h.seller_support_cancel, upd6, ctx6)

    # support:open — admin support entry
    ctx7 = fake_context()
    q7 = fake_callback_query("support:open", user_id=buyer_id)
    upd7 = fake_update(query=q7)
    await safe_call("support:open → support_start",
                    support_h.support_start, upd7, ctx7)

    # ══════════════════════════════════════════════════════════
    # TEST: All shop menu callbacks
    # ══════════════════════════════════════════════════════════
    print("\n───── منوی فروشگاه و محصولات ─────")

    ctx = fake_context()
    ctx.user_data["shop_id"] = shop.id

    # cat:list
    q = fake_callback_query("cat:list", user_id=buyer_id)
    await safe_call("cat:list → show_categories",
                    show_categories, fake_update(query=q), ctx)

    # cat:open
    q = fake_callback_query(f"cat:open:{cat.id}:1", user_id=buyer_id)
    await safe_call(f"cat:open:{cat.id}:1 → show_products",
                    show_products, fake_update(query=q), ctx)

    # product:view
    q = fake_callback_query(f"product:view:{prods[0].id}", user_id=buyer_id)
    await safe_call(f"product:view:{prods[0].id} → show_product_detail",
                    show_product_detail, fake_update(query=q), ctx)

    # cart:add
    ctx2 = fake_context()
    ctx2.user_data["shop_id"] = shop.id
    q2 = fake_callback_query(f"cart:add:{prods[0].id}", user_id=buyer_id)
    await safe_call(f"cart:add:{prods[0].id} → add_to_cart",
                    cart_h.add_to_cart, fake_update(query=q2), ctx2)

    # cart:view
    ctx3 = fake_context()
    ctx3.user_data["shop_id"] = shop.id
    q3 = fake_callback_query("cart:view", user_id=buyer_id)
    await safe_call("cart:view → view_cart",
                    cart_h.view_cart, fake_update(query=q3), ctx3)

    # order:start
    ctx4 = fake_context()
    ctx4.user_data["shop_id"] = shop.id
    q4 = fake_callback_query("order:start", user_id=buyer_id)
    await safe_call("order:start → start_checkout",
                    order_h.start_checkout, fake_update(query=q4), ctx4)

    # order:cancel
    ctx5 = fake_context()
    ctx5.user_data["shop_id"] = shop.id
    async with async_session() as s:
        o = Order(user_id=buyer_id, shop_id=shop.id, total_price=50000,
                  status=OrderStatus.PENDING, payment_method="cod", tracking_code=str(asyncio.get_running_loop().time()).replace(".","")[:14],
                  shipping_address="آدرس تست", phone="09120000000")
        s.add(o)
        await s.commit()
        await s.refresh(o)
        order_id = o.id
    q5 = fake_callback_query(f"order:cancel:{order_id}", user_id=buyer_id)
    await safe_call(f"order:cancel:{order_id} → cancel_order",
                    order_h.cancel_order, fake_update(query=q5), ctx5)

    # search:open
    ctx6 = fake_context()
    q6 = fake_callback_query("search:open", user_id=buyer_id)
    await safe_call("search:open → search_prompt",
                    search_h.search_prompt, fake_update(query=q6), ctx6)

    # wishlist:toggle
    ctx7 = fake_context()
    q7 = fake_callback_query(f"wishlist:toggle:{prods[0].id}", user_id=buyer_id)
    await safe_call(f"wishlist:toggle:{prods[0].id} → toggle_wishlist",
                    wishlist_h.toggle_wishlist, fake_update(query=q7), ctx7)

    # forward products: admin action (entry point)
    ctx8 = fake_context()
    q8 = fake_callback_query("admin:products:add_forward", user_id=admin_id)
    await safe_call("admin:products:add_forward → start_add_forward",
                    fwd_h.start_add_forward, fake_update(query=q8), ctx8)

    # help:show
    ctx9 = fake_context()
    q9 = fake_callback_query("help:show", user_id=buyer_id)
    await safe_call("help:show → help_callback",
                    help_h.help_callback, fake_update(query=q9), ctx9)

    # ══════════════════════════════════════════════════════════
    # TEST: Seller panel
    # ══════════════════════════════════════════════════════════
    print("\n───── پنل فروشنده ─────")

    ctx = fake_context()
    ctx.user_data["shop_id"] = shop.id

    # seller:panel — message-based command, not testable via callback
    SKIP += 1
    print(f"  ⏭️ seller:panel — نیاز به message (callback-based نیست)")

    q = fake_callback_query("seller:panel_back", user_id=seller_id)
    await safe_call("seller:panel_back → panel_back",
                    seller_panel_h.panel_back, fake_update(query=q), ctx)

    q = fake_callback_query("seller:orders:pending", user_id=seller_id)
    await safe_call("seller:orders:pending → seller_orders_pending",
                    seller_panel_h.seller_orders_pending, fake_update(query=q), ctx)

    q = fake_callback_query("seller:orders:history", user_id=seller_id)
    await safe_call("seller:orders:history → seller_orders_history",
                    seller_panel_h.seller_orders_history, fake_update(query=q), ctx)

    # ══════════════════════════════════════════════════════════
    # TEST: Admin panel
    # ══════════════════════════════════════════════════════════
    print("\n───── پنل ادمین ─────")

    ctx = fake_context()
    ctx.user_data["shop_id"] = shop.id

    q = fake_callback_query("admin:panel", user_id=admin_id)
    await safe_call("admin:panel → admin_panel_callback",
                    admin_panel_h.admin_panel_callback, fake_update(query=q), ctx)

    q = fake_callback_query(f"admin:orders:pending:{shop.id}", user_id=admin_id)
    await safe_call(f"admin:orders:pending:{shop.id} → list_pending_orders",
                    admin_orders_h.list_pending_orders, fake_update(query=q), ctx)

    q = fake_callback_query(f"admin:orders:detail:{order_id}", user_id=admin_id)
    await safe_call(f"admin:orders:detail:{order_id} → order_detail",
                    admin_orders_h.order_detail, fake_update(query=q), ctx)

    q = fake_callback_query(f"admin:products:list:{shop.id}", user_id=admin_id)
    await safe_call(f"admin:products:list:{shop.id} → list_products",
                    admin_products_h.list_products, fake_update(query=q), ctx)

    q = fake_callback_query("admin:categories", user_id=admin_id)
    await safe_call("admin:categories → list_categories",
                    admin_categories_h.list_categories, fake_update(query=q), ctx)

    q = fake_callback_query(f"admin:shops:list:{shop.id}", user_id=admin_id)
    await safe_call(f"admin:shops:list:{shop.id} → list_shops",
                    admin_shops_h.list_shops, fake_update(query=q), ctx)

    # ══════════════════════════════════════════════════════════
    # TEST: Discount
    # ══════════════════════════════════════════════════════════
    print("\n───── تخفیف ─────")

    ctx = fake_context()
    ctx.user_data["shop_id"] = shop.id

    q = fake_callback_query("discount:list", user_id=seller_id)
    await safe_call("discount:list → list_discounts",
                    discount_h.list_discounts, fake_update(query=q), ctx)

    # ══════════════════════════════════════════════════════════
    # TEST: Navigation
    # ══════════════════════════════════════════════════════════
    print("\n───── ناوبری ─────")

    ctx = fake_context()
    ctx.user_data["shop_id"] = shop.id

    q = fake_callback_query("nav:main", user_id=buyer_id)
    await safe_call("nav:main → main_menu_callback",
                    start_h.main_menu_callback, fake_update(query=q), ctx)

    q = fake_callback_query("nav:main", user_id=seller_id)
    await safe_call("nav:main (seller) → main_menu_callback",
                    start_h.main_menu_callback, fake_update(query=q), ctx)

    # ══════════════════════════════════════════════════════════
    await cleanup_all()

    # ── Summary ──
    total = OK + FAIL
    print(f"\n{'='*60}")
    print(f"نتایج: {OK} ✅ پاس  |  {FAIL} ❌ شکست  |  {total} مجموع")
    print(f"{'='*60}")
    return FAIL == 0

if __name__ == "__main__":
    success = asyncio.run(run_all())
    sys.exit(0 if success else 1)
