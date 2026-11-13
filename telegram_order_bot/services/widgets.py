"""
ویجت‌های تلگرام (Bot API 10.4) — پیام‌های تعاملی که داخل خود چت اجرا می‌شن.

دو ویجت داریم:
  • رهگیری زنده سفارش (مشتری): نوار وضعیت که با هر تغییر وضعیت درجا به‌روز می‌شه.
  • داشبورد فروش (فروشنده): نمودار فروش ۷ روز اخیر و سفارش‌های منتظر اقدام.

python-telegram-bot هنوز متدهای ویجت رو نداره، پس مستقیم با do_api_request صدا زده می‌شن.
کد HTML هر ویجت ثابته (پوشه‌ی widgets/) و فقط «state» (chat_data، حداکثر ۱۰۲۴ بایت) عوض می‌شه.
"""
from __future__ import annotations

import asyncio
import time
import json
import logging
import zlib
from datetime import timedelta
from pathlib import Path

from sqlalchemy import event, func, select
from sqlalchemy.orm import Session, object_session
from telegram.error import BadRequest, TelegramError

import config
from database.db import async_session
from database.models import Order, OrderStatus, OrderWidget, Shop, ShopOwner, utcnow
from utils.helpers import format_price

logger = logging.getLogger(__name__)

WIDGET_DIR = Path(__file__).resolve().parent.parent / "widgets"

# تلگرام ممکنه ویجت رو برای ربات ببنده (INPUT_MEDIA_WIDGET_NOT_ALLOWED)؛ اون موقع دکمه‌های ویجتی
# پنهان می‌شن تا کاربر فقط خطا نبینه، و بعد از BLOCK_SECONDS دوباره امتحان می‌شه.
BLOCK_SECONDS = 1800
_blocked_until = 0.0


def available() -> bool:
    """آیا الان باید دکمه‌های ویجتی نشون داده بشن؟"""
    return config.WIDGETS_ENABLED and time.monotonic() >= _blocked_until


def _note_failure(error: Exception) -> None:
    global _blocked_until
    if "WIDGET_NOT_ALLOWED" in str(error).upper():
        _blocked_until = time.monotonic() + BLOCK_SECONDS
        logger.warning("Telegram refused widgets for this bot; hiding widget buttons for %s s", BLOCK_SECONDS)

# محدودیت‌های تلگرام
MAX_HTML_BYTES = 32768
MAX_HTML_COMPRESSED = 4096
MAX_STATE_BYTES = 1024

# data درخواست‌هایی که ویجت‌ها می‌فرستن
Q_ORDER_DELIVERED = "o:d"
Q_ORDER_REFRESH = "o:r"
Q_SELLER_REFRESH = "s:r"


def load_widget_html(name: str) -> str:
    return (WIDGET_DIR / f"{name}.html").read_text(encoding="utf-8")


def compressed_size(html: str) -> int:
    return len(zlib.compress(html.encode("utf-8"), 9))


ORDER_TRACKER_HTML = load_widget_html("order_tracker")
SELLER_DASHBOARD_HTML = load_widget_html("seller_dashboard")
SELLER_INVENTORY_HTML = load_widget_html("seller_inventory")

INVENTORY_PAGE_SIZE = 6
INVENTORY_PREFIX = "v:"  # v:<action>:<id|page>:<page> — action: + - t(مخفی/نمایش) g(صفحه)


async def _call(bot, method: str, **params):
    return await bot.do_api_request(method, api_kwargs={k: v for k, v in params.items() if v is not None})


def _dump_state(state: dict) -> str:
    return json.dumps(state, ensure_ascii=False, separators=(",", ":"))


# ════════════════════════════════════════════════════════════════
# رهگیری زنده سفارش
# ════════════════════════════════════════════════════════════════

