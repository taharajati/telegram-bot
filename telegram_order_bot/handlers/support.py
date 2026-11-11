"""
بخش پشتیبانی ساده: به کاربر توضیح داده و پیام‌ها رو
از طریق سیستم مکالمه (conversations.py) رد و بدل می‌کنه.
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from sqlalchemy import select
import config
from database.db import async_session
from database.models import ShopOwner, Shop, Conversation, Message, utcnow
from utils.tg_helpers import render_view

logger = logging.getLogger(__name__)

SUPPORT_WAITING, SELLER_SUPPORT_WAITING = range(2)

SUPPORT_ADMIN_REPLY_WAITING = 2  # Add new state for admin reply

SUPPORT_TEXT = (
    "☎️ پشتیبانی\n\n"
    "اگه سوالی داری یا به کمک نیاز داری، پیامت رو همینجا بنویس؛ "
    "به زودی همکاران پشتیبانی بهت پاسخ می‌دن."
)

SELLER_SUPPORT_TEXT = (
    "💬 پیام به فروشنده\n\n"
    "پیامت رو همینجا بنویس تا مستقیماً به فروشنده فروشگاه برسه 👇\n"
    "فروشنده می‌تونه به پیامت جواب بده."
)


async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point: user clicks 'support' button."""
    query = update.callback_query
    if query:
        await query.answer()
        await render_view(query, context, SUPPORT_TEXT, None)
    return SUPPORT_WAITING


async def support_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive user's support message and forward to admins."""
    if not update.message or not update.message.text:
        return SUPPORT_WAITING

    user = update.effective_user
    text = update.message.text

    # Forward to admins
    sent_to = []
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"✉️ پیام پشتیبانی\n"
                    f"از: {user.first_name} (@{user.username or '-'} | ID: {user.id})\n\n"
                    f"{text}"
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💬 پاسخ", callback_data=f"support:reply:{user.id}")
                ]])
            )
            sent_to.append(f"admin:{admin_id}")
        except Exception as e:
            logger.warning(f"Could not forward to admin {admin_id}: {e}")

    if config.NOTIFICATION_CHANNEL_ID:
        try:
            await context.bot.send_message(
                chat_id=config.NOTIFICATION_CHANNEL_ID,
                text=(
                    f"✉️ پیام پشتیبانی از {user.first_name} (@{user.username or '-'} | ID: {user.id}):\n\n"
                    f"{text}"
                ),
            )
            sent_to.append("channel")
        except Exception as e:
            logger.warning(f"Could not forward to notification channel: {e}")

    if sent_to:
        await update.message.reply_text(
            "✅ پیامت به پشتیبانی ارسال شد، به زودی جواب می‌گیری.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data="nav:main")]
            ])
        )
    else:
        await update.message.reply_text(
            "⚠️ پیام شما ثبت شد ولی متأسفانه در حال حاضر "
            "امکان ارسال به پشتیبانی وجود نداره. لطفاً بعداً دوباره تلاش کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data="nav:main")]
            ])
        )
    return ConversationHandler.END


async def support_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel support."""
    await update.message.reply_text("❌ لغو شد.", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="nav:main")]
    ]))
    return ConversationHandler.END


async def seller_support_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point: customer clicks 'message to seller' button from shop menu.
    Creates a Conversation (without order) and opens the chat view."""
    query = update.callback_query
    if query:
        await query.answer()

    # Get shop_id from context or DB
    shop_id = context.user_data.get("support_shop_id")
    if not shop_id:
        shop_id = context.user_data.get("shop_id")
    if not shop_id:
        async with async_session() as session:
            from database.models import User
            user = await session.get(User, update.effective_user.id)
            shop_id = user.current_shop_id if user else None

    if not shop_id:
        if query:
            await render_view(query, context, "❌ هیچ فروشگاهی انتخاب نشده. از منوی اصلی یه فروشگاه رو باز کن.", None)
        else:
            await update.message.reply_text("❌ فروشگاهی انتخاب نشده.")
        return ConversationHandler.END

    buyer_id = update.effective_user.id

    # Create or get existing conversation (no order_id)
    from handlers.conversations import _get_or_create_conv
    conv_id = await _get_or_create_conv(buyer_id, shop_id, order_id=None)

    context.user_data["conv_id"] = conv_id
    context.user_data["conv_shop_id"] = shop_id
    context.user_data["conv_buyer_id"] = buyer_id

    # Show the conversation view
    from handlers.conversations import _build_conversation_view, ASK_MESSAGE
    text, keyboard = await _build_conversation_view(conv_id, buyer_role=True)

    # Override the back button to point to the shop
    if keyboard:
        keyboard = InlineKeyboardMarkup([
            *keyboard.inline_keyboard[:-1],  # all buttons except last (back)
            [InlineKeyboardButton("🔙 بازگشت به فروشگاه", callback_data="nav:main")],
        ])

    if query:
        try:
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception:
            await query.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")

    context.user_data["conv_id_writing"] = conv_id
    return SELLER_SUPPORT_WAITING


