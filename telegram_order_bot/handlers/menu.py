"""نمایش دسته‌بندی‌ها → محصولات هر دسته (با صفحه‌بندی) → جزئیات یک محصول — چندمستأجری."""
import math

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
from telegram.ext import ContextTypes
from sqlalchemy import select

import config
from database.db import async_session
from database.models import Category, Product, ProductImage
from handlers.subscription_decorator import require_active_subscription
from utils.helpers import format_price
from utils.tg_helpers import get_current_shop_id, render_view


@require_active_subscription
async def show_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی اصلی فروشگاه (برای دکمه 'مشاهده محصولات' بعد از لغو / cancel)."""
    query = update.callback_query
    if query:
        await query.answer()
    
    # Check if shop_id is in callback data (e.g., "menu:shop:123")
    if query and query.data.startswith("menu:shop:"):
        parts = query.data.split(":")
        if len(parts) >= 3:
            try:
                shop_id = int(parts[2])
                context.user_data["current_shop_id"] = shop_id
            except (ValueError, IndexError):
                pass
    
    await show_categories(update, context)


@require_active_subscription
async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    shop_id = await get_current_shop_id(update)
    if not shop_id:
        text = "برای دیدن محصولات، اول باید از لینک یه فروشگاه واردش بشی."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 شروع", callback_data="nav:main")]])
        if query:
            await render_view(query, context, text, keyboard)
        else:
            await update.message.reply_text(text, reply_markup=keyboard)
        return

    async with async_session() as session:
        result = await session.execute(
            select(Category).where(Category.shop_id == shop_id).order_by(Category.name)
        )
        categories = result.scalars().all()

    if not categories:
        text = ("❌ هنوز دسته‌بندی‌ای ثبت نشده.\n\n"
                "اگه فروشنده‌ای، از پنل مدیریت (/myshop) → مدیریت دسته‌بندی‌ها بساز.")
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="nav:main")]])
    else:
        text = "🗂 یکی از دسته‌بندی‌های زیر رو انتخاب کن:"
        rows = [[InlineKeyboardButton(cat.name, callback_data=f"cat:open:{cat.id}:0")] for cat in categories]
        rows.append([InlineKeyboardButton("🔍 جستجوی محصول", callback_data="search:ask")])
        rows.append([InlineKeyboardButton("❤️ علاقه‌مندی‌ها", callback_data="wishlist:view")])
        rows.append([InlineKeyboardButton("🔙 منوی اصلی", callback_data="nav:main")])
        keyboard = InlineKeyboardMarkup(rows)

    if query:
        await render_view(query, context, text, keyboard)
    else:
        await update.message.reply_text(text, reply_markup=keyboard)


@require_active_subscription
async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split(":")
    if data[1] == "open":
        _, _, cat_id, page = data[:4]
        cat_id, page = int(cat_id), int(page)
    shop_id = await get_current_shop_id(update)
    if not shop_id:
        await render_view(query, context, "لطفاً ابتدا با لینک فروشگاه وارد شوید.",
                          InlineKeyboardMarkup([[InlineKeyboardButton("🏠 شروع", callback_data="nav:main")]]))
        return

    async with async_session() as session:
        stmt = select(Product).where(
            Product.shop_id == shop_id,
            Product.category_id == cat_id,
            Product.is_active == True,
        ).order_by(Product.id.desc())

        only_available = context.user_data.get("only_available", False)
        if only_available:
            stmt = stmt.where(Product.stock > Product.reserved_stock)
        result = await session.execute(stmt)
        products = result.scalars().all()

        cat_result = await session.execute(select(Category).where(Category.id == cat_id))
        cat = cat_result.scalar_one_or_none()
        cat_name = cat.name if cat else "نامشخص"

    if not products:
        await render_view(query, context,
            f"❌ فعلاً هیچ محصولی تو دسته‌بندی «{cat_name}» نیست.",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 دسته‌بندی‌ها", callback_data="cat:list")]])
        )
        return

    per_page = config.ITEMS_PER_PAGE
    total_pages = max(1, math.ceil(len(products) / per_page))
    page = max(0, min(page, total_pages - 1))
    page_items = products[page * per_page : (page + 1) * per_page]

    lines = [f"📁 {cat_name} (صفحه {page + 1}/{total_pages})",
             f"🔢 {len(products)} محصول", ""]

    text = "\n".join(lines)

    rows = []
    for p in page_items:
        rows.append([InlineKeyboardButton(
            f"🛒 {p.name} — {format_price(p.price)}",
            callback_data=f"prod:open:{p.id}:{cat_id}:{page}"
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ صفحه قبل", callback_data=f"cat:open:{cat_id}:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("صفحه بعد ▶️", callback_data=f"cat:open:{cat_id}:{page + 1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton("🔙 دسته‌بندی‌ها", callback_data="cat:list")])

    await render_view(query, context, text, InlineKeyboardMarkup(rows))


@require_active_subscription
async def show_product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    product_id = int(parts[2])
    cat_id = int(parts[3]) if len(parts) > 3 else None
    page = int(parts[4]) if len(parts) > 4 else 0

    async with async_session() as session:
        stmt = select(Product).where(Product.id == product_id, Product.is_active == True)
        product = (await session.execute(stmt)).scalar_one_or_none()
        if not product:
            await render_view(query, context,
                "❌ این محصول پیدا نشد یا حذف شده. برگرد به دسته‌بندی‌ها و بقیه محصولات رو ببین.",
                InlineKeyboardMarkup([[InlineKeyboardButton("🔙 دسته‌بندی‌ها", callback_data="cat:list")]])
            )
            return

        imgs = await session.execute(
            select(ProductImage).where(ProductImage.product_id == product_id).order_by(ProductImage.sort_order)
        )
        extra_images = imgs.scalars().all()

    in_stock = product.available_stock > 0
    stock_status = "✅ موجود در انبار" if in_stock else "❌ ناموجود"
    text = (
        f"{product.name}\n\n"
        f"{product.description or ''}\n\n"
        f"💰 قیمت: {format_price(product.price)}\n"
        f"{stock_status}"
    )

    rows = []
    if in_stock:
        rows.append([InlineKeyboardButton("🛒 افزودن به سبد خرید", callback_data=f"cart:add:{product.id}")])
    else:
        rows.append([InlineKeyboardButton("🔔 بهم خبر بده", callback_data=f"restock:sub:{product.id}")])
    rows.append([InlineKeyboardButton("⭐️ علاقه‌مندی", callback_data=f"wishlist:toggle:{product.id}:{cat_id}:{page}")])

    back_data = f"cat:open:{cat_id}:{page}" if cat_id else "cat:list"
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data=back_data)])
    keyboard = InlineKeyboardMarkup(rows)

    # ── Build full image list (main photo + gallery) ──
    # image_ids: real Telegram file_ids (usable directly)
    # image_urls: web paths to fetch and send as photo documents
    image_ids = []
    image_urls = []
    if product.image_file_id:
        image_ids.append(product.image_file_id)
    elif product.image_url:
        # New-style uploads store a web path (e.g. /api/product-image-file/xxx.jpg)
        if product.image_url.startswith('http'):
            image_urls.append(product.image_url)
        else:
            image_urls.append(config.WEBSITE_URL + product.image_url)
    for img in extra_images:
        if img.file_id and img.file_id.startswith(('AgA', 'BAAC', 'http')):
            image_ids.append(img.file_id)
        elif img.local_url:
            # عکس‌هایی که از سایت یا ایمپورت اضافه شدن file_id تلگرام ندارن؛ از آدرس وب فرستاده می‌شن
            image_urls.append(img.local_url if img.local_url.startswith('http') else config.WEBSITE_URL + img.local_url)

    chat_id = query.message.chat_id

    # Delete old message (list was text, now we may send photos)
    try:
        await query.message.delete()
    except Exception:
        pass

    if image_ids or image_urls:
        # Send all images as an album (Telegram limit: 10)
        media_group = []
        # First item: prefer real Telegram file_id, else fetch from web URL
        if image_ids:
            media_group.append(InputMediaPhoto(media=image_ids[0], caption=text, parse_mode=None))
        elif image_urls:
            url = image_urls.pop(0)
            try:
                media_group.append(InputMediaPhoto(media=url, caption=text, parse_mode=None))
            except Exception:
                media_group.append(InputMediaPhoto(media=image_ids[0] if image_ids else url, caption=text, parse_mode=None))
        # Remaining real file_ids
        for fid in image_ids[1:10]:  # cap at 10
            media_group.append(InputMediaPhoto(media=fid))
        # Remaining web URLs
        for url in image_urls[:9]:
            try:
                media_group.append(InputMediaPhoto(media=url))
            except Exception:
                pass
        if media_group:
            await context.bot.send_media_group(chat_id=chat_id, media=media_group)
            # Buttons in a separate message (media groups can't carry reply_markup)
            await context.bot.send_message(chat_id=chat_id, text="⬇️ گزینه‌های محصول:", reply_markup=keyboard)
        else:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
    else:
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
