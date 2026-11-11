"""
Abandoned Cart — notification after configurable idle time.
"""
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.db import async_session
from database.models import CartItem, Product, User
from services.notification_service import get_notification_service

logger = logging.getLogger(__name__)

# Config: hours before sending abandoned cart reminder
ABANDONED_CART_HOURS = 12

# Track which carts we've already notified
_notified_cart_ids: set[int] = set()


async def check_abandoned_carts(bot):
    """Background job: find carts idle > ABANDONED_CART_HOURS and notify users."""
    try:
        async with async_session() as session:
            cutoff = datetime.utcnow() - timedelta(hours=ABANDONED_CART_HOURS)
            
            # Get carts where latest item was added before cutoff
            # and we haven't notified yet
            result = await session.execute(
                select(CartItem.id, CartItem.user_id, CartItem.shop_id)
                .where(CartItem.added_at <= cutoff)
            )
            abandoned = result.all()
            
            if not abandoned:
                return
            
            ns = get_notification_service(bot)
            notified_this_run = 0
            
            for cart_id, user_id, shop_id in abandoned:
                if cart_id in _notified_cart_ids:
                    continue
                
                # Load items for this cart
                items_result = await session.execute(
                    select(CartItem)
                    .where(CartItem.user_id == user_id, CartItem.shop_id == shop_id)
                    .options(selectinload(CartItem.product))
                )
                items = items_result.scalars().all()
                
                if not items:
                    continue
                
                # Check if any item is still available
                available_items = [i for i in items if i.product and i.product.is_active and i.product.available_stock > 0]
                if not available_items:
                    continue
                
                # Send notification
                try:
                    await ns.send_to_customer(
                        user_id,
                        f"🛒 سبد خریدت منتظرته!\n\n"
                        f"هنوز {len(available_items)} تا محصول در سبدت داری:\n"
                        + "\n".join(f"• {i.product.name} × {i.quantity}" for i in available_items[:5])
                        + (f"\n... و {len(available_items) - 5} مورد دیگه" if len(available_items) > 5 else "")
                        + f"\n\n💡 برای تکمیل خرید، از منوی اصلی سبد رو باز کن و سفارش بده."
                    )
                    _notified_cart_ids.add(cart_id)
                    notified_this_run += 1
                    import asyncio
                    await asyncio.sleep(1)  # Prevent Telegram rate limits
                except Exception as e:
                    logger.warning(f"Abandoned cart notification failed for user {user_id}: {e}")
            
            if notified_this_run:
                logger.info(f"Abandoned cart notifications sent: {notified_this_run}")
                
    except Exception as e:
        logger.error(f"Abandoned cart check failed: {e}")


def setup_abandoned_cart_scheduler(application):
    """Setup APScheduler for abandoned cart reminders."""
    scheduler = AsyncIOScheduler(timezone="UTC")
    
    # Run every 30 minutes
    scheduler.add_job(
        check_abandoned_carts,
        "interval",
        minutes=30,
        args=[application.bot],
        id="abandoned_cart_check",
        replace_existing=True,
    )
    
    scheduler.start()
    logger.info("Abandoned cart scheduler started (every 30 min)")
    return scheduler


def clear_notified_cart(cart_id: int):
    """Call this when user modifies cart (add/remove/quantity change) to allow re-notification."""
    _notified_cart_ids.discard(cart_id)