"""تست ویجت‌های تلگرام: محدودیت حجم، state، همگام‌سازی خودکار و درخواست‌های ویجت."""
import asyncio
import json
import re
from unittest.mock import AsyncMock

import pytest
from telegram.error import BadRequest

from database.db import async_session
from database.models import Order, OrderItem, OrderStatus, OrderWidget, Shop, ShopOwner, User, utcnow
from services import widgets
from services.order_service import transition_order

CUSTOMER_ID = 5001
SELLER_ID = 6001
CHAT_ID = 5001
WIDGET_MESSAGE_ID = 77


def make_bot():
    """بات ساختگی: sendWidget یک پیام با message_id برمی‌گردونه."""
    bot = AsyncMock()

    async def do_api_request(method, api_kwargs=None, **_):
        if method == "sendWidget":
            return {"message_id": WIDGET_MESSAGE_ID}
        return True

    bot.do_api_request = AsyncMock(side_effect=do_api_request)
    return bot


def calls(bot, method):
    return [c.kwargs["api_kwargs"] for c in bot.do_api_request.call_args_list if c.args[0] == method]


async def settle():
    """اجازه می‌ده taskهای همگام‌سازی بعد از commit تموم بشن."""
    await asyncio.gather(*list(widgets._tasks))


@pytest.fixture
def bot(monkeypatch):
    monkeypatch.setattr(widgets, "SYNC_DELAY", 0.01)
    bot = make_bot()
    widgets.init(bot)
    yield bot
    widgets.init(None)


async def make_order(status=OrderStatus.PENDING_PAYMENT, **extra) -> int:
    async with async_session() as session:
        shop = Shop(name="گل‌فروشی نرگس", status="active", is_active=True)
        session.add(shop)
        await session.flush()
        session.add(User(user_id=CUSTOMER_ID, first_name="سارا"))
        session.add(ShopOwner(user_id=SELLER_ID, shop_id=shop.id, first_name="نرگس"))
        order = Order(
            shop_id=shop.id, user_id=CUSTOMER_ID, tracking_code="2611110042", total_price=450000,
            status=status, payment_method="card_to_card", receiver_name="سارا",
            shipping_address="تهران", phone="09120000000", **extra,
        )
        session.add(order)
        await session.flush()
        session.add(OrderItem(order_id=order.id, product_name="دسته گل", quantity=2, unit_price=225000))
        await session.commit()
        return order.id


# ─── کد ویجت ───────────────────────────────────────────────────

@pytest.mark.parametrize("html", [widgets.ORDER_TRACKER_HTML, widgets.SELLER_DASHBOARD_HTML])
def test_widget_html_fits_telegram_limits(html):
    assert len(html.encode("utf-8")) <= widgets.MAX_HTML_BYTES
    assert widgets.compressed_size(html) <= widgets.MAX_HTML_COMPRESSED


@pytest.mark.parametrize("html", [widgets.ORDER_TRACKER_HTML, widgets.SELLER_DASHBOARD_HTML])
def test_widget_html_avoids_features_telegram_strips(html):
    # پروفایل ۱ ویجت: بدون شبکه، بدون فرم، بدون منابع خارجی
    for forbidden in ("fetch(", "XMLHttpRequest", "<input", "<form", "<iframe", "src=", "@import", "text-shadow", "vh;"):
        assert forbidden not in html
    assert not re.search(r"https?://", html)


# ─── state رهگیری ──────────────────────────────────────────────

@pytest.mark.parametrize("status,step", [
    (OrderStatus.PENDING_PAYMENT, 0),
    (OrderStatus.PAID, 1),
    (OrderStatus.CONFIRMED, 1),
    (OrderStatus.PREPARING, 2),
    (OrderStatus.SHIPPED, 3),
    (OrderStatus.DELIVERED, 4),
])
def test_order_state_maps_status_to_step(status, step):
    order = Order(tracking_code="X1", total_price=1000, status=status)
    state = json.loads(widgets.order_state(order, "فروشگاه"))
    assert state["s"] == step
    assert "x" not in state


def test_order_state_marks_receipt_waiting_and_cancellation():
    waiting = Order(tracking_code="X1", total_price=1000, status=OrderStatus.PENDING_PAYMENT, payment_receipt_at=utcnow())
    assert json.loads(widgets.order_state(waiting))["w"] == 1

    cancelled = Order(tracking_code="X1", total_price=1000, status=OrderStatus.CANCELLED, cancellation_reason="عدم پرداخت")
    state = json.loads(widgets.order_state(cancelled))
    assert state["x"] == 1 and state["q"] == "عدم پرداخت"


def test_order_state_stays_under_telegram_limit_with_long_values():
    order = Order(
        tracking_code="2611110042", total_price=999_999_999, status=OrderStatus.CANCELLED,
        cancellation_reason="دلیل " * 100, tracking_number="1" * 50,
    )
    state = widgets.order_state(order, "نام خیلی طولانی فروشگاه " * 20, items_count=120)
    assert len(state.encode("utf-8")) <= widgets.MAX_STATE_BYTES


# ─── ارسال و همگام‌سازی ────────────────────────────────────────

async def test_send_order_tracker_records_message(bot):
    order_id = await make_order()
    assert await widgets.send_order_tracker(bot, order_id, CHAT_ID)

    sent = calls(bot, "sendWidget")[0]
    assert sent["chat_id"] == CHAT_ID and sent["allow_queries"] is True
    assert json.loads(sent["chat_data"])["n"] == 2
    async with async_session() as session:
        row = (await session.execute(OrderWidget.__table__.select())).one()
    assert (row.order_id, row.chat_id, row.message_id) == (order_id, CHAT_ID, WIDGET_MESSAGE_ID)


