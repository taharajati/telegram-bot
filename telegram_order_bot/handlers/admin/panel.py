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
            # Count pending subscriptions
            from database.models import ShopSubscription
            async with async_session() as session:
                pending_count_result = await session.execute(
                    __import__("sqlalchemy").select(__import__("sqlalchemy").func.count(ShopSubscription.id))
                    .where(ShopSubscription.approval_status == "pending")
                )
                pending_count = pending_count_result.scalar() or 0

                # Get admin user info for website login
                admin_user = await session.get(User, user_id)
                admin_username = admin_user.username if admin_user else None

            pending_label = f"💳 اشتراک فروشگاه‌ها ({pending_count} جدید)" if pending_count > 0 else "💳 اشتراک فروشگاه‌ها"

            keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("📊 آمار کلی", callback_data="admin:stats")],
                        [InlineKeyboardButton("📦 سفارش‌های در حال پیگیری", callback_data="admin:orders:pending:0")],
                        [InlineKeyboardButton("📜 تاریخچه سفارش‌ها", callback_data="admin:orders:history:0")],
                        [InlineKeyboardButton("🗂 مدیریت فروشگاه‌ها", callback_data="admin:shops:list:0")],
                        [InlineKeyboardButton("🏪 لیست همه فروشگاه‌ها", callback_data="admin:shops:all:0")],
                        [InlineKeyboardButton(pending_label, callback_data="admin:subscription:pending")],
                        [InlineKeyboardButton("📢 پیام همگانی", callback_data="admin:broadcast:start")],
                        [InlineKeyboardButton("📨 پیام‌های پشتیبانی", callback_data="admin:support:messages")],
                        [InlineKeyboardButton("👤 اطلاعات حساب", callback_data="seller:account_info")],
                    ])
            text = (
                "🔧 پنل مدیریت کل\n"
                "دسترسی به همه فروشگاه‌ها\n\n"
                "👇 از دکمه‌های زیر استفاده کن. برای دیدن یوزرنیم و رمز ورود به سایت، «👤 اطلاعات حساب» رو بزن."
            )
    else:
        async with async_session() as session:
            shop = await session.get(Shop, shop_id)
        # Check if shop is approved
        if shop and shop.status != "active":
            status_text = {
                "draft": "⏳ در انتظار تایید",
                "rejected": "❌ درخواست شما رد شده",
            }.get(shop.status, f"⚠️ وضعیت نامعلوم: {shop.status}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تلاش دوباره", callback_data="seller_reg:start")],
                [InlineKeyboardButton("💬 پشتیبانی", callback_data="nav:support")],
            ])
            text = (
                f"🏪 {shop.name}\n\n"
                f"وضعیت فروشگاه: {status_text}\n\n"
                "تا زمان تایید فروشگاه توسط ادمین، دسترسی به پنل مدیریت امکان‌پذیر نیست.\n"
                "لطفاً منتظر بمانید."
            )
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
            else:
                await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
            return
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 آمار فروشگاه", callback_data="admin:stats")],
            [InlineKeyboardButton("📊 آمار پیشرفته", callback_data="admin:stats:advanced")],
            [InlineKeyboardButton("📬 پیام‌های مشتریان", callback_data="seller:inbox")],
            [InlineKeyboardButton("🗂 مدیریت دسته‌بندی‌ها", callback_data="admin:categories")],
            [InlineKeyboardButton("📦 مدیریت محصولات", callback_data="admin:products:list:0")],
            [InlineKeyboardButton("🧾 سفارش‌های در حال پیگیری", callback_data="admin:orders:pending:0")],
            [InlineKeyboardButton("📜 تاریخچه سفارش‌ها", callback_data="admin:orders:history:0")],
        ])
        text = f"🛠 پنل مدیریت فروشگاه «{shop.name if shop else 'نامشخص'}»"

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازگشت به پنل — فروشنده‌ها به پنل یکپارچه هدایت می‌شن."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    is_admin = is_super_admin(user_id)

    # Super admin → admin panel as-is
    if is_admin:
        await admin_command(update, context)
        return

    # Seller → full seller panel
    from handlers.seller_panel import panel_back
    await panel_back(update, context)


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    is_admin = is_super_admin(user_id)
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(user_id)

    async with async_session() as session:
        if is_admin and shop_id is None:
            # ── Super admin: global stats ──
            total_shops = (await session.execute(select(func.count(Shop.id)))).scalar()
            active_shops = (await session.execute(select(func.count(Shop.id)).where(Shop.is_active == True))).scalar()
            total_products = (await session.execute(
                select(func.count(Product.id)).where(Product.is_active == True)
            )).scalar()
            total_orders = (await session.execute(select(func.count(Order.id)))).scalar()
            pending_orders = (await session.execute(
                select(func.count(Order.id)).where(Order.status.in_([
                    OrderStatus.PENDING_PAYMENT, OrderStatus.PENDING, OrderStatus.PAID,
                    OrderStatus.CONFIRMED, OrderStatus.SHIPPED
                ]))
            )).scalar()
            total_revenue = (await session.execute(
                            select(func.coalesce(func.sum(Order.total_price), 0)).where(Order.status.in_([
                                OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.PREPARING,
                                OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.REFUNDED,
                            ]))
                        )).scalar() or 0

            text = (
                f"📊 آمار کلی سیستم:\n\n"
                f"🏪 کل فروشگاه‌ها: {total_shops} (فعال: {active_shops})\n"
                f"📦 محصولات فعال: {total_products}\n"
                f"🧾 کل سفارش‌ها: {total_orders}\n"
                f"⏳ در حال پیگیری: {pending_orders}\n"
                f"💰 درآمد پرداختی: {format_price(total_revenue)}"
            )
        else:
            # ── Seller dashboard: rich stats ──
            sid = shop_id
            text = await _seller_dashboard(session, sid)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin:stats")],
        [InlineKeyboardButton("📈 آمار پیشرفته", callback_data="admin:stats:advanced")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin:panel")],
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def _seller_dashboard(session, shop_id: int) -> str:
    """Generate seller dashboard text with rich stats."""

    # ── Today ──
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = (await session.execute(
        select(func.count(Order.id)).where(
            Order.shop_id == shop_id,
            Order.created_at >= today_start,
        )
    )).scalar() or 0
    today_revenue = (await session.execute(
        select(func.coalesce(func.sum(Order.total_price), 0)).where(
            Order.shop_id == shop_id,
            Order.created_at >= today_start,
            Order.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.SHIPPED, OrderStatus.DELIVERED]),
        )
    )).scalar() or 0

    # ── This week (last 7 days) ──
    week_start = today_start - timedelta(days=6)
    week_count = (await session.execute(
        select(func.count(Order.id)).where(
            Order.shop_id == shop_id,
            Order.created_at >= week_start,
        )
    )).scalar() or 0
    week_revenue = (await session.execute(
        select(func.coalesce(func.sum(Order.total_price), 0)).where(
            Order.shop_id == shop_id,
            Order.created_at >= week_start,
            Order.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.SHIPPED, OrderStatus.DELIVERED]),
        )
    )).scalar() or 0

    # ── This month (last 30 days) ──
    month_start = today_start - timedelta(days=29)
    month_count = (await session.execute(
        select(func.count(Order.id)).where(
            Order.shop_id == shop_id,
            Order.created_at >= month_start,
        )
    )).scalar() or 0
    month_revenue = (await session.execute(
        select(func.coalesce(func.sum(Order.total_price), 0)).where(
            Order.shop_id == shop_id,
            Order.created_at >= month_start,
            Order.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.SHIPPED, OrderStatus.DELIVERED]),
        )
    )).scalar() or 0

    # ── Best-selling product (last 30 days, by quantity) ──
    best_seller = await session.execute(
        select(
            OrderItem.product_name,
            func.sum(OrderItem.quantity).label("qty"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("rev"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .where(
            Order.shop_id == shop_id,
            Order.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.SHIPPED, OrderStatus.DELIVERED]),
            Order.created_at >= month_start,
        )
        .group_by(OrderItem.product_name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(1)
    )
    best_row = best_seller.first()
    best_text = f"🏆 {best_row.product_name} ({int(best_row.qty)} عدد — {format_price(best_row.rev)})" if best_row else "🏆 —"

    # ── Worst-selling product (by quantity, ascending, but has sold) ──
    worst_seller = await session.execute(
        select(
            OrderItem.product_name,
            func.sum(OrderItem.quantity).label("qty"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("rev"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .where(
            Order.shop_id == shop_id,
            Order.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.SHIPPED, OrderStatus.DELIVERED]),
            Order.created_at >= month_start,
        )
        .group_by(OrderItem.product_name)
        .order_by(func.sum(OrderItem.quantity).asc())
        .limit(1)
    )
    worst_row = worst_seller.first()
    worst_text = f"🐢 {worst_row.product_name} ({int(worst_row.qty)} عدد — {format_price(worst_row.rev)})" if worst_row else "🐢 —"

    # ── Products low on stock (< 5) ──
    low_stock_rows = await session.execute(
        select(Product.name, Product.stock, (Product.stock - Product.reserved_stock).label("available_stock"))
        .where(
            Product.shop_id == shop_id,
            Product.is_active == True,
            (Product.stock - Product.reserved_stock) < 5,
        )
        .order_by((Product.stock - Product.reserved_stock).asc())
    )
    low_stock = low_stock_rows.all()
    if low_stock:
        low_lines = [f"⚠️ {p.name}: {p.available_stock} عدد باقی‌مانده" for p in low_stock]
        low_text = "\n".join(low_lines)
    else:
        low_text = "✅ همه محصولات موجودی کافی دارند"

    # ── Average order value (last 30 days) ──
    avg_value = (await session.execute(
        select(func.coalesce(func.avg(Order.total_price), 0)).where(
            Order.shop_id == shop_id,
            Order.created_at >= month_start,
            Order.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.SHIPPED, OrderStatus.DELIVERED]),
        )
    )).scalar() or 0

    # ── Conversion rate (paid/completed vs total in last 30 days) ──
    completed_count = (await session.execute(
        select(func.count(Order.id)).where(
            Order.shop_id == shop_id,
            Order.created_at >= month_start,
            Order.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.SHIPPED, OrderStatus.DELIVERED]),
        )
    )).scalar() or 0
    conversion = (completed_count / month_count * 100) if month_count > 0 else 0

    lines = [
        f"📊 داشبورد فروشگاه\n",
        f"━━━ امروز ━━━",
        f"   📦 {today_count} سفارش | 💰 {format_price(today_revenue)}",
        f"━━━ این هفته ━━━",
        f"   📦 {week_count} سفارش | 💰 {format_price(week_revenue)}",
        f"━━━ این ماه ━━━",
        f"   📦 {month_count} سفارش | 💰 {format_price(month_revenue)}\n",
        f"🛍 محصولات\n"
        f"   {best_text}\n"
        f"   {worst_text}\n",
        f"💰 میانگین مبلغ سفارش: {format_price(avg_value)}\n"
        f"📈 نرخ تبدیل: {completed_count}/{month_count} = {conversion:.0f}%\n\n",
        f"⚠️ هشدار موجودی:\n{low_text}",
    ]
    return "\n".join(lines)


