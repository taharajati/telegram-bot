"""
سرویس اشتراک فروشنده — هسته منطق اشتراک.
Append-only + superseded_at + ترتیب lock ثابت (اول Shop بعد Subscription).
"""
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

import config
from database.db import async_session
from database.models import (
    Shop,
    ShopSubscription,
    ShopOwner,
    SubscriptionPlan,
    utcnow,
)

logger = logging.getLogger(__name__)


# ─── Helper: compute SHA-256 hash for receipt dedup ──────────
def receipt_hash(receipt_file_id: str, caption: str = "") -> str:
    """مثل مکانیزم de-dup سفارش‌ها."""
    raw = f"{receipt_file_id}|{caption}".encode()
    return hashlib.sha256(raw).hexdigest()


# ─── Seed plans (called once at startup from init_db) ────────
PLANS_SEED = [
    {"name": "🥈 ماهانه", "duration_days": 30, "price": 499_000},
    {"name": "🥇 ۳ ماهه", "duration_days": 90, "price": 1_199_000},
    {"name": "💎 ۶ ماهه", "duration_days": 180, "price": 1_999_000},
    {"name": "👑 سالانه", "duration_days": 365, "price": 3_499_000},
]


async def seed_subscription_plans(session: AsyncSession):
    """Seed plans if table is empty."""
    result = await session.execute(select(SubscriptionPlan).limit(1))
    if result.scalar_one_or_none() is not None:
        return  # already seeded

    for p in PLANS_SEED:
        session.add(SubscriptionPlan(**p))
    await session.commit()
    logger.info("✅ Subscription plans seeded (%d plans)", len(PLANS_SEED))


# ─── Trial ─────────────────────────────────────────────────
async def create_trial_subscription(
    shop_id: int,
    admin_user_id: int,
    session: AsyncSession,
) -> ShopSubscription:
    """
    موقع تأیید فروشگاه توسط ادمین صدا زده می‌شه.
    ردیف trial در shop_subscriptions می‌سازه (بدون plan_id).
    """
    # بستن ردیف قبلی (اگه باشه — نباید باشه ولی idempotent)
    await _supersede_current(shop_id, session)

    now = utcnow()
    end = now + timedelta(days=13)
    sub = ShopSubscription(
        shop_id=shop_id,
        plan_id=None,
        is_trial=True,
        start_date=now,
        end_date=end,
        approval_status="approved",  # trial نیازی به تأیید نداره
        verified_by=admin_user_id,
        verified_at=now,
    )
    session.add(sub)
    await session.flush()
    logger.info("🎁 Trial created for shop #%s (until %s)", shop_id, end)
    return sub


# ─── Buy / Renew / Upgrade ─────────────────────────────────
async def create_paid_subscription(
    shop_id: int,
    plan_id: int,
    session: AsyncSession,
    receipt_file_id: Optional[str] = None,
    receipt_caption: str = "",
) -> ShopSubscription:
    """
    خرید اشتراک جدید توسط فروشنده.
    - استراتژی: هر خرید ردیف جدید. اگر shop قبلاً اشتراک فعال داره:
      اگر همون پلن باشه → stack (end_date extend می‌شه روی ردیف جدید از آخر end_date)
      اگر پلن دیگه باشه → replace (از امروز شروع می‌شه، قبلی supersede می‌شه)
    """
    plan = await session.get(SubscriptionPlan, plan_id)
    if not plan or not plan.is_active:
        raise ValueError(f"پلن #{plan_id} یافت نشد یا غیرفعال است.")

    # ردیف فعلی
    current = await get_current_subscription(shop_id, session)

    now = utcnow()
    refund_end_date = None

    if current and current.is_active and current.plan_id == plan_id:
        # **Stack**: از آخر end_date فعلی prolong کن
        start = current.end_date
    else:
        # **Replace**: از امروز شروع کن
        start = now
        if current and current.is_active:
            # بستن ردیف قبلی
            current.superseded_at = now
            refund_end_date = current.end_date

    end = start + timedelta(days=plan.duration_days)

    sub = ShopSubscription(
        shop_id=shop_id,
        plan_id=plan_id,
        is_trial=False,
        start_date=start,
        end_date=end,
        approval_status="pending",
        receipt_file_id=receipt_file_id,
        receipt_hash=receipt_hash(receipt_file_id or "", receipt_caption) if receipt_file_id else None,
    )
    session.add(sub)
    await session.flush()
    logger.info(
        "📦 Subscription created: shop=%s plan=%s (%s → %s) stack=%s",
        shop_id, plan.name, start, end, refund_end_date is None,
    )
    return sub


