"""
هندلر /search — جستجوی محصولات با نام یا توضیحات.
Includes interactive search (button + text input).
Also global search across all shops and shop search.
"""
from sqlalchemy import select, or_
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.db import async_session
from database.models import Category, Product, Shop
from utils.helpers import format_price
from utils.tg_helpers import get_current_shop_id, render_view


async def search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show search prompt when user clicks 🔍 جستجوی محصول button."""
    query = update.callback_query
    await query.answer()
    
    await render_view(
        query, context,
        "🔍 جستجوی محصول\n\n"
        "اسم محصولی که دنبالشی رو بنویس:\n"
        "مثال: هدفون، آیفون، شارژر...",
        InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ انصراف", callback_data="cat:list")]
        ]),
        parse_mode="HTML",
    )
    # Set state so we can capture next text message
    context.user_data["awaiting_search"] = True


async def search_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input when user is in search mode."""
    if not context.user_data.get("awaiting_search"):
        return  # Not in search mode, ignore
    
    context.user_data["awaiting_search"] = False
    text = update.message.text.strip()
    
    if not text or len(text) < 2:
        await update.message.reply_text("❌ عبارت جستجو یه‌کم کوتاهه، حداقل ۲ حرف بنویس:")
        return
    
    await _perform_search(update, context, text)


async def search_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /search <query> — جستجوی محصولات در فروشگاه جاری.
    """
    text = update.message.text.replace("/search", "").strip()

    if not text or len(text) < 2:
        await update.message.reply_text(
            "🔍 برای جستجو، متنی بعد از دستور بذارید:\n"
            "مثال: `/search آیفون`",
            parse_mode="Markdown",
        )
        return

    await _perform_search(update, context, text)


async def _perform_search(update, context, text: str):
    """Shared search logic for both /search command and interactive search."""
    shop_id = await get_current_shop_id(update)
    
    if not shop_id:
        await update.message.reply_text(
            "⚠️ فروشگاهی انتخاب نشده.\n"
            "از منوی اصلی یک فروشگاه رو انتخاب کنید."
        )
        return

    async with async_session() as session:
        result = await session.execute(
            select(Product).where(
                Product.shop_id == shop_id,
                Product.is_active == True,
                or_(
                    Product.name.ilike(f"%{text}%"),
                    Product.description.ilike(f"%{text}%"),
                ),
            ).order_by(Product.name)
        )
        products = result.scalars().all()

        if not products:
            await update.message.reply_text(
                f"🔍 نتیجه‌ای برای «{text}» پیدا نشد.\n\n"
                "💡 امتحان کنید:\n"
                "• کلمات کوتاه‌تر بنویسید\n"
                "• املای دیگه‌ای امتحان کنید\n"
                "• از منوی دسته‌بندی‌ها استفاده کنید"
            )
            return

        # Group products by category
        categories = {}
        for product in products:
            cat_result = await session.execute(
                select(Category).where(Category.id == product.category_id)
            )
            category = cat_result.scalar_one_or_none()
            cat_name = category.name if category else "بدون دسته"
            if cat_name not in categories:
                categories[cat_name] = []
            categories[cat_name].append(product)

        # Build response
        lines = [f"🔍 نتایج جستجو برای «{text}»\n"]
        keyboard = []

        for cat_name, cat_products in categories.items():
            lines.append(f"📂 {cat_name}")
            for product in cat_products:
                stock_status = "✅" if product.available_stock > 0 else "❌"
                lines.append(f"  • {product.name} — {format_price(product.price)} {stock_status}")
                keyboard.append([
                    InlineKeyboardButton(
                        f"🛒 {product.name[:30]} — {format_price(product.price)}",
                        callback_data=f"prod:open:{product.id}:0:0"
                    )
                ])
            lines.append("")

        await update.message.reply_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard[:8]),  # Max 8 buttons
            parse_mode="HTML",
        )


# ─── Global product search (across all shops) ─────────────────────
async def search_all_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /searchall <query> — search products across ALL shops.
    """
    text = update.message.text.replace("/searchall", "").strip()

    if not text or len(text) < 2:
        await update.message.reply_text(
            "🔍 برای جستجوی همگانی، متنی بعد از دستور بذارید:\n"
            "مثال: `/searchall آیفون`",
            parse_mode="Markdown",
        )
        return

    await _perform_global_search(update, context, text)