_STEP = {
    OrderStatus.PENDING_PAYMENT: 0,
    OrderStatus.PENDING: 0,
    OrderStatus.PAID: 1,
    OrderStatus.CONFIRMED: 1,
    OrderStatus.PREPARING: 2,
    OrderStatus.SHIPPED: 3,
    OrderStatus.DELIVERED: 4,
}
_ENDED = {
    OrderStatus.CANCELLED: 1,
    OrderStatus.CARD_PAYMENT_REJECTED: 2,
    OrderStatus.REFUNDED: 3,
}


def order_state(order: Order, shop_name: str = "", items_count: int = 0) -> str:
    """state ویجت رهگیری — کلیدها کوتاهن چون سقف ۱۰۲۴ بایته."""
    state = {
        "c": order.tracking_code,
        "sh": (shop_name or "")[:40],
        "s": _STEP.get(order.status, 0),
        "t": format_price(order.total_price),
    }
    ended = _ENDED.get(order.status)
    if ended:
        state["x"] = ended
        if order.cancellation_reason:
            state["q"] = order.cancellation_reason[:100]
    if order.status == OrderStatus.PENDING_PAYMENT and (order.payment_receipt_at or order.payment_receipt_file_id):
        state["w"] = 1
    if items_count:
        state["n"] = items_count
    if order.tracking_number:
        state["p"] = order.tracking_number
    return _dump_state(state)


async def _load_order_state(order_id: int) -> tuple[Order | None, str | None]:
    from database.models import OrderItem

    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order:
            return None, None
        shop = await session.get(Shop, order.shop_id)
        items_count = (await session.execute(
            select(func.coalesce(func.sum(OrderItem.quantity), 0)).where(OrderItem.order_id == order_id)
        )).scalar_one()
    return order, order_state(order, shop.name if shop else "", int(items_count or 0))


async def send_order_tracker(bot, order_id: int, chat_id: int) -> bool:
    """ویجت رهگیری رو می‌فرسته و پیامش رو برای به‌روزرسانی‌های بعدی ثبت می‌کنه."""
    if not available():
        return False
    order, state = await _load_order_state(order_id)
    if not order:
        return False
    try:
        msg = await _call(
            bot, "sendWidget",
            chat_id=chat_id,
            html=ORDER_TRACKER_HTML,
            chat_data=state,
            allow_queries=True,
            caption=f"📍 رهگیری زنده سفارش #{order.tracking_code}",
        )
    except TelegramError as e:
        _note_failure(e)
        logger.warning("sendWidget (order tracker) failed for order %s: %s", order_id, e)
        return False

    message_id = msg.get("message_id") if isinstance(msg, dict) else getattr(msg, "message_id", None)
    if not message_id:
        return False
    async with async_session() as session:
        row = (await session.execute(select(OrderWidget).where(OrderWidget.order_id == order_id))).scalar_one_or_none()
        if row:
            row.chat_id, row.message_id = chat_id, message_id
        else:
            session.add(OrderWidget(order_id=order_id, chat_id=chat_id, message_id=message_id))
        await session.commit()
    return True


async def sync_order_tracker(bot, order_id: int) -> bool:
    """state ویجت رهگیری سفارش رو با وضعیت فعلی یکی می‌کنه (اگه ویجتی فرستاده شده باشه)."""
    if not available():
        return False
    async with async_session() as session:
        row = (await session.execute(select(OrderWidget).where(OrderWidget.order_id == order_id))).scalar_one_or_none()
    if not row:
        return False
    order, state = await _load_order_state(order_id)
    if not order:
        return False
    try:
        await _call(bot, "editMessageWidgetData", chat_id=row.chat_id, message_id=row.message_id, chat_data=state)
    except BadRequest as e:
        text = str(e).lower()
        if "not modified" in text:
            return True
        if "not found" in text or "can't be edited" in text:
            # مشتری پیام ویجت رو پاک کرده — دیگه دنبالش نمی‌ریم
            async with async_session() as session:
                stale = await session.get(OrderWidget, row.id)
                if stale:
                    await session.delete(stale)
                    await session.commit()
        logger.warning("editMessageWidgetData failed for order %s: %s", order_id, e)
        return False
    except TelegramError as e:
        logger.warning("editMessageWidgetData failed for order %s: %s", order_id, e)
        return False
    return True


