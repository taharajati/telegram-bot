"""
ویزارد ثبت‌نام فروشنده — کوتاه و بدون انتظار.
کاربر دکمه «🏪 می‌خوام فروشگاه بسازم» رو می‌زنه → اسم فروشگاه → شماره تماس → شماره کارت (اختیاری)
→ فروشگاه همون لحظه با دوره‌ی آزمایشی فعال می‌شه (اگه AUTO_APPROVE_SHOPS خاموش باشه می‌ره صف تایید ادمین).
توضیح، لینک کانال و رمز پنل سایت بعداً از پنل مدیریت قابل تنظیمه.
"""
import logging
import re

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from sqlalchemy import select

import config
from database.db import async_session
from database.models import Shop, ShopOwner
from utils.tg_helpers import render_view, escape_html
from utils.crypto import safe_encrypt

logger = logging.getLogger(__name__)

ASK_NAME, ASK_PHONE, ASK_CARD_NUMBER, ASK_CARD_HOLDER = range(4)

_FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_CANCEL_KB = InlineKeyboardMarkup([[InlineKeyboardButton("❌ لغو", callback_data="seller_reg:cancel")]])
_SHARE_PHONE = "📱 ارسال شماره خودم"


def seller_welcome_text() -> str:
    return (
        "🏪 ساخت فروشگاه\n\n"
        "خوش اومدی به فروشگرام 🙌 فروشگاهت با ۳ سؤال کوتاه ساخته می‌شه و همون لحظه آماده‌ی فروشه.\n\n"
        "📍 قدم ۱ از ۳ — اسم فروشگاه\n\n"
        "⬇️ اسم فروشگاهت رو بنویس و بفرست:"
    )


def normalize_phone(raw: str) -> str | None:
    """شماره موبایل ایران رو به قالب 09xxxxxxxxx می‌بره؛ اگه معتبر نباشه None."""
    digits = re.sub(r"\D", "", (raw or "").translate(_FA_DIGITS))
    if digits.startswith("0098"):
        digits = digits[4:]
    elif digits.startswith("98"):
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith("9"):
        digits = "0" + digits
    return digits if re.fullmatch(r"09\d{9}", digits) else None


