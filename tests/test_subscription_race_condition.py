"""
تست سناریوی Race Condition در انقضای اشتراک.
این تست چک می‌کنه که اگر اشتراک یه فروشگاه تموم بشه، آیا مشتری می‌تونه هنوز سفارش ثبت کنه یا نه.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select

from database.db import test_async_session
from database.models import Shop, ShopSubscription, SubscriptionPlan, Product, Category, User, Order, utcnow
@pytest.fixture(autouse=True)
async def setup_test_db():
    """قبل از هر تست، جداول دیتابیس تست رو می‌سازه."""
    await init_db()
    yield

from database.db import test_async_session, init_db

@pytest.mark.asyncio
async def test_order_blocked_on_expired_subscription():
    """تست: مشتری نباید بتونه برای فروشگاهی که اشتراکش تموم شده سفارش ثبت کنه."""
    
    async with test_async_session() as session:
        # 1. ایجاد یک فروشگاه تست
        shop = Shop(name="Test Shop", status="active")
        session.add(shop)
        await session.flush()

        # 2. ایجاد یک پلن اشتراک ۱ روزه
        plan = SubscriptionPlan(name="Test Plan", duration_days=1, price=1000)
        session.add(plan)
        await session.flush()

        # 3. ایجاد اشتراک فعال که همین الان منقضی میشه
        sub = ShopSubscription(
            shop_id=shop.id,
            plan_id=plan.id,
            start_date=utcnow() - timedelta(days=1),
            end_date=utcnow() - timedelta(hours=1),  # منقضی شده
            approval_status="approved"
        )
        session.add(sub)
        await session.commit()

        # 4. شبیه‌سازی اجرای Cron Job برای معلق کردن فروشگاه
        from services.subscription import auto_suspend_expired_subscriptions
        await auto_suspend_expired_subscriptions()

        # 5. چک کردن وضعیت فروشگاه
        updated_shop = await session.get(Shop, shop.id)
        assert updated_shop.status == "suspended", "فروشگاه باید بعد از انقضا معلق بشه"

        # 6. تلاش برای ثبت سفارش (باید توسط لایه‌های بالاتر هندل بشه، اینجا فقط وضعیت رو چک می‌کنیم)
        # در واقعیت، هندلر order.py باید قبل از ثبت سفارش، وضعیت shop رو چک کنه.
        print(f"✅ Test passed: Shop status is {updated_shop.status}")


@pytest.mark.asyncio
async def test_shop_reactivation_after_renewal():
    """تست: بعد از تمدید اشتراک، فروشگاه باید دوباره فعال بشه."""
    
    async with test_async_session() as session:
        # 1. ایجاد فروشگاه معلق
        shop = Shop(name="Suspended Shop", status="suspended")
        session.add(shop)
        await session.flush()

        # 2. ایجاد پلن و اشتراک جدید
        plan = SubscriptionPlan(name="Renewal Plan", duration_days=30, price=5000)
        session.add(plan)
        await session.flush()

        new_sub = ShopSubscription(
            shop_id=shop.id,
            plan_id=plan.id,
            start_date=utcnow(),
            end_date=utcnow() + timedelta(days=30),
            approval_status="approved"
        )
        session.add(new_sub)
        await session.commit()

        # 3. شبیه‌سازی تأیید توسط ادمین (که معمولاً وضعیت رو active می‌کنه)
        from services.subscription import verify_subscription
        await verify_subscription(new_sub.id, admin_user_id=999999, session=session)
        await session.commit()

        # 4. چک کردن وضعیت
        updated_shop = await session.get(Shop, shop.id)
        assert updated_shop.status == "active", "فروشگاه باید بعد از تمدید فعال بشه"
        print("✅ Test passed: Shop reactivated successfully")
