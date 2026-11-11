"""
Image storage utility — download images from Telegram and store locally.
Images are saved under /app/storage/products/ with product_id based naming.
"""
import os
import aiohttp
import asyncio
from pathlib import Path
from typing import Optional, List

STORAGE_DIR = Path("/app/storage/products")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


async def _download_single_image(session: aiohttp.ClientSession, bot_token: str, file_id: str) -> Optional[bytes]:
    """Download a single image from Telegram by file_id."""
    try:
        # Step 1: Get file path from Telegram
        async with session.get(
            f"https://api.telegram.org/bot{bot_token}/getFile",
            params={"file_id": file_id}
        ) as resp:
            data = await resp.json()
            if not data.get("ok"):
                return None
            file_path = data["result"]["file_path"]
        
        # Step 2: Download the actual file
        async with session.get(f"https://api.telegram.org/file/bot{bot_token}/{file_path}") as resp:
            if resp.status != 200:
                return None
            return await resp.read()
    except Exception:
        return None


async def download_and_store_image(bot_token: str, file_id: str, product_id: int = None) -> Optional[str]:
    """
    Download image from Telegram and store locally.
    Returns local URL path (e.g., /storage/products/123.jpg) or None on failure.
    """
    if not file_id:
        return None
    
    async with aiohttp.ClientSession() as session:
        image_data = await _download_single_image(session, bot_token, file_id)
    
    if not image_data:
        return None
    
    # Determine filename
    if product_id:
        ext = ".jpg"
        filename = f"{product_id}{ext}"
    else:
        # Use file_id hash for uniqueness
        import hashlib
        hash_suffix = hashlib.md5(file_id.encode()).hexdigest()[:8]
        filename = f"img_{hash_suffix}.jpg"
    
    local_path = STORAGE_DIR / filename
    local_path.write_bytes(image_data)
    
    return f"/storage/products/{filename}"


async def download_and_store_multiple(bot_token: str, file_ids: List[str], base_product_id: int = None) -> List[str]:
    """
    Download multiple images from Telegram and store locally.
    Returns list of local URL paths.
    """
    if not file_ids:
        return []
    
    local_urls = []
    async with aiohttp.ClientSession() as session:
        for i, file_id in enumerate(file_ids):
            image_data = await _download_single_image(session, bot_token, file_id)
            if image_data:
                if base_product_id and i == 0:
                    filename = f"{base_product_id}.jpg"
                elif base_product_id:
                    filename = f"{base_product_id}_{i}.jpg"
                else:
                    import hashlib
                    hash_suffix = hashlib.md5(file_id.encode()).hexdigest()[:8]
                    filename = f"img_{hash_suffix}.jpg"
                
                local_path = STORAGE_DIR / filename
                local_path.write_bytes(image_data)
                local_urls.append(f"/storage/products/{filename}")
            else:
                local_urls.append(None)
            
            # Small delay to avoid rate limits
            await asyncio.sleep(0.05)
    
    return local_urls


def delete_image(local_url: str) -> bool:
    """Delete a locally stored image."""
    if not local_url or not local_url.startswith("/storage/products/"):
        return False
    try:
        filename = local_url.split("/")[-1]
        path = STORAGE_DIR / filename
        if path.exists():
            path.unlink()
            return True
    except Exception:
        pass
    return False