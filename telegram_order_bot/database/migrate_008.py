"""
Migration 008 — Discount codes, restock subscriptions, shop banner, user saved info.
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import DATABASE_URL


async def run():
    engine = create_async_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        # Discount codes
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS discount_codes (
                id SERIAL PRIMARY KEY,
                shop_id INTEGER NOT NULL REFERENCES shops(id),
                code VARCHAR(50) NOT NULL,
                discount_type VARCHAR(20) NOT NULL,
                discount_value FLOAT NOT NULL,
                min_order_amount FLOAT DEFAULT 0,
                max_uses INTEGER DEFAULT 0,
                used_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_discount_shop_code ON discount_codes(shop_id, code)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_discount_codes_shop ON discount_codes(shop_id)"))

        # Restock subscriptions
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS restock_subscriptions (
                id SERIAL PRIMARY KEY,
                product_id INTEGER NOT NULL REFERENCES products(id),
                user_id BIGINT NOT NULL,
                shop_id INTEGER NOT NULL REFERENCES shops(id),
                notified BOOLEAN DEFAULT FALSE,
                subscribed_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_restock_product_user ON restock_subscriptions(product_id, user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_restock_product ON restock_subscriptions(product_id)"))

        # Shop banner
        await conn.execute(text("ALTER TABLE shops ADD COLUMN IF NOT EXISTS banner_image VARCHAR(500)"))

        # User saved checkout info (fast checkout)
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS saved_name VARCHAR(100)"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS saved_phone VARCHAR(20)"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS saved_address TEXT"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS recent_shops TEXT"))

        print("✅ Migration 008 complete: discount_codes, restock_subscriptions, banner_image, user saved info")


if __name__ == "__main__":
    asyncio.run(run())
