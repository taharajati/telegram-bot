"""
Restock notifications — user subscribes to out-of-stock products,
gets notified when seller updates stock.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from datetime import datetime, timezone

from sqlalchemy import select, delete

from database.db import async_session
from database.models import Product, RestockSubscription, Shop
from services.notification_service import get_notification_service
from utils.tg_helpers import get_current_shop_id


async def _check_and_notify_restock(session, product_id: int, shop_id: int, bot):
    """Check if product was restocked and notify subscribers."""
    product = await session.get(Product, product_id)
    if not product or product.available_stock < 1:
        return

    result = await session.execute(
        select(RestockSubscription).where(
            RestockSubscription.product_id == product_id,
            RestockSubscription.notified == False,
        )
    )
    subs = result.scalars().all()
    if not subs:
        return

    shop = await session.get(Shop, shop_id)
    shop_name = shop.name if shop else ""

    ns = get_notification_service(bot)
    msg = (
        f"🔔 محصول دوباره موجود شد!\n\n"
        f"🛍 {product.name}\n"
        f"💰 {product.price:,} تومان\n"
        f"🏪 {shop_name}\n\n"
        f"اکنون می‌تونی خرید کنی!"
    )

    for sub in subs:
        try:
            await ns.send_to_customer(
                sub.user_id,
                msg,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 مشاهده محصول", callback_data=f"prod:open:{product.id}:0:0")],
                ]),
            )
        except Exception:
            pass
        sub.notified = True

    await session.commit()


async def subscribe_restock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User clicks 🔔 to subscribe for restock notification."""
    query = update.callback_query
    await query.answer()
    try:
        _, _, product_id = query.data.split(":")
        product_id = int(product_id)
    except (ValueError, IndexError):
        return

    user_id = update.effective_user.id
    shop_id = await get_current_shop_id(update)
    if not shop_id:
        return

    async with async_session() as session:
        product = await session.get(Product, product_id)
        if not product:
            await query.message.reply_text("❌ محصول یافت نشد.")
            return

        # Check if already subscribed (active subscription)
        existing = await session.execute(
            select(RestockSubscription).where(
                RestockSubscription.product_id == product_id,
                RestockSubscription.user_id == user_id,
                RestockSubscription.notified == False,
            )
        )
        if existing.scalar_one_or_none():
            await query.message.reply_text("🔔 شما قبلاً برای این محصول ثبت‌نام کرده‌اید. وقتی موجود شد خبر می‌دهیم.")
            return

        # Check if previously notified subscription exists — re-activate it
        old_sub = await session.execute(
            select(RestockSubscription).where(
                RestockSubscription.product_id == product_id,
                RestockSubscription.user_id == user_id,
                RestockSubscription.notified == True,
            )
        )
        old_sub = old_sub.scalar_one_or_none()
        if old_sub:
            old_sub.notified = False
            old_sub.subscribed_at = datetime.now(timezone.utc)
            await session.commit()
        else:
            session.add(RestockSubscription(
                product_id=product_id,
                user_id=user_id,
                shop_id=shop_id,
            ))
            await session.commit()

    await query.message.reply_text(
        f"🔔 ثبت‌نام شد!\n\n"
        f"به محض موجود شدن «{product.name}» بهت خبر می‌دم 🎉",
        parse_mode="HTML",
    )
