"""
هندلر خرید اشتراک توسط فروشنده — از پنل فروشنده شروع می‌شه.
فلوی رسید کارت‌به‌کارت مشابه سفارش‌ها.
"""
import logging
from datetime import datetime

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
from database.models import Shop, ShopOwner, ShopSubscription, SubscriptionPlan, utcnow
from services.subscription import (
    create_paid_subscription,
    get_current_subscription,
    get_subscription_display,
    receipt_hash,
)
from utils.helpers import is_super_admin, format_price
from utils.tg_helpers import render_view

logger = logging.getLogger(__name__)

# Conversation states
SELECT_PLAN = 1
ASK_RECEIPT = 2

# (No states needed for viewing — just callbacks)


# ─── Show subscription status & plans ────────────────────────────
async def show_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش وضعیت اشتراک فعلی + دکمه خرید."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    async with async_session() as session:
        owner = await session.execute(
            __import__("sqlalchemy").select(ShopOwner).where(ShopOwner.user_id == user_id)
        )
        owner = owner.scalar_one_or_none()
        if not owner:
            await query.edit_message_text("❌ شما فروشنده نیستید.")
            return

        status_text = await get_subscription_display(owner.shop_id, session)

    text = (
        "💳 وضعیت اشتراک فروشگاه شما\n\n"
        f"{status_text}\n\n"
        "👇 برای خرید یا تمدید اشتراک، یکی از پلن‌های زیر را انتخاب کنید:"
    )

    async with async_session() as session:
        plans_result = await session.execute(
            __import__("sqlalchemy").select(SubscriptionPlan).where(SubscriptionPlan.is_active == True)
            .order_by(SubscriptionPlan.duration_days)
        )
        plans = plans_result.scalars().all()

    buttons = []
    for p in plans:
        label = f"{p.name} — {format_price(p.price)}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"seller:sub:buy:{p.id}")])

    buttons.append([InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="seller:panel_back")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


# ─── Buy: show plan detail + seller's card info ───────────────
async def buy_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فروشنده یه پلن رو انتخاب کرد — نمایش شماره کارت + دکمه ارسال رسید."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    parts = query.data.split(":")
    plan_id = int(parts[-1])

    async with async_session() as session:
        plan = await session.get(SubscriptionPlan, plan_id)
        if not plan or not plan.is_active:
            await query.edit_message_text("❌ این پلن در دسترس نیست.")
            return

        owner = await session.execute(
            __import__("sqlalchemy").select(ShopOwner).where(ShopOwner.user_id == user_id)
        )
        owner = owner.scalar_one_or_none()
        if not owner:
            await query.edit_message_text("❌ شما فروشنده نیستید.")
            return

        shop = await session.get(Shop, owner.shop_id)

    # ذخیره plan_id موقت برای مرحله بعد
    context.user_data["buy_plan_id"] = plan_id

    # نمایش شماره کارت ادمین (از env یا کانفیگ)
    from config import ADMIN_CARD_NUMBER, ADMIN_CARD_HOLDER, STORE_NAME

    if not ADMIN_CARD_NUMBER:
        # Fallback: به فروشنده بگو با پشتیبانی تماس بگیره
        text = (
            f"📋 {plan.name}\n"
            f"💰 مبلغ: {format_price(plan.price)}\n\n"
            "⚠️ شماره کارتی برای واریز ثبت نشده. لطفاً با پشتیبانی تماس بگیرید:\n"
            "/support"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت", callback_data="seller:subscription:show")],
        ]), parse_mode="HTML")
        return

    text = (
        f"📋 {plan.name}\n"
        f"💰 مبلغ: {format_price(plan.price)}\n"
        f"📆 مدت: {plan.duration_days} روز\n\n"
        "💳 مبلغ را به شماره کارت زیر واریز کنید:\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🏦 {ADMIN_CARD_HOLDER or STORE_NAME}\n"
        f"💳 {ADMIN_CARD_NUMBER}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📸 پس از واریز، عکس رسید را ارسال کنید:"
    )

    buttons = [
        [InlineKeyboardButton("📸 ارسال رسید", callback_data="seller:sub:send_receipt")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="seller:subscription:show")],
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