async def test_send_order_tracker_reports_failure(bot):
    order_id = await make_order()
    bot.do_api_request = AsyncMock(side_effect=BadRequest("WIDGET_UNSUPPORTED"))
    assert not await widgets.send_order_tracker(bot, order_id, CHAT_ID)


async def test_status_change_updates_widget_automatically(bot):
    order_id = await make_order(status=OrderStatus.CONFIRMED)
    await widgets.send_order_tracker(bot, order_id, CHAT_ID)

    await transition_order(order_id, OrderStatus.PREPARING, actor="seller")
    await settle()

    edit = calls(bot, "editMessageWidgetData")[-1]
    assert (edit["chat_id"], edit["message_id"]) == (CHAT_ID, WIDGET_MESSAGE_ID)
    assert json.loads(edit["chat_data"])["s"] == 2


async def test_status_change_without_widget_sends_nothing(bot):
    order_id = await make_order(status=OrderStatus.CONFIRMED)
    await transition_order(order_id, OrderStatus.PREPARING, actor="seller")
    await settle()
    assert not calls(bot, "editMessageWidgetData")


async def test_deleted_widget_message_is_forgotten(bot):
    order_id = await make_order(status=OrderStatus.PAID)
    await widgets.send_order_tracker(bot, order_id, CHAT_ID)
    bot.do_api_request = AsyncMock(side_effect=BadRequest("Message to edit not found"))

    assert not await widgets.sync_order_tracker(bot, order_id)
    async with async_session() as session:
        assert (await session.execute(OrderWidget.__table__.select())).first() is None


# ─── درخواست‌های ویجت ──────────────────────────────────────────

def widget_query(data, user_id=CUSTOMER_ID, message_id=WIDGET_MESSAGE_ID):
    return {
        "id": "q1", "data": data, "message_id": message_id,
        "from": {"id": user_id, "is_bot": False, "first_name": "سارا"},
        "chat": {"id": CHAT_ID, "type": "private"},
    }


async def test_customer_confirms_delivery_from_widget(bot):
    order_id = await make_order(status=OrderStatus.SHIPPED)
    await widgets.send_order_tracker(bot, order_id, CHAT_ID)

    await widgets.handle_widget_query(bot, widget_query(widgets.Q_ORDER_DELIVERED))
    await settle()

    async with async_session() as session:
        assert (await session.get(Order, order_id)).status == OrderStatus.DELIVERED
    answer = calls(bot, "answerWidgetQuery")[0]
    assert answer["widget_query_id"] == "q1"
    assert json.loads(answer["data"])["s"] == 4
    # فروشنده باخبر می‌شه
    assert bot.send_message.await_args.kwargs["chat_id"] == SELLER_ID


async def test_other_user_cannot_act_on_someone_elses_widget(bot):
    order_id = await make_order(status=OrderStatus.SHIPPED)
    await widgets.send_order_tracker(bot, order_id, CHAT_ID)

    await widgets.handle_widget_query(bot, widget_query(widgets.Q_ORDER_DELIVERED, user_id=9999))
    await settle()

    async with async_session() as session:
        assert (await session.get(Order, order_id)).status == OrderStatus.SHIPPED
    answer = calls(bot, "answerWidgetQuery")[0]
    assert "data" not in answer


async def test_delivery_request_is_ignored_before_shipping(bot):
    order_id = await make_order(status=OrderStatus.PAID)
    await widgets.send_order_tracker(bot, order_id, CHAT_ID)

    await widgets.handle_widget_query(bot, widget_query(widgets.Q_ORDER_DELIVERED))

    async with async_session() as session:
        assert (await session.get(Order, order_id)).status == OrderStatus.PAID
    assert json.loads(calls(bot, "answerWidgetQuery")[0]["data"])["s"] == 1


async def test_unknown_widget_request_is_still_answered(bot):
    await widgets.handle_widget_query(bot, widget_query("garbage"))
    assert calls(bot, "answerWidgetQuery") == [{"widget_query_id": "q1"}]


# ─── داشبورد فروشنده ───────────────────────────────────────────

async def test_seller_dashboard_counts_sales_and_pending_work(bot):
    paid_id = await make_order(status=OrderStatus.PAID)
    async with async_session() as session:
        shop_id = (await session.get(Order, paid_id)).shop_id
        session.add(Order(
            shop_id=shop_id, user_id=CUSTOMER_ID, tracking_code="W2", total_price=100000,
            status=OrderStatus.PENDING_PAYMENT, payment_receipt_at=utcnow(),
            shipping_address="تهران", phone="0912",
        ))
        session.add(Order(
            shop_id=shop_id, user_id=CUSTOMER_ID, tracking_code="W3", total_price=70000,
            status=OrderStatus.CANCELLED, shipping_address="تهران", phone="0912",
        ))
        await session.commit()

    state = json.loads(await widgets.seller_dashboard_state(shop_id))
    assert state["t"] == 450000 and state["o"] == 1  # فقط سفارش پرداخت‌شده
    assert state["d"][-1] == 450000 and len(state["d"]) == len(state["l"]) == 7
    assert state["a"] == 1 and state["p"] == 1

    await widgets.handle_widget_query(bot, widget_query(widgets.Q_SELLER_REFRESH, user_id=SELLER_ID))
    assert json.loads(calls(bot, "answerWidgetQuery")[0]["data"])["t"] == 450000
