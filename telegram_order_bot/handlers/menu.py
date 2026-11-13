"""نمایش دسته‌بندی‌ها → محصولات هر دسته (با صفحه‌بندی) → جزئیات یک محصول — چندمستأجری."""
import logging
import math

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
from telegram.ext import ContextTypes
from sqlalchemy import case, func, select

import config
from database.db import async_session
from database.models import CartItem, Category, Product, ProductImage, Shop, WishlistItem
from handlers.subscription_decorator import require_active_subscription
from utils.helpers import format_price, short_price, to_persian_digits
from utils.tg_helpers import escape_html, get_current_shop_id, render_view

logger = logging.getLogger(__name__)



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


PRODUCTS_PER_PAGE = 8
SORTS = ("new", "cheap", "pricey")
SORT_LABELS = {"new": "جدیدترین", "cheap": "ارزان‌ترین", "pricey": "گران‌ترین"}
CAPTION_LIMIT = 1000  # سقف کپشن عکس در تلگرام ۱۰۲۴ کاراکتره


async def _cart_count(session, user_id: int, shop_id: int) -> int:
    total = (await session.execute(
        select(func.coalesce(func.sum(CartItem.quantity), 0)).where(
            CartItem.user_id == user_id, CartItem.shop_id == shop_id)
    )).scalar_one()
    return int(total or 0)


def nav_row(back_data: str, back_label: str = "🔙 بازگشت", cart_count: int = 0) -> list[InlineKeyboardButton]:
    """ردیف پایین همه‌ی صفحه‌های مشتری: برگشت، منوی فروشگاه، سبد خرید."""
    cart = f"🛒 سبد ({to_persian_digits(cart_count)})" if cart_count else "🛒 سبد"
    return [
        InlineKeyboardButton(back_label, callback_data=back_data),
        InlineKeyboardButton("🏠 منو", callback_data="nav:main"),
        InlineKeyboardButton(cart, callback_data="cart:view"),
    ]


