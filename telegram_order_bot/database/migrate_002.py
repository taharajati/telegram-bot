"""
Migration 002 — Add shipping_cost field to shops table.
Run on deploy: python -m database.migrate_002
"""
import asyncio
import logging
from sqlalchemy import text
from database.db import async_session

logger = logging.getLogger(__name__)

SQL = """
ALTER TABLE shops ADD COLUMN IF NOT EXISTS shipping_cost FLOAT DEFAULT 0 NOT NULL;
ALTER TABLE shops ADD COLUMN IF NOT EXISTS free_shipping_above FLOAT DEFAULT NULL;
"""

async def run(conn=None):
    """Apply migration. Supports both CLI (own session) and auto_migrate (conn-based)."""
    if conn is not None:
        await _apply(conn)
        return
    async with async_session() as session:
        await _apply(session)
        await session.commit()
    logger.info("Migration 002: added shipping_cost, free_shipping_above to shops table.")


async def _apply(session):
    for statement in SQL.strip().split(";"):
        stmt = statement.strip()
        if stmt:
            await session.execute(text(stmt))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
