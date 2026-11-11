"""
Migration 003 — Add channel_link field to shops table.
Run on deploy: python -m database.migrate_003
"""
import asyncio
import logging
from sqlalchemy import text
from database.db import async_session

logger = logging.getLogger(__name__)

SQL = """
ALTER TABLE shops ADD COLUMN IF NOT EXISTS channel_link VARCHAR(200) DEFAULT NULL;
"""

async def run():
    async with async_session() as session:
        await session.execute(text(SQL))
        await session.commit()
    logger.info("Migration 003: added channel_link to shops table.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
