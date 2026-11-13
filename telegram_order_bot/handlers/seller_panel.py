"""
پنل مدیریت فروشنده — ادغام شده: محصولات، دسته‌بندی، سفارش‌ها، تنظیمات، پرداخت.
"""
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from database.db import async_session
from database.models import Admin, Shop, ShopOwner
from utils.helpers import format_price, is_super_admin, to_jalali, to_persian_digits
from utils.crypto import safe_encrypt, safe_decrypt
from utils.tg_helpers import escape_html, get_current_shop_id, render_view
import config
from config import WEBSITE_URL
from services.widgets import available as widgets_available

from sqlalchemy import select

logger = logging.getLogger(__name__)

# Conversation states
SET_NEW_PASSWORD, ADMIN_SET_NEW_PASSWORD = range(100, 102)
PAYMENT_SETTING_MENU, SET_CARD_NUMBER, SET_CARD_HOLDER, SET_SHIPPING_COST = range(200, 204)
SHOP_INFO = 300
SET_BANNER = 400


# ═══════════════════════════════════════════════════════════════
# Unified Seller Panel — the ONE place for everything
# ═══════════════════════════════════════════════════════════════

async def _build_seller_panel(user_id: int, bot_username: str = "") -> tuple[str, InlineKeyboardMarkup]:
    """ساخت متن و کیبورد پنل یکپارچه فروشنده."""
    async with async_session() as session:
        owner = await session.execute(
            select(ShopOwner).where(ShopOwner.user_id == user_id)
        )
        owner = owner.scalar_one_or_none()

    if not owner:
        return "⚠️ این بخش فقط برای فروشنده‌هاست. اگه می‌خوای فروشگاه بسازی: /start → «🏪 می‌خوام فروشگاه بسازم»", InlineKeyboardMarkup([])

    async with async_session() as session:
        shop = await session.get(Shop, owner.shop_id)

    if not shop:
        return "❌ فروشگاهی برای حساب شما پیدا نشد. اگه فکر می‌کنی اشتباهی رخ داده، با پشتیبانی تماس بگیر.", InlineKeyboardMarkup([])

    # Card status (decrypt for display)
    card_decrypted = safe_decrypt(shop.card_number) or ""
    card_line = f"💳 کارت: ...{card_decrypted[-4:]}" if card_decrypted else "⚠️ کارت ثبت نشده (مشتری نمی‌تونه پرداخت کنه)"
    link = f"https://t.me/{bot_username}?start=shop_{shop.id}" if bot_username else ""

    # سفارش‌هایی که منتظر اقدام فروشنده‌ان: رسید رسیده یا پرداخت تایید شده ولی هنوز ارسال نشده
    from database.models import Order, OrderStatus
    from sqlalchemy import func, or_, and_
    async with async_session() as session:
        pending = (await session.execute(
            select(func.count(Order.id)).where(
                Order.shop_id == shop.id,
                or_(
                    Order.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.PREPARING]),
                    and_(Order.status == OrderStatus.PENDING_PAYMENT, Order.payment_receipt_at.is_not(None)),
                ),
            )
        )).scalar_one()
    badge = f" ({to_persian_digits(pending)})" if pending else ""

    lines = [f"🏪 <b>{escape_html(shop.name)}</b>", ""]
    lines.append(f"🧾 {to_persian_digits(pending)} سفارش منتظر اقدام تو" if pending else "🧾 سفارش منتظر اقدامی نداری")
    lines.append(card_line)
    if not config.FREE_MODE:
        from services.subscription import get_subscription_display
        async with async_session() as session:
            lines.append(f"🎫 اشتراک: {await get_subscription_display(shop.id, session)}")
    if link:
        lines += ["", f"🔗 لینک فروشگاهت:\n{link}"]
    text = "\n".join(lines)

    buttons = [
        [InlineKeyboardButton(f"🧾 سفارش‌ها{badge}", callback_data="admin:orders:pending:0"),
         InlineKeyboardButton("💬 پیام‌ها", callback_data="seller:inbox")],
        [InlineKeyboardButton("➕ محصول جدید", callback_data="admin:products:add"),
         InlineKeyboardButton("📦 محصولات", callback_data="admin:products:list:0")],
        [*([InlineKeyboardButton("📈 داشبورد زنده", callback_data="seller:live")] if widgets_available() else []),
         InlineKeyboardButton("📊 آمار فروش", callback_data="seller:stats")],
        [InlineKeyboardButton("🔗 لینک فروشگاه", callback_data="seller:show_link"),
         InlineKeyboardButton("💰 کد تخفیف", callback_data="discount:list")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="seller:settings")],
    ]
    return text, InlineKeyboardMarkup(buttons)