# ─── Ask receipt photo ─────────────────────────────────────
async def ask_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """از فروشنده خواسته می‌شه عکس رسید بفرسته."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "📸 لطفاً عکس رسید واریز را ارسال کنید (فقط عکس).\n"
            "برای لغو: /cancel"
        )
    return ASK_RECEIPT


async def receive_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت رسید و ایجاد ردیف اشتراک."""
    user_id = update.effective_user.id
    plan_id = context.user_data.get("buy_plan_id")
    if not plan_id:
        await update.message.reply_text("❌ لطفاً دوباره از اول اقدام کنید. /myshop")
        return ConversationHandler.END

    photo = update.message.photo[-1] if update.message.photo else None
    caption = update.message.caption or ""

    if not photo:
        await update.message.reply_text("❌ لطفاً یک عکس ارسال کنید:")
        return ASK_RECEIPT

    receipt_file_id = photo.file_id

    async with async_session() as session:
        # Get owner
        owner = await session.execute(
            __import__("sqlalchemy").select(ShopOwner).where(ShopOwner.user_id == user_id)
        )
        owner = owner.scalar_one_or_none()
        if not owner:
            await update.message.reply_text("❌ شما فروشنده نیستید.")
            return ConversationHandler.END

        # Dedup check (همان مکانیزم سفارش‌ها)
        h = receipt_hash(receipt_file_id, caption)
        existing = await session.execute(
            __import__("sqlalchemy").select(ShopSubscription).where(
                ShopSubscription.receipt_hash == h
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            await update.message.reply_text(
                "❌ این رسید قبلاً ثبت شده. لطفاً رسید دیگری ارسال کنید یا با پشتیبانی تماس بگیرید."
            )
            return ConversationHandler.END

        # Create subscription record
        try:
            sub = await create_paid_subscription(
                shop_id=owner.shop_id,
                plan_id=plan_id,
                session=session,
                receipt_file_id=receipt_file_id,
                receipt_caption=caption,
            )
            # Preload plan while session is open
            from sqlalchemy.orm import selectinload
            result = await session.execute(
                __import__("sqlalchemy").select(ShopSubscription)
                .where(ShopSubscription.id == sub.id)
                .options(selectinload(ShopSubscription.plan))
            )
            sub = result.scalar_one()
            await session.commit()
        except ValueError as e:
            await update.message.reply_text(f"❌ {e}")
            return ConversationHandler.END

    # ─── session closed here — sub.plan is already loaded ───
    plan_name = sub.plan.name if sub.plan else "نامشخص"
    text = (
        f"✅ درخواست اشتراک شما ثبت شد!\n\n"
        f"📋 {plan_name}\n"
        f"💰 {format_price(sub.plan.price) if sub.plan else '—'}\n"
        f"🆔 کد پیگیری: #{sub.id}\n\n"
        "⏳ پس از تأیید ادمین، اشتراک شما فعال خواهد شد. معمولاً کمتر از ۲۴ ساعت بررسی می‌شود.\n"
        "شما می‌توانید وضعیت را از همین بخش پیگیری کنید."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 وضعیت اشتراک", callback_data="seller:subscription:show")],
        [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="seller:panel_back")],
    ])
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")

    # ─── Notify admins ───
    from config import ADMIN_IDS
    shop_name = owner.first_name or f"فروشنده #{owner.shop_id}"
    admin_text = (
        f"🆕 درخواست اشتراک جدید!\n\n"
        f"👤 فروشنده: {owner.first_name or '—'} (@{owner.username or '—'})\n"
        f"🏪 فروشگاه: #{owner.shop_id}\n"
        f"📋 پلن: {plan_name}\n"
        f"💰 مبلغ: {format_price(sub.plan.price) if sub.plan else '—'}\n"
        f"🆔 کد پیگیری: #{sub.id}\n\n"
        f"📸 رسید ارسال شده برای بررسی در دسترس است."
    )
    admin_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👁 مشاهده و تأیید", callback_data=f"admin:sub:detail:{sub.id}")],
    ])
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, admin_text, reply_markup=admin_keyboard, parse_mode="HTML")
        except Exception as e:
            logger.warning("Failed to notify admin #%s about subscription #%s: %s", admin_id, sub.id, e)

    context.user_data.pop("buy_plan_id", None)
    return ConversationHandler.END


