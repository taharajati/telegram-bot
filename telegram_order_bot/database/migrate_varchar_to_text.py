# ─── Migration: widen encrypted field columns ──────────────────────
# AES-256-GCM output (base64) for 16-digit card = ~60 chars,
# for 100-char name = ~172 chars, for 26-char IBAN = ~72 chars.
# Original VARCHAR(16/100/26) was too small.
#
# Run:  python -m database.migrate_varchar_to_text
# Safe on both PostgreSQL (ALIAS) and SQLite (ALTER).
# ────────────────────────────────────────────────────────────────────
import asyncio
import sys

from database.db import async_session


async def migrate():
    print("[migrate_varchar_to_text] Starting column resize...")
    async with async_session() as session:
        # ── PostgreSQL─style (works on both PG and SQLite) ──
        if session.bind.dialect.name == "postgresql":
            await session.execute(
                'ALTER TABLE shops ALTER COLUMN card_number TYPE TEXT'
            )
            await session.execute(
                'ALTER TABLE shops ALTER COLUMN card_holder_name TYPE TEXT'
            )
            await session.execute(
                'ALTER TABLE shops ALTER COLUMN sheba_number TYPE TEXT'
            )
        else:
            # SQLite does not support ALTER COLUMN TYPE; SQLite TEXT is default.
            # The column is already TEXT-capable; just a no-op for safety.
            print("SQLite detected — columns are already TEXT-capable (no-op).")
        await session.commit()
    print("[migrate_varchar_to_text] Done.")


if __name__ == "__main__":
    asyncio.run(migrate())
