"""
Migration 007 — Create wishlist table.
CREATE TABLE wishlist with indexes.
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import DATABASE_URL


async def run():
    engine = create_async_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        # Wishlist table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS wishlist (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id),
                shop_id INTEGER NOT NULL REFERENCES shops(id),
                product_id INTEGER NOT NULL REFERENCES products(id),
                added_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_wishlist_user_id ON wishlist(user_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_wishlist_user_shop ON wishlist(user_id, shop_id)
        """))
        print("✅ Migration 007 complete: wishlist table created")


if __name__ == "__main__":
    asyncio.run(run())
