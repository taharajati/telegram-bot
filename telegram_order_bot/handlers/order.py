"""
مدیریت سبد خرید و فرآیند سفارش — شامل افزودن به سبد، ثبت سفارش، پرداخت (کارت‌به‌کارت، درب منزل).
"""
import logging
import re
from datetime import timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import func, select

# ── Navigation keyboard for dead-end messages ──
_NAV_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("🛍 ادامه خرید", callback_data="menu:shop")],
    [InlineKeyboardButton("🛒 سبد خرید", callback_data="cart:view")],
    [InlineKeyboardButton("🏠 شروع", callback_data="nav:main")],
])
from sqlalchemy.orm import selectinload

import config
from database.db import async_session
from database.models import utcnow
from services.notification_service import get_notification_service
from database.models import (
    ORDER_STATUS_LABELS,
    CartItem,
    DiscountCode,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    Shop,
    User,
)
from services import payment as payment_svc
from services.order_service import create_order_from_cart, attach_card_receipt, cancel_order_and_release_stock, CustomerInfo, transition_order
from utils.helpers import format_price, generate_tracking_code, notify_shop_owner, to_jalali
from utils.crypto import safe_decrypt
from handlers.subscription_decorator import require_active_subscription
from utils.order_validator import can_transition
from utils.payment_config import get_enabled_payment_methods, get_payment_method_label, should_skip_payment_selection
from utils.tg_helpers import get_current_shop_id, get_current_shop, render_view, escape_html

logger = logging.getLogger(__name__)

ASK_NAME, ASK_PHONE, ASK_ADDRESS, ASK_NOTES, ASK_PAYMENT_METHOD, CONFIRM, ASK_CARD_RECEIPT, ASK_DISCOUNT = range(8)


async def _check_abandoned_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user has too many timed-out orders in last 60 minutes.
    Returns True if the user should be blocked (limitation active).
    Only applies to users with NO prior successful (paid) orders in this shop."""
    user_id = update.effective_user.id
    shop_id = getattr(context.user_data, "shop_id", None) or await get_current_shop_id(update)
    if not shop_id:
        return False

    async with async_session() as session:
        # — trusted customers are exempt —
        has_paid = await session.execute(
            select(Order.id).where(
                Order.user_id == user_id,
                Order.shop_id == shop_id,
                Order.status.in_([
                    OrderStatus.PAID, OrderStatus.CONFIRMED,
                    OrderStatus.SHIPPED, OrderStatus.DELIVERED,
                ]),
            ).limit(1)
        )
        if has_paid.scalar_one_or_none():
            return False

        # — count timed-out orders in the rolling window —
        sixty_ago = utcnow() - timedelta(hours=1)
        abandoned = await session.execute(
            select(func.count(Order.id)).where(
                Order.user_id == user_id,
                Order.shop_id == shop_id,
                Order.status == OrderStatus.CANCELLED,
                Order.cancellation_reason == "timeout",
                Order.updated_at >= sixty_ago,
            )
        )
        count = abandoned.scalar() or 0
        if count < 2:
            return False

        # — find oldest timed-out order to calculate remaining wait —
        oldest_row = await session.execute(
            select(Order).where(
                Order.user_id == user_id,
                Order.shop_id == shop_id,
                Order.status == OrderStatus.CANCELLED,
                Order.cancellation_reason == "timeout",
                Order.updated_at >= sixty_ago,
            ).order_by(Order.updated_at.asc()).limit(1)
        )
        oldest = oldest_row.scalar_one_or_none()
        if oldest:
            elapsed = (utcnow() - oldest.updated_at).total_seconds() / 60
            remaining = max(1, 60 - elapsed)
        else:
            remaining = 60

        msg = (
            f"⚠️ شما در یک ساعت اخیر {int(count)} بار سفارش رها کرده‌اید.\n"
            f"لطفاً {int(remaining)} دقیقه دیگر صبر کنید یا با پشتیبانی تماس بگیرید."
        )
        if update.callback_query:
            await update.callback_query.answer(msg, show_alert=True)
        else:
            await update.message.reply_text(msg)
        return True
PHONE_PATTERN = re.compile(r"^0?9\d{9}$")


async def _check_blocked(update: Update) -> bool:
    """Returns True if user is blocked."""
    async with async_session() as session:
        user = await session.get(User, update.effective_user.id)
    if user and user.is_blocked:
        if update.callback_query:
            await update.callback_query.answer("حساب شما مسدود شده ⛔", show_alert=True)
        else:
            await update.message.reply_text("⚠️ متأسفانه حساب کاربری‌ت مسدود شده و امکان ثبت سفارش نیست. اگه فکر می‌کنی اشتباهی رخ داده، با پشتیبانی تماس بگیر.")
        return True
    return False


async def _calculate_order_total(session, user_id: int, shop_id: int) -> tuple[float, float, float]:
    """Calculate order total with shipping. Returns (subtotal, shipping_cost, total)."""
    cart_items = await _load_cart_with_products(session, user_id, shop_id)
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    shop = await session.get(Shop, shop_id)
    shipping_cost = shop.shipping_cost if shop else 0.0
    total = subtotal + shipping_cost
    return subtotal, shipping_cost, total


async def _load_cart_with_products(session, user_id: int, shop_id: int):
    """Load cart items with eager-loaded product data."""
    result = await session.execute(
        select(CartItem)
        .where(CartItem.user_id == user_id, CartItem.shop_id == shop_id)
        .options(selectinload(CartItem.product))
    )
    return result.scalars().all()


@require_active_subscription
async def start_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await _check_blocked(update):
        return ConversationHandler.END

    # — abandoned order limitation —
    if await _check_abandoned_limit(update, context):
        return ConversationHandler.END

    shop_id = await get_current_shop_id(update)
    if not shop_id:
        await render_view(query, context, "برای این کار اول باید از لینک یه فروشگاه وارد بشی. از منوی اصلی می‌تونی «🏬 فروشگاه‌های اخیر» رو هم ببینی.",
                           InlineKeyboardMarkup([[InlineKeyboardButton("🏠 شروع", callback_data="nav:main")]]))
        return ConversationHandler.END

    # فروشگاهی که هنوز کارت ثبت نکرده نمی‌تونه پول بگیره: مشتری رو وسط راه معطل نمی‌کنیم
    # و همون لحظه به فروشنده خبر می‌دیم که یه خرید منتظر کارتشه.
    async with async_session() as session:
        checkout_shop = await session.get(Shop, shop_id)
    if checkout_shop and not get_enabled_payment_methods(checkout_shop):
        await render_view(query, context,
            "⏳ این فروشگاه هنوز اطلاعات پرداختش رو کامل نکرده.\n\n"
            "به فروشنده خبر دادیم؛ سبد خریدت سر جاشه و کمی بعد می‌تونی سفارشت رو ثبت کنی.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 سبد خرید", callback_data="cart:view")],
                [InlineKeyboardButton("🏠 منوی اصلی", callback_data="nav:main")],
            ]))
        await get_notification_service(context.bot).send_to_seller(
            shop_id,
            "⚠️ یه مشتری همین الان می‌خواست سفارش ثبت کنه، ولی شماره کارت فروشگاهت ثبت نشده.\n\n"
            "کارتت رو ثبت کن تا خریدها از دست نره 👇",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 ثبت شماره کارت", callback_data="seller:payment_settings")],
            ]),
        )
        return ConversationHandler.END

    async with async_session() as session:
        cart_items = await _load_cart_with_products(session, update.effective_user.id, shop_id)

        # اعتبارسنجی موجودی قبل از شروع مکالمه
        for item in cart_items:
            if item.product.available_stock < item.quantity:
                await render_view(query, context,
                    f"⚠️ موجودی «{item.product.name}» کافی نیست.\n"
                    f"(موجودی قابل فروش: {item.product.available_stock} — درخواست: {item.quantity})\n"
                    "لطفاً سبد خریدت رو ویرایش کن.",
                    InlineKeyboardMarkup([[InlineKeyboardButton("🛒 سبد خرید", callback_data="cart:view")]]))
                return ConversationHandler.END

        # ذخیره اطلاعات سبد در context برای استفاده در مراحل بعد
        context.user_data["checkout_shop_id"] = shop_id

        # ─── Fast checkout: check for saved info ───
        user = await session.get(User, update.effective_user.id)
        has_saved = user and user.saved_name and user.saved_phone and user.saved_address

    if has_saved:
        buttons = [
            [InlineKeyboardButton("✅ استفاده از اطلاعات قبلی", callback_data="checkout:use_saved")],
            [InlineKeyboardButton("✏️ وارد کردن اطلاعات جدید", callback_data="checkout:new_info")],
            [InlineKeyboardButton("❌ انصراف", callback_data="order:cancel")],
        ]
        await render_view(query, context,
            f"📝 اطلاعات قبلی شما:\n\n"
            f"👤 {user.saved_name}\n📞 {user.saved_phone}\n📍 {user.saved_address}\n\n"
            "از این اطلاعات استفاده کنم؟",
            InlineKeyboardMarkup(buttons))
        return ASK_NAME  # will be redirected by callback pattern

    await render_view(query, context,
        "برای ثبت سفارش، لطفاً نام و نام خانوادگی گیرنده رو وارد کن:\n\n"
        "(هر لحظه با /cancel می‌تونی لغو کنی)",
        None,
    )
    return ASK_NAME


async def _handle_checkout_saved(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User chose to use saved checkout info."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    async with async_session() as session:
        user = await session.get(User, user_id)
    if user:
        context.user_data["order_name"] = user.saved_name
        context.user_data["order_phone"] = user.saved_phone
        context.user_data["order_address"] = user.saved_address
    # Go straight to payment
    next_state = await _show_payment_method_selection(update, context)
    return next_state if next_state else ASK_PAYMENT_METHOD


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 3 or any(c.isdigit() for c in name):
        await update.message.reply_text("لطفاً نام معتبر وارد کن (فقط حروف، حداقل ۳ کاراکتر):")
        return ASK_NAME
    context.user_data["order_name"] = name
    await update.message.reply_text("شماره تماس رو وارد کن (مثال: 09123456789):")
    return ASK_PHONE


async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip().replace(" ", "").replace("-", "")
    # Convert Persian digits first, then validate
    phone = phone.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    if not PHONE_PATTERN.match(phone):
        await update.message.reply_text("شماره وارد شده معتبر نیست. دوباره امتحان کن (مثال: 09123456789):")
        return ASK_PHONE
    context.user_data["order_phone"] = phone
    await update.message.reply_text("آدرس کامل ارسال رو وارد کن:")
    return ASK_ADDRESS


async def ask_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text.strip()
    if len(address) < 10:
        await update.message.reply_text("لطفاً آدرس کامل‌تری وارد کن (خیابان، محله، شهر — حداقل ۱۰ حرف):")
        return ASK_ADDRESS
    context.user_data["order_address"] = address
    # ذخیره آدرس برای استفاده بعدی
    async with async_session() as session:
        user = await session.get(User, update.effective_user.id)
        if user:
            user.address = address
            await session.commit()
    
    # Ask for optional notes (color, size, etc.)
    await update.message.reply_text(
        "✏️ توضیحات اضافی (اختیاری):\n\n"
        "اگه نکته خاصی مثل رنگ، سایز، یا هر توضیح دیگه‌ای داری اینجا بنویس.\n"
        "اگه نمی‌خوای چیزی بنویسی، یه خط بزن «نخواهم»:"
    )
    return ASK_NOTES


async def ask_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive optional order notes, then go to card summary."""
    text = update.message.text.strip()
    if text and text not in ("نخواهم", "نمیخواهم", "نه", "no", "No"):
        context.user_data["order_notes"] = text
    else:
        context.user_data["order_notes"] = ""

    # Only card_to_card is available — skip selection, go straight to summary
    shop_id = context.user_data.get("checkout_shop_id") or await get_current_shop_id(update)
    context.user_data["payment_method"] = "card_to_card"
    async with async_session() as session:
        shop = await session.get(Shop, shop_id) if shop_id else None
        if not shop or not shop.card_number:
            await update.message.reply_text("❌ این فروشگاه هنوز اطلاعات کارت بانکی ثبت نکرده.")
            return ConversationHandler.END
    return await _start_card_to_card_flow(update, context, shop)


