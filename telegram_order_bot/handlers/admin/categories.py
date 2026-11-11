"""
مدیریت دسته‌بندی‌ها (فروشنده/ادمین کل) — چندمستأجری.
هر فروشنده فقط دسته‌بندی‌های فروشگاه خودش رو می‌بینه.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import delete, select, update as sa_update

from database.db import async_session
from database.models import CartItem, Category, OrderItem, Product
from handlers.admin.panel import admin_only, _get_shop_id_for_admin
from utils.tg_helpers import render_view

ASK_CATEGORY_NAME = 0


def categories_keyboard(categories) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"🗑 {c.name}", callback_data=f"admin:categories:delete:{c.id}")]
        for c in categories
    ]
    rows.append([InlineKeyboardButton("➕ افزودن دسته‌بندی جدید", callback_data="admin:categories:add")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin:panel")])
    return InlineKeyboardMarkup(rows)


@admin_only
async def list_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)

    async with async_session() as session:
        stmt = select(Category).order_by(Category.name)
        if shop_id:
            stmt = stmt.where(Category.shop_id == shop_id)
        result = await session.execute(stmt)
        categories = result.scalars().all()

    text = "🗂 دسته‌بندی‌ها (برای حذف روی هرکدوم بزن):" if categories else "هنوز دسته‌بندی‌ای ثبت نشده."
    await render_view(query, context, text, categories_keyboard(categories))


@admin_only
async def start_add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await render_view(query, context, "نام دسته‌بندی جدید رو بفرست:\n(برای لغو /cancel رو بزن)", None)
    return ASK_CATEGORY_NAME


@admin_only
async def save_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("نام خیلی کوتاهه، یه نام دیگه بفرست:")
        return ASK_CATEGORY_NAME

    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)

    async with async_session() as session:
        session.add(Category(name=name, shop_id=shop_id))
        await session.commit()

    await update.message.reply_text(
        f"✅ دسته‌بندی «{name}» با موفقیت اضافه شد",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ دسته‌بندی جدید", callback_data="admin:categories:add")],
            [InlineKeyboardButton("📋 لیست دسته‌بندی‌ها", callback_data="admin:categories")],
            [InlineKeyboardButton("📦 افزودن عادی", callback_data="admin:products:add")],
            [InlineKeyboardButton("📤 افزودن با فوروارد", callback_data="admin:products:add_forward")],
            [InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin:panel")],
        ])
    )
    return ConversationHandler.END


@admin_only
async def delete_category_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    cat_id = int(query.data.split(":")[3])
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)

    async with async_session() as session:
        stmt = select(Category).where(Category.id == cat_id)
        if shop_id:
            stmt = stmt.where(Category.shop_id == shop_id)
        category = (await session.execute(stmt)).scalar_one_or_none()
        if not category:
            await query.answer("این دسته‌بندی پیدا نشد", show_alert=True)
            return
        result = await session.execute(select(Product.id).where(Product.category_id == cat_id))
        product_count = len(result.all())

    text = f"آیا از حذف دسته‌بندی «{category.name}» مطمئنی؟"
    if product_count:
        text += f"\n⚠️ {product_count} محصول در این دسته وجود داره و همراه با دسته حذف می‌شن."

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ بله، حذف کن", callback_data=f"admin:categories:delete_final:{cat_id}")],
        [InlineKeyboardButton("❌ انصراف", callback_data="admin:categories")],
    ])
    await query.answer()
    await render_view(query, context, text, keyboard)


@admin_only
async def delete_category_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    cat_id = int(query.data.split(":")[3])
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)

    async with async_session() as session:
        stmt = select(Category).where(Category.id == cat_id)
        if shop_id:
            stmt = stmt.where(Category.shop_id == shop_id)
        category = (await session.execute(stmt)).scalar_one_or_none()
        if not category:
            await query.answer("دسته‌بندی پیدا نشد", show_alert=True)
            return

        result = await session.execute(select(Product.id).where(Product.category_id == cat_id))
        product_ids = [row[0] for row in result.all()]
        if product_ids:
            await session.execute(delete(CartItem).where(CartItem.product_id.in_(product_ids)))
            await session.execute(sa_update(OrderItem).where(OrderItem.product_id.in_(product_ids)).values(product_id=None))
            await session.execute(delete(Product).where(Product.category_id == cat_id))

        await session.delete(category)
        await session.commit()

    await query.answer("حذف شد 🗑")
    await list_categories(update, context)
