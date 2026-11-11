"""
افزودن محصول با فوروارد کردن چند پیام همزمان.
فروشنده پیام‌های کانال/چت رو فوروارد می‌کنه → بات متن/عکس می‌گیره →
برای هر پیام: قیمت + دسته‌بندی می‌پرسه → خلاصه + ذخیره همه.
"""
from dataclasses import dataclass, field
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from sqlalchemy import select

from database.db import async_session
from database.models import Category, Product, ProductImage
from handlers.admin.panel import admin_only, _get_shop_id_for_admin
from utils.helpers import format_price
from utils.tg_helpers import render_view

ASK_MESSAGES, ASK_PRICE_CAT, ASK_PRICE, ASK_CATEGORY, CONFIRM_ALL = range(5)

FORWARD_QUEUE_KEY = "forward_products_queue"
CURRENT_INDEX_KEY = "forward_current_idx"
PRODUCTS_TO_SAVE_KEY = "forward_products_to_save"


@dataclass
class ForwardedItem:
    """One forwarded message to become a product."""
    text: str = ""
    image_file_ids: list = field(default_factory=list)
    media_group_id: Optional[str] = None
    has_video: bool = False
    price: Optional[float] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None


async def _get_shop_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    shop_id = context.user_data.get("admin_shop_id")
    if shop_id:
        return shop_id
    # CallbackQuery doesn't have effective_user — use from_user
    user_id = getattr(update, 'effective_user', None) and update.effective_user.id
    if not user_id and hasattr(update, 'from_user'):
        user_id = update.from_user.id
    if not user_id:
        return None
    return await _get_shop_id_for_admin(user_id)


async def _get_categories(shop_id: int) -> list[Category]:
    async with async_session() as session:
        result = await session.execute(
            select(Category).where(Category.shop_id == shop_id).order_by(Category.name)
        )
        return result.scalars().all()


def _format_item_summary(item: ForwardedItem, idx: int, total: int) -> str:
    lines = [
        f"📦 آیتم {idx + 1} از {total}",
        f"📝 متن: {(item.text[:100] + '...') if item.text and len(item.text) > 100 else (item.text or '—')}",
        f"🖼 {len(item.image_file_ids)} عکس{' 🎬 + ویدیو' if item.has_video else ''}",
        f"💰 قیمت: {format_price(item.price) if item.price else '❌ (منتظر)'}",
        f"📁 دسته: {item.category_name or '❌ (منتظر)'}",
    ]
    return "\n".join(lines)


def _is_forwarded(msg) -> bool:
    """Check if a message was forwarded from somewhere."""
    if msg is None:
        return False
    return getattr(msg, "forward_origin", None) is not None or getattr(msg, "forward_from", None) is not None


