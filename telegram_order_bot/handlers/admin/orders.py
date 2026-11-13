"""
مدیریت سفارش‌ها (فروشنده/ادمین کل) — چندمستأجری.
هر فروشنده فقط سفارش‌های فروشگاه خودش رو می‌بینه.
"""
import math
from sqlalchemy import select, func

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler
import config
from database.db import async_session
from database.models import ORDER_STATUS_LABELS, Order, OrderStatus, ALLOWED_TRANSITIONS
from services import payment as payment_svc
from services.order_service import transition_order
from utils.helpers import format_price, to_jalali, notify_shop_owner, history_line, to_persian_digits
from utils.order_validator import can_transition, get_allowed_targets
from utils.tg_helpers import escape_html, get_current_shop_id, render_view
from handlers.admin.panel import admin_only, _get_shop_id_for_admin

ORDERS_PER_PAGE = 8


def _order_detail_text(order: Order) -> str:
    pay = {"card_to_card": "💳 کارت به کارت", "online": "💳 آنلاین"}.get(order.payment_method, "🚚 درب منزل")
    paid = {"paid": "✅ پرداخت شده", "pending": "⏳ منتظر پرداخت", "pending_review": "🔎 رسید رسیده، منتظر تایید تو"}.get(order.payment_status_view, "—")
    lines = [
        f"🧾 سفارش <code>{order.tracking_code}</code>",
        f"وضعیت: {ORDER_STATUS_LABELS[order.status]}",
        f"{pay} · {paid}",
        "",
        f"👤 {escape_html(order.receiver_name)} — {to_persian_digits(order.phone)}",
        f"📍 {escape_html(order.shipping_address)}",
    ]
    if order.customer_notes:
        lines.append(f"✏️ {escape_html(order.customer_notes)}")
    lines += ["", "اقلام:"]
    for item in order.items:
        lines.append(f"• {escape_html(item.product_name)} × {to_persian_digits(item.quantity)} = {format_price(item.unit_price * item.quantity)}")
    lines.append(f"\n💰 جمع کل: <b>{format_price(order.total_price)}</b>")
    lines.append(f"🕒 {to_jalali(order.created_at)}")

    if order.tracking_number:
        lines.append(f"\n📮 کد رهگیری پستی: <code>{escape_html(order.tracking_number)}</code>")

    history = order.get_status_history()
    if history:
        lines.append("\n📜 تاریخچه:")
        lines += [history_line(h) for h in history]

    return "\n".join(lines)


def order_detail_keyboard(order: Order, back_target: str, actor: str = "admin") -> InlineKeyboardMarkup:
    rows = []
    allowed = get_allowed_targets(order, actor)

    # ── paid / confirmed / preparing → shipped (کد رهگیری اختیاریه و نوشتنش خودش ارسال می‌کنه) ──
    if order.status in (OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.PREPARING):
        if order.tracking_number:
            # Already has tracking → show ship button
            rows.append([InlineKeyboardButton(
                "📮 کد رهگیری: " + order.tracking_number,
                callback_data="noop",
            )])
            rows.append([InlineKeyboardButton(
                "🚚 ارسال شد",
                callback_data=f"admin:orders:status:{order.id}:shipped",
            )])
        else:
            # No tracking yet → offer both options
            rows.append([InlineKeyboardButton(
                "📮 ارسال با کد رهگیری",
                callback_data=f"admin:orders:tracking:{order.id}",
            )])
            rows.append([InlineKeyboardButton(
                "🚚 ارسال شد (بدون کد رهگیری)",
                callback_data=f"admin:orders:status:{order.id}:shipped",
            )])

    # ── shipped → waiting for delivery confirmation ──
    elif order.status == OrderStatus.SHIPPED:
        if order.tracking_number:
            rows.append([InlineKeyboardButton(
                "📮 کد رهگیری: " + order.tracking_number,
                callback_data="noop",
            )])
        else:
            rows.append([InlineKeyboardButton(
                "📮 ثبت کد رهگیری",
                callback_data=f"admin:orders:tracking:{order.id}",
            )])
        # No delivered button for seller — only customer can confirm delivery

    # ── other usual status transitions ──
    else:
        for next_status in allowed:
            if next_status == OrderStatus.CANCELLED:
                continue  # دکمه‌ی لغو پایین‌تر جدا اضافه می‌شه
            label = ORDER_STATUS_LABELS[next_status]
            rows.append([InlineKeyboardButton(
                f"➡️ تغییر به «{label}»",
                callback_data=f"admin:orders:status:{order.id}:{next_status}",
            )])
        if order.tracking_number:
            rows.append([InlineKeyboardButton(
                f"📦 کد رهگیری: {order.tracking_number}",
                callback_data="noop",
            )])

    # ── Cancel button (unless terminal) ──
    if order.status not in (
        OrderStatus.DELIVERED, OrderStatus.CANCELLED, OrderStatus.REFUNDED,
        OrderStatus.SHIPPED,
    ):
        rows.append([InlineKeyboardButton("❌ لغو سفارش", callback_data=f"admin:orders:status:{order.id}:cancelled")])

    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data=back_target)])
    return InlineKeyboardMarkup(rows)


