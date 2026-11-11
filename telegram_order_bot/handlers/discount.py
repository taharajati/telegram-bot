"""
Discount codes — seller creates, customer applies at checkout.
"""
import random
import string
from datetime import datetime

from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from database.db import async_session
from database.models import DiscountCode
from utils.tg_helpers import get_current_shop_id, render_view

ASK_CODE_TYPE, ASK_VALUE, ASK_CODE, ASK_MIN, ASK_USES = range(5)


def get_discount_conversation() -> ConversationHandler:
    """Conversation for seller to create a discount code."""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(_start_create_code, pattern="^discount:create$")],
        states={
            ASK_CODE_TYPE: [CallbackQueryHandler(_ask_code_type, pattern="^discount:type:")],
            ASK_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_value_handler)],
            ASK_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_code_handler)],
            ASK_MIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_min_handler)],
            ASK_USES: [MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_uses_handler)],
        },
        fallbacks=[CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern="^noop$")],
        name="discount_code_creation",
    )


async def _start_create_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    buttons = [
        [InlineKeyboardButton("🎯 درصدی (مثلاً ۲۰٪)", callback_data="discount:type:percent")],
        [InlineKeyboardButton("💰 مبلغ ثابت (مثلاً ۱۰۰,۰۰۰)", callback_data="discount:type:fixed")],
        [InlineKeyboardButton("❌ انصراف", callback_data="noop")],
    ]
    await render_view(query, context, "🎯 نوع تخفیف رو انتخاب کن:",
                       InlineKeyboardMarkup(buttons))
    return ASK_CODE_TYPE


async def _ask_code_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    disc_type = query.data.split(":")[2]
    context.user_data["discount_type"] = disc_type

    label = "مقدار تخفیف رو به تومان وارد کن (مثلاً ۱۰۰۰۰۰):" if disc_type == "fixed" else "درصد تخفیف رو وارد کن (مثلاً ۲۰):"
    await query.edit_message_text(f"✏️ {label}\n\n(هر لحظه /cancel رو بزن)",
                                   reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="noop")]]))
    return ASK_VALUE


async def _ask_value_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", "")
    try:
        value = int(text)
        if value <= 0:
            raise ValueError
        if context.user_data.get("discount_type") == "percent" and value > 100:
            await update.message.reply_text("درصد تخفیف نمی‌تونه بیشتر از ۱۰۰ باشه. دوباره وارد کن:")
            return ASK_VALUE
    except ValueError:
        await update.message.reply_text("لطفاً یک عدد معتبر وارد کن (مثلاً ۲۰ یا ۱۰۰۰۰۰):")
        return ASK_VALUE

    context.user_data["discount_value"] = value

    # Auto-generate code
    generated = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    await update.message.reply_text(
        f"یه کد دلخواه برای این تخفیف بنویس، یا از پیشنهاد ما استفاده کن: «{generated}»",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"استفاده از «{generated}»", callback_data="discount:use_generated")],
            [InlineKeyboardButton("❌ انصراف", callback_data="noop")],
        ])
    )
    context.user_data["discount_code_generated"] = generated
    return ASK_CODE


async def _ask_code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper().replace(" ", "")
    if not text or len(text) < 3:
        text = context.user_data.get("discount_code_generated", "DISCOUNT")
    context.user_data["discount_code"] = text

    await update.message.reply_text(
        "حداقل مبلغ سفارش برای اعمال این کد رو وارد کن (۰ = بدون محدودیت):"
    )
    return ASK_MIN


async def _ask_min_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", "")
    try:
        min_amount = int(text) if text else 0
    except ValueError:
        min_amount = 0
    context.user_data["discount_min"] = min_amount

    await update.message.reply_text("حداکثر تعداد استفاده رو وارد کن (۰ = نامحدود):")
    return ASK_USES


