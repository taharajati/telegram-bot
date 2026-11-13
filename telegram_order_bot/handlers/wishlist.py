"""
علاقه‌مندی‌ها — ذخیره محصولات برای خرید بعدی.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from database.db import async_session
from database.models import Product, WishlistItem
from utils.helpers import format_price
from utils.tg_helpers import get_current_shop_id, render_view


async def toggle_wishlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add or remove a product from wishlist (toggle)."""
    query = update.callback_query
    await query.answer()
    _, _, product_id, *_ = query.data.split(":")
    product_id = int(product_id)
    user_id = update.effective_user.id
    shop_id = await get_current_shop_id(update)

    if not shop_id:
        await query.answer("برای این کار اول باید وارد یه فروشگاه بشی.", show_alert=True)
        return

    async with async_session() as session:
        existing = await session.execute(
            select(WishlistItem).where(
                WishlistItem.user_id == user_id,
                WishlistItem.shop_id == shop_id,
                WishlistItem.product_id == product_id,
            )
        )
        item = existing.scalar_one_or_none()
        product = await session.get(Product, product_id)
        product_name = product.name if product else ""

        if item:
            await session.delete(item)
            await session.commit()
            await query.answer("⭐ از علاقه‌مندی‌ها حذف شد", show_alert=False)
        else:
            session.add(WishlistItem(user_id=user_id, shop_id=shop_id, product_id=product_id))
            await session.commit()
            await query.answer("⭐ به علاقه‌مندی‌ها اضافه شد", show_alert=False)

    # از صفحه‌ی محصول: فقط دکمه‌ها درجا عوض می‌شن (پیام تأیید جدا نمی‌فرستیم)
    parts = query.data.split(":")
    if len(parts) >= 5 and getattr(query.message, "photo", None):
        from handlers.menu import load_product_screen
        screen = await load_product_screen(product_id, user_id, int(parts[3]) or None, int(parts[4]))
        if screen:
            try:
                await query.edit_message_reply_markup(reply_markup=screen["keyboard"])
            except Exception:
                pass
        return

    # Send confirmation message after session is closed
    if product_name:
        if item:
            await query.message.reply_text(
                f"⭐ «{product_name}» از علاقه‌مندی‌ها حذف شد.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❤️ مشاهده علاقه‌مندی‌ها", callback_data="wishlist:view")],
                ])
            )
        else:
            await query.message.reply_text(
                f"⭐ «{product_name}» به علاقه‌مندی‌ها اضافه شد!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❤️ مشاهده علاقه‌مندی‌ها", callback_data="wishlist:view")],
                    [InlineKeyboardButton("🛍 ادامه خرید", callback_data="cat:list")],
                ])
            )


async def view_wishlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's wishlist for current shop."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    shop_id = await get_current_shop_id(update)

    if not shop_id:
        await query.answer("لطفاً ابتدا وارد فروشگاه شوید.", show_alert=True)
        return

    async with async_session() as session:
        result = await session.execute(
            select(WishlistItem)
            .options(selectinload(WishlistItem.product))
            .where(WishlistItem.user_id == user_id, WishlistItem.shop_id == shop_id)
            .order_by(WishlistItem.added_at.desc())
        )
        items = result.scalars().all()

        if not items:
            text = "❤️ لیست علاقه‌مندی‌هات فعلاً خالیه.\n\nهر محصولی رو دوست داشتی، روی ⭐ بزن تا اینجا برات ذخیره بشه."
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍 مشاهده محصولات", callback_data="cat:list")],
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data="nav:main")],
            ])
            await render_view(query, context, text, keyboard)
            return

        lines = ["❤️ علاقه‌مندی‌های من\n"]
        rows = []
        for item in items:
            product = item.product
            if not product or not product.is_active:
                continue
            stock = "✅" if product.available_stock > 0 else "❌"
            lines.append(f"• {product.name} — {format_price(product.price)} {stock}")
            rows.append([
                InlineKeyboardButton(
                    f"🛒 {product.name[:30]}",
                    callback_data=f"prod:open:{product.id}:0:0"
                )
            ])

        lines.append("\n💡 برای حذف از لیست، روی محصول رو بزنید و ⭐ بزنید.")
        rows.append([InlineKeyboardButton("🔙 منوی اصلی", callback_data="nav:main")])
        await render_view(query, context, "\n".join(lines), InlineKeyboardMarkup(rows), parse_mode="HTML")
