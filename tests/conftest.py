import sys
import os
import pytest
import asyncio

# اضافه کردن مسیر ریشه پروژه به sys.path برای ایمپورت صحیح ماژول‌ها
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'telegram_order_bot'))

from database.db import init_db, test_async_session
from database.models import Base

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """تنظیم محیط تست و ساخت جداول."""
    asyncio.run(init_db())
