import os
import sys
import pytest

# ─── Ensure SQLite before ANY import ───
# Move before sys.path modifications to guarantee this runs first
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ.pop("TEST_DATABASE_URL", None)
# کلید رمزنگاری فقط برای تست — هیچ ربطی به کلید پروداکشن نداره
os.environ.setdefault("ENCRYPTION_KEY", "test-only-encryption-key-0123456789abcdef")
# تست‌های اشتراک مدل پولی رو بررسی می‌کنن؛ حالت رایگان پیش‌فرض پروداکشنه
os.environ.setdefault("FREE_MODE", "false")

# Clean up config module if already loaded — this ensures the new DATABASE_URL
# is used by SQLAlchemy when the tests start
if "telegram_order_bot.config" in sys.modules:
    del sys.modules["telegram_order_bot.config"]
if "telegram_order_bot.database.db" in sys.modules:
    del sys.modules["telegram_order_bot.database.db"]


@pytest.fixture(autouse=True)
def _force_sqlite(monkeypatch):
    """Monkeypatch os.environ before any import reads config.
    This runs for every test and guarantees tests use SQLite in memory.
    """
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)


@pytest.fixture(autouse=True)
async def _create_and_drop_tables():
    """Create tables once per test session using SQLite, then clean up."""
    # Create tables for this test session
    from database.db import engine
    from database.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Drop tables after each session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)