"""
Migration: Add CHECK constraint on products (reserved_stock >= 0 AND reserved_stock <= stock)

Run:  python -m database.migrate_stock_check
Safe on PostgreSQL; skips on SQLite (no CHECK enforcement).
"""
import asyncio
import sys

from sqlalchemy import text
from database.db import async_session


async def migrate(conn=None):
    print("[migrate_stock_check] Adding CHECK constraint on products...")
    if conn is not None:
        await _apply(conn)
        return
    async with async_session() as session:
        await _apply(session)
        await session.commit()
    print("[migrate_stock_check] Done.")


async def _apply(session):
    if session.bind.dialect.name == "postgresql":
        await session.execute(text("""
            ALTER TABLE products
            ADD CONSTRAINT chk_stock
            CHECK (reserved_stock >= 0 AND reserved_stock <= stock)
        """))
        print("CHECK constraint added.")
    else:
        print("SQLite detected — CHECK constraint not enforceable (SQLite ignores ALTER TABLE ADD CONSTRAINT).")


if __name__ == "__main__":
    asyncio.run(migrate())
