"""
ارسال پیام همگانی (Broadcast) به همه‌ی کاربرانی که تاکنون با ربات تعامل داشتن.
"""
import asyncio
import logging

from telegram import Update
from telegram.error import Forbidden, TimedOut, RetryAfter
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import select

from database.db import async_session
from database.models import User
from handlers.admin.panel import admin_only
from utils.tg_helpers import render_view

logger = logging.getLogger(__name__)
ASK_BROADCAST_TEXT = 0

# فاصله‌ی بین ارسال پیام‌ها برای رعایت محدودیت نرخ ارسال تلگرام (حداکثر ~30 پیام در ثانیه)
BROADCAST_DELAY_SECONDS = 0.04


@admin_only
async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await render_view(
        query, context,
        "متن پیام همگانی رو بفرست تا برای همه‌ی کاربران ارسال بشه:\n(برای لغو /cancel)",
        None,
    )
    return ASK_BROADCAST_TEXT


@admin_only
async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    status_message = await update.message.reply_text("در حال ارسال پیام برای کاربران... ⏳")

    async with async_session() as session:
        result = await session.execute(select(User.user_id).where(User.is_blocked.is_(False)))
        user_ids = [row[0] for row in result.all()]

    sent, failed = 0, 0
    blocked_ids = []
    for uid in user_ids:
        try:
            await context.bot.send_message(chat_id=uid, text=text)
            sent += 1
        except Forbidden:
            failed += 1
            blocked_ids.append(uid)  # Bot blocked by user
        except (TimedOut, RetryAfter):
            failed += 1
            await asyncio.sleep(0.2)  # Extra delay on rate limit
        except Exception as e:
            failed += 1
            logger.warning("Broadcast failed to user %d: %s", uid, e)
        await asyncio.sleep(BROADCAST_DELAY_SECONDS)

    # Mark users who blocked the bot
    if blocked_ids:
        async with async_session() as session:
            for uid in blocked_ids:
                user = await session.get(User, uid)
                if user:
                    user.is_blocked = True
            await session.commit()
        logger.info("Marked %d users as blocked after broadcast", len(blocked_ids))

    await status_message.edit_text(
        f"ارسال تموم شد ✅\nموفق: {sent}\nناموفق: {failed}\n"
        + (f"\n⚠️ {len(blocked_ids)} کاربر ربات را بلاک کرده بودند (مسدود شدند)." if blocked_ids else "")
    )
    return ConversationHandler.END


async def broadcast_shop_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start broadcast to users of a specific shop."""
    query = update.callback_query
    await query.answer()
    shop_id = int(query.data.split(":")[3])
    context.user_data["broadcast_shop_id"] = shop_id

    async with async_session() as session:
        from database.models import Shop
        shop = await session.get(Shop, shop_id)
        shop_name = shop.name if shop else f"ID:{shop_id}"

    await render_view(
        query, context,
        f"📣 پیام تبلیغاتی برای کاربران فروشگاه «{shop_name}»\n\n"
        "متن پیام رو بفرست (برای لغو /cancel):",
        None,
    )
    return ASK_BROADCAST_TEXT


@admin_only
async def send_broadcast_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send broadcast to users who visited a specific shop."""
    text = update.message.text
    shop_id = context.user_data.get("broadcast_shop_id")
    if not shop_id:
        await update.message.reply_text("❌ فروشگاه مشخص نشده.")
        return ConversationHandler.END

    status_message = await update.message.reply_text("در حال ارسال پیام برای کاربران این فروشگاه... ⏳")

    async with async_session() as session:
        result = await session.execute(
            select(User.user_id).where(
                User.is_blocked.is_(False),
                User.last_shop_id == shop_id,
            )
        )
        user_ids = [row[0] for row in result.all()]

        from database.models import Shop
        shop = await session.get(Shop, shop_id)
        shop_name = shop.name if shop else f"ID:{shop_id}"

    sent, failed = 0, 0
    blocked_ids = []
    for uid in user_ids:
        try:
            await context.bot.send_message(chat_id=uid, text=text)
            sent += 1
        except Forbidden:
            failed += 1
            blocked_ids.append(uid)
        except (TimedOut, RetryAfter):
            failed += 1
            await asyncio.sleep(0.2)
        except Exception as e:
            failed += 1
            logger.warning("Broadcast to shop %d failed for user %d: %s", shop_id, uid, e)
        await asyncio.sleep(BROADCAST_DELAY_SECONDS)

    if blocked_ids:
        async with async_session() as session:
            for uid in blocked_ids:
                user = await session.get(User, uid)
                if user:
                    user.is_blocked = True
            await session.commit()
        logger.info("Marked %d users as blocked after shop broadcast", len(blocked_ids))

    await status_message.edit_text(
        f"📣 ارسال تبلیغ برای «{shop_name}» تمام شد ✅\n"
        f"موفق: {sent}\n"
        f"ناموفق: {failed}\n"
        + (f"\n⚠️ {len(blocked_ids)} کاربر ربات را بلاک کرده بودند." if blocked_ids else "")
    )
    context.user_data.pop("broadcast_shop_id", None)
    return ConversationHandler.END
