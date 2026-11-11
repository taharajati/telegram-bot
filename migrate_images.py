#!/usr/bin/env python3
"""
Migration script: Download all product images from Telegram and store locally.
Run once to migrate existing file_id images to local storage.
"""
import os
import asyncio
import aiohttp
import asyncpg
from pathlib import Path

# Config
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://foroshgram:foroshgram_secure_2024@postgres:5432/foroshgram")
BOT_TOKEN = os.getenv("BOT_TOKEN")
STORAGE_DIR = Path("/app/storage/products")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

async def download_image(session, file_id: str) -> bytes | None:
    """Download image from Telegram using file_id."""
    if not file_id:
        return None
    
    # Step 1: Get file path
    async with session.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
        params={"file_id": file_id}
    ) as resp:
        data = await resp.json()
        if not data.get("ok"):
            print(f"  ❌ getFile failed for {file_id[:20]}...: {data.get('description')}")
            return None
        file_path = data["result"]["file_path"]
    
    # Step 2: Download file
    async with session.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}") as resp:
        if resp.status != 200:
            print(f"  ❌ Download failed for {file_path}: HTTP {resp.status}")
            return None
        return await resp.read()

async def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not set")
        return
    
    print("🔄 Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)
    
    # Get all products with image_file_id
    products = await conn.fetch("""
        SELECT id, image_file_id 
        FROM products 
        WHERE image_file_id IS NOT NULL AND image_file_id != ''
    """)
    
    print(f"📦 Found {len(products)} products with images")
    
    async with aiohttp.ClientSession() as session:
        for i, product in enumerate(products, 1):
            pid = product["id"]
            file_id = product["image_file_id"]
            
            # Determine extension from file_id or default to .jpg
            ext = ".jpg"
            if file_id.startswith("AgAC"):  # Photo
                ext = ".jpg"
            elif file_id.startswith("BAAC"):  # Document
                ext = ".jpg"
            
            local_path = STORAGE_DIR / f"{pid}{ext}"
            
            # Skip if already exists
            if local_path.exists():
                print(f"  [{i}/{len(products)}] ✅ Product {pid}: already exists")
                continue
            
            print(f"  [{i}/{len(products)}] ⬇️  Downloading product {pid}...")
            image_data = await download_image(session, file_id)
            
            if image_data:
                local_path.write_bytes(image_data)
                # Update database with local URL
                await conn.execute(
                    "UPDATE products SET image_url = $1 WHERE id = $2",
                    f"/storage/products/{pid}{ext}",
                    pid
                )
                print(f"     ✅ Saved: {local_path.name} ({len(image_data)} bytes)")
            else:
                print(f"     ❌ Failed to download")
            
            # Rate limit
            await asyncio.sleep(0.1)
    
    await conn.close()
    print("🎉 Migration complete!")

if __name__ == "__main__":
    asyncio.run(main())