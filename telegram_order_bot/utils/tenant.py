"""
توابع کمکی چندمستأجری — context shop_id
هر کاربر (مشتری) یه current_shop_id داره که از طریق start=shop_xxx ست میشه.
هر فروشنده (صاحب فروشگاه) از طریق Panel لاگین/ثبت‌نام میشه.
ادمین کل همه چیز رو می‌بینه.
"""
import logging

from sqlalchemy import select

import config
from database.db import async_session
from database.models import Shop, ShopOwner, User

logger = logging.getLogger(__name__)


async def resolve_shop_id_from_start(start_param: str) -> int | None:
    """متدی برای استخراج shop_id از پارامتر start (مثلاً shop_123)"""
    if start_param and start_param.startswith("shop_"):
        try:
            shop_id = int(start_param.split("_")[1])
            return shop_id
        except (ValueError, IndexError):
            return None
    return None


async def resolve_product_id_from_start(start_param: str) -> int | None:
    """استخراج product_id از start=product_123"""
    if start_param and start_param.startswith("product_"):
        try:
            return int(start_param.split("_")[1])
        except (ValueError, IndexError):
            return None
    return None


async def resolve_category_id_from_start(start_param: str) -> int | None:
    """استخراج category_id از start=category_123"""
    if start_param and start_param.startswith("category_"):
        try:
            cat_id = int(start_param.split("_")[1])
            return cat_id
        except (ValueError, IndexError):
            return None
    return None


async def get_user_shop_id(tg_user_id: int) -> int | None:
    """برگردوندن shop_id کاربر (مشتری)"""
    async with async_session() as session:
        user = await session.get(User, tg_user_id)
        if user and user.current_shop_id:
            return user.current_shop_id
    return None


async def set_user_shop_id(tg_user_id: int, shop_id: int) -> None:
    """ذخیره shop_id برای کاربر (مشتری)"""
    async with async_session() as session:
        user = await session.get(User, tg_user_id)
        if user:
            user.current_shop_id = shop_id
            await session.commit()
        else:
            logger.warning("کاربر %s قبل از set_user_shop_id ثبت نشده", tg_user_id)


async def ensure_shop_exists(shop_id: int) -> bool:
    """بررسی وجود فروشگاه"""
    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
        return shop is not None and shop.is_active


async def get_shop(shop_id: int) -> Shop | None:
    async with async_session() as session:
        return await session.get(Shop, shop_id)


async def is_shop_owner(tg_user_id: int, shop_id: int | None = None) -> bool:
    """چک میکنه کاربر صاحب کدوم فروشگاه‌هاست"""
    async with async_session() as session:
        stmt = select(ShopOwner).where(ShopOwner.user_id == tg_user_id)
        result = await session.execute(stmt)
        owners = result.scalars().all()
        if not owners:
            return False
        if shop_id is not None:
            return any(o.shop_id == shop_id for o in owners)
        return True


async def get_owner_shop_id(tg_user_id: int) -> int | None:
    """برگردوندن shop_id صاحب فروشگاه"""
    async with async_session() as session:
        result = await session.execute(
            select(ShopOwner.shop_id).where(ShopOwner.user_id == tg_user_id)
        )
        row = result.first()
        return row[0] if row else None


async def register_shop_owner(tg_user_id: int, shop_id: int, first_name: str | None, username: str | None) -> ShopOwner:
    """ثبت صاحب فروشگاه (یا برگردوندن موجود)"""
    async with async_session() as session:
        existing = await session.execute(
            select(ShopOwner).where(ShopOwner.user_id == tg_user_id)
        )
        owner = existing.scalar_one_or_none()
        if owner:
            owner.shop_id = shop_id
            await session.commit()
            return owner
        owner = ShopOwner(
            user_id=tg_user_id,
            shop_id=shop_id,
            first_name=first_name,
            username=username,
        )
        session.add(owner)
        await session.commit()
        logger.info("صاحب فروشگاه جدید ثبت نام کرد: user=%s shop=%s", tg_user_id, shop_id)
        return owner
