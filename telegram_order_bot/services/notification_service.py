"""
NotificationService — متمرکز کردن تمام ارسال پیام‌ها.
محل واحد برای: send_to_customer, send_to_seller, send_to_admin, broadcast.
"""
from __future__ import annotations

import logging
from typing import Optional, Union

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

import config
from database.db import async_session
from database.models import Shop, ShopOwner, User

logger = logging.getLogger(__name__)


class NotificationService:
    """سرویس متمرکز ارسال اعلان‌ها."""

    def __init__(self, bot: Bot):
        self.bot = bot

    # ════════════════════════════════════════════════════════════════
    # Low-level
    # ════════════════════════════════════════════════════════════════

    async def _send(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        silent: bool = False,
    ) -> bool:
        """ارسال پایه — خطا رو لاگ می‌کنه و False برمی‌گردونه."""
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_notification=silent,
            )
            return True
        except TelegramError as e:
            logger.warning(f"Notification send failed to {chat_id}: {e}")
            return False

    # ════════════════════════════════════════════════════════════════
    # Seller (Shop Owner)
    # ════════════════════════════════════════════════════════════════

    async def send_to_seller(
        self,
        shop_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        silent: bool = False,
    ) -> bool:
        """ارسال به اولین owner فروشگاه."""
        owner = await self._get_shop_owner(shop_id)
        if not owner:
            return False
        return await self._send(owner.user_id, text, parse_mode, reply_markup, silent)

    async def send_photo_to_seller(
        self,
        shop_id: int,
        photo: str,
        caption: str = "",
        parse_mode: str = "HTML",
        reply_markup: Optional[InlineKeyboardMarkup] = None,
    ) -> bool:
        """ارسال عکس به صاحب فروشگاه."""
        owner = await self._get_shop_owner(shop_id)
        if not owner:
            return False
        try:
            await self.bot.send_photo(
                chat_id=owner.user_id,
                photo=photo,
                caption=caption,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
            return True
        except TelegramError as e:
            logger.warning(f"send_photo_to_seller failed (shop {shop_id}): {e}")
            return False

    async def _get_shop_owner(self, shop_id: int):
        from sqlalchemy import select
        from database.models import ShopOwner
        async with async_session() as session:
            result = await session.execute(
                select(ShopOwner).where(ShopOwner.shop_id == shop_id).limit(1)
            )
            return result.scalar_one_or_none()

    # ════════════════════════════════════════════════════════════════
    # Customer (User)
    # ════════════════════════════════════════════════════════════════

    async def send_to_customer(
        self,
        user_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        silent: bool = False,
    ) -> bool:
        """ارسال به مشتری/کاربر."""
        return await self._send(user_id, text, parse_mode, reply_markup, silent)

    async def send_to_user(
        self,
        user_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        silent: bool = False,
    ) -> bool:
        """Alias برای send_to_customer."""
        return await self.send_to_customer(user_id, text, parse_mode, reply_markup, silent)

    # ════════════════════════════════════════════════════════════════
    # Admin
    # ════════════════════════════════════════════════════════════════

    async def send_to_admin(
        self,
        admin_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        silent: bool = False,
    ) -> bool:
        """ارسال به ادمین خاص."""
        return await self._send(admin_id, text, parse_mode, reply_markup, silent)

    async def send_to_all_admins(
        self,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        silent: bool = False,
    ) -> int:
        """ارسال به تمام سوپر ادمین‌ها (از config). count برمی‌گردونه."""
        sent = 0
        for admin_id in config.ADMIN_IDS:
            if await self._send(admin_id, text, parse_mode, reply_markup, silent):
                sent += 1
        return sent

    # ════════════════════════════════════════════════════════════════
    # Broadcast
    # ════════════════════════════════════════════════════════════════

    async def broadcast(
        self,
        user_ids: list[int],
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        silent: bool = False,
        delay: float = 0.05,
    ) -> tuple[int, int]:
        """
        پیام همگانی به لیست user_id.
        return: (success_count, fail_count)
        """
        import asyncio

        success = 0
        fail = 0
        for uid in user_ids:
            if await self._send(uid, text, parse_mode, reply_markup, silent):
                success += 1
            else:
                fail += 1
            if delay:
                await asyncio.sleep(delay)
        return success, fail

    # ════════════════════════════════════════════════════════════════
    # Channel
    # ════════════════════════════════════════════════════════════════

    async def send_to_channel(
        self,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        silent: bool = False,
    ) -> bool:
        """ارسال به کانال نوتیفیکیشن (از config)."""
        if not config.NOTIFICATION_CHANNEL_ID:
            logger.warning("NOTIFICATION_CHANNEL_ID not set")
            return False
        return await self._send(
            config.NOTIFICATION_CHANNEL_ID, text, parse_mode, reply_markup, silent
        )

    # ════════════════════════════════════════════════════════════════
    # Convenience: order-related
    # ════════════════════════════════════════════════════════════════

    async def notify_order_created(self, shop_id: int, message: str) -> bool:
        """اعلان سفارش جدید به فروشنده + کانال."""
        await self.send_to_channel(message)
        return await self.send_to_seller(shop_id, message)

    async def notify_order_paid(
        self, shop_id: int, text: str, is_first_sale: bool = False
    ) -> bool:
        """اعلان پرداخت شده."""
        sent = await self.send_to_seller(shop_id, text)
        if is_first_sale:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🗂 پنل فروشنده", callback_data="seller:panel")]
            ])
            await self.send_to_seller(
                shop_id,
                "🎉🎉🎉 تبریک! اولین سفارشت ثبت شد!\n\n"
                "این شروع مسیر فروش آنلاینته.\n"
                "از اینجا به بعد، فقط کافیه محصولاتت رو به‌روز نگه داری.\n\n"
                "💪 موفق باشی!",
                reply_markup=kb,
            )
        return sent

    async def notify_order_cancelled(
        self, shop_id: int, tracking_code: str, cancelled_by: str, reason: str = ""
    ) -> bool:
        """اعلان لغو سفارش."""
        msg = f"❌ سفارش #{tracking_code} توسط {cancelled_by} لغو شد."
        if reason:
            msg += f"\nدلیل: {reason}"
        return await self.send_to_seller(shop_id, msg)

    async def notify_order_confirmed(self, shop_id: int, tracking_code: str) -> bool:
        """اعلام تأیید سفارش."""
        return await self.send_to_seller(shop_id, f"✅ سفارش #{tracking_code} تأیید شد.")


# ════════════════════════════════════════════════════════════════
# Factory function
# ════════════════════════════════════════════════════════════════

_notification_service: Optional[NotificationService] = None


def get_notification_service(bot: Bot) -> NotificationService:
    """Singleton factory."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService(bot)
    return _notification_service