def _shorten(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


async def build_products_view(shop_id: int, cat_id: int, page: int, user_id: int, user_data: dict):
    """متن و کیبورد لیست محصولات یک دسته؛ اگه دسته خالی باشه None برمی‌گردونه."""
    sort = user_data.get("sort", "new")
    only_available = user_data.get("only_available", False)

    async with async_session() as session:
        cat = (await session.execute(select(Category).where(Category.id == cat_id, Category.shop_id == shop_id))).scalar_one_or_none()
        stmt = select(Product).where(
            Product.shop_id == shop_id, Product.category_id == cat_id, Product.is_active == True)  # noqa: E712
        if only_available:
            stmt = stmt.where(Product.stock > Product.reserved_stock)
        sold_out_last = case((Product.stock > Product.reserved_stock, 0), else_=1)
        order = {"new": Product.id.desc(), "cheap": Product.price.asc(), "pricey": Product.price.desc()}[sort]
        products = (await session.execute(stmt.order_by(sold_out_last, order))).scalars().all()
        cart_count = await _cart_count(session, user_id, shop_id)

    cat_name = cat.name if cat else "محصولات"
    if not products:
        text = f"📁 {cat_name}\n\nاین دسته فعلاً محصولی نداره." + ("\nفیلتر «فقط موجودها» روشنه." if only_available else "")
        rows = []
        if only_available:
            rows.append([InlineKeyboardButton("🎚 نمایش همه", callback_data=f"cat:stock:{cat_id}")])
        rows.append(nav_row("cat:list", "🔙 دسته‌ها", cart_count))
        return text, InlineKeyboardMarkup(rows)

    total_pages = max(1, math.ceil(len(products) / PRODUCTS_PER_PAGE))
    page = max(0, min(page, total_pages - 1))
    page_items = products[page * PRODUCTS_PER_PAGE:(page + 1) * PRODUCTS_PER_PAGE]

    info = [f"{to_persian_digits(len(products))} محصول", f"مرتب‌شده: {SORT_LABELS[sort]}"]
    if only_available:
        info.append("فقط موجودها")
    text = f"📁 {cat_name}\n{' · '.join(info)}\n\nیکی رو انتخاب کن 👇"

    rows = []
    for p in page_items:
        sold_out = p.available_stock <= 0
        label = f"{'⛔ ' if sold_out else ''}{_shorten(p.name, 26)} · {short_price(p.price)}"
        rows.append([InlineKeyboardButton(label, callback_data=f"prod:open:{p.id}:{cat_id}:{page}")])

    rows.append([
        InlineKeyboardButton(f"↕️ {SORT_LABELS[sort]}", callback_data=f"cat:sort:{cat_id}"),
        InlineKeyboardButton("🎚 فقط موجود ✓" if only_available else "🎚 فقط موجود", callback_data=f"cat:stock:{cat_id}"),
    ])
    if total_pages > 1:
        pager = []
        if page > 0:
            pager.append(InlineKeyboardButton("◀️", callback_data=f"cat:open:{cat_id}:{page - 1}"))
        pager.append(InlineKeyboardButton(f"{to_persian_digits(page + 1)} از {to_persian_digits(total_pages)}", callback_data="noop"))
        if page < total_pages - 1:
            pager.append(InlineKeyboardButton("▶️", callback_data=f"cat:open:{cat_id}:{page + 1}"))
        rows.append(pager)
    rows.append(nav_row("cat:list", "🔙 دسته‌ها", cart_count))
    return text, InlineKeyboardMarkup(rows)


@require_active_subscription
async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split(":")
    action = data[1]
    try:
        cat_id = int(data[2])
        page = int(data[3]) if len(data) > 3 else 0
    except (IndexError, ValueError):
        await render_view(query, context, "این صفحه دیگه معتبر نیست.",
                          InlineKeyboardMarkup([nav_row("cat:list", "🔙 دسته‌ها")]))
        return

    if action == "sort":
        current = context.user_data.get("sort", "new")
        context.user_data["sort"] = SORTS[(SORTS.index(current) + 1) % len(SORTS)]
        page = 0
    elif action == "stock":
        context.user_data["only_available"] = not context.user_data.get("only_available", False)
        page = 0

    shop_id = await get_current_shop_id(update)
    if not shop_id:
        await render_view(query, context, "اول از لینک فروشگاه وارد شو.",
                          InlineKeyboardMarkup([[InlineKeyboardButton("🏠 شروع", callback_data="nav:main")]]))
        return

    text, keyboard = await build_products_view(shop_id, cat_id, page, update.effective_user.id, context.user_data)
    await render_view(query, context, text, keyboard)


# ─── صفحه‌ی محصول: یک عکس + کپشن + دکمه‌ها (بدون آلبوم و پیام جدا) ──────────

def product_photo_sources(product: Product, extra_images) -> list[str]:
    """عکس اصلی و گالری به‌ترتیب؛ file_id تلگرام ترجیح داده می‌شه و آدرس وب فقط جایگزینه."""
    def web(url):
        return url if url.startswith("http") else config.WEBSITE_URL + url

    sources: list[str] = []
    if product.image_file_id:
        sources.append(product.image_file_id)
    elif product.image_url:
        sources.append(web(product.image_url))
    for img in extra_images:
        if img.file_id and img.file_id.startswith(("AgA", "BAAC", "http")):
            sources.append(img.file_id)
        elif img.local_url:
            sources.append(web(img.local_url))
    return list(dict.fromkeys(sources))


def product_caption(product: Product, shop_name: str = "") -> str:
    available = product.available_stock
    if available <= 0:
        stock = "⛔ ناموجود"
    elif available <= 3:
        stock = f"⚡ فقط {to_persian_digits(available)} عدد مونده"
    else:
        stock = "✅ موجود"
    lines = [f"<b>{escape_html(product.name)}</b>", "", f"💰 {format_price(product.price)}", stock]
    if product.description:
        lines += ["", escape_html(_shorten(product.description, 420))]
    if shop_name:
        lines += ["", f"🏪 {escape_html(shop_name)}"]
    return "\n".join(lines)[:CAPTION_LIMIT]


def product_keyboard(product: Product, cat_id, page, cart_count: int = 0, photos: int = 1, idx: int = 0, wished: bool = False):
    cat_part = f"{cat_id or 0}:{page or 0}"
    rows = []
    if product.available_stock > 0:
        if cart_count:
            rows.append([InlineKeyboardButton("➕ یکی دیگه به سبد", callback_data=f"cart:add:{product.id}:{cat_part}")])
            rows.append([
                InlineKeyboardButton(f"🛒 سبد ({to_persian_digits(cart_count)})", callback_data="cart:view"),
                InlineKeyboardButton("✅ ثبت سفارش", callback_data="order:start"),
            ])
        else:
            rows.append([InlineKeyboardButton("🛒 افزودن به سبد", callback_data=f"cart:add:{product.id}:{cat_part}")])
    else:
        rows.append([InlineKeyboardButton("🔔 وقتی موجود شد خبرم کن", callback_data=f"restock:sub:{product.id}")])
    if photos > 1:
        rows.append([
            InlineKeyboardButton("◀️", callback_data=f"prod:img:{product.id}:{(idx - 1) % photos}:{cat_part}"),
            InlineKeyboardButton(f"📷 {to_persian_digits(idx + 1)} از {to_persian_digits(photos)}", callback_data="noop"),
            InlineKeyboardButton("▶️", callback_data=f"prod:img:{product.id}:{(idx + 1) % photos}:{cat_part}"),
        ])
    rows.append([
        InlineKeyboardButton("💔 از علاقه‌مندی‌ها حذف" if wished else "⭐ علاقه‌مندی", callback_data=f"wishlist:toggle:{product.id}:{cat_part}"),
        InlineKeyboardButton("💬 پرسش از فروشنده", callback_data="support:seller"),
    ])
    back = f"cat:open:{cat_id}:{page or 0}" if cat_id else "cat:list"
    rows.append(nav_row(back, "🔙 لیست", cart_count))
    return InlineKeyboardMarkup(rows)


async def load_product_screen(product_id: int, user_id: int, cat_id=None, page=0, idx: int = 0):
    """همه‌ی چیزهایی که برای نمایش صفحه‌ی محصول لازمه؛ اگه محصول نبود None."""
    async with async_session() as session:
        product = (await session.execute(
            select(Product).where(Product.id == product_id, Product.is_active == True))).scalar_one_or_none()  # noqa: E712
        if not product:
            return None
        extra = (await session.execute(
            select(ProductImage).where(ProductImage.product_id == product_id).order_by(ProductImage.sort_order))).scalars().all()
        shop = await session.get(Shop, product.shop_id)
        cart_count = await _cart_count(session, user_id, product.shop_id)
        wished = (await session.execute(select(WishlistItem.id).where(
            WishlistItem.user_id == user_id, WishlistItem.product_id == product_id))).first() is not None
    photos = product_photo_sources(product, extra)
    idx = idx % len(photos) if photos else 0
    return {
        "product": product,
        "photos": photos,
        "idx": idx,
        "caption": product_caption(product, shop.name if shop else ""),
        "keyboard": product_keyboard(product, cat_id, page, cart_count, len(photos), idx, wished),
    }


async def send_product_screen(bot, chat_id: int, screen: dict) -> None:
    """صفحه‌ی محصول رو به‌صورت یک پیام می‌فرسته: عکس + کپشن + دکمه‌ها (یا فقط متن اگه عکس نداره)."""
    photos = screen["photos"]
    for src in photos[screen["idx"]:screen["idx"] + 1]:
        try:
            await bot.send_photo(chat_id=chat_id, photo=src, caption=screen["caption"],
                                 parse_mode="HTML", reply_markup=screen["keyboard"])
            return
        except Exception:
            logger.warning("product photo could not be sent for product %s", screen["product"].id)
    await bot.send_message(chat_id=chat_id, text=screen["caption"], parse_mode="HTML", reply_markup=screen["keyboard"])


@require_active_subscription
async def show_product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    product_id = int(parts[2])
    cat_id = int(parts[3]) if len(parts) > 3 and parts[3] != "None" else None
    page = int(parts[4]) if len(parts) > 4 else 0

    screen = await load_product_screen(product_id, update.effective_user.id, cat_id, page)
    if not screen:
        await render_view(query, context,
                          "این محصول دیگه نیست. برگرد به دسته‌ها و بقیه محصولات رو ببین.",
                          InlineKeyboardMarkup([nav_row("cat:list", "🔙 دسته‌ها")]))
        return

    chat_id = query.message.chat_id
    try:
        await query.message.delete()  # لیست متنیه و تلگرام نمی‌ذاره متن رو به عکس تبدیل کنیم
    except Exception:
        pass
    await send_product_screen(context.bot, chat_id, screen)


async def show_product_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """prod:img:<id>:<idx>:<cat>:<page> — عکس بعدی/قبلی همون پیام رو درجا عوض می‌کنه."""
    query = update.callback_query
    parts = query.data.split(":")
    product_id, idx = int(parts[2]), int(parts[3])
    cat_id = int(parts[4]) or None
    page = int(parts[5]) if len(parts) > 5 else 0

    screen = await load_product_screen(product_id, update.effective_user.id, cat_id, page, idx)
    if not screen or not screen["photos"]:
        await query.answer()
        return
    try:
        await query.edit_message_media(
            media=InputMediaPhoto(media=screen["photos"][screen["idx"]], caption=screen["caption"], parse_mode="HTML"),
            reply_markup=screen["keyboard"],
        )
        await query.answer()
    except Exception:
        await query.answer("عکس باز نشد، دوباره امتحان کن", show_alert=False)