async def seller_registration_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نقطه ورود: دکمه '🏪 می‌خوام فروشگاه بسازم'"""
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id

    # اگه قبلاً فروشگاهی داره، دوباره نمی‌سازیم
    async with async_session() as session:
        owner = (await session.execute(
            select(ShopOwner).where(ShopOwner.user_id == user_id)
        )).scalars().first()
        shop = await session.get(Shop, owner.shop_id) if owner else None

    if shop and shop.status in ("active", "draft", "suspended"):
        status_text = {
            "active": "فروشگاهت فعاله. از پنل مدیریت می‌تونی همه‌چیز رو کنترل کنی.",
            "draft": "درخواستت در صف تایید ادمینه. به‌محض تایید خبرت می‌کنیم.",
            "suspended": "فروشگاهت معلق شده. برای پیگیری با پشتیبانی تماس بگیر: /support",
        }[shop.status]
        text = f"✅ تو قبلاً فروشگاه «{shop.name}» رو ثبت کردی.\n\n{status_text}"
        rows = []
        if shop.status == "active":
            rows.append([InlineKeyboardButton("🏪 پنل مدیریت", callback_data="seller:panel_back")])
        rows.append([InlineKeyboardButton("🔙 منوی اصلی", callback_data="nav:main")])
        keyboard = InlineKeyboardMarkup(rows)
        if query:
            await render_view(query, context, text, keyboard)
        else:
            await update.message.reply_text(text, reply_markup=keyboard)
        return ConversationHandler.END

    text = seller_welcome_text()
    if query:
        await render_view(query, context, text, _CANCEL_KB)
    else:
        await update.message.reply_text(text, reply_markup=_CANCEL_KB)
    return ASK_NAME


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت نام فروشگاه → پرسیدن شماره تماس"""
    name = update.message.text.strip()
    if len(name) < 2 or len(name) > 150:
        await update.message.reply_text(
            "❌ اسم فروشگاه باید بین ۲ تا ۱۵۰ کاراکتر باشه.\n"
            "یه اسم مناسب انتخاب کن و دوباره بفرست:"
        )
        return ASK_NAME

    context.user_data["seller_shop_name"] = name

    await update.message.reply_text(
        f"✅ اسم فروشگاه: {name} 👌\n\n"
        "📍 قدم ۲ از ۳ — شماره تماس\n\n"
        "مشتری‌ها برای هماهنگی خرید با این شماره تماس می‌گیرن.\n"
        f"دکمه‌ی «{_SHARE_PHONE}» رو بزن، یا شماره رو تایپ کن (مثال: 09123456789):",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton(_SHARE_PHONE, request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )
    return ASK_PHONE


async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت شماره تماس (تایپ‌شده یا با دکمه‌ی اشتراک شماره) → پرسیدن شماره کارت"""
    contact = update.message.contact
    phone = normalize_phone(contact.phone_number if contact else update.message.text)

    if not phone:
        await update.message.reply_text(
            "❌ این شماره معتبر نیست. شماره موبایل باید ۱۱ رقم باشه و با ۰۹ شروع بشه.\n\n"
            "مثال درست: 09123456789\n"
            "دوباره بفرست:"
        )
        return ASK_PHONE

    context.user_data["seller_shop_phone"] = phone

    await update.message.reply_text("✅ شماره تماس ثبت شد ☎️", reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text(
        "📍 قدم ۳ از ۳ — شماره کارت 💳\n\n"
        "مشتری‌ها مبلغ سفارش رو مستقیم به همین کارت واریز می‌کنن و رسیدش رو برات می‌فرستن.\n\n"
        "شماره کارت ۱۶ رقمی رو بفرست (مثال: 6037991234567890):",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭ بعداً ثبت می‌کنم", callback_data="seller_reg:skip_card")],
            [InlineKeyboardButton("❌ لغو", callback_data="seller_reg:cancel")],
        ]),
    )
    return ASK_CARD_NUMBER


async def ask_card_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت شماره کارت → پرسیدن نام صاحب کارت"""
    card_number = re.sub(r"[\s\-]", "", update.message.text.translate(_FA_DIGITS))

    if not card_number.isdigit() or len(card_number) != 16:
        await update.message.reply_text(
            "❌ شماره کارت باید ۱۶ رقم باشه (فقط عدد).\n\n"
            "مثال درست: 6037991234567890\n"
            "دوباره بفرست، یا «بعداً ثبت می‌کنم» رو بزن:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏭ بعداً ثبت می‌کنم", callback_data="seller_reg:skip_card")],
            ]),
        )
        return ASK_CARD_NUMBER

    context.user_data["seller_card_number"] = card_number

    await update.message.reply_text(
        "✅ شماره کارت ثبت شد 💳\n\n"
        "کارت به نام کیه؟ مشتری موقع واریز این اسم رو می‌بینه تا مطمئن بشه.\n\n"
        "نام صاحب کارت رو بفرست (مثال: علی محمدی):",
        reply_markup=_CANCEL_KB,
    )
    return ASK_CARD_HOLDER


async def ask_card_holder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت نام صاحب کارت → ساخت فروشگاه"""
    card_holder = update.message.text.strip()
    if len(card_holder) < 2 or len(card_holder) > 100:
        await update.message.reply_text("❌ نام صاحب کارت باید بین ۲ تا ۱۰۰ کاراکتر باشه. دوباره بفرست:")
        return ASK_CARD_HOLDER

    context.user_data["seller_card_holder"] = card_holder
    return await _create_shop(update, context)


async def skip_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فروشنده ثبت کارت رو به بعد موکول کرده → ساخت فروشگاه بدون کارت"""
    await update.callback_query.answer()
    context.user_data.pop("seller_card_number", None)
    context.user_data.pop("seller_card_holder", None)
    return await _create_shop(update, context)


