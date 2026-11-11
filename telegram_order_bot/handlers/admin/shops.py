"""
مدیریت فروشگاه‌ها توسط ادمین کل (Super Admin).
ایجاد فروشگاه جدید، لیست فروشگاه‌ها، فعال/غیرفعال کردن.
"""
import math

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import select

from database.db import async_session
from database.models import Shop, ShopOwner
from handlers.bot_commands import delete_seller_menu
from utils.helpers import is_super_admin
from utils.tg_helpers import render_view

SHOPS_PER_PAGE = 8
ASK_SHOP_NAME, ASK_SHOP_DESC = range(2)


async def list_shops(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if not is_super_admin(user_id):
        await query.answer("❌ فقط ادمین کل.", show_alert=True)
        return

    parts = query.data.split(":")
    page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0

    async with async_session() as session:
        result = await session.execute(select(Shop).order_by(Shop.id.desc()))
        shops = result.scalars().all()

    if not shops:
        text = "هیچ فروشگاه‌ای ثبت نشده."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ فروشگاه جدید", callback_data="admin:shops:add")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin:panel")],
        ])
        await render_view(query, context, text, keyboard)
        return

    total_pages = max(1, math.ceil(len(shops) / SHOPS_PER_PAGE))
    page = max(0, min(page, total_pages - 1))
    page_items = shops[page * SHOPS_PER_PAGE : (page + 1) * SHOPS_PER_PAGE]

    rows = [
        [
            InlineKeyboardButton(
                f"{'🟢' if s.is_active else '🔴'} {s.name} (ID:{s.id})",
                callback_data=f"admin:shops:edit:{s.id}",
            )
        ]
        for s in page_items
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"admin:shops:list:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"admin:shops:list:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("➕ فروشگاه جدید", callback_data="admin:shops:add")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin:panel")])

    text = f"🏪 فروشگاه‌ها (صفحه {page + 1} از {total_pages})"
    await render_view(query, context, text, InlineKeyboardMarkup(rows))


async def start_add_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if not is_super_admin(user_id):
        await query.answer("❌ فقط ادمین کل.", show_alert=True)
        return ConversationHandler.END

    await render_view(query, context, "نام فروشگاه جدید رو بفرست:\n(برای لغو /cancel)", None)
    return ASK_SHOP_NAME


async def save_shop_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("نام خیلی کوتاهه، دوباره بفرست:")
        return ASK_SHOP_NAME
    context.user_data["new_shop_name"] = name
    await update.message.reply_text("توضیحات فروشگاه رو بفرست (یا بنویس «ندارد»):")
    return ASK_SHOP_DESC


async def save_shop_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text.strip()
    if desc in ("ندارد", "-", ""):
        desc = None

    name = context.user_data.get("new_shop_name", "فروشگاه جدید")

    async with async_session() as session:
        shop = Shop(name=name, description=desc)
        session.add(shop)
        await session.commit()
        shop_id = shop.id

    await update.message.reply_text(f"✅ فروشگاه «{name}» با ID #{shop_id} ساخته شد!\n\n"
                                    f"حالا لینک فروشگاه: https://t.me/{context.bot.username}?start=shop_{shop_id}")
    context.user_data.pop("new_shop_name", None)
    return ConversationHandler.END


async def edit_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if not is_super_admin(user_id):
        return

    shop_id = int(query.data.split(":")[3])

    async with async_session() as session:
        shop = await session.get(Shop, shop_id)

    if not shop:
        await query.answer("فروشگاه پیدا نشد", show_alert=True)
        return

    status_label = "🟢 فعال" if shop.is_active else "🔴 غیرفعال"
    text = (
        f"🏪 {shop.name}\n"
        f"ID: {shop.id}\n"
        f"وضعیت: {status_label}\n"
        f"توضیحات: {shop.description or '—'}\n"
        f"لینک دسترسی: https://t.me/{context.bot.username}?start=shop_{shop.id}"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 تغییر وضعیت", callback_data=f"admin:shops:toggle:{shop.id}")],
        [InlineKeyboardButton("🗑 حذف فروشگاه", callback_data=f"admin:shops:delete:{shop.id}")],
        [InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="admin:shops:list:0")],
    ])
    await render_view(query, context, text, keyboard)


async def toggle_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    if not is_super_admin(user_id):
        await query.answer("❌ فقط ادمین کل.", show_alert=True)
        return

    shop_id = int(query.data.split(":")[3])

    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
        if shop:
            shop.is_active = not shop.is_active
            # If disabling, remove seller's custom menu
            if not shop.is_active:
                result = await session.execute(
                    select(ShopOwner).where(ShopOwner.shop_id == shop_id)
                )
                owner = result.scalar_one_or_none()
                if owner:
                    try:
                        await delete_seller_menu(context.bot, owner.user_id)
                    except Exception:
                        pass
            await session.commit()

    await query.answer()
    await edit_shop(update, context)


