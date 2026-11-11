"""
ویزارد ثبت‌نام فروشنده — خودکار، بدون دخالت ادمین در مرحله اول.
کاربر دکمه «🏪 می‌خوام فروشگاه بسازم» رو می‌زنه → پرسش‌های ساده → درخواست در صف تایید ادمین.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from sqlalchemy import select
import bcrypt

from database.db import async_session
from database.models import Shop, ShopOwner, User
from utils.helpers import is_super_admin
from utils.tg_helpers import render_view
from utils.crypto import safe_encrypt


ASK_NAME, ASK_DESC, ASK_PHONE, ASK_CHANNEL_LINK, ASK_CARD_NUMBER, ASK_CARD_HOLDER, ASK_PASSWORD, ASK_CONFIRM = range(8)


def seller_welcome_text() -> str:
    return (
        "🏪 ثبت‌نام فروشنده\n\n"
        "سلام، خوش اومدی به فروشگرام 🙌 راه‌اندازی فروشگاهت فقط ۸ مرحله‌ی کوتاهه — قدم‌به‌قدم باهم پیش می‌ریم.\n\n"
        "📍 مرحله ۱ از ۸ — اسم فروشگاه\n\n"
        "⬇️ اسم فروشگاهت رو بنویس و بفرست:"
    )


async def seller_registration_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نقطه ورود: دکمه '🏪 می‌خوام فروشگاه بسازم'"""
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id

    # 1. چک کن اگه قبلاً فروشگاهی داره
    async with async_session() as session:
        # مالکیت فعال
        result = await session.execute(
            select(ShopOwner).where(ShopOwner.user_id == user_id)
        )
        owner = result.scalars().first()

        if owner:
            # داره فروشگاه فعال/معلق داره
            shop = await session.get(Shop, owner.shop_id)
            if shop and shop.status in ("active", "draft", "suspended"):
                text = (
                    f"✅ شما قبلاً فروشگاه «{shop.name}» رو ثبت کرده‌اید.\n"
                    f"وضعیت: {shop.status}\n\n"
                )
                if shop.status == "active":
                    text += "فروشگاه شما فعال است. از پنل مدیریت می‌تونید همه‌چیز رو کنترل کنید."
                elif shop.status == "draft":
                    text += "درخواست شما در صف تایید ادمین است. لطفاً صبر کنید."
                elif shop.status == "suspended":
                    text += "فروشگاه شما معلق شده. با پشتیبانی تماس بگیرید."
                elif shop.status == "rejected":
                    text += f"دلیل رد: {shop.rejection_reason or 'مشخص نشده'}\nمی‌تونید دوباره تلاش کنید."

                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 منوی اصلی", callback_data="nav:main")]
                ])
                if query:
                    await render_view(query, context, text, keyboard)
                else:
                    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
                return ConversationHandler.END

        # 2. چک درخواست در انتظار
        result = await session.execute(
            select(Shop).where(Shop.owners.any(user_id=user_id), Shop.status == "draft")
        )
        pending = result.scalar_one_or_none()
        if pending:
            text = (
                f"⏳ شما قبلاً درخواست ثبت فروشگاه «{pending.name}» رو ارسال کرده‌اید "
                "و هنوز تایید نشده.\nلطفاً صبر کنید."
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data="nav:main")]
            ])
            if query:
                await render_view(query, context, text, keyboard)
            else:
                await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
            return ConversationHandler.END

    # 3. شروع ویزارد
    text = seller_welcome_text()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ لغو", callback_data="seller_reg:cancel")]
    ])
    if query:
        await render_view(query, context, text, keyboard)
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
    return ASK_NAME


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت نام فروشگاه"""
    name = update.message.text.strip()
    if len(name) < 2 or len(name) > 150:
        await update.message.reply_text(
            "❌ اسم فروشگاه باید بین ۲ تا ۱۵۰ کاراکتر باشه.\n"
            "یه اسم مناسب انتخاب کن و دوباره بفرست:"
        )
        return ASK_NAME

    context.user_data["seller_shop_name"] = name

    text = (
        f"✅ اسم فروشگاه: {name} 👌\n\n"
        "(مرحله دو) : حالا یه توضیح کوتاه بده\n\n"
        "مثلاً: «فروش انواع کفش‌های ورزشی و مجلسی» یا «انواع لبنیات محلی و سنتی»\n\n"
        "اگه بخوای می‌تونی خالی رد کنی با فرستادن «-»"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ لغو", callback_data="seller_reg:cancel")]
    ])
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
    return ASK_DESC


async def ask_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت توضیح فروشگاه"""
    desc = update.message.text.strip()
    if desc == "-":
        desc = ""
    if len(desc) > 500:
        await update.message.reply_text(
            "❌ توضیح خیلی طولانی شد (بیش از ۵۰۰ کاراکتر).\n"
            "یه توضیح کوتاه‌تر بده یا اگه نمیخوای بگی «-» رو بفرست:"
        )
        return ASK_DESC

    context.user_data["seller_shop_desc"] = desc

    text = (
        f"✅ توضیح ثبت شد 📝\n\n"
        "(مرحله سه) : حالا نوبت شماره تماس هست\n\n"
        "مشتری‌ها برای هماهنگی خرید باهات تماس می‌گیرن، پس یه شماره معتبر بده.\n\n"
        "📞 مثال: 09123456789"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ لغو", callback_data="seller_reg:cancel")]
    ])
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
    return ASK_PHONE


