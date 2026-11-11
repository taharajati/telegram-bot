"""Migration 009: Add tracking_number column to orders + PREPARING status."""
import asyncio
from sqlalchemy import text
from database.db import engine


async def migrate():
    async with engine.begin() as conn:
        # Add tracking_number column if not exists
        await conn.execute(text(
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS tracking_number VARCHAR(50) DEFAULT NULL"
        ))
        print("✅ tracking_number column added to orders")


if __name__ == "__main__":
    asyncio.run(migrate())