async def _fetch_orders(shop_id: int | None = None, statuses=None):
    async with async_session() as session:
        stmt = select(Order).order_by(Order.created_at.desc())
        if shop_id:
            stmt = stmt.where(Order.shop_id == shop_id)
        if statuses:
            stmt = stmt.where(Order.status.in_(statuses))
        result = await session.execute(stmt)
        orders = result.scalars().all()
        for o in orders:
            await session.refresh(o, attribute_names=["items"])
        return orders


async def _render_orders_list(query, context, orders, page: int, callback_prefix: str, title: str):
    if not orders:
        text = title + "\n\nموردی یافت نشد."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:panel")]])
        await render_view(query, context, text, keyboard)
        return

    total_pages = max(1, math.ceil(len(orders) / ORDERS_PER_PAGE))
    page = max(0, min(page, total_pages - 1))
    page_items = orders[page * ORDERS_PER_PAGE : (page + 1) * ORDERS_PER_PAGE]

    rows = [
        [
            InlineKeyboardButton(
                f"#{o.tracking_code} — {ORDER_STATUS_LABELS[o.status]} — {format_price(o.total_price)}",
                callback_data=f"admin:orders:detail:{o.id}:{callback_prefix.split(':')[-1]}",
            )
        ]
        for o in page_items
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"{callback_prefix}:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"{callback_prefix}:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin:panel")])

    text = f"{title} (صفحه {page + 1} از {total_pages})"
    await render_view(query, context, text, InlineKeyboardMarkup(rows))


ASK_TRACKING_NUMBER = range(1)


@admin_only
async def ask_tracking_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask seller to enter tracking number for the order."""
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    order_id = int(parts[3])
    context.user_data["tracking_order_id"] = order_id

    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order and order.tracking_number:
            context.user_data["existing_tracking"] = order.tracking_number
        else:
            context.user_data["existing_tracking"] = None

    await query.edit_message_text(
        "📮 کد رهگیری پستی رو بفرست.\n"
        "به‌محض فرستادنش سفارش «ارسال شد» می‌شه و مشتری باخبر می‌شه.\n\n"
        "برای انصراف: /cancel",
        parse_mode="HTML",
    )
    return ASK_TRACKING_NUMBER


@admin_only
async def save_tracking_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save tracking number and update order."""
    tracking = update.message.text.strip()
    order_id = context.user_data.get("tracking_order_id")
    if not order_id:
        await update.message.reply_text("❌ خطا: درخواست منقضی شده.")
        return ConversationHandler.END

    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order:
            await update.message.reply_text("❌ سفارش پیدا نشد.")
            return ConversationHandler.END
        order.tracking_number = tracking
        await session.commit()

    # کد رهگیری ثبت شد → سفارش ارسال می‌شه و مشتری یک‌جا باخبر می‌شه
    shipped_now = False
    if order.status in (OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.PREPARING):
        try:
            order = await transition_order(order_id, OrderStatus.SHIPPED, actor="admin", bot=context.bot)
            shipped_now = True
        except ValueError:
            pass
    if shipped_now or order.status == OrderStatus.SHIPPED:
        await notify_customer_shipped(context.bot, order)

    # Show updated order view
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order:
            await session.refresh(order, attribute_names=["items", "histories"])
        back_keyboard = order_detail_keyboard(order, "admin:orders:pending:0")
        await update.message.reply_text(
            f"✅ سفارش <code>{order.tracking_code}</code> ارسال شد و مشتری باخبر شد.\n📮 کد رهگیری: <code>{escape_html(tracking)}</code>"
            if shipped_now else f"✅ کد رهگیری <code>{escape_html(tracking)}</code> برای سفارش {order.tracking_code} ثبت شد.",
            parse_mode="HTML",
            reply_markup=back_keyboard,
        )
    return ConversationHandler.END


@admin_only
async def list_pending_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[3])
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)
    orders = await _fetch_orders(
        shop_id,
        statuses=[OrderStatus.PENDING_PAYMENT, OrderStatus.PENDING, OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.SHIPPED]
    )
    await _render_orders_list(query, context, orders, page, "admin:orders:pending", "🧾 سفارش‌های در حال پیگیری")


