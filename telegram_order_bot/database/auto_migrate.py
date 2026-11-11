"""
سیستم اجرای خودکار و ایمن مایگریشن‌ها.
هر مایگریشن فقط یک بار اجرا می‌شود و وضعیت آن در جدول schema_migrations ثبت می‌گردد.
"""
import logging
import inspect
from sqlalchemy import text, select
from database.db import async_session

logger = logging.getLogger(__name__)

# لیست مایگریشن‌ها به ترتیب اجرا
MIGRATIONS = [
    ("002", "database.migrate_002", "Add initial columns"),
    ("003", "database.migrate_003", "Add shop features"),
    ("005", "database.migrate_005", "Add order history table"),
    ("stock_check", "database.migrate_stock_check", "Add stock constraints"),
    ("010", "database.migrate_010", "Discount columns FLOAT -> INTEGER"),
]

async def ensure_migration_table(conn):
    """ایجاد جدول ردیابی مایگریشن‌ها اگر وجود نداشته باشد."""
    await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(50) PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )
    """))

async def get_applied_versions(conn) -> set:
    """دریافت لیست نسخه‌های اعمال شده."""
    try:
        result = await conn.execute(text("SELECT version FROM schema_migrations"))
        return {row[0] for row in result.fetchall()}
    except Exception:
        return set()

async def run_pending_migrations():
    """اجرای مایگریشن‌های اجرا نشده به ترتیب."""
    async with async_session() as session:
        async with session.begin():
            conn = session
            await ensure_migration_table(conn)
            applied = await get_applied_versions(conn)
            
            for version, module_name, desc in MIGRATIONS:
                if version in applied:
                    logger.debug(f"Migration {version} already applied.")
                    continue
                    
                logger.info(f"🔄 Running migration {version}: {desc}...")
                try:
                    import importlib
                    mod = importlib.import_module(module_name)
                    
                    # اولویت با تابع migrate(conn) است (استاندارد جدید)
                    if hasattr(mod, 'migrate'):
                        func = getattr(mod, 'migrate')
                        if inspect.iscoroutinefunction(func):
                            await func(conn)
                        else:
                            await conn.run_sync(func)
                    
                    # پشتیبانی از تابع run() قدیمی (که سشن داخلی می‌سازد)
                    elif hasattr(mod, 'run'):
                        func = getattr(mod, 'run')
                        if inspect.iscoroutinefunction(func):
                            # هشدار: این تابع سشن خودش را دارد، پس خارج از تراکنش فعلی اجرا می‌شود
                            # اما چون idempotent است (CREATE TABLE IF NOT EXISTS)، امن است.
                            await func()
                        else:
                            await conn.run_sync(func)
                    else:
                        logger.warning(f"⚠️ No migrate/run function in {module_name}. Skipping.")
                        continue

                    # ثبت موفقیت
                    await conn.execute(
                        text("INSERT INTO schema_migrations (version, description) VALUES (:v, :d)"),
                        {"v": version, "d": desc}
                    )
                    logger.info(f"✅ Migration {version} applied successfully.")
                    
                except Exception as e:
                    logger.error(f"❌ Migration {version} failed: {e}")
                    # ادامه ندهیم تا دیتابیس ناسازگار نشود
                    raise RuntimeError(f"Migration {version} failed: {e}") from e
