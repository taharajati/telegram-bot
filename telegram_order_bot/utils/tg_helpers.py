"""
توابع کمکی برای نمایش/ویرایش پیام‌ها.

چرا لازمه؟
وقتی کاربر بین صفحات مختلف (مثلاً از جزئیات یه محصول با عکس، به لیست محصولات که متنیه)
جابه‌جا می‌شه، تلگرام اجازه نمی‌ده یه پیام عکس‌دار مستقیماً با edit_message_text به پیام متنی
تبدیل بشه و خطای BadRequest می‌ده. این تابع این حالت رو تشخیص می‌ده و به‌جای ارور گرفتن،
پیام قبلی رو حذف و پیام جدید رو می‌فرسته.

امنیت: تمام متن‌های ورودی کاربر قبل از ارسال با parse_mode=HTML escape می‌شن.
"""
from html import escape
from telegram import Update
from telegram.error import BadRequest

from utils.tenant import get_user_shop_id


async def render_view(query, context, text: str, reply_markup=None, photo: str | None = None, parse_mode: str | None = None):
    chat_id = query.message.chat_id

    if photo:
        # برای محصولاتی که عکس دارن همیشه پیام جدید می‌فرستیم (عکس رو نمی‌شه با edit متنی جایگزین کرد)
        try:
            await query.message.delete()
        except Exception:
            pass
        await context.bot.send_photo(chat_id=chat_id, photo=photo, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return

    try:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except BadRequest:
        # احتمالاً پیام قبلی عکس بوده و نمی‌شه به متن تبدیلش کرد
        try:
            await query.message.delete()
        except Exception:
            pass
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)


def escape_html(text: str | None) -> str:
    """Escape user input for safe use in Telegram HTML parse_mode."""
    if not text:
        return ""
    return escape(text, quote=False)


async def get_current_shop_id(update: Update) -> int | None:
    """برگردوندن shop_id کاربر فعلی از روی update — نسخه مرکزی.

    اگر current_shop_id ست نشده، به last_shop_id فالبک می‌زنه.
    همه‌ی هندلرها (menu, cart, order) از همین استفاده می‌کنن.
    """
    tg_user_id = update.effective_user.id
    shop_id = await get_user_shop_id(tg_user_id)
    if shop_id:
        return shop_id

    # Fallback: try last_shop_id
    from database.db import async_session
    from database.models import User
    from utils.tenant import ensure_shop_exists

    async with async_session() as session:
        user = await session.get(User, tg_user_id)
        if user and user.last_shop_id:
            if await ensure_shop_exists(user.last_shop_id):
                return user.last_shop_id

    return None


async def get_current_shop(update: Update):
    """برگردوندن شیء Shop کاربر فعلی."""
    from database.db import async_session
    from database.models import Shop
    shop_id = await get_current_shop_id(update)
    if not shop_id:
        return None
    async with async_session() as session:
        return await session.get(Shop, shop_id)