async def admin_advanced_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی آمار پیشرفته (پرفروش‌ترین‌ها + روند فروش)."""
    query = update.callback_query
    await query.answer()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 پرفروش‌ترین محصولات", callback_data="admin:stats:top_products")],
        [InlineKeyboardButton("📈 روند فروش هفتگی", callback_data="admin:stats:weekly")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin:stats")],
    ])
    await query.edit_message_text("📊 آمار پیشرفته", reply_markup=keyboard)


async def admin_top_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پرفروش‌ترین محصولات ۳۰ روز اخیر."""
    query = update.callback_query
    await query.answer()
    shop_id = context.user_data.get("admin_shop_id")
    is_admin = is_super_admin(update.effective_user.id)

    from datetime import datetime, timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    async with async_session() as session:
        base = (
            select(
                func.coalesce(OrderItem.product_id, -1),
                OrderItem.product_name,
                func.sum(OrderItem.quantity).label("total_sold"),
                func.sum(OrderItem.quantity * OrderItem.unit_price).label("total_revenue"),
            )
            .join(Order, OrderItem.order_id == Order.id)
        )
        if shop_id is not None and not is_admin:
            base = base.where(Order.shop_id == shop_id)
        rows = await session.execute(
            base.where(
                Order.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.SHIPPED, OrderStatus.DELIVERED]),
                Order.created_at >= thirty_days_ago,
            )
            .group_by(func.coalesce(OrderItem.product_id, -1), OrderItem.product_name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(5)
        )

        results = rows.all()
        if not results:
            text = "🏆 پرفروش‌ترین‌ها\n\nهیچ سفارش کاملی در ۳۰ روز اخیر ثبت نشده."
        else:
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            lines = ["🏆 پرفروش‌ترین‌های ۳۰ روز اخیر", ""]
            for i, (_, name, qty, rev) in enumerate(results):
                label = medals[i] if i < len(medals) else f"{i+1}."
                lines.append(f"{label} {name} — {int(qty)} عدد ({format_price(rev)})")
            text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت به آمار پیشرفته", callback_data="admin:stats:advanced")],
    ])
    await query.edit_message_text(text, reply_markup=keyboard)


