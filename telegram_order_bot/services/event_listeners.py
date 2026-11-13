"""
Event listeners — each listener is registered via `@event_bus.on(Event.XYZ)`.
Now uses NotificationService instead of raw notify_shop_owner / bot.send_message.
"""
from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from services.events import Event, event_bus
from services.notification_service import get_notification_service
from services.monitoring import metrics as m

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# ORDER_CREATED
# ════════════════════════════════════════════════════════════════

@event_bus.on(Event.ORDER_CREATED)
async def on_order_created(**kw):
    """Notify shop owner about new order."""
    bot = kw.get("bot")
    if not bot:
        return
    m.track_event("order_created")
    ns = get_notification_service(bot)
    await ns.notify_order_created(
        shop_id=kw["shop_id"],
        message=kw.get("message", ""),
    )


# ════════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════════
# ORDER_PAID (first-ever or any new paid)
# ════════════════════════════════════════════════════════════════

@event_bus.on(Event.ORDER_PAID)
async def on_order_paid(**kw):
    bot = kw.get("bot")
    if not bot:
        return
    ns = get_notification_service(bot)
    is_first = kw.get("is_first_sale", False)

    if not is_first:
        return  # فروشنده همین الان خودش تایید کرده؛ پیام «سفارش جدید» تکراری و بی‌محتواست
    text = (
        "🎉 <b>اولین فروشت ثبت شد!</b>\n\n"
        "از «🧾 سفارش‌ها» بسته رو برای ارسال آماده کن و «ارسال شد» رو بزن."
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗂 مشاهده سفارش‌ها", callback_data="admin:orders:pending:0")]
    ])
    await ns.send_to_seller(
        kw["shop_id"],
        text,
        reply_markup=kb,
    )


# ════════════════════════════════════════════════════════════════
# ORDER_CONFIRMED
# ════════════════════════════════════════════════════════════════

@event_bus.on(Event.ORDER_CONFIRMED)
async def on_order_confirmed(**kw):
    """Order confirmed — log (could notify buyer)."""
    bot = kw.get("bot")
    if bot:
        ns = get_notification_service(bot)
        await ns.notify_order_confirmed(kw["shop_id"], kw.get("tracking_code", ""))
    else:
        logger.info(f"Order {kw.get('tracking_code')} confirmed")


# ════════════════════════════════════════════════════════════════
# ORDER_CANCELLED
# ════════════════════════════════════════════════════════════════

@event_bus.on(Event.ORDER_CANCELLED)
async def on_order_cancelled(**kw):
    """Notify shop owner order was cancelled."""
    bot = kw.get("bot")
    if not bot:
        logger.info(f"Order {kw.get('tracking_code')} cancelled by {kw.get('cancelled_by')}")
        return

    ns = get_notification_service(bot)
    await ns.notify_order_cancelled(
        shop_id=kw["shop_id"],
        tracking_code=kw.get("tracking_code", ""),
        cancelled_by=kw.get("cancelled_by", "system"),
        reason=kw.get("reason", ""),
    )


# ════════════════════════════════════════════════════════════════
# SELLER_MESSAGE
# ════════════════════════════════════════════════════════════════

@event_bus.on(Event.SELLER_MESSAGE)
async def on_seller_message(**kw):
    """Forward buyer message to seller."""
    bot = kw.get("bot")
    shop_id = kw.get("shop_id")
    message_text = kw.get("message_text", "")
    if bot and shop_id:
        ns = get_notification_service(bot)
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from utils.tg_helpers import escape_html

        who = escape_html(kw.get("buyer_name") or "یه مشتری")
        reply_markup = None
        if kw.get("conv_id"):
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(f"✏️ پاسخ به {kw.get('buyer_name') or 'مشتری'}", callback_data=f"msg:reply:{kw['conv_id']}")]])
        await ns.send_to_seller(
            shop_id,
            f"💬 <b>{who}</b> پیام داد:\n\n{escape_html(message_text)}",
            reply_markup=reply_markup,
        )