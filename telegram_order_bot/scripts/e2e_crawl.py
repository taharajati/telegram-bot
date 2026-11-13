"""گشت کامل روی همه‌ی دکمه‌های ربات (مشتری، فروشنده، ادمین) روی PostgreSQL موقت با ترنسپورت تلگرامِ ساختگی.

از دستورهای ورودی شروع می‌کنه، از هر پیامی که ربات می‌فرسته همه‌ی دکمه‌های callback رو جمع می‌کنه و هر کدوم رو
با اپلیکیشن واقعی (همه‌ی هندلرها و ConversationHandlerها) می‌زنه. دو چیز گزارش می‌شه:
  ✗ دکمه‌ای که خطا داد (همون «یه مشکل غیرمنتظره» که کاربر می‌بینه)
  ☠ دکمه‌ی مرده: هیچ هندلری جوابش رو نمی‌ده
پیام‌های عکس‌دار و متنی هم شبیه‌سازی می‌شن (edit_message_text روی عکس خطای واقعی تلگرام رو می‌ده).

اجرا (داخل کانتینر ربات، با دیتابیس جدا که اسمش fg_e2e باشه):
    docker exec -e DATABASE_URL=postgresql+asyncpg://USER:PASS@postgres:5432/fg_e2e foroshgram_bot python scripts/e2e_crawl.py
"""
import asyncio
import os
import re
import sys
import tempfile
import traceback
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if "fg_e2e" not in os.environ.get("DATABASE_URL", ""):
    sys.exit("refusing to run: DATABASE_URL must point at a throw-away database named fg_e2e")
os.environ["PROMETHEUS_ENABLED"] = "false"
os.environ["SENTRY_DSN"] = ""
os.environ["BOT_PERSISTENCE_FILE"] = os.path.join(tempfile.gettempdir(), "fg_crawl_persistence")

import config  # noqa: E402

config.FREE_MODE = True
config.AUTO_APPROVE_SHOPS = True

from telegram import Bot, InlineKeyboardMarkup, Update  # noqa: E402
from telegram.error import BadRequest  # noqa: E402

SELLER, CUSTOMER, ADMIN = 7001, 5001, int(next(iter(config.ADMIN_IDS)))
SKIP = re.compile(r"delete_final|delete:confirm|shops:delete_final|seller:delete_final")
BOT_USER = {"id": 99, "is_bot": True, "first_name": "Foroshgram", "username": "Foroshgrambot"}

calls: list[dict] = []
kinds: dict[tuple[int, int], str] = {}  # (chat, message_id) -> "text" | "photo"
_next_id = [1000]


def _message(chat_id, kind="text", text="x"):
    _next_id[0] += 1
    mid = _next_id[0]
    kinds[(chat_id, mid)] = kind
    msg = {"message_id": mid, "date": 0, "chat": {"id": chat_id, "type": "private"}, "from": BOT_USER}
    if kind == "photo":
        msg["photo"] = [{"file_id": "AgAC-x", "file_unique_id": "u", "width": 1, "height": 1}]
        msg["caption"] = text
    else:
        msg["text"] = text
    return msg


