"""سفر کامل فروشنده و مشتری روی PostgreSQL واقعی، با بات تلگرام ساختگی (هیچ پیامی به تلگرام نمی‌ره).

اجرا (روی سرور، داخل کانتینر ربات، با یک دیتابیس موقت جدا از دیتابیس اصلی):
    docker exec -e DATABASE_URL=postgresql+asyncpg://USER:PASS@postgres:5432/fg_e2e foroshgram_bot \
        python scripts/e2e_journey.py

هر قدم یک خط ✅/❌ چاپ می‌کنه و آخرش خلاصه می‌ده. دیتا همون فروشگاه «اشبورن» با قیمت ۲ میلیون برای هر لباسه.
"""
import asyncio
import json
import os
import sys
import traceback
from types import SimpleNamespace
from unittest.mock import AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if "localhost" in os.environ.get("DATABASE_URL", "") or "fg_e2e" not in os.environ.get("DATABASE_URL", ""):
    sys.exit("refusing to run: DATABASE_URL must point at a throw-away database named fg_e2e")

import config  # noqa: E402

config.FREE_MODE = True
config.AUTO_APPROVE_SHOPS = True

from sqlalchemy import func, select  # noqa: E402
from telegram.ext import ConversationHandler  # noqa: E402

from database.db import async_session, init_db  # noqa: E402
from database.models import CartItem, Category, Order, OrderStatus, Product, Shop, ShopOwner, User  # noqa: E402
from handlers import cart as cart_h  # noqa: E402
from handlers import menu as menu_h  # noqa: E402
from handlers import order as order_h  # noqa: E402
from handlers import search as search_h  # noqa: E402
from handlers import seller_panel as panel_h  # noqa: E402
from handlers import seller_registration as reg  # noqa: E402
from handlers import start as start_h  # noqa: E402
from handlers import widgets as widgets_h  # noqa: E402
from handlers import wishlist as wishlist_h  # noqa: E402
from handlers.admin import orders as admin_orders  # noqa: E402
from handlers.admin import panel as admin_panel  # noqa: E402
from handlers.admin import products as products_h  # noqa: E402
from services import widgets  # noqa: E402

SELLER, CUSTOMER = 7001, 5001
DROPS = ["تیشرت بلک‌پینک سفید", "تیشرت بلک‌پینک مشکی", "تیشرت بلک‌پینک مشکی ۲", "کراپ تاپ گوتیک", "تیشرت رادیوهد سفید"]
PRICE_FA = "۲٬۰۰۰٬۰۰۰"

results: list[tuple[bool, str, str]] = []
BOT = AsyncMock()
BOT.username = "testbot"
BOT.token = "1:TEST"


async def api(method, api_kwargs=None, **_):
    return {"message_id": 777} if method == "sendWidget" else True


BOT.do_api_request = AsyncMock(side_effect=api)
widgets.init(BOT)


def ctx(args=None):
    return SimpleNamespace(user_data={}, bot=BOT, args=args or [])


def user(uid):
    return SimpleNamespace(id=uid, first_name="کاربر", last_name=None, username=f"u{uid}", is_premium=False)


def msg_update(uid, text=None, photo=None):
    m = SimpleNamespace(
        text=text, photo=photo or [], contact=None, caption=None,
        reply_text=AsyncMock(), reply_photo=AsyncMock(), reply_media_group=AsyncMock(), reply_html=AsyncMock(),
    )
    return SimpleNamespace(effective_user=user(uid), effective_chat=SimpleNamespace(id=uid), effective_message=m,
                           message=m, callback_query=None, api_kwargs={})


def cb_update(uid, data):
    message = SimpleNamespace(chat_id=uid, message_id=10, delete=AsyncMock(), reply_text=AsyncMock(),
                              reply_photo=AsyncMock(), reply_media_group=AsyncMock(), text_html="x")
    q = SimpleNamespace(
        data=data, answer=AsyncMock(), edit_message_text=AsyncMock(), edit_message_caption=AsyncMock(),
        edit_message_reply_markup=AsyncMock(), message=message,
    )
    return SimpleNamespace(effective_user=user(uid), effective_chat=SimpleNamespace(id=uid), effective_message=message,
                           message=None, callback_query=q, api_kwargs={})