async def seller_support_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive customer's message, save to conversation, notify seller."""
    if not update.message or not update.message.text:
        return SELLER_SUPPORT_WAITING

    text = update.message.text.strip()
    if not text:
        return SELLER_SUPPORT_WAITING

    conv_id = context.user_data.get("conv_id_writing") or context.user_data.get("conv_id")
    if not conv_id:
        await update.message.reply_text("❌ مکالمه یافت نشد.")
        return ConversationHandler.END

    buyer_id = update.effective_user.id

    # Save message to conversation (inline — same logic as save_message in conversations.py)
    async with async_session() as session:
        conv = await session.get(Conversation, conv_id)
        if not conv:
            await update.message.reply_text("❌ مکالمه یافت نشد.")
            return ConversationHandler.END

        # Determine role
        if conv.buyer_id == buyer_id:
            role = "buyer"
        else:
            owner = await session.execute(
                select(ShopOwner).where(
                    ShopOwner.user_id == buyer_id,
                    ShopOwner.shop_id == conv.shop_id,
                )
            )
            if not owner.scalar_one_or_none():
                await update.message.reply_text("❌ شما دسترسی به این مکالمه ندارید.")
                return ConversationHandler.END
            role = "seller"

        msg = Message(conversation_id=conv_id, sender_role=role, content=text)
        session.add(msg)
        conv.updated_at = utcnow()
        await session.commit()

    context.user_data.pop("conv_id_writing", None)

    # Notify the other party
    async with async_session() as session:
        conv = await session.get(Conversation, conv_id)
        shop = await session.get(Shop, conv.shop_id) if conv else None
    if conv:
        if role == "buyer":
            from services.events import event_bus, Event
            context.application.create_task(
                event_bus.emit(
                    Event.SELLER_MESSAGE,
                    bot=context.bot,
                    shop_id=conv.shop_id,
                    message_text=text[:200],
                )
            )
        elif shop:
            try:
                await context.bot.send_message(
                    chat_id=conv.buyer_id,
                    text=f"💬 پاسخ فروشگاه {shop.name}:\n\n{text[:200]}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📨 مشاهده مکالمه", callback_data=f"msg:open:{conv_id}")]
                    ]),
                )
            except Exception as e:
                logger.warning(f"notify buyer failed: {e}")

    await update.message.reply_text("✅ پیام ارسال شد.")

    # Show conversation again with fresh view
    from handlers.conversations import _build_conversation_view
    conv_text, keyboard = await _build_conversation_view(conv_id, buyer_role=True)
    # Override back button to shop
    if keyboard:
        keyboard = InlineKeyboardMarkup([
            *keyboard.inline_keyboard[:-1],
            [InlineKeyboardButton("🔙 بازگشت به فروشگاه", callback_data="nav:main")],
        ])

    await update.message.reply_text(conv_text, reply_markup=keyboard, parse_mode="HTML")
    # Stay in conversation — user can keep messaging
    # Set conv_id_writing so next text message goes to this conversation
    context.user_data["conv_id_writing"] = conv_id
    return SELLER_SUPPORT_WAITING


async def seller_support_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel seller support."""
    context.user_data.pop("support_mode", None)
    context.user_data.pop("support_shop_id", None)
    context.user_data.pop("conv_id", None)
    context.user_data.pop("conv_id_writing", None)
    await update.message.reply_text("❌ لغو شد.", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت به فروشگاه", callback_data="nav:main")]
    ]))
    return ConversationHandler.END


# === Admin reply to support messages ===

async def admin_support_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point: admin clicks reply button on a forwarded support message."""
    query = update.callback_query
    if query:
        await query.answer()
    
    # Extract user_id from callback data: support:reply:{user_id}
    parts = query.data.split(":")
    if len(parts) < 3:
        await render_view(query, context, "❌ داده‌های پاسخ نامعتبر.", None)
        return ConversationHandler.END
    
    target_user_id = int(parts[2])
    context.user_data["support_reply_target"] = target_user_id
    
    await render_view(query, context,
        f"💬 پاسخ به کاربر {target_user_id}\n\n"
        "پیام خود را بنویسید و ارسال کنید:",
        InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ انصراف", callback_data="support:reply_cancel")
        ]])
    )
    return SUPPORT_ADMIN_REPLY_WAITING


async def admin_support_reply_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive admin's reply and send to user."""
    if not update.message or not update.message.text:
        return SUPPORT_ADMIN_REPLY_WAITING
    
    target_user_id = context.user_data.get("support_reply_target")
    if not target_user_id:
        await update.message.reply_text("❌ خطا: کاربر مقصد مشخص نیست.")
        return ConversationHandler.END
    
    text = update.message.text
    admin_user = update.effective_user
    
    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=(
                f"📨 پاسخ پشتیبانی:\n\n"
                f"{text}\n\n"
                f"— {admin_user.first_name} (پشتیبانی)"
            ),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💬 ادامه مکالمه", callback_data="support:open")
            ]])
        )
        await update.message.reply_text("✅ پاسخ به کاربر ارسال شد.")
    except Exception as e:
        logger.warning(f"Could not send reply to user {target_user_id}: {e}")
        await update.message.reply_text(f"❌ ارسال ناموفق: {e}")
    
    context.user_data.pop("support_reply_target", None)
    return ConversationHandler.END


async def admin_support_reply_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel admin reply."""
    query = update.callback_query
    if query:
        await query.answer()
        await render_view(query, context, "❌ لغو شد.", None)
    context.user_data.pop("support_reply_target", None)
    return ConversationHandler.END


# === Admin view: list support messages ===

async def admin_support_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of recent support messages for admin."""
    query = update.callback_query
    await query.answer()
    
    # For now, show a placeholder - we'd need a way to track support messages
    # Since we don't persist them separately, we can show a note
    text = (
        "📨 پیام‌های پشتیبانی\\n\\n"
        "پیام‌های پشتیبانی در حال حاضر در چت ادمین‌ها فوروارد می‌شوند.\\n"
        "برای پاسخ دادن، روی دکمه <b>💬 پاسخ</b> در پیام فوروارد شده کلیک کنید.\\n\\n"
        "📋 لیست پیام‌های اخیر:\n"
        "— (پیام‌ها در تاریخچه چت ادمین‌ها قابل مشاهده‌اند)"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="admin:panel")],
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