async def fake_post(self, endpoint, data, **_):
    chat_id = data.get("chat_id")
    record = {"endpoint": endpoint, "chat_id": chat_id, "message_id": data.get("message_id"),
              "text": data.get("text") or data.get("caption") or "", "markup": data.get("reply_markup")}
    calls.append(record)
    if endpoint == "getMe":
        return BOT_USER
    if endpoint in ("sendMessage", "sendPhoto", "sendDocument", "sendVideo", "sendAnimation", "sendWidget"):
        msg = _message(chat_id, "photo" if endpoint == "sendPhoto" else "text", record["text"])
        record["new_id"] = msg["message_id"]
        return msg
    if endpoint == "sendMediaGroup":
        return [_message(chat_id, "photo") for _ in data.get("media", [])]
    if endpoint == "editMessageText":
        if kinds.get((chat_id, data.get("message_id"))) == "photo":
            raise BadRequest("Bad Request: there is no text in the message to edit")
        return _message(chat_id, "text", record["text"]) | {"message_id": data.get("message_id")}
    if endpoint == "editMessageCaption":
        if kinds.get((chat_id, data.get("message_id"))) == "text":
            raise BadRequest("Bad Request: there is no caption in the message to edit")
        return _message(chat_id, "photo", record["text"]) | {"message_id": data.get("message_id")}
    if endpoint == "editMessageMedia":
        return _message(chat_id, "photo") | {"message_id": data.get("message_id")}
    if endpoint == "editMessageReplyMarkup":
        return _message(chat_id, kinds.get((chat_id, data.get("message_id")), "text")) | {"message_id": data.get("message_id")}
    if endpoint == "getFile":
        return {"file_id": "x", "file_unique_id": "u", "file_path": "x.jpg"}
    return True


Bot._do_post = fake_post

import main  # noqa: E402
from database.db import async_session  # noqa: E402
from database.models import (  # noqa: E402
    CartItem, Category, Conversation, DiscountCode, Message, Order, OrderItem, Product, ProductImage,
    RestockSubscription, Shop, ShopOwner, User, WishlistItem, utcnow,
)
from utils.crypto import safe_encrypt  # noqa: E402

errors: list[tuple[str, BaseException]] = []


async def seed():
    async with async_session() as s:
        shop = Shop(name="ASHBORN | اشبورن", description="لباس با طرح اختصاصی", phone="09123456789", channel_link="@ashbornclothe",
                    status="active", is_active=True, card_number=safe_encrypt("6037991234567890"),
                    card_holder_name=safe_encrypt("طه رجعتی"), shipping_cost=50000)
        s.add(shop)
        await s.flush()
        s.add(ShopOwner(user_id=SELLER, shop_id=shop.id, first_name="Taha", username="Taha_rajati"))
        for uid, name in ((CUSTOMER, "سارا"), (5002, "علی"), (SELLER, "Taha"), (ADMIN, "Admin")):
            s.add(User(user_id=uid, first_name=name, current_shop_id=shop.id, last_shop_id=shop.id,
                       saved_name=name + " رضایی", saved_phone="09121234567", saved_address="تهران، ونک، پلاک ۱۲ طبقه ۳"))
        tee, crop = Category(name="تیشرت", shop_id=shop.id), Category(name="کراپ تاپ", shop_id=shop.id)
        s.add_all([tee, crop])
        await s.flush()
        products = [
            Product(name="تیشرت Jeff Buckley مشکی", description="پارچه نخی. M/L/XL", price=2000000, stock=10, category_id=tee.id, shop_id=shop.id, image_file_id="AgAC-1"),
            Product(name="تیشرت BLACKPINK سفید", description="چاپ دیجیتال", price=2000000, stock=3, reserved_stock=1, category_id=tee.id, shop_id=shop.id, image_file_id="AgAC-2"),
            Product(name="کراپ تاپ Gothic", price=2000000, stock=0, category_id=crop.id, shop_id=shop.id, image_file_id="AgAC-3"),
            Product(name="محصول مخفی", price=1000, stock=5, is_active=False, category_id=tee.id, shop_id=shop.id),
            Product(name="بدون عکس", price=450000, stock=7, category_id=crop.id, shop_id=shop.id),
        ]
        s.add_all(products)
        await s.flush()
        s.add(ProductImage(product_id=products[0].id, file_id="AgAC-g1", sort_order=1))
        s.add(ProductImage(product_id=products[0].id, file_id="web_x.jpg", local_url="/api/product-image-file/x.jpg", sort_order=2))
        s.add(DiscountCode(shop_id=shop.id, code="OFF10", discount_type="percent", discount_value=10, min_order_amount=0, max_uses=5))
        s.add(WishlistItem(user_id=CUSTOMER, shop_id=shop.id, product_id=products[0].id))
        s.add(RestockSubscription(product_id=products[2].id, user_id=CUSTOMER, shop_id=shop.id))
        s.add(CartItem(user_id=CUSTOMER, shop_id=shop.id, product_id=products[0].id, quantity=2))
        s.add(CartItem(user_id=5002, shop_id=shop.id, product_id=products[1].id, quantity=1))
        statuses = [("pending_payment", False), ("pending_payment", True), ("paid", True), ("confirmed", True), ("preparing", True),
                    ("shipped", True), ("delivered", True), ("cancelled", False), ("refunded", True)]
        for i, (status, receipt) in enumerate(statuses):
            order = Order(shop_id=shop.id, user_id=CUSTOMER, tracking_code=f"26111{i:05d}", total_price=2050000, status=status,
                          payment_method="card_to_card", receiver_name="سارا رضایی", phone="09121234567",
                          shipping_address="تهران، ونک، پلاک ۱۲", payment_receipt_at=utcnow() if receipt else None,
                          payment_receipt_text="TX-884412" if receipt else None,
                          tracking_number="1234567890" if status in ("shipped", "delivered") else None)
            s.add(order)
            await s.flush()
            s.add(OrderItem(order_id=order.id, product_id=products[0].id, product_name=products[0].name, quantity=1, unit_price=2000000))
            order.add_status_entry(status, by="system", session=s)
        conv = Conversation(buyer_id=CUSTOMER, shop_id=shop.id, status="open")
        s.add(conv)
        await s.flush()
        s.add(Message(conversation_id=conv.id, sender_role="buyer", content="سلام سایز L دارید؟"))
        await s.commit()


