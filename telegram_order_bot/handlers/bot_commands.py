"""
مدیریت منوی دستورات ربات بر اساس نقش (BotCommandScope).

سه سطح:
- پیش‌فرض (مشتری): ۶ دستور پایه
- فروشنده: دستورات مشتری + دستورات فروشنده
- ادمین: همه دستورات

Telegram Bot API اجازه می‌ده برای هر chat_id منوی جداگانه تنظیم کنیم.
"""
import logging

from telegram import Bot, BotCommand, BotCommandScopeChat, BotCommandScopeDefault

logger = logging.getLogger(__name__)

# ─── لیست دستورات ────────────────────────────────────────────

CUSTOMER_COMMANDS: list[BotCommand] = [
    BotCommand("start", "🏠 شروع"),
    BotCommand("help", "❓ راهنما"),
    BotCommand("menu", "🛍 محصولات"),
    BotCommand("search", "🔍 جستجوی محصول"),
    BotCommand("cart", "🛒 سبد خرید"),
    BotCommand("my_orders", "📦 سفارش‌های من"),
    BotCommand("support", "💬 پشتیبانی"),
    BotCommand("cancel", "❌ لغو"),
]

SELLER_COMMANDS: list[BotCommand] = [
    BotCommand("myshop", "پنل مدیریت فروشگاه"),
    BotCommand("neworders", "سفارش‌های جدید"),
    BotCommand("my_panel", "تنظیمات فروشنده و پرداخت"),
]

ADMIN_COMMANDS: list[BotCommand] = [
    BotCommand("admin", "پنل مدیریت کل"),
    BotCommand("orders", "مدیریت سفارش‌ها"),
]


# ─── توابع تنظیم منو ──────────────────────────────────────────

async def set_default_menu(bot: Bot) -> None:
    """تنظیم منوی پیش‌فرض (مشتری‌ها) برای همه کاربران."""
    await bot.set_my_commands(CUSTOMER_COMMANDS, scope=BotCommandScopeDefault())
    logger.info("منوی پیش‌فرض (مشتری) تنظیم شد")


async def set_seller_menu(bot: Bot, seller_chat_id: int) -> None:
    """تنظیم منوی فروشنده برای یک chat_id خاص."""
    commands = CUSTOMER_COMMANDS + SELLER_COMMANDS
    await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=seller_chat_id))
    logger.info("منوی فروشنده برای %s تنظیم شد", seller_chat_id)


async def set_admin_menu(bot: Bot, admin_chat_id: int) -> None:
    """تنظیم منوی ادمین برای یک chat_id خاص."""
    commands = CUSTOMER_COMMANDS + SELLER_COMMANDS + ADMIN_COMMANDS
    await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=admin_chat_id))
    logger.info("منوی ادمین برای %s تنظیم شد", admin_chat_id)


async def delete_seller_menu(bot: Bot, seller_chat_id: int) -> None:
    """حذف منوی اختصاصی فروشنده (برگشت به منوی پیش‌فرض مشتری)."""
    await bot.delete_my_commands(scope=BotCommandScopeChat(chat_id=seller_chat_id))
    logger.info("منوی فروشنده برای %s حذف شد (برگشت به پیش‌فرض)", seller_chat_id)


async def setup_startup_menus(bot: Bot) -> None:
    """تنظیم منوی ادمین‌ها هنگام شروع ربات."""
    from config import ADMIN_IDS
    for admin_id in ADMIN_IDS:
        try:
            await set_admin_menu(bot, admin_id)
        except Exception as e:
            logger.warning("خطا در تنظیم منوی ادمین %s: %s", admin_id, e)