# ─── Cancel ────────────────────────────────────────────────
async def cancel_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو خرید اشتراک."""
    context.user_data.pop("buy_plan_id", None)
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("❌ خرید لغو شد.")
    else:
        await update.message.reply_text("❌ خرید لغو شد.")
    return ConversationHandler.END


# ─── Admin: list pending subscriptions ──────────────────────
async def admin_list_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ادمین لیست اشتراک‌های در انتظار تأیید."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if not is_super_admin(user_id):
        return

    async with async_session() as session:
        result = await session.execute(
            __import__("sqlalchemy").select(ShopSubscription)
            .where(ShopSubscription.approval_status == "pending")
            .order_by(ShopSubscription.created_at.desc())
            .limit(20)
        )
        pending = result.scalars().all()

    if not pending:
        await query.edit_message_text("✅ هیچ درخواست اشتراک در انتظار تأیید نیست.",
                                       reply_markup=InlineKeyboardMarkup([
                                           [InlineKeyboardButton("🔙 پنل ادمین", callback_data="admin:panel")]
                                       ]))
        return

    text = "📋 درخواست‌های اشتراک در انتظار تأیید:\n\n"
    for s in pending:
        shop_id = s.shop_id
        # Explicitly load plan while session is open
        plan_name = "آزمایشی"
        if s.plan_id:
            plan = await session.get(SubscriptionPlan, s.plan_id)
            if plan:
                plan_name = plan.name
        text += f"🔹 #{s.id} — فروشگاه #{shop_id} — {plan_name} — {s.created_at.strftime('%Y-%m-%d %H:%M')}\n"

    buttons = []
    for s in pending:
        buttons.append([InlineKeyboardButton(f"👁 #{s.id}", callback_data=f"admin:sub:detail:{s.id}")])
    buttons.append([InlineKeyboardButton("🔙 پنل ادمین", callback_data="admin:panel")])

    if query.message:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


async def admin_subscription_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """جزئیات یه درخواست اشتراک برای ادمین."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if not is_super_admin(user_id):
        return

    sub_id = int(query.data.split(":")[-1])

    async with async_session() as session:
        sub = await session.get(ShopSubscription, sub_id)
        if not sub:
            await query.edit_message_text("❌ پیدا نشد.")
            return

        shop = await session.get(Shop, sub.shop_id)
        owner_result = await session.execute(
            __import__("sqlalchemy").select(ShopOwner).where(ShopOwner.shop_id == sub.shop_id)
        )
        owner = owner_result.scalar_one_or_none()
        # Explicitly load plan while session is open
        plan_name = "آزمایشی"
        if sub.plan_id:
            plan = await session.get(SubscriptionPlan, sub.plan_id)
            if plan:
                plan_name = plan.name

        text = (
            f"📋 جزئیات درخواست اشتراک #{sub.id}\n\n"
            f"🏪 فروشگاه: {shop.name if shop else '#' + str(sub.shop_id)}\n"
            f"👤 فروشنده: {owner.first_name if owner else '—'} (@{owner.username if owner else '—'})\n"
            f"📆 پلن: {plan_name}\n"
            f"💰 مبلغ: {format_price(sub.plan.price) if sub.plan else 'رایگان (آزمایشی)'}\n"
            f"📅 شروع: {sub.start_date.strftime('%Y-%m-%d')}\n"
            f"📅 پایان: {sub.end_date.strftime('%Y-%m-%d')}\n"
            f"📸 رسید: {'✅ دارد' if sub.receipt_file_id else '—'}\n"
            f"📊 وضعیت: {sub.approval_status}\n"
        )

    buttons = []
    if sub.approval_status == "pending" and sub.receipt_file_id:
        buttons.append([InlineKeyboardButton("✅ تأیید", callback_data=f"admin:sub:verify:{sub_id}")])
        buttons.append([InlineKeyboardButton("❌ رد", callback_data=f"admin:sub:reject:{sub_id}")])
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin:subscription:pending")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