def texts(update):
    """همه‌ی متن‌هایی که ربات توی این آپدیت نوشته"""
    out = []
    holders = [update.message, update.callback_query]
    for h in holders:
        if h is None:
            continue
        for name in ("reply_text", "edit_message_text", "edit_message_caption"):
            fn = getattr(h, name, None)
            if fn is not None and hasattr(fn, "await_args_list"):
                for c in fn.await_args_list:
                    out.append(str(c.args[0] if c.args else c.kwargs.get("text") or c.kwargs.get("caption") or ""))
    return "\n".join(out)


def keyboard_data(update):
    out = []
    for h in (update.message, update.callback_query):
        if h is None:
            continue
        for name in ("reply_text", "edit_message_text", "edit_message_caption"):
            fn = getattr(h, name, None)
            if fn is not None and hasattr(fn, "await_args_list"):
                for c in fn.await_args_list:
                    kb = c.kwargs.get("reply_markup")
                    if kb is not None and hasattr(kb, "inline_keyboard"):
                        out += [b.callback_data for row in kb.inline_keyboard for b in row if b.callback_data]
    return out


async def step(name, coro):
    try:
        value = await coro
        results.append((True, name, ""))
        print(f"  ✅ {name}")
        return value
    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc().strip().splitlines()
        results.append((False, name, f"{type(e).__name__}: {e}"))
        print(f"  ❌ {name}\n     {type(e).__name__}: {str(e)[:300]}\n     {tb[-3].strip()[:200]}")
        return None


_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789", "٬،,")


def has_amount(text, amount):
    """مبلغ رو با هر نوع رقم و جداکننده‌ی هزارگان پیدا می‌کنه (ربات ۴,۰۰۰,۰۰۰ با ارقام فارسی می‌نویسه)."""
    return str(amount) in (text or "").translate(_DIGITS)


def expect(cond, what):
    if not cond:
        raise AssertionError(what)


async def seller_journey():
    print("\n— فروشنده")
    c = ctx()
    await step("ثبت‌نام: شروع", reg.seller_registration_start(cb_update(SELLER, "seller_reg:start"), c))
    await step("ثبت‌نام: اسم فروشگاه", reg.ask_name(msg_update(SELLER, "اشبورن | ASHBORN"), c))
    u = msg_update(SELLER, "09123456789")
    await step("ثبت‌نام: شماره", reg.ask_phone(u, c))
    await step("ثبت‌نام: کارت", reg.ask_card_number(msg_update(SELLER, "6037991234567890"), c))
    await step("ثبت‌نام: نام صاحب کارت → ساخت فروشگاه", reg.ask_card_holder(msg_update(SELLER, "طه رجعتی"), c))

    async with async_session() as s:
        shop = (await s.execute(select(Shop))).scalar_one()
        expect(shop.status == "active", f"shop status {shop.status}")
    await step("فروشگاه فعال شد", asyncio.sleep(0))

    p = ctx()
    await step("پنل: /myshop", panel_h.seller_panel_command(msg_update(SELLER), p))
    for i, name in enumerate(DROPS):
        c = ctx()
        await step(f"محصول {i + 1}: شروع", products_h.start_add_product(cb_update(SELLER, "admin:products:add"), c))
        await step(f"محصول {i + 1}: نام", products_h.add_name(msg_update(SELLER, name), c))
        await step(f"محصول {i + 1}: توضیح", products_h.add_desc(msg_update(SELLER, "پارچه نخی، چاپ دیجیتال. سایز M/L/XL/XXL"), c))
        await step(f"محصول {i + 1}: قیمت ۲ میلیون", products_h.add_price(msg_update(SELLER, PRICE_FA), c))
        await step(f"محصول {i + 1}: موجودی", products_h.add_stock(msg_update(SELLER, "۱۰"), c))
        await step(f"محصول {i + 1}: ثبت بدون عکس", products_h.add_photo_button(cb_update(SELLER, "admin:products:add:nophoto"), c))
    async with async_session() as s:
        prices = {pr.price for pr in (await s.execute(select(Product))).scalars()}
        count = (await s.execute(select(func.count(Product.id)))).scalar_one()
    await step("۵ محصول با قیمت ۲٬۰۰۰٬۰۰۰ ذخیره شد", asyncio.sleep(0) if count == 5 and prices == {2000000} else _fail(f"{count} products, prices {prices}"))
    await step("لیست محصولات فروشنده", products_h.list_products(cb_update(SELLER, "admin:products:list:0"), ctx()))
    await step("دسته‌بندی‌ها", _call_categories())


async def _fail(message):
    raise AssertionError(message)


async def _call_categories():
    from handlers.admin import categories as cats
    return await cats.list_categories(cb_update(SELLER, "admin:categories"), ctx())