async def seller_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنظیمات کم‌استفاده‌تر یک‌جا، تا صفحه‌ی اصلی پنل شلوغ نشه."""
    query = update.callback_query
    await query.answer()
    rows = [
        [InlineKeyboardButton("🧾 تنظیمات پرداخت و ارسال", callback_data="seller:payment_settings")],
        [InlineKeyboardButton("🗂 دسته‌بندی‌ها", callback_data="admin:categories"),
         InlineKeyboardButton("📷 عکس کاور", callback_data="seller:set_banner")],
        [InlineKeyboardButton("📜 تاریخچه سفارش‌ها", callback_data="admin:orders:history:0")],
        [InlineKeyboardButton("⚙️ تنظیمات سایت", callback_data="seller:site_settings"),
         InlineKeyboardButton("👤 اطلاعات حساب", callback_data="seller:account_info")],
    ]
    if not config.FREE_MODE:
        rows.insert(1, [InlineKeyboardButton("💳 اشتراک فروشگاه", callback_data="seller:subscription:show")])
    rows += [
        [InlineKeyboardButton("🗑 حذف فروشگاه", callback_data="seller:delete_shop")],
        [InlineKeyboardButton("🔙 پنل فروشگاه", callback_data="seller:panel_back")],
    ]
    await render_view(query, context, "⚙️ تنظیمات فروشگاه", InlineKeyboardMarkup(rows))


async def seller_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /myshop — پنل یکپارچه مدیریت فروشنده."""
    user_id = update.effective_user.id
    async with async_session() as session:
        owner = await session.execute(
            select(ShopOwner).where(ShopOwner.user_id == user_id)
        )
        owner = owner.scalar_one_or_none()
        admin_record = await session.execute(
            select(Admin).where(Admin.user_id == user_id)
        )
        admin_record = admin_record.scalar_one_or_none()

    if not owner and not admin_record:
        await update.message.reply_text(
            "⚠️ شما فروشنده نیستید.\n"
            "برای ساخت فروشگاه: /start → 🏪 می‌خوام فروشگاه بسازم"
        )
        return

    # Super admin without shop → go to admin panel
    if is_super_admin(user_id) and not owner:
        from handlers.admin.panel import admin_command
        await admin_command(update, context)
        return

    # Check shop status
    if owner:
        async with async_session() as session:
            shop = await session.get(Shop, owner.shop_id)
        if shop and shop.status != "active":
            status_text = {
                "draft": "⏳ فروشگاه شما در انتظار تایید ادمین است.",
                "suspended": "🚫 فروشگاه شما معلق شده.",
                "rejected": "❌ فروشگاه شما تایید نشده." + (f"\nدلیل: {shop.rejection_reason}" if shop.rejection_reason else ""),
            }
            await update.message.reply_text(
                f"🏪 {shop.name}\n{status_text.get(shop.status, '⚠️ وضعیت نامشخص.')}\n\n"
                "تا زمان تایید، امکان مدیریت وجود ندارد.\n💬 برای پیگیری: /support"
            )
            return

    text, keyboard = await _build_seller_panel(user_id, context.bot.username)
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


async def my_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /my_panel — همون پنل یکپارچه."""
    await seller_panel_command(update, context)


# ═══════════════════════════════════════════════════════════════
# Callback-based panel back (for inline buttons)
# ═══════════════════════════════════════════════════════════════

async def panel_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازگشت به پنل یکپارچه فروشنده (callback-based)."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    text, keyboard = await _build_seller_panel(user_id, context.bot.username)
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════
# /neworders command
# ═══════════════════════════════════════════════════════════════

async def neworders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /neworders — show pending orders for seller."""
    user_id = update.effective_user.id
    async with async_session() as session:
        owner = await session.execute(
            select(ShopOwner).where(ShopOwner.user_id == user_id)
        )
        owner = owner.scalar_one_or_none()

    if not owner:
        await update.message.reply_text("⚠️ فقط فروشنده‌ها به این بخش دسترسی دارن.")
        return

    # Check shop status
    async with async_session() as session:
        shop = await session.get(Shop, owner.shop_id)
    if shop and shop.status != "active":
        await update.message.reply_text(
            f"🏪 {shop.name}\n⏳ فروشگاه شما در انتظار تایید ادمین است.\n\n"
            "تا زمان تایید، امکان مدیریت سفارش‌ها وجود ندارد.\n💬 برای پیگیری: /support"
        )
        return

    await _show_seller_pending_orders(update.message, user_id)