async def _show_payment_method_selection(update_or_query, context) -> int | None:
    """نمایش دکمه‌های روش پرداخت — داینامیک بر اساس تنظیمات فروشگاه + فلگ جهانی.
    Returns: int (next conversation state) or None if should stay in current state.
    """
    shop_id = context.user_data.get("checkout_shop_id") or await get_current_shop_id(update_or_query)
    if not shop_id:
        return None

    async with async_session() as session:
        shop = await session.get(Shop, shop_id)

    # If only one method is enabled, skip selection entirely
    should_skip, default_method = should_skip_payment_selection(shop)
    if should_skip and default_method:
        context.user_data["payment_method"] = default_method
        return await _route_to_payment_flow(update_or_query, context, default_method, shop)

    enabled_methods = get_enabled_payment_methods(shop)

    if not enabled_methods:
        msg = update_or_query.message if hasattr(update_or_query, 'message') else update_or_query
        await msg.reply_text(
            "❌ این فروشگاه در حال حاضر هیچ روش پرداختی فعال ندارد.\n"
            "لطفاً با پشتیبانی تماس بگیرید یا بعداً تلاش کنید."
        )
        return ConversationHandler.END

    buttons = []
    for method in enabled_methods:
        buttons.append([InlineKeyboardButton(
            get_payment_method_label(method, shop),
            callback_data=f"pay:{method}"
        )])
    buttons.append([InlineKeyboardButton("❌ انصراف", callback_data="order:cancel")])

    keyboard = InlineKeyboardMarkup(buttons)
    msg = update_or_query.message if hasattr(update_or_query, 'message') else update_or_query.message
    await msg.reply_text("چطور می‌خوای پرداخت کنی؟ 👇", reply_markup=keyboard)
    
    # Return to ASK_PAYMENT_METHOD state — the conversation handler will wait for
    # the user to click a payment button
    return ASK_PAYMENT_METHOD


async def _route_to_payment_flow(update_or_query, context, method: str, shop: Shop | None):
    """Route to the appropriate payment flow handler."""
    if method == "card_to_card":
        if not shop or not shop.card_number:
            msg = update_or_query.message if hasattr(update_or_query, 'message') else update_or_query
            await msg.reply_text("❌ این فروشگاه هنوز اطلاعات کارت بانکی ثبت نکرده، پس فعلاً پرداخت کارت‌به‌کارت ممکن نیست.")
            return ConversationHandler.END
        return await _start_card_to_card_flow(update_or_query, context, shop)

    elif method == "cod":
        return await _show_order_summary(update_or_query, context)

    return ConversationHandler.END