async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت شماره تماس + درخواست رمز عبور"""
    phone = update.message.text.strip()
    # تبدیل ارقام فارسی
    phone = phone.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))

    # اعتبارسنجی ساده
    import re
    if not re.match(r"^09\d{9}$", phone):
        await update.message.reply_text(
            "❌ فرمت شماره غلطه! باید:\n"
            "• با ۰۹ شروع بشه\n"
            "• ۱۱ رقم باشه\n"
            "• فقط عدد باشه\n\n"
            "مثال درست: 09123456789\n"
            "دوباره وارد کن:"
        )
        return ASK_PHONE

    context.user_data["seller_shop_phone"] = phone

    text = (
        f"✅ شماره تماس ثبت شد ☎️\n\n"
        "(مرحله چهار) : حالا لینک کانال تلگرام فروشگاهت رو بفرست\n\n"
        "مشتری‌ها از این طریق می‌تونن محصولات جدید رو ببینن.\n\n"
        "🔗 مثال: https://t.me/yourchannel یا @yourchannel\n\n"
        "اگر کانال نداری، فقط - بفرست تا رد بشه."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ لغو", callback_data="seller_reg:cancel")]
    ])
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
    return ASK_CHANNEL_LINK


async def ask_channel_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت لینک کانال تلگرام فروشنده"""
    link = update.message.text.strip()

    if link != "-" and link != "—":
        # normalize: strip @ or full link
        if link.startswith("https://t.me/"):
            channel_username = link.replace("https://t.me/", "")
        elif link.startswith("@"):
            channel_username = link
        else:
            channel_username = link
        context.user_data["seller_channel_link"] = channel_username
    else:
        context.user_data["seller_channel_link"] = ""

    text = (
        "✅ لینک کانال ثبت شد 📢\n\n"
        "(مرحله پنج) : حالا نوبت اطلاعات پرداخت هست 💳\n\n"
        "لطفاً شماره کارت بانکی رو بفرست که مشتری‌ها پول رو به حسابش واریز کنن.\n\n"
        "💡 مثال: 6037991234567890\n\n"
        "برای رد کردن (و اضافه کردن بعداً) کافیه - بفرستی:"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ لغو", callback_data="seller_reg:cancel")]
    ])
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
    return ASK_CARD_NUMBER


