"""
Migration 005 — Add order_history table for proper audit trail.
Run on deploy: python -m database.migrate_005
"""
import asyncio
import json
import logging
from sqlalchemy import text
from database.db import async_session

logger = logging.getLogger(__name__)

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS order_history (
        id SERIAL PRIMARY KEY,
        order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
        status VARCHAR(50) NOT NULL,
        changed_by VARCHAR(50) NOT NULL,
        description VARCHAR(500),
        meta_json TEXT,
        changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_oh_order_id ON order_history(order_id);",
    "CREATE INDEX IF NOT EXISTS ix_oh_status ON order_history(status);",
    "CREATE INDEX IF NOT EXISTS ix_oh_changed_by ON order_history(changed_by);",
    "CREATE INDEX IF NOT EXISTS ix_oh_changed_at ON order_history(changed_at);",
]

MIGRATE_DATA = """
INSERT INTO order_history (order_id, status, changed_by, description, meta_json, changed_at)
SELECT
    id,
    status,
    'system',
    'imported from legacy status_history',
    status_history,
    updated_at
FROM orders
WHERE status_history IS NOT NULL AND status_history != '[]'
ON CONFLICT DO NOTHING;
"""


async def run():
    async with async_session() as session:
        for stmt in STATEMENTS:
            await session.execute(text(stmt))
        # Migrate existing data
        result = await session.execute(text("SELECT COUNT(*) FROM order_history"))
        count = result.scalar()
        if count == 0:
            await session.execute(text(MIGRATE_DATA))
            logger.info("Migrated existing status_history JSON data to order_history table")
        else:
            logger.info("order_history already has %d records, skipping migration", count)
        await session.commit()
    logger.info("Migration 005: order_history table created ✅")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
