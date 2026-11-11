"""
هندلرهای عمومی مشترک بین بخش‌های مختلف ربات.
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

logger = logging.getLogger(__name__)


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فالبک عمومی /cancel برای لغو هر نوع مکالمه‌ای."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    # آزادسازی رزرو سفارش‌های در حال پرداخت این کاربر
    cancelled_orders = 0
    try:
        from database.db import async_session
        from database.models import Order, OrderStatus
        from services.order_service import cancel_order_and_release_stock
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(
                select(Order).where(
                    Order.user_id == update.effective_user.id,
                    Order.status.in_([OrderStatus.PENDING_PAYMENT]),
                )
            )
            for order in result.scalars().all():
                await cancel_order_and_release_stock(order.id)
                cancelled_orders += 1
    except Exception as e:
        logger.warning(f"cancel_conversation cleanup: {e}")

    context.user_data.clear()
    if update.message:
        text = "❌ عملیات لغو شد."
        if cancelled_orders:
            text += f"\n\n📦 {cancelled_orders} سفارش در انتظار پرداخت هم لغو شد و موجودی آزاد شد."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍 مشاهده محصولات", callback_data="menu:shop")],
            [InlineKeyboardButton("🛒 سبد خرید", callback_data="cart:view")],
            [InlineKeyboardButton("📦 سفارش‌های من", callback_data="order:history")],
            [InlineKeyboardButton("ℹ️ راهنما", callback_data="help:show")],
        ])
        await update.message.reply_text(text, reply_markup=kb)
    elif update.callback_query:
        await update.callback_query.answer()
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍 مشاهده محصولات", callback_data="menu:shop")],
            [InlineKeyboardButton("🛒 سبد خرید", callback_data="cart:view")],
            [InlineKeyboardButton("📦 سفارش‌های من", callback_data="order:history")],
        ])
        await update.callback_query.edit_message_text("❌ عملیات لغو شد.", reply_markup=kb)
    return ConversationHandler.END


async def noop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """برای دکمه‌های صرفاً نمایشی (مثل عدد تعداد در سبد خرید)."""
    await update.callback_query.answer()


async def about_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دکمه 'ℹ️ درباره فروشگرام' — یه popup کوتاه."""
    await update.callback_query.answer(
        "فروشگرام یه پلتفرم فروشگاه‌سازیه؛ هرکسی می‌تونه فقط تو چند دقیقه، فروشگاه تلگرامی خودشو راه بندازه و شروع به فروش کنه 🚀",
        show_alert=True,
    )
