"""
پنل ادمین/فروشنده — چندمستأجری.

هر فروشنده فقط به دیتای فروشگاه خودش دسترسی داره.
ادمین کل به همه‌چی دسترسی داره.
"""
import functools
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import config
from database.db import async_session
from database.models import OrderItem, Shop, ShopOwner, Order, OrderStatus, Product, Category, User
from sqlalchemy import func, select
from utils.helpers import is_super_admin, format_price, to_persian_digits


async def _get_shop_id_for_admin(user_id: int) -> int | None:
    """برمی‌گردونه shop_id برای این ادمین (اولین فروشگاهی که مالکیت داره)."""
    if is_super_admin(user_id):
        return None  # ادمین کل: همه فروشگاه‌ها
    async with async_session() as session:
        result = await session.execute(
            select(ShopOwner).where(ShopOwner.user_id == user_id).limit(1)
        )
        owner = result.scalar_one_or_none()
    return owner.shop_id if owner else None


def admin_only(func):
    """دکوراتور برای محدود کردن دستورات ادمین/فروشنده.
    فروشنده‌هایی که فروشگاهشون تایید نشده (draft/rejected/suspended) رد می‌شن."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        shop_id = await _get_shop_id_for_admin(user_id)

        if is_super_admin(user_id):
            return await func(update, context)

        if not shop_id:
            if update.callback_query:
                await update.callback_query.answer("دسترسی ندارید ⛔", show_alert=True)
            else:
                await update.message.reply_text("دسترسی ندارید ⛔")
            return

        # برای فروشنده — چک وضعیت فروشگاه
        async with async_session() as session:
            shop = await session.get(Shop, shop_id)
        if shop and shop.status != "active":
            status_msg = {
                "draft": "⏳ فروشگاه شما هنوز تایید نشده.",
                "suspended": "🚫 فروشگاه شما معلق شده.",
                "rejected": "❌ فروشگاه شما تایید نشده.",
            }.get(shop.status, "⚠️ وضعیت نامشخص.")
            if update.callback_query:
                await update.callback_query.answer(status_msg, show_alert=True)
            else:
                await update.message.reply_text(status_msg)
            return

        return await func(update, context)
    return wrapper


# ─── آمار کلی سیستم (ادمین کل) ──────────────────────────────

async def get_system_stats() -> dict:
    """آمار کلی پلتفرم."""
    async with async_session() as session:
        total_shops = await session.execute(select(func.count(Shop.id)))
        active_shops = await session.execute(select(func.count(Shop.id)).where(Shop.status == "active"))
        total_products = await session.execute(select(func.count(Product.id)))
        total_orders = await session.execute(select(func.count(Order.id)))
        completed_orders = await session.execute(select(func.count(Order.id)).where(Order.status == OrderStatus.COMPLETED))
        
        # Total revenue from completed orders
        revenue_result = await session.execute(
            select(func.coalesce(func.sum(Order.total_price), 0)).where(Order.status == OrderStatus.COMPLETED)
        )
        total_revenue = revenue_result.scalar()

    return {
        "total_shops": total_shops.scalar(),
        "active_shops": active_shops.scalar(),
        "total_products": total_products.scalar(),
        "total_orders": total_orders.scalar(),
        "completed_orders": completed_orders.scalar(),
        "total_revenue": total_revenue,
    }


# ─── هندلر اصلی پنل ادمین ─────────────────────────────────────

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ورودی پنل ادمین — فروشنده‌ها به پنل یکپارچه هدایت می‌شن."""
    user_id = update.effective_user.id
    is_admin = is_super_admin(user_id)
    shop_id = await _get_shop_id_for_admin(user_id)

    if not is_admin and not shop_id:
        await update.message.reply_text("به نظر می‌رسه هنوز به‌عنوان صاحب هیچ فروشگاهی ثبت‌نام نکردی.")
        return

    context.user_data["admin_shop_id"] = shop_id

    # فروشنده‌ها → پنل یکپارچه
    if not is_admin:
        from handlers.seller_panel import seller_panel_command
        await seller_panel_command(update, context)
        return

    if is_admin:
        # Get user info for login credentials
        async with async_session() as session:
            user = await session.get(User, user_id)
            username = user.username or user.first_name or "کاربر"
            
            # Count pending subscriptions
            from database.models import ShopSubscription
            pending_count_result = await session.execute(
                select(func.count(ShopSubscription.id))
                .where(ShopSubscription.approval_status == "pending")
            )
            pending_count = pending_count_result.scalar() or 0

        pending_label = f"💳 اشتراک فروشگاه‌ها ({pending_count} جدید)" if pending_count > 0 else "💳 اشتراک فروشگاه‌ها"

        stats = await get_system_stats()
        
        # Prepare login info message
        login_info = (
            f"👤 سلام {username} عزیز (ادمین کل)\n\n"
            f"🔐 اطلاعات ورود به پنل مدیریت وبسایت:\n"
            f"• شناسه تلگرام: `{user_id}`\n"
            f"• لینک پنل: https://telegramorder.ir/admin/login\n\n"
            f"📊 آمار کلی پلتفرم:\n"
            f"• تعداد فروشگاه‌ها: {stats['total_shops']} ({stats['active_shops']} فعال)\n"
            f"• تعداد محصولات: {stats['total_products']}\n"
            f"• کل سفارشات: {stats['total_orders']}\n"
            f"• درآمد کل: {format_price(stats['total_revenue'])}\n\n"
            f"از منوی زیر برای مدیریت استفاده کنید:"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏪 مدیریت فروشگاه‌ها", callback_data="admin:shops")],
            [InlineKeyboardButton(pending_label, callback_data="admin:subscriptions")],
            [InlineKeyboardButton("📦 مدیریت سفارشات", callback_data="admin:orders")],
            [InlineKeyboardButton("👥 کاربران", callback_data="admin:users")],
            [InlineKeyboardButton("📈 گزارشات مالی", callback_data="admin:reports")],
            [InlineKeyboardButton("🔧 تنظیمات سیستم", callback_data="admin:settings")],
        ])

        # Send the message with login info
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(login_info, reply_markup=keyboard, parse_mode="Markdown")
            except:
                await update.callback_query.message.reply_text(login_info, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text(login_info, reply_markup=keyboard, parse_mode="Markdown")


# ─── مدیریت فروشگاه‌ها ────────────────────────────────────────

@admin_only
async def manage_shops(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لیست فروشگاه‌ها برای ادمین."""
    query = update.callback_query
    await query.answer()

    async with async_session() as session:
        shops = await session.execute(
            select(Shop).order_by(Shop.created_at.desc()).limit(20)
        )
        shops_list = shops.scalars().all()

    if not shops_list:
        await query.edit_message_text("هنوز هیچ فروشگاهی ثبت نشده.")
        return

    buttons = []
    for shop in shops_list:
        status_icon = {"active": "✅", "draft": "⏳", "rejected": "❌", "suspended": "🚫"}.get(shop.status, "❓")
        buttons.append([InlineKeyboardButton(f"{status_icon} {shop.name}", callback_data=f"admin:shop_detail:{shop.id}")])
    
    buttons.append([InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="admin:panel_back")])
    
    await query.edit_message_text("🏪 لیست فروشگاه‌های ثبت‌شده:", reply_markup=InlineKeyboardMarkup(buttons))


# ─── بازگشت به پنل اصلی ──────────────────────────────────────

async def admin_panel_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازگشت به منوی اصلی ادمین."""
    query = update.callback_query
    await query.answer()
    await admin_command(update, context)