async def admin_weekly_sales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """روند فروش ۷ روز اخیر با sparkline."""
    query = update.callback_query
    await query.answer()
    shop_id = context.user_data.get("admin_shop_id")
    is_admin = is_super_admin(update.effective_user.id)

    from datetime import datetime, timedelta
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)

    async with async_session() as session:
        base = (
            select(
                func.date(Order.created_at).label("day"),
                func.coalesce(func.sum(Order.total_price), 0).label("daily_revenue"),
                func.count(Order.id).label("order_count"),
            )
        )
        if shop_id is not None and not is_admin:
            base = base.where(Order.shop_id == shop_id)
        rows = await session.execute(
            base.where(
                Order.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.SHIPPED, OrderStatus.DELIVERED]),
                Order.created_at >= seven_days_ago,
            )
            .group_by(func.date(Order.created_at))
            .order_by(func.date(Order.created_at))
        )

        revenue_by_day: dict[str, int] = {}
        counts_by_day: dict[str, int] = {}
        for row in rows.all():
            day_str = row.day.strftime("%Y-%m-%d") if hasattr(row.day, "strftime") else str(row.day)
            revenue_by_day[day_str] = int(row.daily_revenue or 0)
            counts_by_day[day_str] = int(row.order_count or 0)

    # build 7-day series (fill gaps with 0)
    day_names = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
    # shift so index 0 = 6 days ago, 6 = today
    series = []
    for i in range(6, -1, -1):
        d = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        series.append(revenue_by_day.get(d, 0))

    # sparkline (Unicode blocks)
    def _sparkline(values):
        blocks = "▁▂▃▄▅▆▇█"
        vmax = max(values) or 1
        return "".join(blocks[min(int(v / vmax * (len(blocks) - 1)), len(blocks) - 1)] for v in values)

    spark = _sparkline(series)

    # build per-day lines
    day_lines = []
    total_rev = 0
    total_orders = 0
    for i in range(7):
        d = (now - timedelta(days=6 - i)).strftime("%Y-%m-%d")
        rev = revenue_by_day.get(d, 0)
        cnt = counts_by_day.get(d, 0)
        total_rev += rev
        total_orders += cnt
        wd_idx = (now.weekday() + 1 - (6 - i)) % 7  # map to persian weekday
        wd_name = day_names[wd_idx]
        rev_str = format_price(rev) if rev else "—"
        day_lines.append(f"{wd_name} {rev_str} ({cnt} سفارش)")

    lines = [
        "📈 روند فروش ۷ روز اخیر",
        f"جمع: {format_price(total_rev)} | {total_orders} سفارش",
        "",
        spark,
        *day_lines,
    ]
    text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت به آمار پیشرفته", callback_data="admin:stats:advanced")],
    ])
    await query.edit_message_text(text, reply_markup=keyboard)