async def _start_card_to_card_flow(update_or_query, context, shop):
    """Show order summary first, then on confirm create order and ask for receipt."""
    msg = update_or_query.message if hasattr(update_or_query, 'message') else update_or_query
    user_id = update_or_query.effective_user.id
    shop_id = shop.id

    # Build customer info from collected data
    customer_info = CustomerInfo(
        receiver_name=context.user_data.get("order_name", ""),
        phone=context.user_data.get("order_phone", ""),
        shipping_address=context.user_data.get("order_address", ""),
        notes=context.user_data.get("order_notes", ""),
    )

    # Show order summary first
    async with async_session() as session:
        cart_items = await _load_cart_with_products(session, user_id, shop_id)

    if not cart_items:
        await msg.reply_text("سبد خریدت خالیه 🛒")
        context.user_data.clear()
        return ConversationHandler.END

    # Calculate totals
    async with async_session() as session:
        subtotal, shipping_cost, total = await _calculate_order_total(session, user_id, shop_id)

    # Check if discount already applied
    discount_code = context.user_data.get("discount_code", "")
    discount_amount = context.user_data.get("discount_amount", 0)
    if discount_amount > 0:
        total = max(0, total - discount_amount)

    lines = [
        "📋 خلاصه سفارش (پیش‌نویس)\n",
        *[f"• {it.product.name} × {it.quantity} = {format_price(it.product.price * it.quantity)}" for it in cart_items],
        f"\n👤 گیرنده: {customer_info.receiver_name}",
        f"📞 تماس: {customer_info.phone}",
        f"📍 آدرس: {customer_info.shipping_address}",
        f"💳 روش پرداخت: 🧾 کارت به کارت",
    ]
    if shipping_cost > 0:
        lines.append(f"\n📦 جمع کالاها: {format_price(subtotal)}")
        lines.append(f"🚚 هزینه ارسال: {format_price(shipping_cost)}")
        lines.append("─────────────")
    if discount_amount > 0:
        lines.append(f"🎁 کد تخفیف: {discount_code} (-{format_price(discount_amount)})")
        lines.append("─────────────")
    notes = context.user_data.get("order_notes", "")
    if notes:
        lines.append(f"✏️ توضیحات: {notes}")
    lines.append(f"\n💰 مبلغ قابل پرداخت: {format_price(total)}")

    rows = [
        [InlineKeyboardButton("✅ تأیید و ادامه به پرداخت", callback_data="order:confirm_card")],
    ]
    if not discount_code:
        rows.append([InlineKeyboardButton("🎁 اعمال کد تخفیف", callback_data="order:ask_discount")])
    else:
        rows.append([InlineKeyboardButton("🔄 تغییر کد تخفیف", callback_data="order:ask_discount")])
    rows.append([InlineKeyboardButton("❌ انصراف", callback_data="order:cancel")])
    keyboard = InlineKeyboardMarkup(rows)

    await msg.reply_text("\n".join(lines), reply_markup=keyboard, parse_mode="HTML")
    
    # Store info for next step
    context.user_data["card_shop_id"] = shop_id
    context.user_data["card_total"] = total

    return ASK_PAYMENT_METHOD


async def ask_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.split(":")[1]

    # Validate method is actually enabled for this shop
    shop_id = context.user_data.get("checkout_shop_id") or await get_current_shop_id(update)
    async with async_session() as session:
        shop = await session.get(Shop, shop_id)

    if method not in get_enabled_payment_methods(shop):
        await query.edit_message_text("❌ این روش پرداخت فعلاً برای این فروشگاه فعال نیست. یکی دیگه رو انتخاب کن.", reply_markup=_NAV_KB)
        return ConversationHandler.END

    context.user_data["payment_method"] = method

    # Route to appropriate handler — returns next state
    return await _route_to_payment_flow(query, context, method, shop)


