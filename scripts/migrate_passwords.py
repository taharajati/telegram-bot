#!/usr/bin/env python3
# ─── Migrate SHA-256 passwords to bcrypt ────────────────────────────
# Run this once after deploying the bcrypt upgrade:
#   python scripts/migrate_passwords.py
#
# This script checks all shop_owners and:
# 1. If password_hash is SHA-256 (64 hex chars), marks it for migration
# 2. Cannot auto-migrate without knowing the original password
# 3. Outputs a list of user_ids that need to reset password via bot
# ─────────────────────────────────────────────────────────────────────

import asyncio
import re
import sys
from sqlalchemy import select, update
from database.db import async_session
from database.models import ShopOwner
import config

SHA256_PATTERN = re.compile(r'^[0-9a-f]{64}$', re.IGNORECASE)

async def check_passwords():
    """Check all shop_owners for legacy SHA-256 hashes."""
    async with async_session() as session:
        result = await session.execute(select(ShopOwner))
        owners = result.scalars().all()

    legacy_users = []
    bcrypt_users = []
    no_password = []

    for owner in owners:
        if not owner.password_hash:
            no_password.append(owner.user_id)
        elif SHA256_PATTERN.match(owner.password_hash) and not owner.password_hash.startswith('$2'):
            legacy_users.append({
                'user_id': owner.user_id,
                'shop_id': owner.shop_id,
                'first_name': owner.first_name,
                'username': owner.username,
            })
        else:
            bcrypt_users.append(owner.user_id)

    return legacy_users, bcrypt_users, no_password

async def main():
    print("🔍 Checking for legacy SHA-256 passwords...")
    legacy, bcrypt, no_pwd = await check_passwords()

    print(f"\n📊 Summary:")
    print(f"   ✅ bcrypt (new):     {len(bcrypt)}")
    print(f"   ⚠️  SHA-256 (legacy): {len(legacy)}")
    print(f"   ❌ No password:      {len(no_pwd)}")

    if legacy:
        print("\n📋 Users needing password reset via /my_panel in bot:")
        for u in legacy:
            print(f"   • user_id={u['user_id']}  shop_id={u['shop_id']}  name={u['first_name'] or '—'}  @{u['username'] or '—'}")
        
        print("\n💡 Next steps:")
        print("   1. Notify these sellers to use /my_panel → '🔑 تغییر رمز عبور'")
        print("   2. Or admins can send them a message to reset password")
        print("   3. Once all migrated, you can remove legacy code from login route")
    else:
        print("\n✅ No legacy passwords found — all users on bcrypt!")

    return 0 if not legacy else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))