async def customer_journey():
    print("\n— مشتری")
    async with async_session() as s:
        shop_id = (await s.execute(select(Shop.id))).scalar_one()
    c = ctx([f"shop_{shop_id}"])
    u = msg_update(CUSTOMER)
    await step("لینک فروشگاه (/start shop_N)", start_h.start_command(u, c))
    expect(True, "")
    await step("منوی فروشگاه: دسته‌ها", menu_h.show_categories(cb_update(CUSTOMER, "cat:list"), c))
    async with async_session() as s:
        cat_id = (await s.execute(select(Category.id))).scalars().first()
        pid = (await s.execute(select(Product.id).order_by(Product.id))).scalars().first()
        pid2 = (await s.execute(select(Product.id).order_by(Product.id.desc()))).scalars().first()
    await step("لیست محصولات دسته", menu_h.show_products(cb_update(CUSTOMER, f"cat:open:{cat_id}:0"), c))
    await step("جزئیات محصول", menu_h.show_product_detail(cb_update(CUSTOMER, f"prod:open:{pid}:{cat_id}:0"), c))
    await step("افزودن به سبد (۱)", cart_h.add_to_cart(cb_update(CUSTOMER, f"cart:add:{pid}"), c))
    await step("افزودن به سبد (۲)", cart_h.add_to_cart(cb_update(CUSTOMER, f"cart:add:{pid2}"), c))
    v = cb_update(CUSTOMER, "cart:view")
    await step("نمایش سبد", cart_h.view_cart(v, c))
    expect(has_amount(texts(v), 4000000), f"cart total missing: {texts(v)[-120:]}")
    async with async_session() as s:
        item_id = (await s.execute(select(CartItem.id))).scalars().first()
    await step("افزایش تعداد", cart_h.change_quantity(cb_update(CUSTOMER, f"cart:inc:{item_id}"), c))
    await step("کاهش تعداد", cart_h.change_quantity(cb_update(CUSTOMER, f"cart:dec:{item_id}"), c))
    await step("علاقه‌مندی‌ها", wishlist_h.toggle_wishlist(cb_update(CUSTOMER, f"wishlist:toggle:{pid}"), c))
    s_up = msg_update(CUSTOMER, "کراپ")
    c.user_data["search_shop_id"] = shop_id
    await step("جستجوی محصول", search_h.search_all_products(s_up, ctx(["کراپ"])))

    print("\n— ثبت سفارش")
    ck = ctx()
    ck.user_data["current_shop_id"] = shop_id
    st = await step("شروع ثبت سفارش", order_h.start_checkout(cb_update(CUSTOMER, "order:start"), ck))
    await step("نام گیرنده", order_h.ask_name(msg_update(CUSTOMER, "سارا احمدی"), ck))
    await step("شماره تماس", order_h.ask_phone(msg_update(CUSTOMER, "۰۹۱۲۱۲۳۴۵۶۷"), ck))
    await step("آدرس", order_h.ask_address(msg_update(CUSTOMER, "تهران، ونک، خیابان ملاصدرا، پلاک ۱۲"), ck))
    sm = msg_update(CUSTOMER, "سایز L")
    await step("توضیحات → خلاصه سفارش", order_h.ask_notes(sm, ck))
    expect(has_amount(texts(sm), 4000000), f"summary total: {texts(sm)[-150:]}")
    cf = cb_update(CUSTOMER, "order:confirm_card")
    await step("تأیید و رفتن به پرداخت", order_h.confirm_card_payment(cf, ck))
    expect("6037991234567890" in texts(cf), "card number not shown to customer")
    rc = msg_update(CUSTOMER, "TX-884412")
    await step("ارسال شماره تراکنش (رسید)", order_h.handle_card_receipt(rc, ck))
    async with async_session() as s:
        order = (await s.execute(select(Order))).scalar_one()
        expect(order.total_price == 4000000, f"order total {order.total_price}")
        expect(order.status == OrderStatus.PENDING_PAYMENT, order.status)
    return order.id


