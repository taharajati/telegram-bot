"""Migration: add CHECK constraint to products (reserved_stock >= 0 AND <= stock).

این مهاجرت یک CHECK CONSTRAINT به جدول products اضافه می‌کند تا:
1. reserved_stock هیچ‌وقت از stock بیشتر نشود
2. reserved_stock هیچ‌وقت منفی نشود

این مهاجرت برای اولین بار روی محیط اجرایی sqlite (تست) کار نمی‌کند
چون PostgreSQL-only است. فقط روی PostgreSQL اجرا شود.

Usage:
    docker exec foroshgram_postgres psql -U foroshgram -c \
        "ALTER TABLE products ADD CONSTRAINT products_stock_check CHECK (reserved_stock >= 0 AND reserved_stock <= stock)"
"""
import logging

logger = logging.getLogger(__name__)

CHECK_CONSTRAINT_SQL = """
    ALTER TABLE products
    ADD CONSTRAINT IF NOT EXISTS products_stock_check
    CHECK (reserved_stock >= 0 AND reserved_stock <= stock)
    NOT VALID;
"""


async def run_migration():
    """Run the migration — idempotent, can be run multiple times."""
    from database.db import async_session
    from sqlalchemy import text

    async with async_session() as session:
        # Step 1: fix any existing data violations before adding constraint
        await session.execute(
            text("""
                UPDATE products
                SET reserved_stock = GREATEST(0, LEAST(reserved_stock, stock))
                WHERE reserved_stock < 0 OR reserved_stock > stock
            """)
        )
        # Step 2: add check constraint (idempotent)
        try:
            await session.execute(text(CHECK_CONSTRAINT_SQL))
        except Exception as e:
            # PostgreSQL <= 9.x doesn't support IF NOT EXISTS for CHECK
            if "already exists" in str(e):
                logger.info("Constraint already exists — skipping")
            else:
                raise
        await session.commit()

    logger.info("✅ products_stock_check constraint applied")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_migration())