# ═══════════════════════════════════════════════════════════════
# Support command
# ═══════════════════════════════════════════════════════════════

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /support for sellers — show inbox (Message context)."""
    user_id = update.effective_user.id
    async with async_session() as session:
        from sqlalchemy import select, func as sf
        from database.models import Conversation, Message
        owner = await session.execute(
            select(ShopOwner).where(ShopOwner.user_id == user_id)
        )
        owner = owner.scalar_one_or_none()
        if not owner:
            await update.message.reply_text(
                "⚠️ اینباکس پیام‌ها فقط برای فروشنده‌هاست.\n"
                "💬 اگه به پشتیبانی نیاز داری: /start → «☎️ پشتیبانی»"
            )
            return

        conv_rows = await session.execute(
            select(Conversation).where(
                Conversation.shop_id == owner.shop_id,
                Conversation.status == "open",
            ).order_by(Conversation.updated_at.desc())
        )
        conversations = conv_rows.scalars().all()

    if not conversations:
        await update.message.reply_text(
            "📭 اینباکس پیام‌ها\n\nهیچ پیامی از خریداران ندارید."
        )
    else:
        from database.models import User
        lines = ["📬 اینباکس پیام‌ها", "برای مشاهده کلیک کن:\n"]
        buttons = []
        async with async_session() as session:
            for conv in conversations:
                buyer = await session.get(User, conv.buyer_id)
                buyer_name = buyer.first_name or f"کاربر {conv.buyer_id}" if buyer else f"کاربر {conv.buyer_id}"
                unread = await session.execute(
                    select(sf.count(Message.id)).where(
                        Message.conversation_id == conv.id,
                        Message.sender_role == "buyer",
                        Message.read_at.is_(None),
                    )
                )
                unread_count = unread.scalar() or 0
                badge = f" ({unread_count} جدید)" if unread_count else ""
                lines.append(f"• {buyer_name}{badge}")
                buttons.append([
                    InlineKeyboardButton(
                        f"💬 {buyer_name}{badge}",
                        callback_data=f"msg:open:{conv.id}",
                    )
                ])
        text = "\n".join(lines)
        buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin:panel")])
        await update.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=None
        )


# ═══════════════════════════════════════════════════════════════
# Password change
# ═══════════════════════════════════════════════════════════════

async def change_password_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    role = query.data.split(":")[0]  # 'seller' or 'admin'
    context.user_data["change_password_role"] = role
    await query.edit_message_text(
        "🔐 رمز عبور جدید رو وارد کن (حداقل ۶ کاراکتر):\n"
        "برای لغو /cancel رو بزن."
    )
    if role == "admin":
        return ADMIN_SET_NEW_PASSWORD
    return SET_NEW_PASSWORD


async def save_new_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    if len(password) < 6:
        await update.message.reply_text("❌ رمز عبور باید حداقل ۶ کاراکتر باشه. یه رمز قوی‌تر انتخاب کن:")
        return SET_NEW_PASSWORD if context.user_data.get("change_password_role") != "admin" else ADMIN_SET_NEW_PASSWORD

    import bcrypt
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    user_id = update.effective_user.id
    role = context.user_data.get("change_password_role", "seller")

    if role == "admin":
        async with async_session() as session:
            admin = await session.execute(
                select(Admin).where(Admin.user_id == user_id)
            )
            admin = admin.scalar_one_or_none()
            if not admin:
                await update.message.reply_text("❌ شما ادمین نیستید.")
                return ConversationHandler.END
            admin.password_hash = hashed
            await session.commit()
    else:
        async with async_session() as session:
            owner = await session.execute(
                select(ShopOwner).where(ShopOwner.user_id == user_id)
            )
            owner = owner.scalar_one_or_none()
            if not owner:
                await update.message.reply_text("❌ شما فروشنده نیستید.")
                return ConversationHandler.END
            owner.password_hash = hashed
            owner.password_salt = ""
            await session.commit()

    back_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="seller:panel_back")]])
    await update.message.reply_text("✅ رمز عبور جدیدت با موفقیت ذخیره شد 🔐", reply_markup=back_keyboard)
    context.user_data.pop("change_password_role", None)
    return ConversationHandler.END


async def reset_password_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازیابی رمز عبور — /reset_password"""
    user_id = update.effective_user.id
    import bcrypt
    import secrets

    async with async_session() as session:
        owner = await session.execute(
            select(ShopOwner).where(ShopOwner.user_id == user_id).limit(1)
        )
        owner = owner.scalar_one_or_none()

        admin = await session.execute(
            select(Admin).where(Admin.user_id == user_id).limit(1)
        )
        admin = admin.scalar_one_or_none()

    if not owner and not admin:
        await update.message.reply_text(
            "❌ شما نه فروشنده هستید و نه ادمین.\n"
            "اگه مشتری هستی برای ورود به سایت نیازی به رمز نداری — "
            "فقط شناسه تلگرامت رو تو صفحه لاگین وارد کن."
        )
        return

    temp_pass = secrets.token_hex(4)
    hashed = bcrypt.hashpw(temp_pass.encode(), bcrypt.gensalt()).decode()

    role_name = ""
    if owner:
        async with async_session() as session:
            o = await session.get(ShopOwner, owner.id)
            o.password_hash = hashed
            o.password_salt = ""
            o.must_change_password = True
            await session.commit()
        role_name = "فروشنده"

    if admin:
        async with async_session() as session:
            a = await session.get(Admin, admin.id)
            a.password_hash = hashed
            a.must_change_password = True
            await session.commit()
        role_name = "ادمین" if not role_name else f"{role_name} + ادمین"

    await update.message.reply_text(
        f"🔐 رمز موقت برای نقش {role_name} ساخته شد:\n\n"
        f"{temp_pass}\n\n"
        f"⚠️ این رمز یک‌بار مصرف است و بعد از ورود به سایت باید حتماً از بخش "
        f"«⚙️ تنظیمات» داخل پنل (https://telegramorder.ir/admin/settings برای ادمین "
        f"یا https://telegramorder.ir/seller/settings برای فروشنده) یک رمز جدید بذاری. "
        f"اعتبار این رمز فقط ۱۵ دقیقه هست.\n"
        f"(این پیام رو پاک کن بعد از خوندن)",
        parse_mode="HTML"
    )
    logger.info(f"رمز عبور {user_id} بازنشانی شد")


# ═══════════════════════════════════════════════════════════════
# Shop Link
# ═══════════════════════════════════════════════════════════════

