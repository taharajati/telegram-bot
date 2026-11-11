"""
سیستم پیام‌رسانی خریدار-فروشنده.
خریدار می‌تونه از داخل جزئیات سفارش پیام بده، فروشنده اینباکس داره.
"""
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler

from database.db import async_session
from database.models import (
    Order,
    OrderStatus,
    Shop,
    ShopOwner,
    Conversation,
    Message,
    utcnow,
)
from sqlalchemy import select
from utils.helpers import format_price, to_jalali

logger = logging.getLogger(__name__)

# ── Conversation states ──
ASK_MESSAGE = range(1, 2)


# ─────────────── Helpers ───────────────


async def _get_or_create_conv(buyer_id: int, shop_id: int, order_id: int | None = None) -> int:
    """Get existing open conversation or create a new one. Returns conversation id."""
    from sqlalchemy import select
    async with async_session() as session:
        stmt = select(Conversation).where(
            Conversation.buyer_id == buyer_id,
            Conversation.shop_id == shop_id,
            Conversation.status == "open",
        )
        if order_id:
            stmt = stmt.where(Conversation.order_id == order_id)
        result = await session.execute(stmt.order_by(Conversation.updated_at.desc()).limit(1))
        conv = result.scalar_one_or_none()
        if conv:
            conv.order_id = conv.order_id or order_id
            await session.commit()
            conv_id = conv.id
        else:
            conv = Conversation(
                buyer_id=buyer_id,
                shop_id=shop_id,
                order_id=order_id,
                status="open",
            )
            session.add(conv)
            await session.commit()
            await session.refresh(conv)
            conv_id = conv.id
    return conv_id