async def fulfilment(order_id):
    print("\n— تأیید و ارسال")
    BOT.send_message.reset_mock()
    ap = cb_update(SELLER, f"seller:payment:approve:{order_id}")
    await step("فروشنده: تأیید پرداخت", order_h.seller_approve_card_payment(ap, ctx()))
    async with async_session() as s:
        expect((await s.get(Order, order_id)).status == OrderStatus.PAID, "not paid")
    await step("لیست سفارش‌های جدید", panel_h.seller_orders_pending(cb_update(SELLER, "seller:orders:pending"), ctx()))
    await step("تاریخچه سفارش‌ها", panel_h.seller_orders_history(cb_update(SELLER, "seller:orders:history"), ctx()))
    await step("لیست سفارش‌ها (ادمین/فروشنده)", admin_orders.list_pending_orders(cb_update(SELLER, "admin:orders:pending:0"), ctx()))
    await step("جزئیات سفارش", admin_orders.order_detail(cb_update(SELLER, f"admin:orders:detail:{order_id}"), ctx()))

    t = await step("رهگیری زنده: ارسال ویجت", widgets.send_order_tracker(BOT, order_id, CUSTOMER))
    expect(t, "widget not sent")
    sh = cb_update(SELLER, f"admin:orders:status:{order_id}:shipped")
    await step("فروشنده: «ارسال شد»", admin_orders.change_order_status(sh, ctx()))
    await asyncio.sleep(0.6)
    edits = [c.kwargs["api_kwargs"] for c in BOT.do_api_request.call_args_list if c.args[0] == "editMessageWidgetData"]
    await step("ویجت رهگیری خودکار به‌روز شد", asyncio.sleep(0) if edits and json.loads(edits[-1]["chat_data"])["s"] == 3 else _fail(f"edits={edits[-1:]}"))
    await step("مشتری: «بسته رسید» از ویجت", widgets.handle_widget_query(BOT, {
        "id": "q1", "data": widgets.Q_ORDER_DELIVERED, "message_id": 777,
        "from": {"id": CUSTOMER}, "chat": {"id": CUSTOMER, "type": "private"}}))
    async with async_session() as s:
        expect((await s.get(Order, order_id)).status == OrderStatus.DELIVERED, "not delivered")
    await step("جزئیات سفارش برای مشتری", order_h.order_detail_customer(cb_update(CUSTOMER, f"order:detail:{order_id}"), _with_shop()))
    await step("تاریخچه سفارش مشتری", order_h.order_history(cb_update(CUSTOMER, "order:history"), _with_shop()))
    await step("داشبورد زنده فروشنده (ویجت)", widgets.send_seller_dashboard(BOT, (await _shop_id()), SELLER))
    await step("آمار فروش", admin_panel.admin_stats(cb_update(SELLER, "seller:stats"), _seller_ctx()))
    await step("روند ۷ روزه", admin_panel.admin_weekly_sales(cb_update(SELLER, "admin:stats:weekly"), _seller_ctx()))


async def _shop_id():
    async with async_session() as s:
        return (await s.execute(select(Shop.id))).scalar_one()


def _with_shop():
    c = ctx()
    return c


def _seller_ctx():
    c = ctx()
    return c


async def checkout(uid, shop_id, product_id, name, receipt=True):
    """یک مشتری از سبد تا ثبت سفارش؛ آیدی سفارش یا None (اگه موجودی نبود) برمی‌گردونه."""
    c = ctx()
    c.user_data["current_shop_id"] = shop_id
    async with async_session() as s:
        if await s.get(User, uid) is None:
            s.add(User(user_id=uid, first_name=name, current_shop_id=shop_id, last_shop_id=shop_id))
            await s.commit()
    await cart_h.add_to_cart(cb_update(uid, f"cart:add:{product_id}"), c)
    await order_h.start_checkout(cb_update(uid, "order:start"), c)
    await order_h.ask_name(msg_update(uid, name), c)
    await order_h.ask_phone(msg_update(uid, "09121234567"), c)
    await order_h.ask_address(msg_update(uid, "تهران، خیابان آزادی، پلاک ۴۰"), c)
    await order_h.ask_notes(msg_update(uid, "نخواهم"), c)
    cf = cb_update(uid, "order:confirm_card")
    await order_h.confirm_card_payment(cf, c)
    order_id = c.user_data.get("card_order_id")
    if order_id is None:
        return None
    if receipt:
        await order_h.handle_card_receipt(msg_update(uid, f"TX-{uid}"), c)
    return order_id