@admin_only
async def list_all_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[3])
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)
    orders = await _fetch_orders(shop_id)
    await _render_orders_list(query, context, orders, page, "admin:orders:history", "📜 تاریخچه‌ی کامل سفارش‌ها")


@admin_only
async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)
    orders = await _fetch_orders(
        shop_id,
        statuses=[OrderStatus.PENDING_PAYMENT, OrderStatus.PENDING, OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.SHIPPED]
    )
    if not orders:
        await update.message.reply_text("فعلاً هیچ سفارش در حال پیگیری‌ای نیست ✅")
        return
    lines = ["🧾 سفارش‌های در حال پیگیری:\n"]
    for o in orders[:20]:
        lines.append(f"#{o.tracking_code} — {ORDER_STATUS_LABELS[o.status]} — {format_price(o.total_price)}")
    lines.append("\nبرای مدیریت کامل، از /admin استفاده کن.")
    await update.message.reply_text("\n".join(lines))


@admin_only
async def orders_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)
    orders = await _fetch_orders(shop_id)
    if not orders:
        await update.message.reply_text("هنوز هیچ سفارشی ثبت نشده.")
        return
    lines = ["📜 تاریخچه‌ی کامل سفارش‌ها:\n"]
    for o in orders[:30]:
        lines.append(
            f"#{o.tracking_code} — {ORDER_STATUS_LABELS[o.status]} — {format_price(o.total_price)} — {to_jalali(o.created_at)}"
        )
    await update.message.reply_text("\n".join(lines))


@admin_only
async def order_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    order_id = int(parts[3])
    back_source = parts[4] if len(parts) > 4 else "pending"
    back_target = f"admin:orders:{back_source}:0"
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)

    async with async_session() as session:
        stmt = select(Order).where(Order.id == order_id)
        if shop_id:
            stmt = stmt.where(Order.shop_id == shop_id)
        order = (await session.execute(stmt)).scalar_one_or_none()
        if order:
            await session.refresh(order, attribute_names=["items", "histories"])

    if not order:
        await render_view(query, context, "این سفارش پیدا نشد.",
                           InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data=back_target)]]))
        return

    is_super = shop_id is None
    await render_view(query, context, _order_detail_text(order),
                       order_detail_keyboard(order, back_target, actor="admin" if is_super else "admin"))


@admin_only
async def change_order_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, _, _, order_id_str, new_status_str = query.data.split(":")
    order_id = int(order_id_str)
    new_status = new_status_str
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)

    async with async_session() as session:
        stmt = select(Order).where(Order.id == order_id)
        if shop_id:
            stmt = stmt.where(Order.shop_id == shop_id)
        order = (await session.execute(stmt)).scalar_one_or_none()
        if not order:
            await query.answer("سفارش پیدا نشد", show_alert=True)
            return

    try:
        order = await transition_order(order_id, new_status, actor="admin")
    except ValueError as e:
        await query.answer(str(e), show_alert=True)
        return

    customer_id = order.user_id
    tracking_code = order.tracking_code
    status_label = ORDER_STATUS_LABELS[order.status]

    await query.answer("وضعیت به‌روزرسانی شد ✅")
    await render_view(query, context, _order_detail_text(order),
                       order_detail_keyboard(order, "admin:orders:pending:0"))

    # ── Notify customer ──
    try:
        if new_status == OrderStatus.SHIPPED:
            await notify_customer_shipped(context.bot, order)
        elif new_status == OrderStatus.DELIVERED:
            await context.bot.send_message(
                chat_id=customer_id,
                text=f"✅ <b>سفارش #{tracking_code} تحویل داده شد!</b>\n\n"
                     f"امیدواریم از خریدتون لذت برده باشید 🎉\n"
                     f"برای خرید بعدی، به /start مراجعه کنید.",
                parse_mode="HTML",
            )
        else:
            await context.bot.send_message(
                chat_id=customer_id,
                text=f"📦 وضعیت سفارش #{tracking_code} به‌روزرسانی شد:\n{status_label}",
            )
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
# Customer delivery confirmation
# ═══════════════════════════════════════════════════════════════