async def _ask_uses_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        max_uses = int(text) if text else 0
    except ValueError:
        max_uses = 0
    context.user_data["discount_max_uses"] = max_uses

    # Save to database
    shop_id = context.user_data.get("seller_shop_id")
    if not shop_id:
        # Get from ShopOwner record (seller's actual shop)
        from database.models import ShopOwner
        async with async_session() as session2:
            owner_result = await session2.execute(
                select(ShopOwner).where(ShopOwner.user_id == update.effective_user.id)
            )
            owner = owner_result.scalar_one_or_none()
            shop_id = owner.shop_id if owner else await get_current_shop_id(update)
    code = context.user_data.get("discount_code", "DISCOUNT")
    disc_type = context.user_data.get("discount_type", "percent")
    disc_value = context.user_data.get("discount_value", 0)
    min_amount = context.user_data.get("discount_min", 0)

    async with async_session() as session:
        # Verify shop exists
        from database.models import Shop
        shop = await session.get(Shop, shop_id)
        if not shop:
            await update.message.reply_text("❌ فروشگاه پیدا نشد. با /start دوباره شروع کن.")
            return ConversationHandler.END

        existing = await session.execute(
            select(DiscountCode).where(DiscountCode.shop_id == shop_id, DiscountCode.code == code)
        )
        if existing.scalar_one_or_none():
            await update.message.reply_text("❌ این کد قبلاً استفاده شده. یه کد دیگه انتخاب کن:")
            return ASK_CODE

        session.add(DiscountCode(
            shop_id=shop_id,
            code=code,
            discount_type=disc_type,
            discount_value=disc_value,
            min_order_amount=min_amount,
            max_uses=max_uses,
        ))
        await session.commit()

    type_label = "درصدی" if disc_type == "percent" else "مبلغی"
    value_label = f"{disc_value}٪" if disc_type == "percent" else f"{disc_value:,} تومان"
    await update.message.reply_text(
        f"✅ کد تخفیف ساخته شد!\n\n"
        f"🎯 کد: {code}\n"
        f"📊 نوع: {type_label}\n"
        f"💰 مقدار: {value_label}\n"
        f"📋 حداقل سفارش: {min_amount:,} تومان\n"
        f"🔢 حداکثر استفاده: {'نامحدود' if max_uses == 0 else max_uses}\n\n"
        f"مشتری‌ها می‌تونن در هنگام پرداخت این کد رو وارد کنن.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="seller:panel_back")],
        ])
    )

    context.user_data.clear()
    return ConversationHandler.END


async def list_discounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show seller's active discount codes."""
    query = update.callback_query
    await query.answer()
    shop_id = await get_current_shop_id(update)
    # For sellers (shop owners), get shop_id from ShopOwner
    if not shop_id:
        from database.models import ShopOwner
        async with async_session() as session:
            owner = await session.execute(
                select(ShopOwner).where(ShopOwner.user_id == update.effective_user.id)
            )
            owner = owner.scalar_one_or_none()
            if owner:
                shop_id = owner.shop_id
    if not shop_id:
        await render_view(query, context,
            "❌ فروشگاهی برای حساب شما پیدا نشد.\n"
            "اگه صاحب فروشگاه هستی با /start شروع کن.",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="seller:panel_back")]]))
        return

    async with async_session() as session:
        result = await session.execute(
            select(DiscountCode).where(
                DiscountCode.shop_id == shop_id,
                DiscountCode.is_active == True,
            ).order_by(DiscountCode.created_at.desc())
        )
        codes = result.scalars().all()

    if not codes:
        text = "📋 هنوز هیچ کد تخفیفی نساختی. با دکمه پایین اولین کدتو بساز 👇"
        buttons = [[InlineKeyboardButton("➕ ساخت کد تخفیف", callback_data="discount:create")],
                   [InlineKeyboardButton("🔙 بازگشت", callback_data="seller:panel_back")]]
    else:
        lines = ["📋 کدهای تخفیف فعال\n"]
        for c in codes:
            if c.expires_at and c.expires_at < datetime.utcnow():
                continue
            type_label = "٪" if c.discount_type == "percent" else " تومان"
            value_show = f"{c.discount_value}{type_label}"
            uses = f"{c.used_count}/{c.max_uses}" if c.max_uses else f"{c.used_count}/∞"
            min_label = f" (سفارش > {c.min_order_amount:,})" if c.min_order_amount else ""
            lines.append(f"🎯 {c.code} — {value_show}{min_label} — استفاده: {uses}")

        text = "\n".join(lines)
        buttons = [[InlineKeyboardButton("➕ ساخت کد جدید", callback_data="discount:create")],
                   [InlineKeyboardButton("🔙 بازگشت", callback_data="seller:panel_back")]]

    await render_view(query, context, text, InlineKeyboardMarkup(buttons), parse_mode="HTML")