async def confirm_card_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User confirmed the order summary for card payment — create order and ask for receipt."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    shop_id = context.user_data.get("card_shop_id")
    
    if not shop_id:
        await query.edit_message_text("❌ یه مشکلی تو ثبت سفارش پیش اومد. لطفاً دوباره امتحان کن؛ اگه ادامه داشت، با پشتیبانی تماس بگیر.", reply_markup=_NAV_KB)
        context.user_data.clear()
        return ConversationHandler.END
    
    # Build customer info
    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
        if not shop or not shop.card_number:
            await query.edit_message_text("❌ اطلاعات کارت برای این فروشگاه موجود نیست.")
            return ConversationHandler.END
    
    # Build customer info
    customer_info = CustomerInfo(
        receiver_name=context.user_data.get("order_name", ""),
        phone=context.user_data.get("order_phone", ""),
        shipping_address=context.user_data.get("order_address", ""),
        notes=context.user_data.get("order_notes", ""),
    )
    
    # Create order using unified service (includes atomic stock reservation)
    try:
        result = await create_order_from_cart(
            user_id=user_id,
            shop_id=shop_id,
            customer_info=customer_info,
            payment_method="card_to_card",
            discount_code=context.user_data.get("discount_code", ""),
            discount_amount=context.user_data.get("discount_amount", 0),
        )
    except ValueError as e:
        await query.edit_message_text(f"❌ {e}")
        return ConversationHandler.END
    
    order = result.order
    tracking_code = result.tracking_code
    total_price = result.total_price
    
    # Show card details with reservation confirmation
    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
    
    # Decrypt card info for display
    card_display = safe_decrypt(shop.card_number) or ""
    holder_display = safe_decrypt(shop.card_holder_name) or ""
    
    text = (
        f"✅ موجودی رزرو شد!\n"
        f"⏰ ۱۵ دقیقه فرصت دارید پرداخت کنید.\n\n"
        f"🧾 پرداخت کارت به کارت\n\n"
        f"شماره کارت: {card_display}\n"
        f"به نام: {holder_display or 'صاحب حساب'}\n\n"
        f"📦 کد پیگیری: {tracking_code}\n"
        f"💰 مبلغ: {format_price(total_price)}\n\n"
        f"⚠️ لطفاً کد پیگیری {tracking_code} رو حتماً\n"
        f"در قسمت «توضیحات» انتقال بنویسید تا فروشنده\n"
        f"سریع‌تر پرداختتون رو تایید کنه.\n\n"
        f"بعد از واریز، می‌تونی عکس رسید یا شماره تراکنش رو بفرستی 👇"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ انصراف", callback_data=f"order:pay_cancel:{order.id}")]
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
    
    # Store order_id for receipt handling
    context.user_data["card_order_id"] = order.id
    
    return ASK_CARD_RECEIPT


async def handle_card_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت عکس رسید یا شماره تراکنش کارت‌به‌کارت از مشتری و ذخیره در سفارش."""
    try:
        user_id = update.effective_user.id
        order_id = context.user_data.get("card_order_id")
        
        if not order_id:
            await update.message.reply_text("❌ خطا در ثبت سفارش. لطفاً دوباره تلاش کنید.", reply_markup=_NAV_KB)
            return ConversationHandler.END

        # Check if it's a photo or text
        photo = update.message.photo[-1] if update.message.photo else None
        # Use caption as fallback for receipt_text (user may send photo with caption)
        receipt_text = (update.message.caption or update.message.text or "").strip() or None
        file_id = None  # رسید متنی (شماره تراکنش) عکس نداره

        if photo:
            file_id = photo.file_id
        elif receipt_text:
            # Text receipt — validate it looks like a transaction number
            if len(receipt_text) < 4 or len(receipt_text) > 100:
                await update.message.reply_text(
                    "❌ شماره تراکنش معتبر نیست.\n"
                    "می‌تونی عکس رسید بفرستی یا شماره تراکنش (حداقل ۴ رقم) رو بنویسی 👇",
                    parse_mode="HTML"
                )
                return ASK_CARD_RECEIPT

            # Normalize Persian numbers
            receipt_text = receipt_text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
        else:
            await update.message.reply_text(
                "❌ لطفاً عکس رسید یا شماره تراکنش رو بفرست:",
                parse_mode="HTML"
            )
            return ASK_CARD_RECEIPT

        # Attach receipt to order using service
        try:
            await attach_card_receipt(
                order_id=order_id,
                receipt_file_id=file_id,
                receipt_caption=receipt_text or "",
            )
        except ValueError as e:
            error_msg = str(e)
            await update.message.reply_text(f"❌ {error_msg}", parse_mode="HTML")
            # If duplicate receipt, let user try again
            if "قبلاً" in error_msg:
                return ASK_CARD_RECEIPT
            return ConversationHandler.END

        # Notify shop owner with receipt
        async with async_session() as session:
            order = await session.get(Order, order_id)
            if not order:
                await update.message.reply_text("❌ سفارش یافت نشد.")
                return ConversationHandler.END
            tracking = order.tracking_code
            total = order.total_price
            shop_id = order.shop_id

        await _notify_seller_receipt(context, order_id, shop_id, tracking, total, file_id, receipt_text)

        receipt_rows = [
            [InlineKeyboardButton("📦 سفارش‌های من", callback_data="order:history")],
            [InlineKeyboardButton("🛍 منوی اصلی", callback_data="nav:main")],
        ]
        if config.WIDGETS_ENABLED and not config.WIDGET_AUTO_SEND:
            receipt_rows.insert(0, [InlineKeyboardButton("📍 رهگیری زنده سفارش", callback_data=f"order:track:{order_id}")])

        if file_id:
            await update.message.reply_text(
                f"✅ رسید شما دریافت شد!\n\n"
                f"📦 کد پیگیری: {tracking}\n"
                f"💰 مبلغ: {format_price(total)}\n\n"
                f"⏳ در انتظار تایید فروشنده...\n"
                f"به محض تایید، بهت اطلاع می‌دیم ✅",
                reply_markup=InlineKeyboardMarkup(receipt_rows),
            )
        else:
            await update.message.reply_text(
                f"✅ شماره تراکنش دریافت شد!\n\n"
                f"📦 کد پیگیری: {tracking}\n"
                f"💰 مبلغ: {format_price(total)}\n"
                f"🧾 شماره تراکنش: {receipt_text}\n\n"
                f"⏳ در انتظار تایید فروشنده...\n"
                f"به محض تایید، بهت اطلاع می‌دیم ✅",
                reply_markup=InlineKeyboardMarkup(receipt_rows),
                parse_mode="HTML"
            )

        if config.WIDGET_AUTO_SEND:
            from services import widgets
            await widgets.send_order_tracker(context.bot, order_id, update.effective_chat.id)

        context.user_data.clear()
        return ConversationHandler.END

    except Exception as e:
        logger.exception(f"خطا در handle_card_receipt برای user={update.effective_user.id}: {e}")
        await update.message.reply_text(
            "❌ یه خطا رخ داد. لطفاً دوباره تلاش کن یا با /start شروع کن."
        )
        context.user_data.clear()
        return ConversationHandler.END


async def _show_order_summary(update_or_query, context) -> int:
    """نمایش خلاصه سفارش برای تایید نهایی. هم از callback و هم از direct message کار میکنه."""
    # Handle both CallbackQuery and Update
    if hasattr(update_or_query, 'callback_query') and update_or_query.callback_query:
        query = update_or_query.callback_query
        user_id = query.from_user.id
    else:
        query = None
        user_id = update_or_query.effective_user.id

    shop_id = context.user_data.get("checkout_shop_id") or await get_current_shop_id(update_or_query)
    if not shop_id:
        text = "لطفاً با لینک فروشگاه وارد شوید."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 شروع", callback_data="nav:main")]])
        if query:
            await render_view(query, context, text, keyboard)
        else:
            await update_or_query.effective_message.reply_text(text, reply_markup=keyboard)
        return ConversationHandler.END

    async with async_session() as session:
        cart_items = await _load_cart_with_products(session, user_id, shop_id)

    if not cart_items:
        text = "سبد خریدت الان خالیه، پس عملیات لغو شد. هر وقت خواستی می‌تونی از منوی اصلی دوباره خرید کنی."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🛍 محصولات", callback_data="cat:list")]])
        if query:
            await render_view(query, context, text, keyboard)
        else:
            await update_or_query.effective_message.reply_text(text, reply_markup=keyboard)
        context.user_data.clear()
        return ConversationHandler.END

    async with async_session() as session:
        subtotal, shipping_cost, total = await _calculate_order_total(session, user_id, shop_id)
        shop = await session.get(Shop, shop_id)
    
    # Check if discount already applied
    discount_code = context.user_data.get("discount_code", "")
    discount_amount = context.user_data.get("discount_amount", 0)
    
    if discount_amount > 0:
        total = max(0, total - discount_amount)
    
    method = context.user_data.get("payment_method", "cod")
    method_labels = {"card_to_card": "🧾 کارت به کارت", "cod": "🚚 پرداخت درب منزل"}
    method_label = method_labels.get(method, "🚚 پرداخت درب منزل")

    lines = [
        "📋 خلاصه سفارش:\n",
        *[f"• {it.product.name} × {it.quantity} = {format_price(it.product.price * it.quantity)}" for it in cart_items],
        f"\n👤 گیرنده: {context.user_data['order_name']}",
        f"📞 تماس: {context.user_data['order_phone']}",
        f"📍 آدرس: {context.user_data['order_address']}",
        f"💳 روش پرداخت: {method_label}",
    ]
    if shipping_cost > 0:
        lines.append(f"\n📦 جمع کالاها: {format_price(subtotal)}")
        lines.append(f"🚚 هزینه ارسال: {format_price(shipping_cost)}")
        lines.append("─────────────")
    if discount_amount > 0:
        lines.append(f"🎁 کد تخفیف: {discount_code} (-{format_price(discount_amount)})")
        lines.append("─────────────")
    notes = context.user_data.get("order_notes", "")
    if notes:
        lines.append(f"✏️ توضیحات: {notes}")
    lines.append(f"\n💰 مبلغ قابل پرداخت: {format_price(total)}")

    rows = [
        [InlineKeyboardButton("✅ ثبت نهایی سفارش", callback_data="order:confirm")],
    ]
    if not discount_code:
        rows.append([InlineKeyboardButton("🎁 اعمال کد تخفیف", callback_data="order:ask_discount")])
    else:
        rows.append([InlineKeyboardButton("🔄 تغییر کد تخفیف", callback_data="order:ask_discount")])
    rows.append([InlineKeyboardButton("❌ انصراف", callback_data="order:cancel")])
    keyboard = InlineKeyboardMarkup(rows)

    if query:
        await render_view(query, context, "\n".join(lines), keyboard)
    else:
        await update_or_query.effective_message.reply_text("\n".join(lines), reply_markup=keyboard)

    return CONFIRM


async def _validate_and_apply_discount(
    context, code: str, shop_id: int, user_id: int
) -> tuple[str, int]:
    """Validate discount code and return (error_message, discount_amount).
    Returns ("", amount) on success, (error_msg, 0) on failure."""
    from datetime import datetime

    async with async_session() as session:
        result = await session.execute(
            select(DiscountCode).where(
                DiscountCode.shop_id == shop_id,
                DiscountCode.code == code.upper().strip(),
                DiscountCode.is_active == True,
            )
        )
        dc = result.scalar_one_or_none()
        if not dc:
            return "❌ کد تخفیف نامعتبر است.", 0

        if dc.expires_at and dc.expires_at < datetime.utcnow():
            return "❌ این کد تخفیف منقضی شده.", 0

        if dc.max_uses and dc.used_count >= dc.max_uses:
            return "❌ ظرفیت استفاده از این کد تمام شده.", 0

        # Calculate discount
        subtotal, shipping_cost, total = await _calculate_order_total(session, user_id, shop_id)
        if total < (dc.min_order_amount or 0):
            return f"❌ حداقل مبلغ سفارش برای این کد {format_price(dc.min_order_amount)} تومان است.", 0

        if dc.discount_type == "percent":
            amount = int(total * dc.discount_value / 100)
        else:
            amount = dc.discount_value

        # Clamp: don't exceed total
        amount = min(amount, total)
        amount = max(0, amount)

        return "", amount

    return "❌ خطا در اعمال کد تخفیف.", 0


async def ask_discount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask user to enter discount code."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🎁 کد تخفیف خود را وارد کنید:\n\n"
        "کد تخفیفت رو در خط بعدی بنویس (یا /cancel بزن تا انصراف بدی):",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ انصراف", callback_data="order:cancel")],
        ]),
    )
    return ASK_DISCOUNT


async def receive_discount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and validate discount code from user text input."""
    code = update.message.text.strip()
    shop_id = context.user_data.get("checkout_shop_id") or await get_current_shop_id(update)
    if not shop_id:
        await update.message.reply_text("❌ خطا: فروشگاه مشخص نیست.")
        return ConversationHandler.END

    error, amount = await _validate_and_apply_discount(context, code, shop_id, update.effective_user.id)
    if error:
        await update.message.reply_text(
            f"{error}\n\nکد دیگری وارد کن یا /cancel بزن:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ انصراف", callback_data="order:cancel")],
            ]),
        )
        return ASK_DISCOUNT

    context.user_data["discount_code"] = code.upper().strip()
    context.user_data["discount_amount"] = amount

    # Return to summary with discount applied
    await update.message.reply_text(
        f"✅ کد تخفیف {code.upper().strip()} با موفقیت اعمال شد! {format_price(amount)} تومان از مبلغت کم شد 🎉",
        parse_mode="HTML",
    )

    # If user was in card_to_card flow, go back to that summary view
    if context.user_data.get("card_total") is not None:
        return await _start_card_to_card_flow(update, context, await get_current_shop(update))

    return await _show_order_summary(update, context)