async def show_shop_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لینک اشتراک‌گذاری فروشگاه."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    shop_id = await _get_shop_id(user_id)
    if not shop_id:
        await query.edit_message_text("❌ شما فروشنده نیستید.")
        return ConversationHandler.END

    async with async_session() as session:
        shop = await session.get(Shop, shop_id)

    shop_name = shop.name if shop else "فروشگاه شما"
    bot_username = context.bot.username
    deep_link = f"https://t.me/{bot_username}?start=shop_{shop_id}"

    text = (
        f"🏪 لینک اشتراک‌گذاری فروشگاه «{shop_name}»\n\n"
        f"🔗 {deep_link}\n\n"
        "💡 این لینک رو با مشتریات به اشتراک بذار.\n"
        "وقتی مشتری روش کلیک می‌کنه، مستقیم منوی همین فروشگاه میاد:"
    )

    from urllib.parse import quote
    share = f"https://t.me/share/url?url={quote(deep_link)}&text={quote('فروشگاه ' + shop_name)}"
    buttons = [
        [InlineKeyboardButton("📤 اشتراک‌گذاری", url=share)],
        [InlineKeyboardButton("📋 بازگشت به پنل", callback_data="seller:panel_back")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML", disable_web_page_preview=True)
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════
# Payment Settings
# ═══════════════════════════════════════════════════════════════

async def payment_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی تنظیمات پرداخت."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    async with async_session() as session:
        owner = await session.execute(
            select(ShopOwner).where(ShopOwner.user_id == user_id)
        )
        owner = owner.scalar_one_or_none()
        if not owner:
            await query.edit_message_text("❌ شما فروشنده نیستید.")
            return ConversationHandler.END

        shop = await session.get(Shop, owner.shop_id)

    if not shop:
        await query.edit_message_text("❌ فروشگاه شما یافت نشد.")
        return ConversationHandler.END

    # Decrypt for display
    card_decrypted = safe_decrypt(shop.card_number) or ""
    holder_decrypted = safe_decrypt(shop.card_holder_name) or ""
    card_status = f"✅ ...{card_decrypted[-4:]}" if card_decrypted else "🔴 تنظیم نشده"
    card_holder = f"✅ {holder_decrypted}" if holder_decrypted else "🔴 تنظیم نشده"
    shipping_status = f"{format_price(shop.shipping_cost)}" if shop.shipping_cost else "🆓 رایگان"

    text = (
        f"🧾 تنظیمات پرداخت «{shop.name}»\n\n"
        f"💳 کارت به کارت\n"
        f"   شماره: {card_status}\n"
        f"   به نام: {card_holder}\n\n"
        f"🚚 هزینه ارسال\n"
        f"   مبلغ: {shipping_status}\n\n"
        "برای تغییر هر بخش روی دکمه مربوطه کلیک کن:"
    )

    buttons = [
        [InlineKeyboardButton("💳 شماره کارت", callback_data="payment:set_card_number")],
        [InlineKeyboardButton("👤 نام صاحب کارت", callback_data="payment:set_card_holder")],
        [InlineKeyboardButton("🚚 هزینه ارسال", callback_data="payment:set_shipping")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="seller:panel_back")],
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")
    return PAYMENT_SETTING_MENU


async def _get_shop_id(user_id: int) -> int | None:
    """Helper: get shop_id for user."""
    async with async_session() as session:
        owner = await session.execute(
            select(ShopOwner).where(ShopOwner.user_id == user_id)
        )
        owner = owner.scalar_one_or_none()
        if not owner:
            return None
        return owner.shop_id


async def ask_card_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "شماره کارت ۱۶ رقمی رو بدون فاصله وارد کن:\n"
        "(مثال: 6037991234567890)\n\n"
        "برای لغو: /cancel"
    )
    return SET_CARD_NUMBER


async def save_card_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ذخیره شماره کارت فروشنده."""
    card_number = update.message.text.strip().replace(" ", "").replace("-", "")
    card_number = card_number.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))

    if not card_number.isdigit() or len(card_number) != 16:
        await update.message.reply_text("❌ شماره کارت باید ۱۶ رقم باشه. دوباره وارد کن:")
        return SET_CARD_NUMBER

    user_id = update.effective_user.id
    shop_id = await _get_shop_id(user_id)
    if not shop_id:
        await update.message.reply_text("❌ شما فروشنده نیستید.")
        return ConversationHandler.END

    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
        if shop:
            shop.card_number = safe_encrypt(card_number)
            await session.commit()

    await update.message.reply_text(
        f"✅ شماره کارت ذخیره شد: {card_number[:4]}****{card_number[-4:]}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="seller:panel_back")]])
    )
    return ConversationHandler.END


async def ask_card_holder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "نام صاحب کارت رو وارد کن:\n\n"
        "برای لغو: /cancel"
    )
    return SET_CARD_HOLDER


async def save_card_holder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    card_holder = update.message.text.strip()
    if len(card_holder) < 2:
        await update.message.reply_text("❌ نام خیلی کوتاهه. دوباره وارد کن:")
        return SET_CARD_HOLDER

    user_id = update.effective_user.id
    shop_id = await _get_shop_id(user_id)
    if not shop_id:
        await update.message.reply_text("❌ شما فروشنده نیستید.")
        return ConversationHandler.END

    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
        if shop:
            shop.card_holder_name = safe_encrypt(card_holder)
            await session.commit()

    await update.message.reply_text(
        f"✅ نام صاحب کارت ذخیره شد: {card_holder}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="seller:panel_back")]])
    )
    return ConversationHandler.END


async def ask_shipping_cost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "هزینه ارسال رو به تومان وارد کن (عدد ساده، مثلا 50000):\n"
        "برای ارسال رایگان عدد ۰ رو بفرست.\n\n"
        "برای لغو: /cancel"
    )
    return SET_SHIPPING_COST


async def save_shipping_cost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cost_text = update.message.text.strip()
    cost_text = cost_text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    cost_text = cost_text.replace(",", "").replace("٫", "")

    if not cost_text.isdigit():
        await update.message.reply_text("❌ لطفاً یه عدد وارد کن (مثلاً 50000):")
        return SET_SHIPPING_COST

    cost = int(cost_text)
    user_id = update.effective_user.id
    shop_id = await _get_shop_id(user_id)
    if not shop_id:
        await update.message.reply_text("❌ شما فروشنده نیستید.")
        return ConversationHandler.END

    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
        if shop:
            shop.shipping_cost = cost
            await session.commit()

    if cost == 0:
        display = "رایگان 🆓"
    else:
        display = format_price(cost)

    await update.message.reply_text(
        f"✅ هزینه ارسال روی {display} تنظیم شد.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="seller:panel_back")]])
    )
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════
# Banner (Cover Photo)
# ═══════════════════════════════════════════════════════════════

async def set_banner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📷 یه عکس بفرست تا کاور فروشگاهت بشه.\n"
        "برای حذف کاور فعلی: /remove_banner\n"
        "برای لغو: /cancel"
    )
    return SET_BANNER


async def save_banner_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    shop_id = await _get_shop_id(user_id)
    if not shop_id:
        await update.message.reply_text("❌ شما فروشنده نیستید.")
        return ConversationHandler.END

    photo = update.message.photo[-1] if update.message.photo else None
    if not photo:
        await update.message.reply_text("❌ لطفاً یه عکس بفرست:")
        return SET_BANNER

    file_id = photo.file_id
    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
        if shop:
            shop.banner_image = file_id
            await session.commit()

    await update.message.reply_text(
        "✅ عکس کاور فروشگاه ذخیره شد!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="seller:panel_back")]])
    )
    return ConversationHandler.END


async def remove_banner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    shop_id = await _get_shop_id(user_id)
    if not shop_id:
        await update.message.reply_text("❌ شما فروشنده نیستید.")
        return ConversationHandler.END

    async with async_session() as s:
        shop = await s.get(Shop, shop_id)
        if shop:
            shop.banner_image = None
            await s.commit()

    await update.message.reply_text("✅ عکس کاور فروشگاه حذف شد.")
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════
# Shop Delete
# ═══════════════════════════════════════════════════════════════

async def seller_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    shop_id = await _get_shop_id(user_id)
    if not shop_id:
        await query.edit_message_text("❌ شما فروشنده نیستید.")
        return

    async with async_session() as session:
        shop = await session.get(Shop, shop_id)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚠️ بله، حذف بشه", callback_data=f"seller:delete_final:{shop_id}"),
            InlineKeyboardButton("❌ نه، بی‌خیال", callback_data="seller:panel_back"),
        ]
    ])
    await query.edit_message_text(
        f"🗑 آیا مطمئنی می‌خوای فروشگاه «{shop.name if shop else 'نامشخص'}» رو حذف کنی؟\n\n"
        "⚠️ این عمل غیرقابل بازگشت است!\n"
        "• محصولات و سبد خرید مشتریان حذف می‌شن\n"
        "• سفارش‌ها حفظ می‌شن\n"
        "• به مشتریان پیام حذف ارسال می‌شه",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


async def seller_delete_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    shop_id = int(query.data.split(":")[2])

    owner_user_id = None
    shop_name = None

    async with async_session() as session:
        from sqlalchemy import text as sa_text
        from database.models import Shop

        # Verify ownership
        owner_check = await session.execute(
            sa_text("SELECT user_id FROM shop_owners WHERE shop_id = :sid AND user_id = :uid"),
            {"sid": shop_id, "uid": user_id},
        )
        if not owner_check.first():
            await query.edit_message_text("❌ شما صاحب این فروشگاه نیستید.")
            return

        shop = await session.get(Shop, shop_id)
        if not shop:
            await query.edit_message_text("❌ فروشگاه پیدا نشد.")
            return
        shop_name = shop.name

        # Get owner user_id before cleanup
        result = await session.execute(
            sa_text("SELECT user_id FROM shop_owners WHERE shop_id = :sid"),
            {"sid": shop_id},
        )
        owner_row = result.first()
        owner_user_id = owner_row[0] if owner_row else None

        # FK cleanup
        await session.execute(
            sa_text("UPDATE users SET last_shop_id = NULL WHERE last_shop_id = :sid"),
            {"sid": shop_id},
        )

        # Delete all related data
        await session.execute(sa_text("DELETE FROM shop_subscriptions WHERE shop_id = :sid"), {"sid": shop_id})
        await session.execute(sa_text("DELETE FROM cart WHERE shop_id = :sid"), {"sid": shop_id})
        await session.execute(sa_text("DELETE FROM wishlist WHERE product_id IN (SELECT id FROM products WHERE shop_id = :sid)"), {"sid": shop_id})
        await session.execute(sa_text("DELETE FROM products WHERE shop_id = :sid"), {"sid": shop_id})
        await session.execute(sa_text("DELETE FROM categories WHERE shop_id = :sid"), {"sid": shop_id})
        await session.execute(sa_text("DELETE FROM shop_owners WHERE shop_id = :sid"), {"sid": shop_id})
        await session.execute(sa_text("DELETE FROM claim_codes WHERE shop_id = :sid"), {"sid": shop_id})
        await session.execute(sa_text("DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE shop_id = :sid)"), {"sid": shop_id})
        await session.execute(sa_text("DELETE FROM order_widgets WHERE order_id IN (SELECT id FROM orders WHERE shop_id = :sid)"), {"sid": shop_id})
        await session.execute(sa_text("DELETE FROM orders WHERE shop_id = :sid"), {"sid": shop_id})
        await session.execute(sa_text("DELETE FROM conversations WHERE shop_id = :sid"), {"sid": shop_id})
        await session.execute(sa_text("DELETE FROM discount_codes WHERE shop_id = :sid"), {"sid": shop_id})
        await session.execute(sa_text("DELETE FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE shop_id = :sid)"), {"sid": shop_id})

        await session.delete(shop)
        await session.commit()

    await query.edit_message_text(
        f"✅ فروشگاه «{shop_name}» با موفقیت حذف شد.\n\n"
        "• همه محصولات، سفارش‌ها و داده‌های مرتبط حذف شدند.\n"
        "• دسترسی فروشندگی شما قطع شد.\n"
        "با /start می‌تونی از امکانات دیگه استفاده کنی."
    )

    # Notify seller + remove menu
    if owner_user_id:
        try:
            await context.bot.send_message(
                owner_user_id,
                f"❌ فروشگاه «{shop_name}» شما با موفقیت حذف شد.\n\n"
                f"در صورت نیاز به اطلاعات بیشتر با پشتیبانی تماس بگیرید.",
            )
        except Exception:
            pass
        try:
            from handlers.bot_commands import delete_seller_menu
            await delete_seller_menu(context.bot, owner_user_id)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
# Seller Orders — pending (both message-based and callback-based)
# ═══════════════════════════════════════════════════════════════

async def _show_seller_pending_orders(message, user_id: int):
    """نمایش سفارش‌های در انتظار پرداخت — message object."""
    shop_id = await _get_shop_id(user_id)
    if not shop_id:
        await message.reply_text("❌ شما فروشنده نیستید.")
        return

    async with async_session() as session:
        from database.models import Order, OrderStatus
        from sqlalchemy import select, func
        result = await session.execute(
            select(Order).where(
                Order.shop_id == shop_id,
                Order.status.in_([
                    OrderStatus.PENDING_PAYMENT, OrderStatus.PENDING,
                    OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.PREPARING,
                ]),
            ).order_by(Order.created_at.desc())
        )
        orders = result.scalars().all()

    if not orders:
        await message.reply_text(
            "🧾 سفارش‌های جدید\n\n"
            "فعلاً سفارشی منتظر اقدام تو نیست. 🎉",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="seller:panel_back")]
            ]),
            parse_mode="HTML"
        )
        return

    lines = ["🧾 سفارش‌های جدید و در جریان\n"]
    buttons = []
    for o in orders:
        payment_info = ""
        if o.status in (OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.PREPARING):
            payment_info = " — پرداخت شده، منتظر ارسال 📦"
        elif o.payment_method == "card_to_card":
            if o.payment_receipt_at:
                payment_info = " — رسید آپلود شده ✅"
            else:
                payment_info = " — در انتظار رسید ⏳"
        elif o.payment_method == "cod":
            payment_info = " — پرداخت درب منزل 🚚"

        lines.append(
            f"🔹 {o.tracking_code} — {format_price(o.total_price)}{payment_info}\n"
            f"   {to_jalali(o.created_at)}"
        )
        buttons.append([
            InlineKeyboardButton(f"👁 {o.tracking_code}", callback_data=f"admin:orders:detail:{o.id}")
        ])

    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="seller:panel_back")])

    await message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML"
    )


async def seller_orders_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش سفارش‌های در انتظار پرداخت — callback-based."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    await _show_seller_pending_orders(query.message, user_id)


async def seller_orders_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش تاریخچه سفارش‌ها."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    shop_id = await _get_shop_id(user_id)
    if not shop_id:
        await query.edit_message_text("❌ شما فروشنده نیستید.")
        return

    async with async_session() as session:
        from database.models import Order, OrderStatus
        from sqlalchemy import select
        result = await session.execute(
            select(Order).where(
                Order.shop_id == shop_id,
            ).order_by(Order.created_at.desc()).limit(50)
        )
        orders = result.scalars().all()

    if not orders:
        await query.edit_message_text(
            "📋 تاریخچه سفارش‌ها\n\n"
            "هیچ سفارشی یافت نشد.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="seller:panel_back")]
            ]),
            parse_mode="HTML"
        )
        return

    lines = ["📋 تاریخچه سفارش‌ها (۵۰ اخیر)\n"]
    buttons = []
    for o in orders:
        status_emoji = {
            "paid": "✅",
            "pending_payment": "⏳",
            "pending": "⏳",
            "confirmed": "📦",
            "preparing": "📦",
            "shipped": "🚚",
            "delivered": "✅",
            "cancelled": "❌",
            "card_payment_rejected": "❌",
        }.get(o.status, "❓")

        payment_info = ""
        if o.payment_method == "card_to_card":
            payment_info = " (کارت‌به‌کارت)"
        elif o.payment_method == "cod":
            payment_info = " (درب منزل)"

        lines.append(
            f"{status_emoji} {o.tracking_code} — {format_price(o.total_price)}{payment_info}\n"
            f"   {to_jalali(o.created_at)}"
        )
        buttons.append([
            InlineKeyboardButton(f"👁 {o.tracking_code}", callback_data=f"admin:orders:detail:{o.id}:history")
        ])

    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="seller:panel_back")])

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════
# Account Info
# ═══════════════════════════════════════════════════════════════

async def show_account_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش اطلاعات حساب فروشنده/ادمین."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    async with async_session() as session:
        owner = await session.execute(
            select(ShopOwner).where(ShopOwner.user_id == user_id)
        )
        owner = owner.scalar_one_or_none()

        admin = await session.execute(
            select(Admin).where(Admin.user_id == user_id)
        )
        admin = admin.scalar_one_or_none()

    if not owner and not admin:
        await query.edit_message_text("❌ شما فروشنده یا ادمین نیستید.")
        return ConversationHandler.END

    lines = ["👤 <b>اطلاعات حساب شما</b>", ""]
    lines.append(f"🆔 شناسه تلگرام: <code>{user_id}</code>")
    tg_user = update.effective_user
    if tg_user.username:
        lines.append(f"📛 یوزرنیم تلگرام: @{tg_user.username}")
    if tg_user.first_name:
        lines.append(f"👤 نام: {tg_user.first_name}")

    if owner:
        lines.append("")
        lines.append("🏪 <b>اطلاعات فروشنده</b>")
        lines.append(f"   شناسه فروشگاه: <code>{owner.shop_id}</code>")
        if owner.username:
            lines.append(f"   یوزرنیم سایت: <code>{owner.username}</code>")
        lines.append("   ⚠️ رمز عبور به صورت هش شده ذخیره شده و قابل نمایش نیست.")
        lines.append("   💡 برای تغییر رمز: «🔐 تغییر رمز عبور»")
        lines.append("   💡 فراموشی رمز: /reset_password")

    if admin:
        lines.append("")
        lines.append("🛡 <b>اطلاعات ادمین</b>")
        lines.append(f"   یوزرنیم سایت: <code>{admin.user_id}</code> (شناسه تلگرام)")
        lines.append("   ⚠️ رمز عبور به صورت هش شده ذخیره شده و قابل نمایش نیست.")
        lines.append("   💡 برای تغییر رمز: «🔐 تغییر رمز عبور»")
        lines.append("   💡 فراموشی رمز: /reset_password")
        lines.append("")
        lines.append("   🌐 لینک ورود به پنل: https://telegramorder.ir/admin/login")

    text = "\n".join(lines)
    buttons = [
        [InlineKeyboardButton("🔐 تغییر رمز عبور", callback_data="seller:change_password")],
        [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="seller:panel_back")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════
# ConversationHandler
# ═══════════════════════════════════════════════════════════════

def get_seller_panel_conversation():
    return ConversationHandler(
        entry_points=[
            # /myshop command
            MessageHandler(filters.COMMAND & filters.Regex(r"^/myshop$"), seller_panel_command),
            # /my_panel alias
            MessageHandler(filters.COMMAND & filters.Regex(r"^/my_panel$"), my_panel_command),
            # Inline button callbacks that start conversation
            CallbackQueryHandler(show_shop_link, pattern="^seller:show_link$"),
            CallbackQueryHandler(panel_back, pattern="^seller:(panel|panel_back)$"),
            CallbackQueryHandler(payment_settings_menu, pattern="^seller:payment_settings$"),
            CallbackQueryHandler(change_password_start, pattern="^(seller|admin):change_password$"),
            CallbackQueryHandler(site_settings_menu, pattern="^seller:site_settings$"),
            CallbackQueryHandler(site_set_username_start, pattern="^site:set_username$"),
            CallbackQueryHandler(site_set_password_start, pattern="^site:set_password$"),
            CallbackQueryHandler(ask_card_number, pattern=r"^payment:set_card_number$"),
            CallbackQueryHandler(ask_card_holder, pattern=r"^payment:set_card_holder$"),
            CallbackQueryHandler(ask_shipping_cost, pattern=r"^payment:set_shipping$"),
            CallbackQueryHandler(set_banner, pattern=r"^seller:set_banner$"),
            CallbackQueryHandler(show_account_info, pattern=r"^seller:account_info$"),
        ],
        states={
            SET_NEW_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_password),
            ],
            ADMIN_SET_NEW_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_password),
            ],
            SHOP_INFO: [
                CallbackQueryHandler(show_shop_link, pattern=r"^seller:show_link$"),
                CallbackQueryHandler(panel_back, pattern=r"^seller:panel_back$"),
                CallbackQueryHandler(payment_settings_menu, pattern="^seller:payment_settings$"),
                CallbackQueryHandler(change_password_start, pattern="^(seller|admin):change_password$"),
                CallbackQueryHandler(ask_card_number, pattern=r"^payment:set_card_number$"),
                CallbackQueryHandler(ask_card_holder, pattern=r"^payment:set_card_holder$"),
                CallbackQueryHandler(ask_shipping_cost, pattern=r"^payment:set_shipping$"),
            ],
            PAYMENT_SETTING_MENU: [
                CallbackQueryHandler(show_shop_link, pattern=r"^seller:show_link$"),
                CallbackQueryHandler(panel_back, pattern=r"^seller:panel_back$"),
                CallbackQueryHandler(ask_card_number, pattern=r"^payment:set_card_number$"),
                CallbackQueryHandler(ask_card_holder, pattern=r"^payment:set_card_holder$"),
                CallbackQueryHandler(ask_shipping_cost, pattern=r"^payment:set_shipping$"),
                CallbackQueryHandler(change_password_start, pattern="^(seller|admin):change_password$"),
            ],
            SITE_SETTINGS_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, site_save_username),
            ],
            SITE_SETTINGS_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, site_save_password),
            ],
            SET_CARD_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_card_number),
            ],
            SET_CARD_HOLDER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_card_holder),
            ],
            SET_SHIPPING_COST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_shipping_cost),
            ],
            SET_BANNER: [
                MessageHandler(filters.PHOTO & ~filters.COMMAND, save_banner_photo),
                MessageHandler(filters.COMMAND & filters.Regex(r"^/remove_banner$"), remove_banner),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            CallbackQueryHandler(cancel_conversation, pattern=r"^seller:cancel$"),
        ],
        allow_reentry=True,
        per_chat=True,
    )


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو هر مکالمه‌ای."""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("❌ عملیات لغو شد.")
    elif update.message:
        await update.message.reply_text("❌ عملیات لغو شد.")
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
# Site Settings — username + password for web login
# ═══════════════════════════════════════════════════════════

SITE_SETTINGS_USERNAME, SITE_SETTINGS_PASSWORD = range(2)

async def site_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی تنظیمات سایت با وضعیت فعلی."""
    query = update.callback_query
    user_id = query.from_user.id

    async with async_session() as session:
        owner = await session.execute(
            select(ShopOwner).where(ShopOwner.user_id == user_id)
        )
        owner = owner.scalar_one_or_none()

    if not owner:
        await query.answer("⚠️ فقط فروشنده‌ها دسترسی دارند.", show_alert=True)
        return ConversationHandler.END

    username_display = owner.username or "❌ تنظیم نشده"
    password_display = "✅ تنظیم شده" if owner.password_hash else "❌ تنظیم نشده"

    text = (
        f"⚙️ <b>تنظیمات ورود به سایت</b>\n\n"
        f"👤 نام کاربری: <code>{username_display}</code>\n"
        f"🔒 رمز عبور: {password_display}\n\n"
        f"💡 با این اطلاعات می‌توانید وارد پنل فروشگاهی خود در سایت شوید:\n"
        f"🔗 https://telegramorder.ir/login\n\n"
        f"👇 چه کاری انجام بدیم؟"
    )

    buttons = [
        [InlineKeyboardButton("✏️ تغییر نام کاربری", callback_data="site:set_username")],
        [InlineKeyboardButton("🔑 تغییر رمز عبور", callback_data="site:set_password")],
        [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="seller:panel")],
    ]

    await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    await query.answer()
    return ConversationHandler.END


async def site_set_username_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند تنظیم نام کاربری."""
    query = update.callback_query
    await query.answer()
    await query.message.edit_text(
        "✏️ <b>نام کاربری جدید را وارد کنید:</b>\n\n"
        "• فقط حروف انگلیسی، اعداد و _ مجاز است\n"
        "• حداقل ۳ کاراکتر\n"
        "• مثال: <code>my_shop_123</code>\n\n"
        "برای لغو /cancel را بزنید.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ لغو", callback_data="seller:site_settings")]])
    )
    return SITE_SETTINGS_USERNAME