async def _create_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ثبت فروشگاه در دیتابیس، فعال‌سازی (یا ارسال به صف تایید) و راهنمای قدم بعدی."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    shop_name = context.user_data.get("seller_shop_name")
    phone = context.user_data.get("seller_shop_phone")
    card_number = context.user_data.get("seller_card_number")
    card_holder = context.user_data.get("seller_card_holder")

    if not shop_name or not phone:
        await context.bot.send_message(
            chat_id, "❌ اطلاعات ثبت‌نام کامل نشده. لطفاً با /start دوباره شروع کن."
        )
        context.user_data.clear()
        return ConversationHandler.END

    auto_approve = config.AUTO_APPROVE_SHOPS
    async with async_session() as session:
        shop = Shop(
            name=shop_name,
            phone=phone,
            status="active" if auto_approve else "draft",
            is_active=True,
            card_number=safe_encrypt(card_number) if card_number else None,
            card_holder_name=safe_encrypt(card_holder) if card_holder else None,
        )
        session.add(shop)
        await session.flush()
        session.add(ShopOwner(
            user_id=user.id,
            shop_id=shop.id,
            first_name=user.first_name,
            username=user.username,
        ))
        if auto_approve and not config.FREE_MODE:
            from services.subscription import create_trial_subscription
            await create_trial_subscription(shop.id, user.id, session)
        await session.commit()
        shop_id = shop.id

    await _notify_admins(context, user, shop_id, shop_name, phone, card_number, auto_approve)

    if auto_approve:
        try:
            from handlers.bot_commands import set_seller_menu
            await set_seller_menu(context.bot, user.id)
        except Exception:
            logger.warning("Could not set seller menu for %s", user.id)

        link = f"https://t.me/{context.bot.username}?start=shop_{shop_id}"
        text = (
            f"🎉 فروشگاه «{escape_html(shop_name)}» ساخته شد و همین الان فعاله!\n\n"
            f"🔗 لینک فروشگاهت (برای بیو و کانال):\n{link}\n\n"
            + ("🆓 استفاده از فروشگرام برای همه رایگانه.\n\n" if config.FREE_MODE else "🎁 ۱۳ روز اول رایگانه.\n\n")
        )
        rows = [[InlineKeyboardButton("➕ افزودن اولین محصول", callback_data="admin:products:add")]]
        if card_number:
            text += "قدم بعدی: اولین محصولت رو اضافه کن تا مشتری‌ها بتونن سفارش بدن 👇"
        else:
            text += (
                "⚠️ هنوز شماره کارت ثبت نکردی؛ تا ثبتش نکنی مشتری نمی‌تونه پرداخت کنه.\n\n"
                "قدم بعدی: اولین محصولت رو اضافه کن و کارتت رو ثبت کن 👇"
            )
            rows.append([InlineKeyboardButton("💳 ثبت شماره کارت", callback_data="seller:payment_settings")])
        rows.append([InlineKeyboardButton("🏪 پنل مدیریت", callback_data="seller:panel_back")])
    else:
        text = (
            f"🎉 درخواست فروشگاه «{escape_html(shop_name)}» ثبت شد!\n\n"
            "📬 درخواستت برای تایید فرستاده شد و به‌محض تایید همین‌جا خبرت می‌کنیم."
        )
        rows = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="nav:main")]]

    await context.bot.send_message(
        chat_id, text, reply_markup=InlineKeyboardMarkup(rows), parse_mode="HTML",
        disable_web_page_preview=True,
    )
    context.user_data.clear()
    return ConversationHandler.END


async def _notify_admins(context, user, shop_id: int, shop_name: str, phone: str, card_number: str | None, auto_approved: bool):
    title = "🆕 فروشگاه جدید ساخته و فعال شد" if auto_approved else "🆕 درخواست فروشگاه جدید"
    admin_text = (
        f"{title}\n\n"
        f"👤 {escape_html(user.first_name) or 'بدون نام'} "
        f"(@{user.username or 'بدون یوزرنیم'} — آیدی: {user.id})\n"
        f"🏪 نام: {escape_html(shop_name)}\n"
        f"📞 تماس: {phone}\n"
        f"💳 کارت: {('...' + card_number[-4:]) if card_number else '— ثبت نشده'}\n\n"
        f"🆔 Shop ID: {shop_id}"
    )
    if auto_approved:
        admin_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔎 مشاهده و مدیریت فروشگاه", callback_data=f"admin:shops:edit:{shop_id}")],
        ])
    else:
        admin_keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ تایید و فعال‌سازی", callback_data=f"admin:seller:approve:{shop_id}"),
            InlineKeyboardButton("❌ رد کردن", callback_data=f"admin:seller:reject:{shop_id}"),
        ]])
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, admin_text, reply_markup=admin_keyboard, parse_mode="HTML")
        except Exception:
            pass


async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو ثبت‌نام در هر مرحله"""
    query = update.callback_query
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="nav:main")]])
    text = "❌ ساخت فروشگاه لغو شد. هر وقت خواستی می‌تونی با /start دوباره شروع کنی."
    if query:
        await query.answer()
        await render_view(query, context, text, keyboard)
    else:
        await update.message.reply_text(text, reply_markup=keyboard)
    context.user_data.clear()
    return ConversationHandler.END


def get_seller_registration_conversation():
    """ConversationHandler برای ثبت‌نام فروشنده"""
    text_only = filters.TEXT & ~filters.COMMAND
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(seller_registration_start, pattern="^seller_reg:start$"),
        ],
        states={
            ASK_NAME: [MessageHandler(text_only, ask_name)],
            ASK_PHONE: [MessageHandler(filters.CONTACT | text_only, ask_phone)],
            ASK_CARD_NUMBER: [
                MessageHandler(text_only, ask_card_number),
                CallbackQueryHandler(skip_card, pattern="^seller_reg:skip_card$"),
            ],
            ASK_CARD_HOLDER: [MessageHandler(text_only, ask_card_holder)],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_registration, pattern="^seller_reg:cancel$"),
        ],
        name="seller_registration",
        persistent=False,
    )
