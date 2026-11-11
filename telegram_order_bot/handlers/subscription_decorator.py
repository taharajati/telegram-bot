"""
دکوریتور مرکزی محدودیت دسترسی بر اساس اشتراک.
قاعده: فقط روی مسیرهای مشتری (مرور، سبد، سفارش جدید) اعمال می‌شه.
روی مسیر خرید اشتراک و مشاهده سفارش‌های قبلی نه.
"""
import functools
import logging

from telegram import Update
from telegram.ext import ContextTypes

from database.db import async_session
from database.models import ShopOwner
from services.subscription import has_active_subscription, get_current_subscription

logger = logging.getLogger(__name__)

SUSPENDED_MESSAGE = (
    "🚫 فروشگاه شما موقتاً غیرفعال شده‌است.\\n"
    "برای فعال‌سازی مجدد، اشتراک خود را تمدید کنید:"
)


def require_active_subscription(customer_handler):
    """
    دکوریتور برای مسیرهای مشتری (مرور، سبد خرید، ثبت سفارش جدید).
    اگه فروشنده تعلیق شده باشه یا اشتراک نداشته باشه → پیام خطا نشون می‌ده
    و اجازه ادامه نمی‌ده.

    مسیرهای استثنا (خرید اشتراک، مشاهده سفارش‌های قبلی) این دکوریتور رو ندارن.
    """
    @functools.wraps(customer_handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id

        async with async_session() as session:
            owner = await session.execute(
                __import__("sqlalchemy").select(ShopOwner).where(ShopOwner.user_id == user_id)
            )
            owner = owner.scalar_one_or_none()

            if not owner:
                # مشتری عادی — مسیر مشتری رو دسترسی نداره ولی مشکلی نیست
                # چون این دکوریتور فقط برای فروشنده‌ها کاربرد داره
                return await customer_handler(update, context)

            shop_id = owner.shop_id

            # چک وضعیت فروشگاه
            from database.models import Shop
            shop = await session.get(Shop, shop_id)
            if not shop:
                return await customer_handler(update, context)

            if shop.status == "suspended":
                # فروشنده تعلیق شده — اجازه دسترسی به محتوای فروشگاه رو نداره
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                from config import CURRENCY_LABEL

                # بررسی کن ببینیم اصلاً اشتراکی داره یا نه
                sub = await get_current_subscription(shop_id, session)

                text = (
                    "🚫 فروشگاه شما به دلیل اتمام اشتراک غیرفعال شده‌است.\\n\\n"
                )
                if sub and sub.is_expired:
                    text += (
                        f"📅 آخرین اشتراک شما در {sub.end_date.strftime('%Y-%m-%d')} به پایان رسیده.\\n"
                    )
                text += (
                    "✅ برای فعال‌سازی دوباره، از دکمه زیر اشتراک جدید تهیه کنید:"
                )

                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 خرید اشتراک جدید", callback_data="seller:subscription:show")],
                ])

                if update.callback_query:
                    await update.callback_query.answer()
                    await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
                elif update.message:
                    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
                return

            # shop.status == "active" -> اجازه ادامه
            return await customer_handler(update, context)

    return wrapper