async def customer_confirm_delivery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """When customer clicks 'بسته به دستم رسید' — set order to delivered."""
    query = update.callback_query
    await query.answer()

    _, _, order_id_str = query.data.split(":")
    order_id = int(order_id_str)

    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order:
            await query.edit_message_text("❌ این سفارش پیدا نشد.")
            return
        if order.status != OrderStatus.SHIPPED:
            await query.answer("سفارش در وضعیت فعلی قابل تایید نیست.", show_alert=True)
            return

    try:
        order = await transition_order(order_id, OrderStatus.DELIVERED, actor="customer")
    except ValueError as e:
        await query.answer(str(e), show_alert=True)
        return

    await notify_seller_delivered(context.bot, order)

    # Show detailed confirmation to customer
    detail_text = _order_detail_text(order)
    detail_text = detail_text.replace(
        f"وضعیت: {ORDER_STATUS_LABELS[OrderStatus.SHIPPED]}",
        f"وضعیت: {ORDER_STATUS_LABELS[OrderStatus.DELIVERED]} ✅"
    )
    await query.edit_message_text(
        f"✅ <b>تایید دریافت سفارش #{order.tracking_code}</b>\n\n"
        f"ممنون! سفارش شما با موفقیت تحویل گرفته شد.\n"
        f"امیدواریم از خریدتون راضی بوده باشید 🎉\n\n"
        f"{detail_text}\n\n"
        f"برای خرید بعدی: /start",
        parse_mode="HTML",
    )


async def notify_customer_shipped(bot, order: Order) -> None:
    """به مشتری خبر می‌ده سفارشش ارسال شد (با کد رهگیری و دکمه‌ی «بسته رسید»)."""
    text = f"📦 <b>سفارشت ارسال شد!</b>\nکد سفارش: <code>{order.tracking_code}</code>\n"
    if order.tracking_number:
        text += f"📮 کد رهگیری پست: <code>{escape_html(order.tracking_number)}</code>\n(با همین کد از سایت پست پیگیری کن)\n"
    text += "\nوقتی بسته دستت رسید، دکمه‌ی زیر رو بزن 👇"
    try:
        await bot.send_message(
            chat_id=order.user_id, text=text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 بسته دستم رسید ✅", callback_data=f"customer:confirm_delivery:{order.id}")]
            ]),
        )
    except Exception:
        pass


async def notify_seller_delivered(bot, order: Order) -> None:
    """به فروشنده خبر می‌ده که مشتری دریافت سفارش رو تأیید کرده."""
    try:
        shop_owner = await _get_shop_owner(order.shop_id)
        if shop_owner:
            seller_text = (
                f"✅ <b>مشتری تحویل گرفت — سفارش #{order.tracking_code}</b>\n\n"
                f"👤 مشتری: {order.receiver_name}\n"
                f"📞 تماس: {order.phone}\n"
                f"📍 آدرس: {order.shipping_address}\n"
                f"💰 مبلغ: {format_price(order.total_price)}\n"
            )
            if order.tracking_number:
                seller_text += f"📮 کد رهگیری: <code>{order.tracking_number}</code>\n"
            await bot.send_message(
                chat_id=shop_owner,
                text=seller_text,
                parse_mode="HTML",
            )
    except Exception:
        pass


async def _get_shop_owner(shop_id: int) -> int | None:
    from database.models import ShopOwner
    async with async_session() as session:
        owner = await session.execute(
            select(ShopOwner).where(ShopOwner.shop_id == shop_id)
        )
        owner = owner.scalar_one_or_none()
        return owner.user_id if owner else None