async def _count_unread(shop_id: int) -> int:
    """Number of unread messages across all conversations for this shop."""
    from sqlalchemy import select, func as sf
    async with async_session() as session:
        result = await session.execute(
            select(sf.count(Message.id))
            .select_from(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(
                Conversation.shop_id == shop_id,
                Message.sender_role == "buyer",
                Message.read_at.is_(None),
            )
        )
        return result.scalar() or 0


async def _mark_read(conv_id: int):
    """Mark all buyer messages as read."""
    from sqlalchemy import update as sql_update
    async with async_session() as session:
        await session.execute(
            sql_update(Message)
            .where(
                Message.conversation_id == conv_id,
                Message.sender_role == "buyer",
                Message.read_at.is_(None),
            )
            .values(read_at=utcnow())
        )
        await session.commit()


# ─────────────── Buyer side ───────────────


async def open_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دکمه 💬 پیام به فروشنده در جزئیات سفارش."""
    query = update.callback_query
    await query.answer()
    _, _, order_id = query.data.split(":")
    order_id = int(order_id)
    buyer_id = update.effective_user.id

    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order or order.user_id != buyer_id:
            await query.edit_message_text("❌ سفارش پیدا نشد.")
            return

        conv_id = await _get_or_create_conv(buyer_id, order.shop_id, order_id)
        context.user_data["conv_id"] = conv_id
        context.user_data["conv_shop_id"] = order.shop_id
        context.user_data["conv_buyer_id"] = buyer_id

    await _show_conversation(query, context, conv_id, buyer_role=True)
    return ASK_MESSAGE


async def _build_conversation_view(conv_id: int, buyer_role: bool) -> tuple[str, InlineKeyboardMarkup | None]:
    """Build conversation text and keyboard without sending. Returns (text, keyboard)."""
    from sqlalchemy import select
    async with async_session() as session:
        conv = await session.get(Conversation, conv_id)
        if not conv:
            return "❌ مکالمه یافت نشد.", None

        rows = await session.execute(
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at.asc())
        )
        messages = rows.scalars().all()

    lines = ["💬 مکالمه با فروشگاه", ""]
    for msg in messages:
        who = "🧑 شما" if (buyer_role and msg.sender_role == "buyer") else\
              "🧑 مشتری" if (not buyer_role and msg.sender_role == "buyer") else "👤 فروشنده"
        ts = to_jalali(msg.created_at)
        lines.append(f"{who} — {ts}")
        lines.append(msg.content)
        if msg.has_attachment and msg.attachment_file_id:
            lines.append("📎 فایل ضمیمه شده")
        lines.append("")

    if not messages:
        lines.append("هنوز پیامی ارسال نشده. اولین پیامت رو بنویس 👇")

    text = "\n".join(lines)

    if buyer_role:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ نوشتن پیام", callback_data=f"msg:send:{conv_id}")],
            [InlineKeyboardButton("🔙 بازگشت به سفارش", callback_data=f"order:detail:{conv.order_id or 0}")],
        ])
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ پاسخ", callback_data=f"msg:reply:{conv_id}")],
            [InlineKeyboardButton("🔙 بازگشت به اینباکس", callback_data="seller:inbox")],
        ])

    return text, keyboard


async def _show_conversation(query, context, conv_id: int, buyer_role: bool):
    """Show the conversation history + reply button (legacy wrapper)."""
    text, keyboard = await _build_conversation_view(conv_id, buyer_role)
    if keyboard is None:
        await query.edit_message_text(text)
        return
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def start_send_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start writing a message (buyer or seller)."""
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    action = parts[1]  # send or reply
    conv_id = int(parts[2])
    context.user_data["conv_id_writing"] = conv_id

    await query.edit_message_text(
        "✏️ پیامت رو بنویس (یا /cancel برای لغو):"
        if action == "send" else
        "✏️ پاسخت رو بنویس (یا /cancel برای لغو):"
    )
    return ASK_MESSAGE


async def save_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save a text message from buyer or seller."""
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("❌ پیامت خالیه. یه متن بنویس و بفرست:")
        return ASK_MESSAGE

    conv_id = context.user_data.get("conv_id_writing")
    buyer_id = update.effective_user.id
    if not conv_id:
        await update.message.reply_text("❌ مکالمه یافت نشد.")
        return ConversationHandler.END

    async with async_session() as session:
        conv = await session.get(Conversation, conv_id)
        if not conv:
            await update.message.reply_text("❌ مکالمه یافت نشد.")
            return ConversationHandler.END

        # Determine who is sending
        if conv.buyer_id == buyer_id:
            role = "buyer"
        else:
            # Check if user is an owner of this shop
            from sqlalchemy import select
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
        shop: Shop | None = await session.get(Shop, conv.shop_id) if conv else None
    if conv:
        if role == "buyer":
            # Notify seller
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
            # Notify buyer
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
    # Show conversation again
    text, keyboard = await _build_conversation_view(conv_id, buyer_role=(role == "buyer"))
    if keyboard:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await update.message.reply_text(text)
    return ConversationHandler.END


async def cancel_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("conv_id_writing", None)
    await update.message.reply_text("❌ پیام لغو شد.")
    return ConversationHandler.END


# ─────────────── Seller inbox ───────────────


async def seller_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش اینباکس فروشنده — لیست مکالمات باز با خریداران."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    from sqlalchemy import select, func as sf

    async with async_session() as session:
        owner = await session.execute(
            select(ShopOwner).where(ShopOwner.user_id == user_id)
        )
        owner = owner.scalar_one_or_none()
        if not owner:
            await query.edit_message_text("❌ شما فروشنده نیستید.")
            return
        shop_id = owner.shop_id

        # Get all open conversations for this shop
        conv_rows = await session.execute(
            select(Conversation).where(
                Conversation.shop_id == shop_id,
                Conversation.status == "open",
            ).order_by(Conversation.updated_at.desc())
        )
        conversations = conv_rows.scalars().all()

    if not conversations:
        text = "📭 اینباکس پیام‌ها\n\nهیچ پیامی از خریداران ندارید."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="admin:panel")],
        ])
    else:
        from database.models import User
        lines = ["📬 اینباکس پیام‌ها", "برای مشاهده کلیک کن:\n"]
        buttons = []
        async with async_session() as session:
            for conv in conversations:
                # Get buyer info
                buyer = await session.get(User, conv.buyer_id)
                buyer_name = buyer.first_name or f"کاربر {conv.buyer_id}" if buyer else f"کاربر {conv.buyer_id}"

                # Count unread
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
        buttons.append([InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="admin:panel")])
        keyboard = InlineKeyboardMarkup(buttons)

    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def seller_open_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فروشنده یک مکالمه رو باز می‌کنه."""
    query = update.callback_query
    await query.answer()
    _, _, conv_id = query.data.split(":")
    conv_id = int(conv_id)

    user_id = update.effective_user.id
    async with async_session() as session:
        owner = await session.execute(
            select(ShopOwner).where(ShopOwner.user_id == user_id)
        )
        owner = owner.scalar_one_or_none()
        if not owner:
            await query.edit_message_text("❌ شما فروشنده نیستید.")
            return
        conv = await session.get(Conversation, conv_id)
        if not conv or conv.shop_id != owner.shop_id:
            await query.edit_message_text("❌ دسترسی ندارید.")
            return

    # Mark messages as read
    await _mark_read(conv_id)
    context.user_data["conv_id"] = conv_id
    context.user_data["conv_shop_id"] = conv.shop_id
    context.user_data["conv_buyer_id"] = conv.buyer_id

    await _show_conversation(query, context, conv_id, buyer_role=False)


# ─────────────── Main entry: add button to order detail ───────────────


def add_message_button_to_order(order_detail_text: str) -> InlineKeyboardMarkup:
    """This is no longer needed — button is added in _show_conversation context."""
    return None
