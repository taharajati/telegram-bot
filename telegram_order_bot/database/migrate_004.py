"""
Migration 004: Add product_images table for multi-image gallery support.
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database.db import async_session


async def migrate():
    """Create product_images table."""
    async with async_session() as session:
        # Check if table already exists
        result = await session.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'product_images'
                )
            """)
        )
        table_exists = result.scalar()
        
        if table_exists:
            print("✅ Table product_images already exists, skipping")
            return
        
        # Create the table
        await session.execute(text("""
            CREATE TABLE product_images (
                id SERIAL PRIMARY KEY,
                product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                file_id VARCHAR(255) NOT NULL,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            )
        """))
        
        # Create index
        await session.execute(text("""
            CREATE INDEX ix_product_images_product_id ON product_images (product_id)
        """))
        
        await session.commit()
        print("✅ Created product_images table with index")


if __name__ == "__main__":
    asyncio.run(migrate())