async def start_add_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point: seller clicks 'افزودن با فوروارد'."""
    query = update.callback_query
    await query.answer()

    shop_id = await _get_shop_id(update, context)
    if not shop_id:
        await render_view(query, context, "❌ فروشگاه مشخص نیست.", InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin:panel")]
        ]))
        return ConversationHandler.END

    categories = await _get_categories(shop_id)
    if not categories:
        await render_view(query, context,
            "⚠️ قبل از افزودن محصول، باید دسته‌بندی بسازید!\n\n"
            "اول از بخش «مدیریت دسته‌بندی‌ها» یه دسته بسازید، بعدش برگردید.",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="admin:panel")]])
        )
        return ConversationHandler.END

    context.user_data[FORWARD_QUEUE_KEY] = []
    context.user_data[CURRENT_INDEX_KEY] = 0
    context.user_data[PRODUCTS_TO_SAVE_KEY] = []

    await render_view(query, context,
        "📤 افزودن محصول با فوروارد\n\n"
        "پیام‌های کانال/چت رو اینجا فوروارد کنید (هرچندتا خواستید).\n"
        "می‌تونید متن، عکس، یا هر دو بفرستید.\n\n"
        "✅ وقتی تموم شد، دکمه «تمام شد، ادامه» رو بزنید.",
        InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ تمام شد، ادامه", callback_data="fwd:done_collecting")],
            [InlineKeyboardButton("❌ انصراف", callback_data="fwd:cancel_all")],
        ])
    )
    return ASK_MESSAGES


async def collect_forwarded(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collect each forwarded message."""
    if not update.message:
        return ASK_MESSAGES

    msg = update.message

    # Only accept forwarded messages
    if not _is_forwarded(msg):
        await msg.reply_text(
            "⚠️ لطفاً فقط پیام فوروارد شده بفرستید.\n"
            "روی پیام مورد نظر در کانال/چت بزنید → Forward → اینجا بفرستید.",
            parse_mode="HTML"
        )
        return ASK_MESSAGES

    text = msg.text or msg.caption or ""
    image_file_id = msg.photo[-1].file_id if msg.photo else None
    video_file_id = msg.video.file_id if msg.video else None
    media_group_id = msg.media_group_id

    if not text and not image_file_id and not video_file_id:
        await msg.reply_text("⚠️ این پیام نه متن داره نه عکس/ویدیو، پس نادیده گرفته می‌شه.")
        return ASK_MESSAGES

    queue = context.user_data.get(FORWARD_QUEUE_KEY, [])

    # اگر همون آلبوم آیتم قبلیه (media_group_id یکسان)، عکس رو بهش اضافه کن
    if media_group_id and queue and queue[-1].media_group_id == media_group_id:
        if image_file_id:
            queue[-1].image_file_ids.append(image_file_id)
        if text and not queue[-1].text:
            queue[-1].text = text.strip()
        if video_file_id and not queue[-1].has_video:
            queue[-1].has_video = True
        img_count = len(queue[-1].image_file_ids)
        await msg.reply_text(f"✅ عکس اضافه شد به آیتم {len(queue)} (مجموع {img_count} عکس{' + ویدیو' if queue[-1].has_video else ''})")
        context.user_data[FORWARD_QUEUE_KEY] = queue
        return ASK_MESSAGES

    item = ForwardedItem(
        text=text.strip(),
        image_file_ids=[image_file_id] if image_file_id else [],
        media_group_id=media_group_id,
        has_video=bool(video_file_id),
    )
    queue.append(item)
    context.user_data[FORWARD_QUEUE_KEY] = queue

    await msg.reply_text(f"✅ ذخیره شد ({len(queue)} آیتم). پیام بعدی رو فوروارد کن یا «تمام شد» رو بزن.")
    return ASK_MESSAGES


async def done_collecting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User clicked 'تمام شد' — start asking price/category for each item."""
    query = update.callback_query
    await query.answer()

    queue = context.user_data.get(FORWARD_QUEUE_KEY, [])
    if not queue:
        await render_view(query, context,
            "❌ هیچ پیامی فوروارد نشده. حداقل یکی بفرستید.",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:products:add")]])
        )
        return ASK_MESSAGES

    context.user_data[CURRENT_INDEX_KEY] = 0
    context.user_data[PRODUCTS_TO_SAVE_KEY] = queue
    return await _ask_price_for_current(query, context)


async def _ask_price_for_current(query_or_update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for price of the current item in queue."""
    idx = context.user_data.get(CURRENT_INDEX_KEY, 0)
    queue = context.user_data.get(PRODUCTS_TO_SAVE_KEY, [])

    if idx >= len(queue):
        context.user_data[CURRENT_INDEX_KEY] = 0
        return await _ask_category_for_current(query_or_update, context)

    item = queue[idx]
    preview = (item.text[:200] + '...') if item.text and len(item.text) > 200 else (item.text or '—')
    media_info = f"{len(item.image_file_ids)} عکس" if item.image_file_ids else "بدون عکس"
    if item.has_video:
        media_info += " + 🎬 ویدیو"
    text = (
        f"💰 قیمت برای آیتم {idx + 1} از {len(queue)}\n\n"
        f"📝 پیش‌نمایش متن:\n{preview}\n"
        f"🖼 {media_info}\n\n"
        "قیمت رو به تومان و فقط با عدد بفرستید (مثال: 150000):"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭ رد کن (بدون قیمت)", callback_data="fwd:skip_price")],
        [InlineKeyboardButton("❌ انصراف از همه", callback_data="fwd:cancel_all")],
    ])

    if hasattr(query_or_update, "edit_message_text"):
        await render_view(query_or_update, context, text, kb)
    else:
        await query_or_update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

    return ASK_PRICE


