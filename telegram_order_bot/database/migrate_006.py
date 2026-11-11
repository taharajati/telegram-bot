"""
Migration 006 — Add missing database indexes.

Uses isolation_level="AUTOCOMMIT" for CREATE INDEX CONCURRENTLY compatibility.
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://foroshgram:foroshgram_secure_2024@postgres:5432/foroshgram"

INDEXES = [
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_orders_user_id ON orders (user_id)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_orders_status ON orders (status)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_orders_created_at ON orders (created_at)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_orders_shop_status ON orders (shop_id, status)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_products_category_id ON products (category_id)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_cart_user_id ON cart (user_id)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_cart_user_shop ON cart (user_id, shop_id)",
]


async def migrate():
    engine = create_async_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        for sql in INDEXES:
            name = sql.split("ix_")[1].split(" ")[0]
            try:
                await conn.execute(text(sql))
                print(f"  ✅ ix_{name}")
            except Exception as e:
                print(f"  ⚠️ ix_{name}: {e}")
    await engine.dispose()
    print("\n✅ Index migration complete")


if __name__ == "__main__":
    asyncio.run(migrate())