async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    shop_id = context.user_data.get("checkout_shop_id") or await get_current_shop_id(update)

    # ── Idempotency: جلوگیری از کلیک مضاعف ──
    if context.user_data.get("_order_in_progress"):
        await query.answer("⏳ سفارش قبلی در حال ثبت است...", show_alert=True)
        return
    context.user_data["_order_in_progress"] = True

    if not shop_id:
        await query.edit_message_text("لطفاً ابتدا با لینک فروشگاه وارد شوید.", reply_markup=_NAV_KB)
        context.user_data.clear()
        return ConversationHandler.END

    payment_method = context.user_data.get("payment_method", "cod")

    # Validate payment method
    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
    if payment_method not in get_enabled_payment_methods(shop):
        await query.edit_message_text("❌ این روش پرداخت برای این فروشگاه فعال نیست.", reply_markup=_NAV_KB)
        return ConversationHandler.END

    # Build customer info
    customer_info = CustomerInfo(
        receiver_name=context.user_data.get("order_name", ""),
        phone=context.user_data.get("order_phone", ""),
        shipping_address=context.user_data.get("order_address", ""),
        notes=context.user_data.get("order_notes", ""),
    )

    # Use the unified order service
    try:
        result = await create_order_from_cart(
            user_id=user_id,
            shop_id=shop_id,
            customer_info=customer_info,
            payment_method="card" if payment_method == "card_to_card" else "cod",
            discount_code=context.user_data.get("discount_code", ""),
            discount_amount=context.user_data.get("discount_amount", 0),
        )
    except ValueError as e:
        await query.edit_message_text(f"❌ {e}")
        return ConversationHandler.END

    order = result.order
    tracking_code = result.tracking_code
    total_price = result.total_price

    # ─── Notification ──────────────────────────────────
    notify_data = context.user_data
    await _notify(query, context, order.id, shop_id, tracking_code, total_price, notify_data)

    # Confirm to buyer
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user:
            user.saved_name = context.user_data.get("order_name")
            user.saved_phone = context.user_data.get("order_phone")
            user.saved_address = context.user_data.get("order_address")
            await session.commit()

    await query.edit_message_text(
        f"✅ سفارش شما ثبت شد!\n\n"
        f"📦 کد پیگیری: {tracking_code}\n"
        f"💰 مبلغ: {format_price(total_price)}\n\n"
        f"⏳ در انتظار تأیید فروشنده...",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 سفارش‌های من", callback_data="order:history")],
            [InlineKeyboardButton("🛍 منوی اصلی", callback_data="nav:main")],
        ]),
        parse_mode="HTML"
    )
    context.user_data.clear()
    return ConversationHandler.END


async def change_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    next_state = await _show_payment_method_selection(query, context)
    if next_state is None:
        return ASK_PAYMENT_METHOD
    return next_state


async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "❌ ثبت سفارش لغو شد، ولی نگران نباش — سبد خریدت دست‌نخورده باقی موند و هر وقت خواستی می‌تونی ادامه بدی.",
        reply_markup=_NAV_KB
    )
    context.user_data.clear()
    return ConversationHandler.END


# ─── Seller Approval: Card-to-Card Receipt ────────────────

async def _notify_seller_receipt(context, order_id: int, shop_id: int, tracking: str, total: float, file_id: str | None = None, receipt_text: str | None = None):
    """Send receipt (photo or text) to shop owner with approve/reject buttons."""
    # Get order items and customer info for shipping breakdown
    async with async_session() as session:
        order = await session.get(Order, order_id)
        shop = await session.get(Shop, shop_id)
        shipping_cost = shop.shipping_cost or 0.0 if shop else 0.0
        result = await session.execute(
            select(OrderItem).where(OrderItem.order_id == order_id)
        )
        order_items = result.scalars().all()
        subtotal = sum(item.unit_price * item.quantity for item in order_items) if order_items else 0

    msg = (
        f"🧾 رسید پرداخت جدید\n\n"
        f"سفارش: #{tracking}\n"
    )
    # Show breakdown if shipping cost applies
    if total != subtotal:
        msg += (
            f"جمع کالاها: {format_price(subtotal)}\n"
            f"هزینه ارسال: {format_price(total - subtotal)}\n"
            "─────────────\n"
        )
    msg += f"مبلغ قابل پرداخت: {format_price(total)}\n"

    if receipt_text:
        msg += f"🧾 شماره تراکنش: {receipt_text}\n"

    # ── Customer info ──
    msg += (
        f"\n👤 {order.receiver_name or '—'}"
        f"\n📞 {order.phone or '—'}"
        f"\n📍 {order.shipping_address or '—'}"
    )
    if order.customer_notes:
        msg += f"\n✏️ توضیحات: {order.customer_notes}"

    msg += "\n\nلطفاً پس از تطبیق مبلغ و رسید، تایید یا رد کنید:"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ تایید پرداخت", callback_data=f"seller:payment:approve:{order_id}"),
            InlineKeyboardButton("❌ رد کردن", callback_data=f"seller:payment:reject:{order_id}"),
        ]
    ])

    # Send to shop owner via NotificationService
    ns = get_notification_service(context.bot)
    if file_id:
        await ns.send_photo_to_seller(shop_id, file_id, msg, reply_markup=keyboard)
    elif receipt_text:
        await ns.send_to_seller(shop_id, msg, reply_markup=keyboard)