async def admin_verify_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأیید اشتراک توسط ادمین — idempotent."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if not is_super_admin(user_id):
        return

    sub_id = int(query.data.split(":")[-1])

    async with async_session() as session:
        # **ترتیب lock ثابت**: اول Shop بعد Subscription
        # قفل روی Subscription
        sub = await session.get(ShopSubscription, sub_id)
        if not sub:
            await query.edit_message_text("❌ پیدا نشد.")
            return

        # Idempotency: اگه قبلاً تأیید شده، ignore
        if sub.verified_at is not None:
            await query.answer("✅ قبلاً تأیید شده.", show_alert=True)
            return

        # with_for_update روی Subscription
        result = await session.execute(
            __import__("sqlalchemy").select(ShopSubscription).where(ShopSubscription.id == sub_id)
            .with_for_update()
        )
        sub = result.scalar_one_or_none()
        if not sub:
            await query.edit_message_text("❌ پیدا نشد.")
            return

        if sub.approval_status != "pending":
            await query.answer(f"وضعیت فعلی: {sub.approval_status}", show_alert=True)
            return

        # با with_for_update چک دوباره verified_at
        if sub.verified_at is not None:
            await query.answer("✅ قبلاً تأیید شده (دومین چک).", show_alert=True)
            return

        from services.subscription import verify_subscription
        from sqlalchemy import select

        # قفل روی Shop
        shop = await session.get(Shop, sub.shop_id)
        if not shop:
            await query.edit_message_text("❌ فروشگاه پیدا نشد.")
            return

        # Look up owner while session is open
        owner_row = await session.execute(
            __import__("sqlalchemy").select(ShopOwner).where(ShopOwner.shop_id == sub.shop_id)
        )
        owner = owner_row.scalar_one_or_none()

        await verify_subscription(sub.id, user_id, session)
        await session.commit()

    await query.edit_message_text(
        f"✅ اشتراک #{sub_id} تأیید شد و فروشگاه فعال گردید.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 لیست درخواست‌ها", callback_data="admin:subscription:pending")]
        ]),
        parse_mode="HTML"
    )
    await query.answer("✅ تأیید شد.", show_alert=True)

    # نوتیف به فروشنده
    if shop and owner:
        try:
            await context.bot.send_message(
                owner.user_id,
                f"🎉 اشتراک شما تأیید شد!\n\n"
                f"فروشگاه «{shop.name}» تا {sub.end_date.strftime('%Y-%m-%d')} فعال است.",
                parse_mode="HTML",
            )
        except Exception:
            pass


async def admin_reject_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رد اشتراک توسط ادمین."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if not is_super_admin(user_id):
        return

    sub_id = int(query.data.split(":")[-1])

    async with async_session() as session:
        sub = await session.get(ShopSubscription, sub_id)
        if not sub or sub.approval_status != "pending":
            await query.edit_message_text("❌ درخواست قابل رد نیست.")
            return

        from services.subscription import reject_subscription
        await reject_subscription(sub.id, user_id, reason="رد شده توسط ادمین", session=session)
        await session.commit()

        # Look up owner while session is open
        shop = await session.get(Shop, sub.shop_id)
        owner_row = await session.execute(
            __import__("sqlalchemy").select(ShopOwner).where(ShopOwner.shop_id == sub.shop_id)
        )
        owner = owner_row.scalar_one_or_none()

    await query.edit_message_text(
        f"❌ اشتراک #{sub_id} رد شد.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 لیست درخواست‌ها", callback_data="admin:subscription:pending")]
        ]),
        parse_mode="HTML"
    )
    await query.answer("❌ رد شد.", show_alert=True)

    # Notify seller
    if shop and owner:
        try:
            await context.bot.send_message(
                owner.user_id,
                f"❌ اشتراک شما رد شد.\n\n"
                f"فروشگاه «{shop.name if shop else '—'}»\n"
                f"دلیل: رد شده توسط ادمین\n\n"
                f"برای اطلاعات بیشتر به پنل فروشنده مراجعه کنید: /myshop",
                parse_mode="HTML",
            )
        except Exception:
            pass


# ─── Register handlers ──────────────────────────────────────
def register_subscription_handlers(application):
    """ثبت همه هندلرهای اشتراک در application."""

    # Seller side — subscription purchase conversation
    buy_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(show_subscription, pattern="^seller:subscription:show$"),
            CallbackQueryHandler(buy_subscription, pattern="^seller:sub:buy:"),
            CallbackQueryHandler(ask_receipt, pattern="^seller:sub:send_receipt$"),
        ],
        states={
            ASK_RECEIPT: [
                MessageHandler(filters.PHOTO & ~filters.COMMAND, receive_receipt),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_buy),
            CallbackQueryHandler(cancel_buy, pattern="^seller:sub:cancel$"),
        ],
        name="subscription_buy",
        allow_reentry=True,
    )
    application.add_handler(buy_conv)

    # Admin side — subscription verification
    application.add_handler(CallbackQueryHandler(admin_list_pending, pattern="^admin:subscription:pending$"))
    application.add_handler(CallbackQueryHandler(admin_subscription_detail, pattern="^admin:sub:detail:"))
    application.add_handler(CallbackQueryHandler(admin_verify_subscription, pattern="^admin:sub:verify:"))
    application.add_handler(CallbackQueryHandler(admin_reject_subscription, pattern="^admin:sub:reject:"))