async def site_save_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ذخیره نام کاربری جدید."""
    import re
    username = update.message.text.strip()

    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]{2,49}$', username):
        await update.message.reply_text(
            "❌ نام کاربری نامعتبر!\nفقط حروف انگلیسی، اعداد و _ مجاز است (حداقل ۳ کاراکتر، شروع با حرف).\nدوباره تلاش کنید:"
        )
        return SITE_SETTINGS_USERNAME

    # Check uniqueness via direct DB query
    from sqlalchemy import text as sql_text
    async with async_session() as session:
        existing = await session.execute(
            sql_text("SELECT user_id FROM shop_owners WHERE LOWER(username) = LOWER(:u) AND user_id != :uid"),
            {"u": username, "uid": update.effective_user.id}
        )
        if existing.fetchone():
            await update.message.reply_text("❌ این نام کاربری قبلاً استفاده شده. یکی دیگر انتخاب کنید:")
            return SITE_SETTINGS_USERNAME

        await session.execute(
            sql_text("UPDATE shop_owners SET username = :u WHERE user_id = :uid"),
            {"u": username, "uid": update.effective_user.id}
        )
        await session.commit()

    await update.message.reply_text(
        f"✅ نام کاربری شما تنظیم شد:\n<code>{username}</code>\n\n"
        f"اکنون از بخش ⚙️ تنظیمات سایت → 🔑 تغییر رمز عبور، رمز خود را تعیین کنید.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ تنظیمات سایت", callback_data="seller:site_settings")]])
    )
    return ConversationHandler.END


async def site_set_password_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند تنظیم رمز عبور."""
    query = update.callback_query
    user_id = query.from_user.id

    # Check if username is set first
    async with async_session() as session:
        owner = await session.execute(
            select(ShopOwner).where(ShopOwner.user_id == user_id)
        )
        owner = owner.scalar_one_or_none()

    if not owner or not owner.username:
        await query.answer("⚠️ ابتدا نام کاربری تنظیم کنید!", show_alert=True)
        await query.message.edit_text(
            "⚠️ <b>ابتدا باید نام کاربری تنظیم کنید!</b>\n\nاز دکمه زیر شروع کنید:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ تنظیم نام کاربری", callback_data="site:set_username")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="seller:site_settings")],
            ])
        )
        await query.answer()
        return ConversationHandler.END

    await query.answer()
    await query.message.edit_text(
        "🔑 <b>رمز عبور جدید را وارد کنید:</b>\n\n"
        "• حداقل ۶ کاراکتر\n"
        "• ترکیب حروف و اعداد توصیه می‌شود\n\n"
        "برای لغو /cancel را بزنید.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ لغو", callback_data="seller:site_settings")]])
    )
    return SITE_SETTINGS_PASSWORD


async def site_save_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ذخیره رمز عبور جدید."""
    import bcrypt
    password = update.message.text.strip()

    if len(password) < 6:
        await update.message.reply_text("❌ رمز عبور باید حداقل ۶ کاراکتر باشد. دوباره تلاش کنید:")
        return SITE_SETTINGS_PASSWORD

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    from sqlalchemy import text as sql_text
    async with async_session() as session:
        await session.execute(
            sql_text("UPDATE shop_owners SET password_hash = :h WHERE user_id = :uid"),
            {"h": hashed, "uid": update.effective_user.id}
        )
        await session.commit()

    await update.message.reply_text(
        "✅ <b>رمز عبور شما با موفقیت تنظیم شد!</b>\n\n"
        "اکنون می‌توانید با نام کاربری و رمز عبور خود وارد سایت شوید:\n"
        "🔗 https://telegramorder.ir/login",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ تنظیمات سایت", callback_data="seller:site_settings")]])
    )
    return ConversationHandler.END


async def site_settings_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو فرآیند تنظیمات سایت."""
    await update.message.reply_text(
        "❌ لغو شد.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ تنظیمات سایت", callback_data="seller:site_settings")]])
    )
    return ConversationHandler.END