async def seller_approve_card_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فروشنده دکمه «تایید پرداخت» رو زده."""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split(":")
    order_id = int(parts[3])
    
    try:
        order = await transition_order(order_id, OrderStatus.PAID, actor="seller", bot=context.bot)
    except ValueError as e:
        await query.answer(str(e), show_alert=True)
        return

    # همون‌جا قدم بعدی رو جلوی دست فروشنده می‌ذاریم (ثبت کد رهگیری / ارسال شد)
    from handlers.admin.orders import order_detail_keyboard
    await query.edit_message_caption(
        caption=(
            f"✅ پرداخت سفارش #{order.tracking_code} تایید شد.\n\n"
            "وقتی بسته رو فرستادی «🚚 ارسال شد» رو بزن تا مشتری باخبر بشه."
        ),
        reply_markup=order_detail_keyboard(order, "admin:orders:pending:0"),
    )
    # Send confirmation to customer
    ns = get_notification_service(context.bot)
    await ns.send_to_customer(
        order.user_id,
        f"✅ پرداخت سفارش #{order.tracking_code} توسط فروشنده تایید شد!\n"
        f"سفارش شما در حال پردازش است 📦"
    )


async def handle_reject_card_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فروشنده دکمه «رد کردن» را زده — اول دلیل می‌خواهیم."""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split(":")
    order_id = int(parts[3])
    
    # Store order_id and ask for reason
    context.user_data["seller_reject_order_id"] = order_id
    
    await query.edit_message_caption(
        caption="✏️ لطفاً دلیل رد رسید رو بنویسید:\n\n"
                "مثال: مبلغ نادرست، تصویر رسید واضح نیست، کد پیگیری وجود نداره.\n\n"
                "⚠️ این دلیل به مشتری نمایش داده می‌شه.\n"
                "(برای انصراف /cancel رو بزنید)",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ انصراف از رد", callback_data=f"pay:cancel_reject:{order_id}")]
        ]),
        parse_mode="HTML",
    )


async def seller_submit_reject_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت دلیل رد از فروشنده و اجرای رد."""
    order_id = context.user_data.pop("seller_reject_order_id", None)
    if not order_id:
        return  # not in reject flow
    
    reason = update.message.text.strip() if update.message.text else ""
    if not reason:
        await update.message.reply_text("❌ لطفاً دلیل رد رو بنویسید یا /cancel بزنید.")
        context.user_data["seller_reject_order_id"] = order_id
        return
    
    try:
        success = await payment_svc.reject_card_payment(order_id, reason=reason)
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        return
    
    if not success:
        await update.message.reply_text("❌ این سفارش قبلاً پردازش شده یا قابل رد نیست.")
        return
    
    await update.message.reply_text("✅ رسید رد شد و دلیلش برای مشتری ارسال شد.")
    
    # Notify customer with retry options + appeal button + reason
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 آپلود رسید جدید", callback_data=f"pay:receipt_retry:{order_id}")],
        [InlineKeyboardButton("🚩 فکر می‌کنم این رد اشتباهه", callback_data=f"pay:appeal:{order_id}")],
        [InlineKeyboardButton("❌ لغو کامل سفارش", callback_data=f"pay:cancel:{order_id}")],
    ])
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order:
            ns = get_notification_service(context.bot)
            await ns.send_to_customer(
                order.user_id,
                text=(
                    "❌ رسید پرداخت شما توسط فروشنده تایید نشد.\n\n"
                    f"📌 دلیل فروشنده: {reason}\n\n"
                    "می‌تونی یکی از این گزینه‌ها رو انتخاب کنی:\n"
                    "🔁 آپلود رسید جدید — رسید دیگه‌ای بفرست\n"
                    "🚩 فکر می‌کنم اشتباه شده — درخواست به ادمین ارسال می‌شه\n"
                    "❌ لغو کامل سفارش — سفارش لغو و موجودی آزاد می‌شه\n\n"
                    "💡 رسید بانکی‌ت رو نگه‌دار — اگه پول واریز کرده باشی و کالا رو دریافت نکنی، "
                    "می‌تونی از طریق بانک یا پلیس فتا شکایت کنی."
                ),
                reply_markup=keyboard,
            )
async def handle_appeal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مشتری «فکر می‌کنم اشتباه شده» رو زده — به ادمین ارسال می‌کنه."""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split(":")
    order_id = int(parts[2])
    
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order:
            await query.edit_message_text("❌ سفارش یافت نشد.", reply_markup=_NAV_KB)
            return
        
        shop = await session.get(Shop, order.shop_id)
        
        # Build the appeal context
        appeal_text = (
            f"🚩 اعتراض به رد رسید\n\n"
            f"🆔 سفارش: #{order.tracking_code}\n"
            f"💰 مبلغ: {format_price(order.total_price)}\n"
            f"👤 مشتری: {order.receiver_name or '—'}\n"
            f"🏪 فروشگاه: {shop.name if shop else order.shop_id}\n"
            f"🔢 شماره پیگیری: {order.tracking_code}\n\n"
        )
        
        # Send to all admins via NotificationService
        ns = get_notification_service(context.bot)
        for admin_id in config.ADMIN_IDS:
            try:
                if order.payment_receipt_file_id:
                    await ns.bot.send_photo(
                        chat_id=admin_id,
                        photo=order.payment_receipt_file_id,
                        caption=appeal_text + "\n📎 رسید پیوست شده.",
                        parse_mode="HTML",
                    )
                else:
                    await ns.bot.send_message(
                        chat_id=admin_id,
                        text=appeal_text + f"📝 متن رسید:\n{order.payment_receipt_text or '—'}",
                        parse_mode="HTML",
                    )
            except Exception as e:
                logger.warning(f"اعتراض برای ادمین {admin_id} ارسال نشد: {e}")
    
    await query.edit_message_text(
        "✅ درخواستت برای ادمین فرستاده شد و به‌زودی بررسی می‌شه.",
    )