# ─── همگام‌سازی خودکار ─────────────────────────────────────────
# وضعیت سفارش از چند مسیر عوض می‌شه (فروشنده، مشتری، کرون لغو خودکار، ...). به‌جای صدا زدن
# sync از تک‌تک اون‌ها، تغییر ستون‌های مؤثر رو روی خود مدل می‌گیریم و بعد از commit همگام می‌کنیم.

_DIRTY_KEY = "widget_dirty_orders"
# چند تغییر پشت‌سرهم روی یک سفارش یک ویرایش می‌شن (editMessageWidgetData جزو سقف ارسال باته)
SYNC_DELAY = 0.3
_bot = None
_tasks: set[asyncio.Task] = set()
_pending: set[int] = set()


def init(bot) -> None:
    """در استارتاپ صدا زده می‌شه تا همگام‌سازی خودکار به بات دسترسی داشته باشه."""
    global _bot
    _bot = bot


def _mark_dirty(target: Order, value, oldvalue, initiator) -> None:
    if value == oldvalue or target.id is None:
        return
    session = object_session(target)
    if session is not None:
        session.info.setdefault(_DIRTY_KEY, set()).add(target.id)


for _attr in (Order.status, Order.tracking_number, Order.payment_receipt_at):
    event.listen(_attr, "set", _mark_dirty)


@event.listens_for(Session, "after_commit")
def _sync_after_commit(session: Session) -> None:
    order_ids = session.info.pop(_DIRTY_KEY, None)
    if not order_ids or _bot is None or not available():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    for order_id in order_ids - _pending:
        _pending.add(order_id)
        task = loop.create_task(_sync_later(_bot, order_id))
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)


async def _sync_later(bot, order_id: int) -> None:
    try:
        await asyncio.sleep(SYNC_DELAY)
    finally:
        _pending.discard(order_id)
    try:
        await sync_order_tracker(bot, order_id)
    except Exception:
        logger.exception("Widget sync failed for order %s", order_id)


@event.listens_for(Session, "after_rollback")
def _forget_after_rollback(session: Session) -> None:
    session.info.pop(_DIRTY_KEY, None)


# ════════════════════════════════════════════════════════════════
# داشبورد فروشنده
# ════════════════════════════════════════════════════════════════

_PAID_STATUSES = (
    OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.PREPARING,
    OrderStatus.SHIPPED, OrderStatus.DELIVERED,
)
_TO_SHIP_STATUSES = (OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.PREPARING)
# datetime.weekday(): دوشنبه = 0
_WEEKDAY_FA = ["د", "س", "چ", "پ", "ج", "ش", "ی"]
_TEHRAN_OFFSET = timedelta(hours=3, minutes=30)


async def seller_dashboard_state(shop_id: int) -> str:
    """state داشبورد: فروش روزانه‌ی ۷ روز اخیر (به وقت تهران) + سفارش‌های منتظر اقدام."""
    now_local = utcnow() + _TEHRAN_OFFSET
    today = now_local.date()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    since_utc = utcnow() - timedelta(days=8)

    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
        recent = (await session.execute(
            select(Order.created_at, Order.total_price).where(
                Order.shop_id == shop_id,
                Order.status.in_(_PAID_STATUSES),
                Order.created_at >= since_utc,
            )
        )).all()
        awaiting_approval = (await session.execute(
            select(func.count(Order.id)).where(
                Order.shop_id == shop_id,
                Order.status == OrderStatus.PENDING_PAYMENT,
                Order.payment_receipt_at.is_not(None),
            )
        )).scalar_one()
        to_ship = (await session.execute(
            select(func.count(Order.id)).where(Order.shop_id == shop_id, Order.status.in_(_TO_SHIP_STATUSES))
        )).scalar_one()

    revenue = {d: 0 for d in days}
    orders_count = 0
    for created_at, total in recent:
        day = (created_at + _TEHRAN_OFFSET).date()
        if day in revenue:
            revenue[day] += int(total or 0)
            orders_count += 1

    return _dump_state({
        "n": (shop.name if shop else "")[:40],
        "d": [revenue[d] for d in days],
        "l": [_WEEKDAY_FA[d.weekday()] for d in days],
        "t": sum(revenue.values()),
        "o": orders_count,
        "a": int(awaiting_approval or 0),
        "p": int(to_ship or 0),
        "u": now_local.strftime("%H:%M"),
    })