async def ask_card_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت شماره کارت فروشنده"""
    card_number = update.message.text.strip().replace(" ", "").replace("-", "")

    if card_number == "-":
        context.user_data["seller_card_number"] = ""
        context.user_data["seller_card_holder"] = ""
        text = (
            "✅ باشه، فعلاً رد شد. هر وقت خواستی می‌تونی از پنل مدیریت اضافه‌اش کنی.\n\n"
            "(مرحله شش) : آخرین مرحله 🔐\n\n"
            "یه رمز عبور انتخاب کن برای ورود به پنل مدیریت فروشگاه در سایت.\n"
            "این رمز رو فقط خودت می‌دونی و می‌تونی بعداً از همین ربات عوضش کنی.\n\n"
            "🔑 حداقل ۶ کاراکتر وارد کن:"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ لغو", callback_data="seller_reg:cancel")]
        ])
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
        return ASK_PASSWORD

    if not card_number.isdigit() or len(card_number) != 16:
        await update.message.reply_text(
            "❌ فرمت شماره کارت غلطه! باید:\n"
            "• ۱۶ رقم باشه\n"
            "• فقط عدد باشه\n\n"
            "مثال درست: 6037991234567890\n"
            "دوباره وارد کن یا - بفرست تا رد بشی:",
            parse_mode="HTML"
        )
        return ASK_CARD_NUMBER

    context.user_data["seller_card_number"] = card_number

    text = (
        f"✅ شماره کارت با موفقیت ثبت شد 💳\n\n"
        "(مرحله شش) : حالا نام صاحب کارت رو بنویس\n\n"
        "مثال: علی محمدی\n\n"
        "برای رد کردن و رفتن به مرحله بعد - بفرست:"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ لغو", callback_data="seller_reg:cancel")]
    ])
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
    return ASK_CARD_HOLDER


async def ask_card_holder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت نام صاحب کارت"""
    card_holder = update.message.text.strip()

    if card_holder == "-":
        context.user_data["seller_card_holder"] = ""
        text = (
            "✅ رد شد. می‌تونی بعداً از پنل مدیریت اضافه کنی.\n\n"
            "📍 مرحله ۷ از ۸ — رمز عبور (آخرین قدمه!) 🔐\n\n"
            "یه رمز عبور انتخاب کن برای ورود به پنل مدیریت فروشگاه در سایت.\n"
            "این رمز رو فقط خودت می‌دونی و می‌تونی بعداً از همین ربات عوضش کنی.\n\n"
            "🔑 حداقل ۶ کاراکتر وارد کن:"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ لغو", callback_data="seller_reg:cancel")]
        ])
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
        return ASK_PASSWORD

    if len(card_holder) < 2:
        await update.message.reply_text(
            "❌ نام خیلی کوتاهه! حداقل ۲ کاراکتر بنویس، یا - بفرست تا رد بشی:",
            parse_mode="HTML"
        )
        return ASK_CARD_HOLDER

    context.user_data["seller_card_holder"] = card_holder

    text = (
        f"✅ نام صاحب کارت ثبت شد 👤\n\n"
        "(مرحله هفت) : آخرین مرحله مونده 🔐\n\n"
        "یه رمز عبور انتخاب کن برای ورود به پنل مدیریت فروشگاه در سایت.\n"
        "این رمز رو فقط خودت می‌دونی و می‌تونی بعداً از همین ربات عوضش کنی.\n\n"
        "🔑 حداقل ۶ کاراکتر وارد کن:"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ لغو", callback_data="seller_reg:cancel")]
    ])
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
    return ASK_PASSWORD


