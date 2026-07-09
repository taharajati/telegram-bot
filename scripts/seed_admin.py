#!/usr/bin/env python3
"""
One-time migration: seed admin (8497713691) with bcrypt hash of admin password.
Run this inside the bot container after deploy.
Usage: docker exec -w /app -e PYTHONPATH=/app foroshgram_bot python /tmp/seed_admin.py
"""
import asyncio
import bcrypt
import os
import sys

sys.path.insert(0, '/app')

from database.db import async_session
from database.models import Admin


async def main():
    admin_id = int(os.getenv('ADMIN_ID', '8497713691'))
    admin_password = os.getenv('ADMIN_PASSWORD', 'tahar6784')

    password_hash = bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt()).decode()

    async with async_session() as session:
        # Check if admin exists
        from sqlalchemy import select
        result = await session.execute(select(Admin).where(Admin.user_id == admin_id))
        admin = result.scalars().first()

        if admin:
            admin.password_hash = password_hash
            print(f"Updated admin {admin_id}")
        else:
            admin = Admin(user_id=admin_id, password_hash=password_hash)
            session.add(admin)
            print(f"Created admin {admin_id}")

        await session.commit()
        print("Done")


if __name__ == '__main__':
    asyncio.run(main())