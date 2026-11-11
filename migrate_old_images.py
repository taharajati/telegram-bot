#!/usr/bin/env python3
"""
Migrate old product images from Telegram file_id to local storage.
Uses the SAME storage path as image_storage.py (/app/storage/products/).

Run ONCE on the server:
    python migrate_old_images.py              # full migration
    python migrate_old_images.py --dry-run    # preview only
    python migrate_old_images.py --limit 10   # test with 10 products

Requires: DATABASE_URL, BOT_TOKEN in environment or .env file.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "telegram_order_bot"))

from dotenv import load_dotenv
load_dotenv()

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv("DATABASE_URL", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
# Match image_storage.py exactly
STORAGE_DIR = Path("/app/storage/products")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)
if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN not set")
    sys.exit(1)

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("sqlite:///"):
    DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///", 1)


async def ensure_image_url_column(engine):
    """Add image_url column if it doesn't exist (safe for re-runs)."""
    async with engine.begin() as conn:
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'products' AND column_name = 'image_url'"
        ))
        if result.fetchone() is None:
            print("Adding missing column: products.image_url")
            await conn.execute(text(
                "ALTER TABLE products ADD COLUMN image_url VARCHAR(500)"
            ))


async def migrate(dry_run: bool = False, limit: int | None = None):
    engine = create_async_engine(DATABASE_URL)

    # Ensure column exists
    await ensure_image_url_column(engine)

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    query = text("""
        SELECT id, image_file_id
        FROM products
        WHERE image_file_id IS NOT NULL
          AND (image_url IS NULL OR image_url = '')
        ORDER BY id
    """)

    async with engine.begin() as conn:
        result = await conn.execute(query)
        rows = result.fetchall()

    if not rows:
        print("No products need migration.")
        await engine.dispose()
        return

    if limit:
        rows = rows[:limit]

    mode = "DRY RUN" if dry_run else "LIVE"
    print(f"Found {len(rows)} products to migrate [{mode}]")

    success = expired = failed = 0

    async with httpx.AsyncClient(timeout=30) as client:
        for row in rows:
            pid, fid = row[0], row[1]
            try:
                res = await client.get(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
                    params={"file_id": fid}
                )
                data = res.json()
                if not data.get("ok") or not data.get("result", {}).get("file_path"):
                    print(f"  [SKIP] #{pid}: file_id expired")
                    expired += 1
                    continue

                fp = data["result"]["file_path"]
                ext = Path(fp).suffix.lower() or ".jpg"
                filename = f"{pid}{ext}"
                local_path = STORAGE_DIR / filename

                file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}"
                res = await client.get(file_url)
                if res.status_code != 200:
                    print(f"  [FAIL] #{pid}: download {res.status_code}")
                    failed += 1
                    continue

                if dry_run:
                    print(f"  [OK]   #{pid}: would save {filename} ({len(res.content)}B)")
                else:
                    local_path.write_bytes(res.content)
                    url_value = f"/storage/products/{filename}"
                    async with engine.begin() as conn:
                        await conn.execute(
                            text("UPDATE products SET image_url = :u WHERE id = :i"),
                            {"u": url_value, "i": pid}
                        )
                    print(f"  [OK]   #{pid}: saved -> {url_value}")
                success += 1

            except Exception as e:
                print(f"  [ERR]  #{pid}: {e}")
                failed += 1

    print(f"\nDone: {success} ok, {expired} expired, {failed} failed")
    await engine.dispose()


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()
    asyncio.run(migrate(dry_run=args.dry_run, limit=args.limit))