async def handle_card_receipt_retry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مشتری خواست رسید جدید بفرسته — سفارش رو توی context ذخیره می‌کنیم و منتظر عکس یا متن می‌شیم."""
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    order_id = int(parts[2])
    context.user_data["retry_receipt_order_id"] = order_id
    await query.edit_message_text(
        "لطفاً عکس رسید یا شماره تراکنش جدید رو بفرست:\n"
        "(برای لغو /cancel رو بزن)",
        parse_mode="HTML",
        reply_markup=_NAV_KB
    )
    return ASK_CARD_RECEIPT


async def handle_card_receipt_retry_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت عکس رسید یا شماره تراکنش جدید بعد از retry و ذخیره در سفارش موجود."""
    try:
        order_id = context.user_data.get("retry_receipt_order_id")
        if order_id is None:
            # این هندلر برای همه پیام‌ها fire میشه — فقط وقتی سکوت کن که retry فعال نیست
            return

        file_id = None
        receipt_text = None

        if update.message.photo:
            file_id = update.message.photo[-1].file_id
        elif update.message.text:
            receipt_text = update.message.text.strip()
            receipt_text = receipt_text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
            if len(receipt_text) < 4 or len(receipt_text) > 100:
                await update.message.reply_text(
                    "❌ شماره تراکنش معتبر نیست.\n"
                    "لطفاً یه شماره تراکنش معتبر (حداقل ۴ رقم) یا عکس رسید بفرست:",
                    parse_mode="HTML"
                )
                return ASK_CARD_RECEIPT
        else:
            await update.message.reply_text(
                "❌ لطفاً عکس رسید یا شماره تراکنش رو بفرست:",
                parse_mode="HTML"
            )
            return ASK_CARD_RECEIPT

        success = await payment_svc.retry_card_receipt(order_id, file_id=file_id, receipt_text=receipt_text)
    except Exception as e:
        logger.exception(f"خطا در handle_card_receipt_retry_photo برای user={update.effective_user.id}: {e}")
        await update.message.reply_text("❌ خطا در ذخیره رسید. لطفاً دوباره تلاش کن.")
        context.user_data.pop("retry_receipt_order_id", None)
        return ConversationHandler.END

    if success:
        # Re-notify seller
        async with async_session() as session:
            order = await session.get(Order, order_id)
            if order:
                try:
                    from database.models import ShopOwner
                    result = await session.execute(
                        select(ShopOwner).where(ShopOwner.shop_id == order.shop_id).limit(1)
                    )
                    owner = result.scalar_one_or_none()
                    if owner:
                        notificationsrv = get_notification_service(context.bot)
                        notify_text = (
                            f"🔄 مشتری رسید جدید برای سفارش #{order.tracking_code} ارسال کرد.\n\n"
                        )
                        if receipt_text:
                            notify_text += f"🧾 شماره تراکنش: {receipt_text}\n\n"
                        notify_text += "لطفاً تایید یا رد کنید:"

                        ns = notificationsrv
                        if file_id:
                            await ns.send_photo_to_seller(
                                order.shop_id,
                                file_id,
                                caption=notify_text,
                                reply_markup=InlineKeyboardMarkup([
                                    [
                                        InlineKeyboardButton("✅ تایید پرداخت", callback_data=f"seller:payment:approve:{order_id}"),
                                        InlineKeyboardButton("❌ رد کردن", callback_data=f"seller:payment:reject:{order_id}"),
                                    ]
                                ]),
                            )
                        else:
                            await ns.send_to_seller(
                                order.shop_id,
                                notify_text,
                                reply_markup=InlineKeyboardMarkup([
                                    [
                                        InlineKeyboardButton("✅ تایید پرداخت", callback_data=f"seller:payment:approve:{order_id}"),
                                        InlineKeyboardButton("❌ رد کردن", callback_data=f"seller:payment:reject:{order_id}"),
                                    ]
                                ]),
                            )
                except Exception as e:
                    logger.error(f"ارسال رسید جدید به فروشنده ناموفق: {e}")
        
        await update.message.reply_text(
            f"✅ رسید جدید دریافت شد و برای فروشنده ارسال گردید.\n"
            f"منتظر تایید فروشنده باش... ⏳",
            reply_markup=_NAV_KB
        )
        context.user_data.pop("retry_receipt_order_id", None)

    else:
        await update.message.reply_text("❌ مشکلی پیش اومد. لطفاً دوباره تلاش کن.", reply_markup=_NAV_KB)

    return ConversationHandler.END


async def handle_convert_to_cod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مشتری خواست روش پرداخت رو به درب منزل تغییر بده."""
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    order_id = int(parts[2])
    
    try:
        order = await transition_order(order_id, OrderStatus.CANCELLED, actor="customer", bot=context.bot)
    except ValueError as e:
        await query.answer(str(e), show_alert=True)
        return

    # Update order payment method to COD via direct DB update
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order:
            order.payment_method = "cod"
            await session.commit()

    await query.edit_message_text(
        "✅ روش پرداخت سفارش به **درب منزل** تغییر یافت.\n\n"
        "هزینه سفارش زمان تحویل دریافت می‌شه.",
        parse_mode="Markdown",
        reply_markup=_NAV_KB
    )
    from services.events import event_bus, Event
    context.application.create_task(
        event_bus.emit(
            Event.ORDER_CANCELLED,
            order_id=order.id,
            shop_id=order.shop_id,
            tracking_code=order.tracking_code,
            cancelled_by="customer",
            reason="payment_method_changed_to_cod",
            bot=context.bot,
        )
    )


async def handle_cancel_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فروشنده از رد منصرف شد."""
    query = update.callback_query
    await query.answer()
    context.user_data.pop("seller_reject_order_id", None)
    await query.edit_message_caption(caption="✅ از رد رسید منصرف شدید.", reply_markup=None)


async def handle_pay_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو کامل سفارش از دکمه‌های جایگزین بعد از رد رسید یا انصراف هنگام پرداخت."""
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    order_id = int(parts[2])
    context.user_data.pop("seller_reject_order_id", None)

    try:
        order = await cancel_order_and_release_stock(order_id, actor="customer")
    except ValueError as e:
        await query.answer(str(e), show_alert=True)
        return

    await query.edit_message_text(
        "❌ سفارش شما لغو شد.\n"
        "موجودی محصولات آزاد شد.",
        reply_markup=_NAV_KB
    )


# ─── Order History ────────────────────────────────────────────

def _order_detail_progress_bar(order) -> str:
    """Build a text progress bar for order status."""
    steps = [
        ("📦 ثبت سفارش", OrderStatus.PENDING_PAYMENT),
        ("✅ پرداخت", OrderStatus.PAID),
        ("📦 آماده‌سازی", OrderStatus.PREPARING),
        ("🚚 ارسال", OrderStatus.SHIPPED),
        ("📬 تحویل", OrderStatus.DELIVERED),
    ]
    lines = ["\n━━━ وضعیت سفارش ━━━\n"]
    found_current = False
    completed = True
    for label, status in steps:
        if order.status == status:
            lines.append(f"🟢 {label} ⬅️")
            found_current = True
            completed = False
        elif order.status in (OrderStatus.DELIVERED,):
            lines.append(f"  ✅ {label}")
        elif order.status == OrderStatus.CANCELLED and not found_current and completed:
            lines.append(f"  ⬜️ {label}")
            completed = False
        elif order.status == OrderStatus.CANCELLED:
            lines.append(f"  ⬜️ {label}")
        elif order.status == OrderStatus.REFUNDED:
            lines.append(f"  ⬜️ {label}")
        elif found_current:
            lines.append(f"  ⬜️ {label}")
        else:
            lines.append(f"  ✅ {label}")
    if order.status == OrderStatus.DELIVERED:
        lines.append("\n✅ سفارش تکمیل شد!")
    elif order.status == OrderStatus.CANCELLED:
        lines.append("\n❌ سفارش لغو شد")
    elif order.status == OrderStatus.REFUNDED:
        lines.append("\n↩️ وجه برگردانده شد")
    return "\n".join(lines)


def _order_detail_text_customer(order: Order) -> str:
    """Generate order detail text for customer view."""
    payment_methods = {
        "card_to_card": "🧾 کارت به کارت",
        "cod": "🚚 درب منزل",
        None: "—"
    }
    payment_statuses = {
        "paid": "✅ پرداخت شده",
        "pending": "⏳ در انتظار",
        "cancelled": "❌ لغو شده",
        None: "—"
    }
    lines = [
        f"🧾 سفارش #{order.tracking_code}",
        f"وضعیت: {ORDER_STATUS_LABELS.get(order.status, order.status)}",
        f"💳 روش پرداخت: {payment_methods.get(order.payment_method, order.payment_method or '—')}",
        f"💲 وضعیت پرداخت: {payment_statuses.get(order.payment_status_view, '—')}",
        f"👤 گیرنده: {order.receiver_name}",
        f"📞 تماس: {order.phone}",
        f"📍 آدرس: {order.shipping_address}",
        f"🕒 تاریخ ثبت: {to_jalali(order.created_at)}",
        "",
        "اقلام سفارش:",
    ]
    for item in order.items:
        lines.append(f"• {item.product_name} × {item.quantity} = {format_price(item.unit_price * item.quantity)}")
    
    # Add shipping breakdown
    subtotal = sum(item.unit_price * item.quantity for item in order.items)
    shipping_cost = order.total_price - subtotal
    if shipping_cost > 0:
        lines.append(f"\n📦 جمع کالاها: {format_price(subtotal)}")
        lines.append(f"🚚 هزینه ارسال: {format_price(shipping_cost)}")
        lines.append("─────────────")
    lines.append(f"💰 جمع کل: {format_price(order.total_price)}")

    # کد رهگیری
    if order.tracking_number:
        lines.append(f"\n📮 <b>کد رهگیری پستی:</b> <code>{order.tracking_number}</code>")

    history = order.get_status_history()
    if history:
        lines.append("\n📜 تاریخچه وضعیت:")
        for h in history:
            ts = h.changed_at.strftime("%Y-%m-%d %H:%M") if h.changed_at else ""
            meta = h.get_meta()
            reason = f" — {meta.get('reason', '')}" if meta.get('reason') else ""
            lines.append(f"  • {ts} — {h.status} (توسط {h.changed_by}){reason}")

    # Progress bar
    lines.append(_order_detail_progress_bar(order))

    return "\n".join(lines)


async def order_detail_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مشاهده جزئیات سفارش توسط مشتری."""
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    order_id = int(parts[2])  # order:detail:123 -> parts[2] = 123
    shop_id = await get_current_shop_id(update)

    if not shop_id:
        await render_view(query, context, "لطفاً ابتدا با لینک فروشگاه وارد شوید.",
                          InlineKeyboardMarkup([[InlineKeyboardButton("🏠 شروع", callback_data="nav:main")]]))
        return

    async with async_session() as session:
        stmt = select(Order).where(Order.id == order_id, Order.user_id == update.effective_user.id, Order.shop_id == shop_id)
        order = (await session.execute(stmt)).scalar_one_or_none()
        if order:
            # تاریخچه‌ی وضعیت هم توی متن جزئیات نشون داده می‌شه؛ بیرون از session لود نمی‌شه
            await session.refresh(order, attribute_names=["items", "histories"])

    if not order:
        await render_view(query, context, "این سفارش پیدا نشد.",
                          InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="order:history")]]))
        return

    # دکمه پیام به فروشنده
    rows = []
    if order.status not in (OrderStatus.CANCELLED, OrderStatus.REFUNDED):
        rows.append([InlineKeyboardButton("🔄 خرید دوباره", callback_data=f"order:reorder:{order.id}")])
    if config.WIDGETS_ENABLED and order.status not in (OrderStatus.CANCELLED, OrderStatus.REFUNDED):
        rows.append([InlineKeyboardButton("📍 رهگیری زنده", callback_data=f"order:track:{order.id}")])
    rows.append([InlineKeyboardButton("💬 پیام به فروشنده", callback_data=f"msg:open_conv:{order.id}")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="order:history")])
    await render_view(query, context, _order_detail_text_customer(order), InlineKeyboardMarkup(rows))


