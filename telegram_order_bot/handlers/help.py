"""
راهنمای دستورات ربات بر اساس نقش.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from handlers.admin.panel import _get_shop_id_for_admin
from utils.helpers import is_super_admin


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = is_super_admin(user_id)
    shop_id = await _get_shop_id_for_admin(user_id)

    lines = ["📖 راهنمای دستورات\n"]

    lines.append("👤 کاربری (همه):")
    lines.append("/start — منوی اصلی و ورود به فروشگاه")
    lines.append("/menu — مشاهده دسته‌بندی‌ها و محصولات")
    lines.append("/cart — سبد خرید من")
    lines.append("/my_orders — تاریخچه سفارش‌های من")
    lines.append("/help — این راهنما")
    lines.append("/cancel — لغو عملیات جاری")

    if is_admin:
        lines.append("\n🔧 ادمین کل:")
        lines.append("/admin — پنل مدیریت کل")
        lines.append("/orders — سفارش‌های در حال پیگیری")
    elif shop_id:
        lines.append("\n🏪 فروشنده:")
        lines.append("/myshop — پنل مدیریت فروشگاه")
        lines.append("/neworders — سفارش‌های جدید")
        lines.append("/my_panel — تنظیمات فروشنده و پرداخت")
        lines.append("/support — پیام‌های مشتریان")
    else:
        lines.append("\n💡 برای ساخت فروشگاه: /start → دکمه «🏪 می‌خوام فروشگاه بسازم»")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Version for callback_query (used from cancel_conversation inline button)."""
    query = update.callback_query
    await query.answer()
    # Reuse the same logic
    user_id = update.effective_user.id
    is_admin = is_super_admin(user_id)
    shop_id = await _get_shop_id_for_admin(user_id)

    lines = ["📖 راهنمای دستورات\n"]

    lines.append("👤 کاربری (همه):")
    lines.append("/start — منوی اصلی و ورود به فروشگاه")
    lines.append("/menu — مشاهده دسته‌بندی‌ها و محصولات")
    lines.append("/cart — سبد خرید من")
    lines.append("/my_orders — تاریخچه سفارش‌های من")
    lines.append("/help — این راهنما")
    lines.append("/cancel — لغو عملیات جاری")

    if is_admin:
        lines.append("\n🔧 ادمین کل:")
        lines.append("/admin — پنل مدیریت کل")
        lines.append("/orders — سفارش‌های در حال پیگیری")
    elif shop_id:
        lines.append("\n🏪 فروشنده:")
        lines.append("/myshop — پنل مدیریت فروشگاه")
        lines.append("/neworders — سفارش‌های جدید")
        lines.append("/my_panel — تنظیمات فروشنده و پرداخت")
        lines.append("/support — پیام‌های مشتریان")
    else:
        lines.append("\n💡 برای ساخت فروشگاه: /start → دکمه «🏪 می‌خوام فروشگاه بسازم»")

    await query.edit_message_text("\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="nav:main")]]))