def _update(update_id: int, **fields) -> Update:
    return Update.de_json({"update_id": update_id, **fields}, bot=APP.bot)


def command_update(uid: int, text: str, n: int) -> Update:
    cmd_len = len(text.split()[0])
    return _update(n, message={
        "message_id": n, "date": 0, "chat": {"id": uid, "type": "private"},
        "from": {"id": uid, "is_bot": False, "first_name": "T"}, "text": text,
        "entities": [{"type": "bot_command", "offset": 0, "length": cmd_len}],
    })


def callback_update(uid: int, data: str, chat_id: int, message_id: int, n: int) -> Update:
    kind = kinds.get((chat_id, message_id), "text")
    message = {"message_id": message_id, "date": 0, "chat": {"id": chat_id, "type": "private"}, "from": BOT_USER}
    if kind == "photo":
        message["photo"] = [{"file_id": "AgAC-x", "file_unique_id": "u", "width": 1, "height": 1}]
        message["caption"] = "x"
    else:
        message["text"] = "x"
    return _update(n, callback_query={"id": str(n), "from": {"id": uid, "is_bot": False, "first_name": "T"},
                                      "chat_instance": "c", "data": data, "message": message})


async def main_crawl():
    global APP
    APP = main.build_application()

    async def record_error(update, context):
        errors.append((getattr(update, "callback_query", None) and update.callback_query.data or "message", context.error))

    APP.add_error_handler(record_error)
    await APP.initialize()
    from database.db import init_db
    await init_db()  # جدول‌ها و مایگریشن‌ها (post_init ممکنه هنوز تموم نشده باشه)
    await seed()

    actors = {CUSTOMER: ["/start shop_1", "/menu", "/cart", "/my_orders", "/help", "/support", "/searchall تیشرت", "/findshop اشبورن", "/start product_1", "/start category_1"],
              SELLER: ["/start", "/myshop", "/neworders", "/support"],
              ADMIN: ["/start", "/admin", "/orders"]}
    queue: deque = deque()
    seen: set = set()
    clicked = 0
    failures: list[tuple[str, str, str]] = []
    dead: list[tuple[int, str]] = []
    counter = [0]

    def harvest(actor: int):
        for c in calls:
            markup = c["markup"]
            if not isinstance(markup, InlineKeyboardMarkup):
                continue
            chat_id = c["chat_id"]
            message_id = c.get("new_id") or c.get("message_id")
            if chat_id is None or message_id is None:
                continue
            for row in markup.inline_keyboard:
                for b in row:
                    key = (chat_id, b.callback_data)
                    if b.callback_data and key not in seen and not SKIP.search(b.callback_data):
                        seen.add(key)
                        queue.append((chat_id, b.callback_data, chat_id, message_id))

    async def run(update, actor):
        errors.clear()
        calls.clear()
        await APP.process_update(update)
        generic = any("یه مشکل غیرمنتظره" in c["text"] for c in calls)
        run.stale = any(c["endpoint"] == "answerCallbackQuery" and "دیگه معتبر نیست" in (c["text"] or "") for c in calls)
        harvest(actor)
        run.last_endpoints = [c["endpoint"] for c in calls]
        return list(errors), generic, any(c["endpoint"] == "answerCallbackQuery" for c in calls)

    only = os.environ.get("CRAWL_CLICKS")
    if only:  # حالت دیباگ: فقط همین دکمه‌ها (جدا با ;) رو به‌ترتیب بزن و همه‌ی تماس‌های API رو چاپ کن
        import logging
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("telegram.ext.ConversationHandler").setLevel(logging.DEBUG)
        for text in ("/start", "/myshop"):
            counter[0] += 1
            await run(command_update(SELLER, text, counter[0]), SELLER)
        for data in only.split(";"):
            counter[0] += 1
            errs, generic, answered = await run(callback_update(SELLER, data, SELLER, 1001, counter[0]), SELLER)
            print("CLICK", data, "->", run.last_endpoints, "errors:", [repr(e[1])[:150] for e in errs], "answered:", answered)
        await APP.shutdown()
        return

    for actor, commands in actors.items():
        for text in commands:
            counter[0] += 1
            errs, generic, _ = await run(command_update(actor, text, counter[0]), actor)
            if errs or generic:
                failures.append((str(actor), text, repr(errs[0][1])[:200] if errs else "generic error message"))
            counter[0] += 1
            await run(command_update(actor, "/cancel", counter[0]), actor)

    while queue:
        actor, data, chat_id, message_id = queue.popleft()
        counter[0] += 1
        clicked += 1
        errs, generic, answered = await run(callback_update(actor, data, chat_id, message_id, counter[0]), actor)
        if errs or generic:
            detail = "".join(traceback.format_exception_only(type(errs[0][1]), errs[0][1])).strip()[:220] if errs else "generic error message"
            failures.append((str(actor), data, detail))
        elif run.stale or not answered:
            dead.append((actor, f"{data}   [{'stale-button reply' if run.stale else ','.join(run.last_endpoints) or 'no api call'}]"))
        counter[0] += 1
        await run(command_update(actor, "/cancel", counter[0]), actor)  # از هر مکالمه‌ی باز بیرون بیا

    print(f"\nclicked {clicked} distinct buttons (+ entry commands) as customer / seller / admin")
    if failures:
        print(f"\n✗ {len(failures)} buttons raise an error:")
        for actor, data, detail in failures:
            print(f"  ✗ [{actor}] {data}\n      {detail}")
    state_bound = re.compile(r"order:confirm|order:ask_discount|discount:type|pay:card_to_card")
    expected = [d for d in dead if state_bound.search(d[1])]
    dead = [d for d in dead if not state_bound.search(d[1])]
    if expected:
        print(f"\nℹ {len(expected)} step-bound buttons answer with the 'expired' notice outside their conversation (expected)")
    if dead:
        print(f"\n☠ {len(dead)} dead buttons (no handler answers):")
        for actor, data in dead:
            print(f"  ☠ [{actor}] {data}")
    if not failures and not dead:
        print("\n✅ every button answered without an error")
    await APP.shutdown()
    sys.exit(1 if failures or dead else 0)


asyncio.run(main_crawl())
