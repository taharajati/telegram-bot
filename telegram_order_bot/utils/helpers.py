"""توابع کمکی عمومی."""
import random
import string
from datetime import datetime

import jdatetime

import config

_EN_TO_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def to_persian_digits(text: str | int | float) -> str:
    return str(text).translate(_EN_TO_FA_DIGITS)


def format_price(amount: float) -> str:
    """فرمت قیمت: ۱۲۰٬۰۰۰ تومان"""
    amount = int(round(amount))
    s = f"{amount:,}"
    return f"{to_persian_digits(s)} {config.CURRENCY_LABEL}"


def short_price(amount: float) -> str:
    """قیمت کوتاه برای روی دکمه‌ها: ۲ میلیون، ۴۵۰ هزار، ۹۹۰ تومان."""
    amount = int(round(amount))
    if amount >= 1_000_000:
        value = amount / 1_000_000
        text = f"{value:.1f}".rstrip("0").rstrip(".").replace(".", "٫")
        return f"{to_persian_digits(text)} میلیون"
    if amount >= 1000:
        return f"{to_persian_digits(round(amount / 1000))} هزار"
    return f"{to_persian_digits(amount)} تومان"


_EXTRA_HISTORY_LABELS = {
    "receipt_uploaded": "🧾 رسید ثبت شد",
    "receipt_retry_uploaded": "🔄 رسید جدید ثبت شد",
}


def history_line(entry) -> str:
    """یک خط تاریخچه‌ی وضعیت سفارش: تاریخ شمسی + برچسب فارسی (نه «paid توسط admin»)."""
    from database.models import ORDER_STATUS_LABELS
    label = _EXTRA_HISTORY_LABELS.get(entry.status) or ORDER_STATUS_LABELS.get(entry.status, entry.status)
    when = to_jalali(entry.changed_at) if entry.changed_at else ""
    reason = entry.get_meta().get("reason", "")
    return f"  • {when} — {label}" + (f" ({reason})" if reason else "")


def generate_tracking_code() -> str:
    now = datetime.utcnow()
    date_part = now.strftime("%y%m%d")
    rand_part = "".join(random.choices(string.digits, k=4))
    return date_part + rand_part


def to_jalali(dt: datetime) -> str:
    try:
        return to_persian_digits(jdatetime.datetime.fromgregorian(datetime=dt).strftime("%Y/%m/%d %H:%M"))
    except Exception:
        return to_persian_digits(dt.strftime("%Y-%m-%d %H:%M"))


def is_super_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


async def notify_shop_owner(bot, shop_id: int, message: str):
    """
    ارسال پیام به صاحب فروشگاه (اولین owner).
    """
    from sqlalchemy import select
    from database.db import async_session
    from database.models import ShopOwner

    async with async_session() as session:
        result = await session.execute(
            select(ShopOwner).where(ShopOwner.shop_id == shop_id).limit(1)
        )
        owner = result.scalar_one_or_none()
    if owner:
        try:
            await bot.send_message(chat_id=owner.user_id, text=message)
        except Exception as e:
            print(f"⚠️ notify_shop_owner failed: {e}")