async def _perform_global_search(update, context, text: str):
    """Search products across ALL active shops."""
    async with async_session() as session:
        result = await session.execute(
            select(Product, Shop.name.label("shop_name"))
            .join(Shop, Product.shop_id == Shop.id)
            .where(
                Shop.is_active == True,
                Shop.status == "active",
                Product.is_active == True,
                or_(
                    Product.name.ilike(f"%{text}%"),
                    Product.description.ilike(f"%{text}%"),
                ),
            )
            .order_by(Product.name)
            .limit(30)
        )
        rows = result.all()

        if not rows:
            await update.message.reply_text(
                f"🔍 نتیجه‌ای برای «{text}» در هیچ فروشگاهی پیدا نشد.\n\n"
                "💡 امتحان کنید:\n"
                "• کلمات کوتاه‌تر بنویسید\n"
                "• املای دیگه‌ای امتحان کنید"
            )
            return

        lines = [f"🌐 نتایج جستجوی همگانی برای «{text}»\n"]
        keyboard = []

        for product, shop_name in rows:
            stock_status = "✅" if product.available_stock > 0 else "❌"
            lines.append(f"🛍 {shop_name} — {product.name} — {format_price(product.price)} {stock_status}")
            keyboard.append([
                InlineKeyboardButton(
                    f"🛒 {product.name[:28]} | {shop_name[:15]} — {format_price(product.price)}",
                    callback_data=f"prod:open:{product.id}:0:0"
                )
            ])

        await update.message.reply_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard[:8]),
            parse_mode="HTML",
        )


# ─── Shop search (by name/username) ────────────────────────────────
async def search_shops(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /findshop <query> — search shops by name or username.
    """
    text = update.message.text.replace("/findshop", "").strip()

    if not text or len(text) < 2:
        await update.message.reply_text(
            "🔍 برای جستجوی فروشگاه، متنی بعد از دستور بذارید:\n"
            "مثال: `/findshop тех`",
            parse_mode="Markdown",
        )
        return

    await _perform_shop_search(update, context, text)


async def _perform_shop_search(update, context, text: str):
    """Search shops by name or username."""
    async with async_session() as session:
        result = await session.execute(
            select(Shop).where(
                Shop.is_active == True,
                Shop.status == "active",
                or_(
                    Shop.name.ilike(f"%{text}%"),
                    Shop.username.ilike(f"%{text}%"),
                ),
            )
            .order_by(Shop.name)
            .limit(20)
        )
        shops = result.scalars().all()

        if not shops:
            await update.message.reply_text(
                f"🔍 فروشگاهی با نام/یوزرنیم «{text}» پیدا نشد.\n\n"
                "💡 امتحان کنید:\n"
                "• کلمات کوتاه‌تر بنویسید\n"
                "• املای دیگه‌ای امتحان کنید"
            )
            return

        lines = [f"🏪 نتایج جستجوی فروشگاه برای «{text}»\n"]
        keyboard = []

        for shop in shops:
            # Count active products
            result = await session.execute(
                select(Product).where(Product.shop_id == shop.id, Product.is_active == True)
            )
            count = len(result.scalars().all())

            lines.append(f"🏪 {shop.name} (@{shop.username or '—'}) — {count} محصول")
            keyboard.append([
                InlineKeyboardButton(
                    f"🏪 {shop.name[:30]} — {count} محصول",
                    callback_data=f"menu:shop:{shop.id}"
                )
            ])

        await update.message.reply_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard[:8]),
            parse_mode="HTML",
        )