async def _ask_category_for_current(query_or_update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for category of the current item in queue."""
    idx = context.user_data.get(CURRENT_INDEX_KEY, 0)
    queue = context.user_data.get(PRODUCTS_TO_SAVE_KEY, [])

    if idx >= len(queue):
        return await _show_summary(query_or_update, context)

    item = queue[idx]
    shop_id = await _get_shop_id(query_or_update, context)
    categories = await _get_categories(shop_id) if shop_id else []

    if not categories:
        await render_view(query_or_update, context,
            "❌ هیچ دسته‌بندی‌ای پیدا نشد.",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:products:add")]])
        )
        return ConversationHandler.END

    rows = [[InlineKeyboardButton(c.name, callback_data=f"fwd:cat:{c.id}")] for c in categories]
    rows.append([InlineKeyboardButton("⏭ رد کن (بدون دسته)", callback_data="fwd:skip_cat")])
    rows.append([InlineKeyboardButton("❌ انصراف از همه", callback_data="fwd:cancel_all")])

    price_str = format_price(item.price) if item.price else "—"
    text = (
        f"📁 دسته‌بندی برای آیتم {idx + 1} از {len(queue)}\n\n"
        f"💰 قیمت: {price_str}\n"
        "دسته‌بندی رو انتخاب کن:"
    )

    if hasattr(query_or_update, "edit_message_text"):
        await render_view(query_or_update, context, text, InlineKeyboardMarkup(rows))
    else:
        await query_or_update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(rows), parse_mode="HTML")

    return ASK_CATEGORY


async def receive_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User sent a price number."""
    raw = update.message.text.strip().replace(",", "").replace("٬", "")
    if not raw.isdigit():
        await update.message.reply_text("❌ فقط عدد بفرستید (مثال: 150000).")
        return ASK_PRICE

    idx = context.user_data.get(CURRENT_INDEX_KEY, 0)
    queue = context.user_data.get(PRODUCTS_TO_SAVE_KEY, [])
    queue[idx].price = float(raw)

    context.user_data[CURRENT_INDEX_KEY] = idx + 1
    return await _ask_price_for_current(update, context)


async def skip_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip price for current item."""
    query = update.callback_query
    await query.answer()
    idx = context.user_data.get(CURRENT_INDEX_KEY, 0)
    context.user_data[CURRENT_INDEX_KEY] = idx + 1
    return await _ask_price_for_current(query, context)


async def receive_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User selected a category."""
    query = update.callback_query
    await query.answer()

    cat_id = int(query.data.split(":")[2])
    async with async_session() as session:
        cat = await session.get(Category, cat_id)
        cat_name = cat.name if cat else "نامشخص"

    idx = context.user_data.get(CURRENT_INDEX_KEY, 0)
    queue = context.user_data.get(PRODUCTS_TO_SAVE_KEY, [])
    queue[idx].category_id = cat_id
    queue[idx].category_name = cat_name

    context.user_data[CURRENT_INDEX_KEY] = idx + 1
    return await _ask_category_for_current(query, context)


async def skip_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip category for current item."""
    query = update.callback_query
    await query.answer()
    idx = context.user_data.get(CURRENT_INDEX_KEY, 0)
    context.user_data[CURRENT_INDEX_KEY] = idx + 1
    return await _ask_category_for_current(query, context)


async def _show_summary(query_or_update, context: ContextTypes.DEFAULT_TYPE):
    """Show summary of all items before final save."""
    queue = context.user_data.get(PRODUCTS_TO_SAVE_KEY, [])

    lines = ["📋 خلاصه محصولات برای ذخیره\n"]
    for i, item in enumerate(queue):
        lines.append(_format_item_summary(item, i, len(queue)))

    text = "\n\n".join(lines)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💾 ذخیره همه", callback_data="fwd:save_all")],
        [InlineKeyboardButton("✏️ ویرایش آیتم", callback_data="fwd:edit_item")],
        [InlineKeyboardButton("❌ انصراف", callback_data="fwd:cancel_all")],
    ])

    if hasattr(query_or_update, "edit_message_text"):
        await render_view(query_or_update, context, text, kb)
    else:
        await query_or_update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

    return CONFIRM_ALL


async def save_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save all products to database."""
    query = update.callback_query
    await query.answer()

    queue = context.user_data.get(PRODUCTS_TO_SAVE_KEY, [])
    shop_id = await _get_shop_id(query, context)
    if not shop_id:
        await render_view(query, context, "❌ فروشگاه مشخص نیست.", InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin:panel")]
        ]))
        return ConversationHandler.END

    saved = 0
    skipped = 0
    async with async_session() as session:
        for item in queue:
            if not item.price or not item.category_id:
                skipped += 1
                continue

            product = Product(
                name=item.text[:150] if item.text else "محصول بدون نام",
                description=item.text if item.text and len(item.text) > 150 else None,
                price=item.price,
                category_id=item.category_id,
                stock=0,
                image_file_id=item.image_file_ids[0] if item.image_file_ids else None,
                shop_id=shop_id,
                is_active=True,
            )
            session.add(product)
            await session.flush()

            # Save additional images
            for i, fid in enumerate(item.image_file_ids):
                if i == 0:
                    continue  # first is already in Product.image_file_id
                session.add(ProductImage(
                    product_id=product.id,
                    file_id=fid,
                    sort_order=i,
                ))

            saved += 1
        await session.commit()

    context.user_data.pop(FORWARD_QUEUE_KEY, None)
    context.user_data.pop(CURRENT_INDEX_KEY, None)
    context.user_data.pop(PRODUCTS_TO_SAVE_KEY, None)

    msg = f"✅ {saved} محصول ذخیره شد"
    if skipped:
        msg += f"\n⚠️ {skipped} آیتم رد شد (بدون قیمت/دسته)"
    if saved > 0:
        msg += "\n\n⚠️ موجودی همه روی ۰ ست شده — قبل از اینکه مشتری ببینشون، از لیست محصولات موجودی هرکدوم رو تنظیم کن."

    await render_view(query, context, msg, InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 لیست محصولات", callback_data="admin:products:list:0")],
        [InlineKeyboardButton("➕ افزودن با فوروارد", callback_data="admin:products:add_forward")],
        [InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin:panel")],
    ]))
    return ConversationHandler.END