# ─── Get current active subscription for a shop ─────────────
async def get_current_subscription(
    shop_id: int,
    session: AsyncSession,
) -> Optional[ShopSubscription]:
    """آخرین ردیف با superseded_at IS NULL برای shop."""
    result = await session.execute(
        select(ShopSubscription)
        .where(
            ShopSubscription.shop_id == shop_id,
            ShopSubscription.superseded_at.is_(None),
        )
        .order_by(ShopSubscription.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


# ─── Check if shop has active subscription ──────────────────
async def has_active_subscription(shop_id: int, session: AsyncSession) -> bool:
    """
    آیا shop اشتراک معتبر داره؟
    معتبر = approved + end_date نگذشته + بسته نشده.
    (برای trial هم صادقه چون approval_status=approved داره.)
    """
    sub = await get_current_subscription(shop_id, session)
    return sub.is_active if sub else False


# ─── Get subscription status for display ───────────────────
async def get_subscription_display(shop_id: int, session: AsyncSession) -> str:
    """متن وضعیت اشتراک برای نمایش به فروشنده."""
    if config.FREE_MODE:
        return "🆓 رایگان"
    sub = await get_current_subscription(shop_id, session)

    if not sub:
        return "❌ اشتراکی یافت نشد"

    if sub.is_trial:
        remaining = (sub.end_date - utcnow()).days
        if sub.is_active:
            return f"🎁 آزمایشی — {remaining} روز باقی‌مانده"
        else:
            return "🎁 آزمایشی — به پایان رسیده"

    # Explicitly load plan to avoid lazy-load outside session
    plan_name = "نامشخص"
    if sub.plan_id:
        plan = await session.get(SubscriptionPlan, sub.plan_id)
        if plan:
            plan_name = plan.name

    if sub.approval_status == "pending":
        return f"⏳ {plan_name} — در انتظار تأیید ادمین"

    if sub.approval_status == "rejected":
        return f"❌ {plan_name} — تأیید نشد" + (f" ({sub.rejection_reason})" if sub.rejection_reason else "")

    if sub.is_expired:
        return f"⛔ {plan_name} — منقضی شده در {sub.end_date.strftime('%Y-%m-%d')}"

    remaining = (sub.end_date - utcnow()).days
    return f"✅ {plan_name} — {remaining} روز باقی‌مانده (تا {sub.end_date.strftime('%Y-%m-%d')})"


# ─── Admin: verify a subscription ──────────────────────────
async def verify_subscription(
    sub_id: int,
    admin_user_id: int,
    session: AsyncSession,
) -> Optional[ShopSubscription]:
    """
    تأیید رسید اشتراک توسط ادمین.
    **ترتیب:** with_for_update روی Shop بعد Subscription → چک verified_at → اقدام.
    Idempotent: اگه قبلاً verified_at داشته باشه، رد می‌شه.
    """
    sub = await session.get(ShopSubscription, sub_id)
    if not sub:
        return None

    # Idempotency check — بعد از گرفتن lock (caller باید با with_for_update صدا بزنه)
    if sub.verified_at is not None:
        logger.warning("Idempotent: subscription #%s already verified at %s", sub_id, sub.verified_at)
        return sub

    if sub.approval_status != "pending":
        return None

    now = utcnow()
    sub.approval_status = "approved"
    sub.verified_by = admin_user_id
    sub.verified_at = now

    # Sync shop.status = active
    shop = await session.get(Shop, sub.shop_id)
    if shop:
        shop.status = "active"
        shop.is_active = True

    await session.flush()
    logger.info("✅ Subscription #%s verified by admin #%s", sub_id, admin_user_id)
    return sub


# ─── Admin: reject a subscription ──────────────────────────
async def reject_subscription(
    sub_id: int,
    admin_user_id: int,
    reason: str = "",
    session: AsyncSession = None,
) -> Optional[ShopSubscription]:
    """رد رسید اشتراک توسط ادمین."""
    sub = await session.get(ShopSubscription, sub_id)
    if not sub or sub.approval_status != "pending":
        return None

    sub.approval_status = "rejected"
    sub.verified_by = admin_user_id
    sub.rejection_reason = reason or None
    await session.flush()
    logger.info("❌ Subscription #%s rejected by admin #%s", sub_id, admin_user_id)
    return sub


# ─── Supersede (close) current subscription ─────────────────
async def _supersede_current(shop_id: int, session: AsyncSession):
    """بستن ردیف فعلی (داخلی)."""
    current = await get_current_subscription(shop_id, session)
    if current:
        current.superseded_at = utcnow()


# ─── Cron job: check expired subscriptions ─────────────────
async def auto_suspend_expired_subscriptions(bot=None):
    """
    کرون‌جاب روزانه.
    هر فروشگاهی که اشتراک فعلیش منقضی شده → shop.status = 'suspended'.
    فقط سفارش‌های جدید مسدود می‌شن (سفارش‌های در حال پردازش کامل می‌شن).
    همچنین ۳ روز مونده به اتمام هشدار میده.
    """
    if config.FREE_MODE:
        return  # حالت رایگان: هیچ فروشگاهی به‌خاطر اتمام اشتراک تعلیق نمی‌شه و یادآوری هم نمی‌ره

    now = utcnow()
    three_days = timedelta(days=3)
    grace_days = timedelta(days=config.SUBSCRIPTION_GRACE_DAYS)

    async with async_session() as session:
        # ─── Expired subscriptions ───
        result = await session.execute(
            select(ShopSubscription)
            .where(
                ShopSubscription.superseded_at.is_(None),
                ShopSubscription.end_date <= now,
                ShopSubscription.approval_status == "approved",
            )
        )
        expired = result.scalars().all()

        for sub in expired:
            # Lock the shop row to prevent race conditions during status change
            lock_stmt = select(Shop).where(Shop.id == sub.shop_id).with_for_update()
            await session.execute(lock_stmt)

            shop = await session.get(Shop, sub.shop_id)
            if shop and shop.status == "active":
                shop.status = "suspended"
                shop.is_active = False
                logger.info("⛔ Shop #%s suspended — subscription expired", sub.shop_id)

                # نوتیف به فروشنده
                owner_result = await session.execute(
                    select(ShopOwner).where(ShopOwner.shop_id == sub.shop_id)
                )
                owner = owner_result.scalar_one_or_none()
                if owner and bot:
                    try:
                        await bot.send_message(
                            owner.user_id,
                            f"🚫 اشتراک فروشگاه «{shop.name}» به پایان رسید.\n"
                            f"فروشگاه شما تا زمان خرید اشتراک جدید غیرفعال است.\n"
                            f"💳 برای خرید اشتراک جدید: /myshop",
                        )
                    except Exception:
                        logger.warning("Failed to notify seller #%s about suspension", owner.user_id)

        # ─── Reminder: 3 days before expiry ───
        remind_result = await session.execute(
            select(ShopSubscription)
            .where(
                ShopSubscription.superseded_at.is_(None),
                ShopSubscription.end_date.between(now, now + three_days),
                ShopSubscription.approval_status == "approved",
            )
        )
        about_to_expire = remind_result.scalars().all()

        for sub in about_to_expire:
            owner_result = await session.execute(
                select(ShopOwner).where(ShopOwner.shop_id == sub.shop_id)
            )
            owner = owner_result.scalar_one_or_none()
            if owner and bot:
                try:
                    remaining = (sub.end_date - now).days + 1
                    await bot.send_message(
                        owner.user_id,
                        f"⚠️ اشتراک شما {remaining} روز دیگر به پایان می‌رسد.\n"
                        f"فروشگاه: {sub.shop.name if sub.shop else '—'}\n"
                        f"📅 تاریخ پایان: {sub.end_date.strftime('%Y-%m-%d')}\n\n"
                        f"💳 برای تمدید از پنل فروشنده اقدام کنید: /myshop",
                    )
                except Exception:
                    logger.warning("Failed to send expiry reminder to seller #%s", owner.user_id)

        await session.commit()

    if expired:
        logger.info("⏰ Auto-suspend: %d shops suspended", len(expired))
    if about_to_expire:
        logger.info("🔔 Expiry reminder sent to %d shops", len(about_to_expire))
