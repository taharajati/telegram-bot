"""
هندلرهای تایید/رد درخواست فروشگاه توسط ادمین.
دکمه‌های inline روی پیام اعلان، بدون نیاز به رفتن به پنل.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, CommandHandler, filters
from sqlalchemy import select

from database.db import async_session
from database.models import Shop, ShopOwner
from handlers.bot_commands import set_seller_menu
from utils.helpers import is_super_admin
from utils.tg_helpers import render_view


ASK_REJECT_REASON = range(1)


async def handle_admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تایید فروشگاه توسط ادمین (یک تپ)"""
    query = update.callback_query
    await query.answer()

    if not is_super_admin(update.effective_user.id):
        await query.answer("❌ فقط ادمین کل می‌تونه تایید کنه.", show_alert=True)
        return

    shop_id = int(query.data.split(":")[3])

    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
        if not shop:
            await query.answer("فروشگاه پیدا نشد!", show_alert=True)
            return

        if shop.status != "draft":
            await query.answer(f"وضعیت فعلی: {shop.status}. فقط draft قابل تایید است.", show_alert=True)
            return

        # تغییر وضعیت
        shop.status = "active"
        shop.is_active = True
        # ایجاد ردیف trial اشتراک
        from services.subscription import create_trial_subscription
        await create_trial_subscription(shop_id, update.effective_user.id, session)
        await session.commit()

        # گرفتن مالک
        result = await session.execute(
            select(ShopOwner).where(ShopOwner.shop_id == shop_id)
        )
        owner = result.scalar_one_or_none()

    # به‌روزرسانی پیام ادمین
    await query.edit_message_text(
        query.message.text_html + "\n\n✅ تایید شد! 🎉",
        parse_mode="HTML",
        reply_markup=None,
    )

    # پیام به فروشنده
    if owner:
        link = f"https://t.me/{context.bot.username}?start=shop_{shop_id}"
        seller_text = (
            "🎉 فروشگاه شما تایید شد!\n\n"
            f"🏪 {shop.name}\n"
            f"لینک فروشگاه شما:\n"
            f"{link}\n\n"
            "حالا با این دستورات می‌تونی فروشگاهت رو مدیریت کنی:\n"
            "📌 /myshop — مدیریت محصولات، سفارش‌ها و تنظیمات\n\n"
            "💳 برای فعال‌سازی کارت‌به‌کارت، از پنل /myshop → تنظیمات پرداخت اقدام کن."
        )
        try:
            await context.bot.send_message(owner.user_id, seller_text, parse_mode="HTML")
            # Also send a friendly follow-up with shortcut buttons
            welcome_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 مدیریت محصولات", callback_data="admin:products:list:0")],
                [InlineKeyboardButton("⚙️ تنظیمات فروشگاه", callback_data="seller:panel_back")],
            ])
            await context.bot.send_message(
                owner.user_id,
                "از کجا می‌خوای شروع کنی؟ 👇",
                reply_markup=welcome_keyboard,
            )
            # Set seller menu commands
            await set_seller_menu(context.bot, owner.user_id)
        except Exception:
            pass

    await query.answer("✅ فروشگاه تایید شد.", show_alert=True)


async def handle_admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند رد با پرسش دلیل"""
    query = update.callback_query
    await query.answer()

    if not is_super_admin(update.effective_user.id):
        await query.answer("❌ فقط ادمین کل.", show_alert=True)
        return

    shop_id = int(query.data.split(":")[3])

    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
        if not shop or shop.status != "draft":
            await query.answer("قابل رد کردن نیست.", show_alert=True)
            return

    context.user_data["reject_shop_id"] = shop_id
    context.user_data["reject_shop_name"] = shop.name if shop else ""

    # پیام موقت جایگزین دکمه‌ها
    await query.edit_message_text(
        query.message.text_html + "\n\n✍️ دلیل رد را بنویسید (اختیاری — صرفاً Enter برای رد بدون دلیل):",
        parse_mode="HTML",
    )
    return ASK_REJECT_REASON


async def reject_with_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت دلیل رد + اعمال رد"""
    reason = update.message.text.strip() if update.message.text else ""

    shop_id = context.user_data.get("reject_shop_id")
    if not shop_id:
        await update.message.reply_text("❌ خطا: درخواست منقضی شده.")
        return ConversationHandler.END

    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
        if not shop:
            await update.message.reply_text("❌ فروشگاه پیدا نشد.")
            return ConversationHandler.END

        shop.status = "rejected"
        shop.rejection_reason = reason if reason else None
        await session.commit()

        # گرفتن مالک
        result = await session.execute(
            select(ShopOwner).where(ShopOwner.shop_id == shop_id)
        )
        owner = result.scalar_one_or_none()

    # پیام به فروشنده
    if owner:
        text_parts = [
            "❌ درخواست فروشگاه شما تایید نشد."
        ]
        if reason:
            text_parts.append(f"\n📋 دلیل: {reason}")
        text_parts.append(
            "\n\nمی‌توانید بعداً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
        )

        try:
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🏪 تلاش دوباره", callback_data="seller_reg:start")]])
            await context.bot.send_message(owner.user_id, "\n".join(text_parts), parse_mode="HTML", reply_markup=keyboard)
        except Exception:
            pass

    # اطلاع به ادمینی که رد کرد — برای پیگیری
    await update.message.reply_text(
        f"✅ فروشگاه #{shop_id} («{context.user_data.get('reject_shop_name', 'نامشخص')}») رد شد.\n"
        f"{'دلیل: ' + reason if reason else 'بدون دلیل.'}"
    )

    context.user_data.clear()
    return ConversationHandler.END


async def reject_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انصراف از رد کردن"""
    context.user_data.clear()
    query = update.callback_query
    if query:
        try:
            await query.answer()
            await query.edit_message_text("❌ رد کردن لغو شد.")
        except Exception:
            pass
    elif update.message:
        await update.message.reply_text("❌ رد کردن لغو شد.")
    return ConversationHandler.END


def get_admin_approval_conversation():
    """ConversationHandler برای تایید/رد پیام اعلان ادمین"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_admin_reject, pattern=r"^admin:seller:reject:\d+$"),
        ],
        states={
            ASK_REJECT_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, reject_with_reason),
                MessageHandler(filters.COMMAND, reject_with_reason),  # /skip یا چیزی
            ],
        },
        fallbacks=[
            CallbackQueryHandler(reject_cancel, pattern="^admin:seller:reject_cancel$"),
            CommandHandler("cancel", reject_cancel),
        ],
        name="admin_approval",
        persistent=False,
    )