async def edit_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Let user pick which item to re-edit."""
    query = update.callback_query
    await query.answer()

    queue = context.user_data.get(PRODUCTS_TO_SAVE_KEY, [])
    rows = []
    for i, item in enumerate(queue):
        label = (item.text[:30] + "...") if item.text and len(item.text) > 30 else (item.text or "⚠️ بدون متن")
        price_str = format_price(item.price) if item.price else "—"
        cat_str = item.category_name or "—"
        rows.append([InlineKeyboardButton(
            f"{i+1}. {label} | {price_str} | {cat_str}",
            callback_data=f"fwd:reedit:{i}"
        )])
    rows.append([InlineKeyboardButton("🔙 بازگشت به خلاصه", callback_data="fwd:back_to_summary")])

    await render_view(query, context, "✏️ کدوم آیتم رو می‌خواید ویرایش کنید؟", InlineKeyboardMarkup(rows))
    return CONFIRM_ALL


async def reedit_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Re-edit a specific item."""
    query = update.callback_query
    await query.answer()

    idx = int(query.data.split(":")[2])
    context.user_data[CURRENT_INDEX_KEY] = idx
    return await _ask_price_for_current(query, context)


async def back_to_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to summary from edit menu."""
    query = update.callback_query
    await query.answer()
    return await _show_summary(query, context)


async def cancel_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel everything and cleanup."""
    query = update.callback_query
    await query.answer()

    context.user_data.pop(FORWARD_QUEUE_KEY, None)
    context.user_data.pop(CURRENT_INDEX_KEY, None)
    context.user_data.pop(PRODUCTS_TO_SAVE_KEY, None)

    await render_view(query, context, "❌ لغو شد.",
        InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ افزودن با فوروارد", callback_data="admin:products:add_forward")],
            [InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin:panel")],
        ])
    )
    return ConversationHandler.END


def get_forward_products_conversation() -> ConversationHandler:
    """ConversationHandler for forward-based product creation."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_add_forward, pattern="^admin:products:add_forward$"),
        ],
        states={
            ASK_MESSAGES: [
                MessageHandler(filters.ALL & ~filters.COMMAND, collect_forwarded),
                CallbackQueryHandler(done_collecting, pattern="^fwd:done_collecting$"),
                CallbackQueryHandler(cancel_all, pattern="^fwd:cancel_all$"),
            ],
            ASK_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_price),
                CallbackQueryHandler(skip_price, pattern="^fwd:skip_price$"),
                CallbackQueryHandler(cancel_all, pattern="^fwd:cancel_all$"),
            ],
            ASK_CATEGORY: [
                CallbackQueryHandler(receive_category, pattern="^fwd:cat:"),
                CallbackQueryHandler(skip_category, pattern="^fwd:skip_cat$"),
                CallbackQueryHandler(cancel_all, pattern="^fwd:cancel_all$"),
            ],
            CONFIRM_ALL: [
                CallbackQueryHandler(save_all, pattern="^fwd:save_all$"),
                CallbackQueryHandler(edit_item, pattern="^fwd:edit_item$"),
                CallbackQueryHandler(reedit_item, pattern="^fwd:reedit:"),
                CallbackQueryHandler(back_to_summary, pattern="^fwd:back_to_summary$"),
                CallbackQueryHandler(cancel_all, pattern="^fwd:cancel_all$"),
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel_all, pattern="^fwd:cancel_all$")],
        name="forward_products_conversation",
        persistent=False,
    )