async def send_seller_dashboard(bot, shop_id: int, chat_id: int) -> bool:
    if not available():
        return False
    state = await seller_dashboard_state(shop_id)
    try:
        await _call(
            bot, "sendWidget",
            chat_id=chat_id,
            html=SELLER_DASHBOARD_HTML,
            chat_data=state,
            allow_queries=True,
            caption="📊 داشبورد زنده فروشگاه",
        )
    except TelegramError as e:
        _note_failure(e)
        logger.warning("sendWidget (seller dashboard) failed for shop %s: %s", shop_id, e)
        return False
    return True


# ════════════════════════════════════════════════════════════════
# موجودی سریع فروشنده: افزایش/کاهش موجودی و مخفی‌کردن محصول توی یک پیام
# ════════════════════════════════════════════════════════════════

def _short_name(name: str, limit: int = 15) -> str:
    name = (name or "").strip()
    return name if len(name) <= limit else name[: limit - 1].rstrip() + "…"


async def inventory_state(shop_id: int, page: int = 0) -> str:
    """state ویجت موجودی: یک صفحه‌ی ۶تایی از محصولات (سقف state ۱۰۲۴ بایته)."""
    from database.models import Product

    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
        total = (await session.execute(select(func.count(Product.id)).where(Product.shop_id == shop_id))).scalar_one()
        pages = max(1, -(-total // INVENTORY_PAGE_SIZE))
        page = max(0, min(page, pages - 1))
        products = (await session.execute(
            select(Product).where(Product.shop_id == shop_id)
            .order_by(Product.id.desc()).offset(page * INVENTORY_PAGE_SIZE).limit(INVENTORY_PAGE_SIZE)
        )).scalars().all()

    return _dump_state({
        "s": _short_name(shop.name if shop else "", 24),
        "g": page,
        "m": pages,
        "t": int(total),
        # [id, اسم کوتاه, موجودی, رزرو, قیمت (هزار تومان), فعال]
        "p": [[p.id, _short_name(p.name), int(p.stock), int(p.reserved_stock), int(p.price // 1000), 1 if p.is_active else 0] for p in products],
    })


async def send_seller_inventory(bot, shop_id: int, chat_id: int) -> bool:
    if not available():
        return False
    state = await inventory_state(shop_id, 0)
    try:
        await _call(bot, "sendWidget", chat_id=chat_id, html=SELLER_INVENTORY_HTML, chat_data=state,
                    allow_queries=True, caption="📊 موجودی سریع: با + و − موجودی رو عوض کن، با 👁 محصول رو مخفی کن")
    except TelegramError as e:
        _note_failure(e)
        logger.warning("sendWidget (seller inventory) failed for shop %s: %s", shop_id, e)
        return False
    return True


async def _apply_inventory_action(bot, shop_id: int, action: str, product_id: int) -> None:
    """یک تغییر روی محصول؛ موجودی هیچ‌وقت زیر تعداد رزروشده یا صفر نمی‌ره."""
    from database.models import Product

    async with async_session() as session:
        product = (await session.execute(
            select(Product).where(Product.id == product_id, Product.shop_id == shop_id).with_for_update()
        )).scalar_one_or_none()
        if not product:
            return
        was_sold_out = product.available_stock <= 0
        if action == "+":
            product.stock += 1
        elif action == "-":
            product.stock = max(int(product.reserved_stock), product.stock - 1, 0)
        elif action == "t":
            product.is_active = not product.is_active
        await session.commit()
        restocked = was_sold_out and product.available_stock > 0
    if restocked:
        from handlers.admin.products import _check_and_notify_restock
        async with async_session() as session:
            await _check_and_notify_restock(session, product_id, shop_id, bot)


async def _answer_inventory_query(bot, user_id: int, chat_id: int | None, message_id: int | None, data: str) -> str | None:
    parts = data.split(":")
    if len(parts) != 4:
        return None
    action = parts[1]
    try:
        target, page = int(parts[2]), int(parts[3])
    except ValueError:
        return None
    async with async_session() as session:
        owner = (await session.execute(select(ShopOwner).where(ShopOwner.user_id == user_id).limit(1))).scalar_one_or_none()
    if not owner:
        return None  # from رو تلگرام تأیید می‌کنه؛ فقط صاحب فروشگاه اجازه‌ی تغییر داره

    if action == "g":
        page = target
    elif action in ("+", "-", "t"):
        await _apply_inventory_action(bot, owner.shop_id, action, target)
    else:
        return None

    state = await inventory_state(owner.shop_id, page)
    if chat_id is not None and message_id is not None:
        try:  # state رو نگه می‌داریم تا اگه ویجت دوباره ساخته شد، قدیمی نباشه
            await _call(bot, "editMessageWidgetData", chat_id=chat_id, message_id=message_id, chat_data=state)
        except TelegramError:
            pass
    return state


# ════════════════════════════════════════════════════════════════
# درخواست‌های ویجت (widget_query)
# ════════════════════════════════════════════════════════════════

async def _answer_order_query(bot, user_id: int, chat_id: int | None, message_id: int | None, data: str) -> str | None:
    if chat_id is None or message_id is None:
        return None
    async with async_session() as session:
        row = (await session.execute(
            select(OrderWidget).where(OrderWidget.chat_id == chat_id, OrderWidget.message_id == message_id)
        )).scalar_one_or_none()
        order = await session.get(Order, row.order_id) if row else None
    # from رو تلگرام تأیید می‌کنه؛ data ورودی نامطمئنه و فقط نوع عمل رو مشخص می‌کنه
    if not order or order.user_id != user_id:
        return None

    if data == Q_ORDER_DELIVERED and order.status == OrderStatus.SHIPPED:
        from handlers.admin.orders import notify_seller_delivered
        from services.order_service import transition_order

        try:
            order = await transition_order(order.id, OrderStatus.DELIVERED, actor="customer", bot=bot)
        except ValueError as e:
            logger.info("Widget delivery confirm rejected for order %s: %s", order.id, e)
        else:
            await notify_seller_delivered(bot, order)

    _, state = await _load_order_state(order.id)
    return state


async def _answer_seller_query(user_id: int) -> str | None:
    async with async_session() as session:
        owner = (await session.execute(
            select(ShopOwner).where(ShopOwner.user_id == user_id).limit(1)
        )).scalar_one_or_none()
    if not owner:
        return None
    return await seller_dashboard_state(owner.shop_id)


async def handle_widget_query(bot, widget_query: dict) -> None:
    """به درخواست یک ویجت جواب می‌ده. هر درخواست باید ظرف ۱۵ ثانیه answer بشه."""
    query_id = widget_query.get("id")
    data = widget_query.get("data") or ""
    user_id = (widget_query.get("from") or {}).get("id")
    chat_id = (widget_query.get("chat") or {}).get("id")
    answer = None
    try:
        if data in (Q_ORDER_DELIVERED, Q_ORDER_REFRESH):
            answer = await _answer_order_query(bot, user_id, chat_id, widget_query.get("message_id"), data)
        elif data == Q_SELLER_REFRESH:
            answer = await _answer_seller_query(user_id)
        elif data.startswith(INVENTORY_PREFIX):
            answer = await _answer_inventory_query(bot, user_id, chat_id, widget_query.get("message_id"), data)
    except Exception:
        logger.exception("Widget query %r failed", data)
    try:
        await _call(bot, "answerWidgetQuery", widget_query_id=query_id, data=answer)
    except TelegramError as e:
        logger.warning("answerWidgetQuery failed: %s", e)
