"""تنظیمات اتصال به پایگاه داده — Foroshgram."""
import logging
import os
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import config

logger = logging.getLogger(__name__)

# Determine if we're on PostgreSQL or SQLite
if "postgresql" in config.DATABASE_URL or "postgres" in config.DATABASE_URL:
    engine = create_async_engine(config.DATABASE_URL, echo=False, future=True, pool_size=10, max_overflow=20)
else:
    # SQLite fallback for local dev
    DB_DIR = Path(config.DATABASE_URL.split(":///")[-1]).parent if ":///" in config.DATABASE_URL else Path("data")
    os.makedirs(DB_DIR, exist_ok=True)
    engine = create_async_engine(config.DATABASE_URL, echo=False, future=True)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ─── دیتابیس جداگانه برای تست‌ها (نکشتن دیتای پروداکشن) ─────────
_test_db_url = getattr(config, "TEST_DATABASE_URL", config.DATABASE_URL)
if "postgresql" in _test_db_url or "postgres" in _test_db_url:
    _test_engine = create_async_engine(_test_db_url, echo=False, future=True, pool_size=5, max_overflow=10)
else:
    _test_engine = create_async_engine(_test_db_url, echo=False, future=True)

test_async_session = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    from database.models import Base
    
    # 1. ایجاد جداول پایه
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. اجرای مایگریشن‌های ایمن و خودکار
    try:
        from database.auto_migrate import run_pending_migrations
        await run_pending_migrations()
    except Exception as e:
        logger.error(f"❌ Auto-migration failed: {e}")
        raise

    # 3. Seed داده‌های اولیه
    async with async_session() as session:
        from services.subscription import seed_subscription_plans
        await seed_subscription_plans(session)

    # 4. Health check نهایی
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1 FROM shops LIMIT 1"))
        if result.scalar_one_or_none() is not None:
            logger.info("✅ Database health check passed")
        else:
            logger.warning("⚠️ Shops table exists but is empty")