async def multi_user():
    print("\n— چند کاربر تستی هم‌زمان")
    shop_id = await _shop_id()
    async with async_session() as s:
        cat_id = (await s.execute(select(Category.id))).scalars().first()
        last_one = Product(name="تیشرت محدود (آخرین عدد)", description="تست رقابت", price=2000000,
                           category_id=cat_id, stock=1, shop_id=shop_id)
        s.add(last_one)
        await s.commit()
        last_id = last_one.id
        normal = [p for p in (await s.execute(select(Product.id).where(Product.id != last_id).order_by(Product.id))).scalars()]

    names = ["علی رضایی", "مریم کریمی", "حسین مرادی", "نگار صادقی"]
    out = await asyncio.gather(*[checkout(6100 + i, shop_id, normal[i % len(normal)], n) for i, n in enumerate(names)], return_exceptions=True)
    errors = [o for o in out if isinstance(o, Exception)]
    await step("۴ مشتری هم‌زمان سفارش دادن", asyncio.sleep(0) if not errors and all(out) else _fail(f"{out}"))

    race = await asyncio.gather(*[checkout(6200 + i, shop_id, last_id, f"رقیب شماره {i + 1}") for i in range(3)], return_exceptions=True)
    ok = [r for r in race if isinstance(r, int)]
    errs = [r for r in race if isinstance(r, Exception)]
    await step("رقابت روی آخرین موجودی: فقط یک سفارش", asyncio.sleep(0) if len(ok) == 1 and not errs else _fail(f"succeeded={len(ok)} errors={errs}"))
    async with async_session() as s:
        p = await s.get(Product, last_id)
        orders_total = (await s.execute(select(func.count(Order.id)))).scalar_one()
    await step("رزرو موجودی درست ثبت شد", asyncio.sleep(0) if p.reserved_stock == 1 and p.stock == 1 else _fail(f"stock={p.stock} reserved={p.reserved_stock}"))
    await step(f"جمع سفارش‌های ثبت‌شده: {orders_total}", asyncio.sleep(0))
    await step("داشبورد پس از چند سفارش", widgets.seller_dashboard_state(shop_id))
    await cron_check(shop_id, normal[0])
    await step("سفارش‌های جدید فروشنده (چند سفارش)", panel_h.seller_orders_pending(cb_update(SELLER, "seller:orders:pending"), ctx()))


async def cron_check(shop_id, product_id):
    """کرون لغو خودکار: سفارش بدون رسید بعد از ۱۵ دقیقه لغو می‌شه، ولی سفارشی که رسیدش رسیده نه."""
    from sqlalchemy import text as sql
    from services import payment as payment_svc

    no_receipt = await checkout(6300, shop_id, product_id, "بدون رسید", receipt=False)
    async with async_session() as s:
        await s.execute(sql("UPDATE orders SET created_at = created_at - interval '1 hour' WHERE status = 'pending_payment'"))
        await s.commit()
        pending_with_receipt = (await s.execute(select(func.count(Order.id)).where(
            Order.status == OrderStatus.PENDING_PAYMENT, Order.payment_receipt_at.is_not(None)))).scalar_one()
    await step("سفارش‌های رسیددار قبل از کرون «در انتظار تأیید» هستن", asyncio.sleep(0) if pending_with_receipt >= 5 else _fail(f"only {pending_with_receipt}"))
    cancelled = await step("کرون لغو خودکار بدون خطا اجرا شد", payment_svc.auto_cancel_unpaid_orders())
    async with async_session() as s:
        still = (await s.execute(select(func.count(Order.id)).where(
            Order.status == OrderStatus.PENDING_PAYMENT, Order.payment_receipt_at.is_not(None)))).scalar_one()
        lost = (await s.get(Order, no_receipt)).status if no_receipt else None
    await step("سفارش رسیددار لغو نشد", asyncio.sleep(0) if still == pending_with_receipt else _fail(f"{pending_with_receipt} -> {still}"))
    await step("سفارش بدون رسید لغو شد", asyncio.sleep(0) if lost == OrderStatus.CANCELLED else _fail(f"status={lost}"))


async def extras():
    print("\n— موارد دیگه")
    await step("/start برای فروشنده", start_h.start_command(msg_update(SELLER), ctx()))
    await step("/start برای مشتری برگشتی", start_h.start_command(msg_update(CUSTOMER), ctx()))
    await step("/start لینک ساخت فروشگاه از سایت", start_h.start_command(msg_update(9999), ctx(["newshop"])))
    await step("پنل ادمین کل", admin_panel.admin_command(msg_update(int(next(iter(config.ADMIN_IDS)))), ctx()) if config.ADMIN_IDS else asyncio.sleep(0))


async def main():
    await init_db()
    print("schema ready")
    await seller_journey()
    order_id = await customer_journey()
    if order_id:
        await fulfilment(order_id)
    await multi_user()
    await extras()
    failed = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(failed)}/{len(results)} steps passed")
    for _, name, err in failed:
        print(f"  ✗ {name}: {err[:200]}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main())