async def delete_shop_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش تأیید حذف فروشگاه (با اخطار)"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if not is_super_admin(user_id):
        return

    shop_id = int(query.data.split(":")[3])

    async with async_session() as session:
        shop = await session.get(Shop, shop_id)

    if not shop:
        await query.answer("فروشگاه پیدا نشد", show_alert=True)
        return

    text = (
        f"⚠️ **اخطار: حذف فروشگاه «{shop.name}» (ID:{shop.id})**\n\n"
        f"با حذف این فروشگاه، موارد زیر **برای همیشه** حذف می‌شوند:\n"
        f"• همه محصولات این فروشگاه\n"
        f"• همه دسته‌بندی‌ها\n"
        f"• همه سفارش‌ها و آیتم‌های سفارش\n"
        f"• سبد خرید کاربران مربوط به این فروشگاه\n"
        f"• دسترسی صاحب فروشگاه\n\n"
        f"❗️ این عملیات برگشت‌ناپذیر است.\n"
        f"آیا مطمئنی؟"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑 بله، حذف کن", callback_data=f"admin:shops:delete_final:{shop.id}")],
        [InlineKeyboardButton("🔙 انصراف", callback_data=f"admin:shops:edit:{shop.id}")],
    ])
    await render_view(query, context, text, keyboard)


async def delete_shop_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف نهایی فروشگاه با تمام وابستگی‌ها"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if not is_super_admin(user_id):
        return

    shop_id = int(query.data.split(":")[3])

    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
        if not shop:
            await query.answer("فروشگاه پیدا نشد", show_alert=True)
            return

        # Get owner before deleting
        result = await session.execute(
            select(ShopOwner).where(ShopOwner.shop_id == shop_id)
        )
        owner = result.scalar_one_or_none()
        owner_user_id = owner.user_id if owner else None

        # حذف وابستگی‌ها با کوئری مستقیم
        from sqlalchemy import text as sa_text

        # FK cleanup: NULLify users.last_shop_id BEFORE deleting shop
        await session.execute(
            sa_text("UPDATE users SET last_shop_id = NULL WHERE last_shop_id = :sid"),
            {"sid": shop_id},
        )

        # حذف اشتراک‌های فروشگاه (shop_subscriptions)
        await session.execute(sa_text("DELETE FROM shop_subscriptions WHERE shop_id = :sid"), {"sid": shop_id})

        # حذف CartItem (سبد خرید — داده موقت)
        await session.execute(sa_text("DELETE FROM cart WHERE shop_id = :sid"), {"sid": shop_id})
        # حذف wishlist (موارد ذخیره‌شده کاربران)
        await session.execute(sa_text("DELETE FROM wishlist WHERE product_id IN (SELECT id FROM products WHERE shop_id = :sid)"), {"sid": shop_id})
        # حذف محصولات (Product)
        await session.execute(sa_text("DELETE FROM products WHERE shop_id = :sid"), {"sid": shop_id})
        # حذف دسته‌بندی‌ها
        await session.execute(sa_text("DELETE FROM categories WHERE shop_id = :sid"), {"sid": shop_id})
        # حذف ShopOwner و ClaimCode
        await session.execute(sa_text("DELETE FROM shop_owners WHERE shop_id = :sid"), {"sid": shop_id})
        await session.execute(sa_text("DELETE FROM claim_codes WHERE shop_id = :sid"), {"sid": shop_id})
        # حذف آیتم‌های سفارش (order_items) — این‌ها داده‌های تاریخی هستند
        # ⚠️ توجه: حذف فروشگاه، تاریخچه سفارش‌ها رو هم پاک می‌کنه
        # در آینده soft-delete جایگزین بهتری خواهد بود
        await session.execute(sa_text("DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE shop_id = :sid)"), {"sid": shop_id})
        await session.execute(sa_text("DELETE FROM orders WHERE shop_id = :sid"), {"sid": shop_id})
        await session.delete(shop)
        await session.commit()

    await query.edit_message_text(f"✅ فروشگاه #{shop_id} و همه داده‌های وابسته با موفقیت حذف شد.")
    # Remove seller menu
    if owner_user_id:
        try:
            await delete_seller_menu(context.bot, owner_user_id)
        except Exception:
            pass
    # برگشت به لیست بعد از ۲ ثانیه — کاربر دکمه رو می‌زنه

async def list_all_shops(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لیست همه فروشگاه‌ها با دکمه‌های broadcast برای هر کدام."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if not is_super_admin(user_id):
        await query.answer("❌ فقط ادمین کل.", show_alert=True)
        return

    parts = query.data.split(":")
    page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0

    async with async_session() as session:
        result = await session.execute(select(Shop).order_by(Shop.id.desc()))
        shops = result.scalars().all()

    if not shops:
        text = "هیچ فروشگاهی ثبت نشده."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ فروشگاه جدید", callback_data="admin:shops:add")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin:panel")],
        ])
        await render_view(query, context, text, keyboard)
        return

    total_pages = max(1, math.ceil(len(shops) / SHOPS_PER_PAGE))
    page = max(0, min(page, total_pages - 1))
    page_items = shops[page * SHOPS_PER_PAGE : (page + 1) * SHOPS_PER_PAGE]

    rows = []
    for s in page_items:
        rows.append([
            InlineKeyboardButton(
                f"{'🟢' if s.is_active else '🔴'} {s.name} (ID:{s.id})",
                callback_data=f"admin:shops:edit:{s.id}",
            )
        ])
        # Broadcast button for each shop
        rows.append([
            InlineKeyboardButton(
                f"📣 تبلیغ برای «{s.name}»",
                callback_data=f"admin:broadcast:shop:{s.id}",
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"admin:shops:all:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"admin:shops:all:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("➕ فروشگاه جدید", callback_data="admin:shops:add")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin:panel")])

    text = f"🏪 همه فروشگاه‌ها (صفحه {page + 1} از {total_pages})\n\nدکمه تبلیغ برای ارسال پیام همگانی به کاربران آن فروشگاه"
    await render_view(query, context, text, InlineKeyboardMarkup(rows))