async def ask_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت رمز عبور + نمایش خلاصه برای تأیید نهایی"""
    password = update.message.text.strip()
    if len(password) < 6:
        await update.message.reply_text(
            "❌ رمز باید حداقل ۶ کاراکتر باشه.\n"
            "یه رمز امن‌تر انتخاب کن (حرف و عدد داشته باشه بهتره):"
        )
        return ASK_PASSWORD

    # ذخیره موقت (هنوز commit نمی‌شه)
    context.user_data["seller_password_raw"] = password

    user = update.effective_user
    shop_name = context.user_data.get("seller_shop_name")
    shop_desc = context.user_data.get("seller_shop_desc")
    phone = context.user_data.get("seller_shop_phone")
    channel_link = context.user_data.get("seller_channel_link")
    card_number = context.user_data.get("seller_card_number")
    card_holder = context.user_data.get("seller_card_holder")

    text = (
        "📋 خلاصه اطلاعات فروشگاهت — لطفاً تأیید کن:\n\n"
        f"🏪 نام فروشگاه: {shop_name}\n"
        f"📝 توضیح: {shop_desc or '—'}\n"
        f"📞 شماره تماس: {phone}\n"
        f"📢 لینک کانال: {channel_link or '—'}\n"
        f"💳 شماره کارت: {card_number[-4:] if card_number else '— ثبت نشده (بعداً اضافه کن)'}\n"
        f"👤 صاحب کارت: {card_holder or '—'}\n"
        f"🔐 رمز: ✅ تنظیم شد\n\n"
        "همه‌چیز درسته؟ دکمه «تأیید و ارسال» رو بزن تا درخواستت بره پیش ادمین."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید و ارسال", callback_data="seller_reg:confirm")],
        [InlineKeyboardButton("✏️ ویرایش اطلاعات", callback_data="seller_reg:edit")],
        [InlineKeyboardButton("❌ لغو", callback_data="seller_reg:cancel")],
    ])
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
    return ASK_CONFIRM


async def confirm_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأیید نهایی و ثبت فروشگاه در دیتابیس + اطلاع به ادمین‌ها."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    shop_name = context.user_data.get("seller_shop_name")
    shop_desc = context.user_data.get("seller_shop_desc")
    phone = context.user_data.get("seller_shop_phone")
    channel_link = context.user_data.get("seller_channel_link")
    card_number = context.user_data.get("seller_card_number")
    card_holder = context.user_data.get("seller_card_holder")
    password = context.user_data.get("seller_password_raw")

    if not shop_name or not phone or not password:
        await query.edit_message_text("❌ به‌نظر می‌رسه اطلاعات ثبت‌نامت کامل نشده. لطفاً با /start دوباره از اول شروع کن.")
        context.user_data.clear()
        return ConversationHandler.END

    import bcrypt
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode(), salt).decode()
    salt_str = salt.decode()

    async with async_session() as session:
        shop = Shop(
            name=shop_name,
            description=shop_desc,
            phone=phone,
            channel_link=channel_link,
            status="draft",
            card_number=safe_encrypt(card_number) if card_number else None,
            card_holder_name=safe_encrypt(card_holder) if card_holder else None,
        )
        session.add(shop)
        await session.flush()

        owner = ShopOwner(
            user_id=user.id,
            shop_id=shop.id,
            first_name=user.first_name,
            username=user.username,
            password_hash=password_hash,
            password_salt=salt_str,
        )
        session.add(owner)
        await session.commit()
        shop_id = shop.id

    # اطلاع به ادمین‌ها
    from config import ADMIN_IDS, WEBSITE_URL
    admin_text = (
        "🆕 درخواست فروشگاه جدید\n\n"
        f"👤 {user.first_name or 'بدون نام'} "
        f"(@{user.username or 'بدون یوزرنیم'} — آیدی: {user.id})\n"
        f"🏪 نام پیشنهادی: {shop_name}\n"
        f"📝 توضیح: {shop_desc}\n"
        f"📞 تماس: {phone}\n"
        f"📢 کانال: {channel_link or '—'}\n"
        f"💳 کارت: {card_number[-4:] if card_number else '— ثبت نشده'}\n"
        f"👤 صاحب کارت: {card_holder or '—'}\n"
        f"🔐 رمز: ✅ تنظیم شد\n\n"
        f"🆔 Shop ID: {shop_id}"
    )
    admin_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ تایید و فعال‌سازی", callback_data=f"admin:seller:approve:{shop_id}"),
            InlineKeyboardButton("❌ رد کردن", callback_data=f"admin:seller:reject:{shop_id}"),
        ]
    ])
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, admin_text, reply_markup=admin_keyboard, parse_mode="HTML")
        except Exception:
            pass

    # پاسخ به فروشنده
    text = (
        "🎉 درخواستت با موفقیت ثبت شد!\n\n"
        "📋 خلاصه اطلاعات فروشگاهت:\n"
        f"🏪 نام: {shop_name}\n"
        f"📝 توضیح: {shop_desc or '—'}\n"
        f"📞 تماس: {phone}\n"
        f"📢 کانال: {channel_link or '—'}\n"
        f"💳 کارت: {card_number[-4:] if card_number else '— ثبت نشده (بعداً اضافه کنید)'}\n"
        f"👤 صاحب کارت: {card_holder or '—'}\n"
        f"🔐 رمز: ✅ تنظیم شد\n\n"
        "📬 درخواستت الان پیش ادمین‌هاست. معمولاً کمتر از ۲۴ ساعت بررسی میشه.\n\n"
        "✅ بعد از تایید، هر کدوم از دستورات زیر برات فعال میشه:\n"
        "• /myshop — پنل مدیریت فروشگاه\n"
        "• /neworders — سفارش‌های جدید\n"
        "• /my_panel — تنظیمات فروشنده و پرداخت\n"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="nav:main")]
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")

    context.user_data.clear()
    return ConversationHandler.END


async def edit_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ویرایش اطلاعات — برمی‌گرده عقب به مرحله اسم فروشگاه."""
    query = update.callback_query
    await query.answer()

    # پاک کردن مرحله رمز (که مرحله آخر بود) و برگشت به ASK_NAME
    context.user_data.pop("seller_password_raw", None)
    text = (
        "✏️ بیا از اول اسم فروشگاهت رو بنویس (الان فرصت درستش کنی):\n\n"
        "هر مرحله رو که رد کردی، می‌تونی با دکمه لغو کنسل کنی."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ لغو", callback_data="seller_reg:cancel")]
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
    return ASK_NAME


async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو ثبت‌نام در هر مرحله"""
    query = update.callback_query
    if query:
        await query.answer()
        await render_view(query, context, "❌ ثبت‌نام فروشگاه لغو شد. هر وقت خواستی می‌تونی با /start دوباره شروع کنی.", InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="nav:main")]
        ]))
    else:
        await update.message.reply_text("❌ لغو شد.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="nav:main")]
        ]))
    context.user_data.clear()
    return ConversationHandler.END


def get_seller_registration_conversation():
    """ConversationHandler برای ثبت‌نام فروشنده"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(seller_registration_start, pattern="^seller_reg:start$"),
        ],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_desc)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASK_CHANNEL_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_channel_link)],
            ASK_CARD_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_card_number)],
            ASK_CARD_HOLDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_card_holder)],
            ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_password)],
            ASK_CONFIRM: [
                CallbackQueryHandler(confirm_registration, pattern="^seller_reg:confirm$"),
                CallbackQueryHandler(edit_registration, pattern="^seller_reg:edit$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_registration, pattern="^seller_reg:cancel$"),
        ],
        name="seller_registration",
        persistent=False,
    )