async def handle_reorder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔄 خرید دوباره: add all products from a previous order to cart."""
    query = update.callback_query
    await query.answer()
    _, _, order_id = query.data.split(":")
    order_id = int(order_id)
    shop_id = await get_current_shop_id(update)
    user_id = update.effective_user.id

    if not shop_id:
        await query.answer("لطفاً ابتدا وارد فروشگاه شوید.", show_alert=True)
        return

    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order or order.user_id != user_id or order.shop_id != shop_id:
            await query.answer("این سفارش پیدا نشد.", show_alert=True)
            return

        await session.refresh(order, attribute_names=["items"])
        added = 0
        skipped = 0
        already_in_cart = 0

        for item in order.items:
            product = await session.get(Product, item.product_id) if item.product_id else None
            if not product or not product.is_active or product.available_stock < 1:
                skipped += 1
                continue

            # Check if already in cart
            existing = await session.execute(
                select(CartItem).where(
                    CartItem.user_id == user_id,
                    CartItem.shop_id == shop_id,
                    CartItem.product_id == product.id,
                )
            )
            cart_item = existing.scalar_one_or_none()
            if cart_item:
                cart_item.quantity += item.quantity
                already_in_cart += 1
            else:
                session.add(CartItem(user_id=user_id, shop_id=shop_id, product_id=product.id, quantity=item.quantity))
            added += 1

        await session.commit()

    msg = f"🔄 خرید مجدد از سفارش #{order.tracking_code}\n\n✅ {added} محصول به سبد اضافه شد."
    if already_in_cart:
        msg += f"\n🔁 {already_in_cart} محصول قبلاً تو سبد بود (تعداد افزایش یافت)."
    if skipped:
        msg += f"\n❌ {skipped} محصول ناموجود/غیرفعال بود."
    msg += "\n\nاز منوی اصلی سبد خرید رو ببین و سفارش بده."

    await query.message.reply_text(msg)


async def _append_order_summary(lines: list, order: Order):
    """Add one order line to summary — safely handles deleted products."""
    status_label = ORDER_STATUS_LABELS.get(order.status, order.status)
    lines.append(
        f"#{order.tracking_code} — {status_label} — "
        f"{format_price(order.total_price)} — {to_jalali(order.created_at)}"
    )


async def _order_history_keyboard(orders) -> InlineKeyboardMarkup:
    """Build inline keyboard with order detail buttons."""
    rows = []
    for o in orders[:15]:
        status_label = ORDER_STATUS_LABELS.get(o.status, o.status)
        rows.append([
            InlineKeyboardButton(
                f"#{o.tracking_code} — {status_label} — {format_price(o.total_price)}",
                callback_data=f"order:detail:{o.id}"
            )
        ])
    rows.append([InlineKeyboardButton("🔙 منوی اصلی", callback_data="nav:main")])
    return InlineKeyboardMarkup(rows)


async def order_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query if update.callback_query else None
    if query:
        await query.answer()

    shop_id = await get_current_shop_id(update)
    if not shop_id:
        text = "لطفاً ابتدا با لینک فروشگاه وارد شوید."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 شروع", callback_data="nav:main")]])
        if query:
            await render_view(query, context, text, keyboard)
        else:
            await update.message.reply_text(text, reply_markup=keyboard)
        return

    async with async_session() as session:
        result = await session.execute(
            select(Order).where(Order.user_id == update.effective_user.id, Order.shop_id == shop_id)
            .order_by(Order.created_at.desc())
        )
        orders = result.scalars().all()

    if not orders:
        text = "📭 هنوز هیچ سفارشی ثبت نکردی. وقتشه یه سر به محصولات بزنی!"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="nav:main")]])
    else:
        text = "📦 سفارش‌های شما (برای جزئیات بزنید):"
        keyboard = await _order_history_keyboard(orders)

    if query:
        await render_view(query, context, text, keyboard)
    else:
        await update.message.reply_text(text, reply_markup=keyboard)


# ─── Helper: Notifications ──────────────────────────────────

async def _notify(query, context, order_id: int, shop_id: int, tracking_code: str, total: float, user_data: dict):
    """Send notification to channel + shop owner via event."""
    from services.events import event_bus, Event

    name = user_data.get("order_name", "نامشخص")
    phone = user_data.get("order_phone", "—")
    address = user_data.get("order_address", "—")

    msg = (
        f"🆕 سفارش جدید #{tracking_code}\n"
        f"👤 {name}\n📞 {phone}\n💰 {format_price(total)}\n📍 {address}"
    )

    # Emit event
    context.application.create_task(
        event_bus.emit(Event.ORDER_CREATED, order_id=order_id, shop_id=shop_id, message=msg, total=total)
    )

    # Channel notification
    ns = get_notification_service(context.bot)
    await ns.send_to_channel(msg)