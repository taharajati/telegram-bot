"""مدیریت سبد خرید کاربر — چندمستأجری."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.db import async_session
from database.models import CartItem, Product
from handlers.subscription_decorator import require_active_subscription
from utils.helpers import format_price
from utils.tg_helpers import get_current_shop_id, render_view


async def _load_cart_with_products(session, user_id: int, shop_id: int):
    """Load cart items with eager-loaded product data."""
    result = await session.execute(
        select(CartItem)
        .where(CartItem.user_id == user_id, CartItem.shop_id == shop_id)
        .options(selectinload(CartItem.product))
    )
    return result.scalars().all()


def _build_cart_view(cart_items):
    if not cart_items:
        text = "سبد خریدت فعلاً خالیه 🛒\n\nبرو یه سر به محصولات بزن، شاید چیز خوبی پیدا کردی!"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍 مشاهده محصولات", callback_data="cat:list")],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="nav:main")],
        ])
        return text, keyboard

    lines = ["🛒 سبد خرید شما:\n"]
    rows = []
    total = 0
    for item in cart_items:
        subtotal = item.product.price * item.quantity
        total += subtotal
        lines.append(f"• {item.product.name} × {item.quantity} = {format_price(subtotal)}")
        rows.append([
            InlineKeyboardButton("➖", callback_data=f"cart:dec:{item.id}"),
            InlineKeyboardButton(str(item.quantity), callback_data="noop"),
            InlineKeyboardButton("➕", callback_data=f"cart:inc:{item.id}"),
            InlineKeyboardButton("🗑", callback_data=f"cart:remove:{item.id}"),
        ])

    lines.append(f"\n💰 جمع کل: {format_price(total)}")
    rows.append([InlineKeyboardButton("✅ ثبت سفارش", callback_data="order:start")])
    rows.append([InlineKeyboardButton("🗑 خالی کردن سبد", callback_data="cart:clear")])
    rows.append([InlineKeyboardButton("🔙 منوی اصلی", callback_data="nav:main")])

    return "\n".join(lines), InlineKeyboardMarkup(rows)


@require_active_subscription
async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    user_id = update.effective_user.id
    shop_id = await get_current_shop_id(update)

    if not shop_id:
        text = "برای دیدن سبد خرید، اول باید از لینک یه فروشگاه واردش بشی."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 شروع", callback_data="nav:main")]])
        if query:
            await render_view(query, context, text, keyboard)
        else:
            await update.message.reply_text(text, reply_markup=keyboard)
        return

    async with async_session() as session:
        cart_items = await _load_cart_with_products(session, user_id, shop_id)

    text, keyboard = _build_cart_view(cart_items)

    if query:
        await render_view(query, context, text, keyboard)
    else:
        await update.message.reply_text(text, reply_markup=keyboard)


@require_active_subscription
async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    shop_id = await get_current_shop_id(update)

    if not shop_id:
        await query.answer("لطفاً ابتدا با لینک فروشگاه وارد شوید.", show_alert=True)
        return

    product_id = int(query.data.split(":")[2])

    async with async_session() as session:
        product = await session.get(Product, product_id)
        if not product or product.shop_id != shop_id or product.available_stock <= 0:
            await query.answer("متأسفانه این محصول الان موجود نیست 🙁", show_alert=True)
            return

        result = await session.execute(
            select(CartItem).where(
                CartItem.user_id == user_id,
                CartItem.shop_id == shop_id,
                CartItem.product_id == product_id
            )
        )
        cart_item = result.scalar_one_or_none()

        if cart_item:
            if cart_item.quantity + 1 > product.available_stock:
                await query.answer("⚠️ به سقف موجودی این محصول رسیدی، نمی‌تونی بیشتر از این به سبدت اضافه کنی.", show_alert=True)
                return
            cart_item.quantity += 1
        else:
            session.add(CartItem(user_id=user_id, shop_id=shop_id, product_id=product_id, quantity=1))

        await session.commit()

    parts = query.data.split(":")
    on_product_screen = bool(getattr(query.message, "photo", None)) or len(parts) > 4

    if on_product_screen:
        # صفحه‌ی محصول: فقط یک اعلان کوچیک + به‌روزرسانی دکمه‌ها (۱ تپ، بدون پیام جدید)
        from handlers.menu import load_product_screen
        cat_id = int(parts[3]) or None if len(parts) > 3 else None
        page = int(parts[4]) if len(parts) > 4 else 0
        await query.answer("✅ به سبد اضافه شد")
        screen = await load_product_screen(product_id, user_id, cat_id, page)
        if screen:
            try:
                await query.edit_message_reply_markup(reply_markup=screen["keyboard"])
            except Exception:
                pass
        return

    await query.answer()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 مشاهده سبد", callback_data="cart:view"), InlineKeyboardButton("✅ ثبت سفارش", callback_data="order:start")],
        [InlineKeyboardButton("🛍 ادامه خرید", callback_data="cat:list")],
    ])
    await query.message.reply_text(f"✅ «{product.name}» به سبدت اضافه شد.", reply_markup=keyboard)


@require_active_subscription
async def change_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, action, cart_item_id = query.data.split(":")
    cart_item_id = int(cart_item_id)
    user_id = update.effective_user.id
    shop_id = await get_current_shop_id(update)

    if not shop_id:
        await query.answer()
        await view_cart(update, context)
        return

    async with async_session() as session:
        cart_item = await session.get(CartItem, cart_item_id)
        if not cart_item or cart_item.shop_id != shop_id:
            await query.answer()
            await view_cart(update, context)
            return

        await session.refresh(cart_item, attribute_names=["product"])

        if action == "inc":
            if cart_item.quantity + 1 > cart_item.product.available_stock:
                await query.answer("موجودی قابل فروش این محصول به سقف رسیده ⚠️", show_alert=True)
                return
            cart_item.quantity += 1
            await session.commit()
        else:  # dec
            cart_item.quantity -= 1
            if cart_item.quantity <= 0:
                await session.delete(cart_item)
            await session.commit()

    await query.answer()
    await view_cart(update, context)


@require_active_subscription
async def remove_from_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    cart_item_id = int(query.data.split(":")[2])
    user_id = update.effective_user.id
    shop_id = await get_current_shop_id(update)

    if not shop_id:
        await query.answer()
        await view_cart(update, context)
        return

    async with async_session() as session:
        cart_item = await session.get(CartItem, cart_item_id)
        if cart_item and cart_item.shop_id == shop_id:
            await session.delete(cart_item)
            await session.commit()

    await query.answer("حذف شد 🗑")
    await view_cart(update, context)


async def clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # نمایش تاییدیه
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ بله، خالی کن", callback_data="cart:clear:confirm")],
        [InlineKeyboardButton("❌ انصراف", callback_data="cart:view")],
    ])
    await render_view(query, context, "🗑 مطمئنی می‌خوای همه‌ی سبد خریدت رو خالی کنی؟", keyboard)


async def clear_cart_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    shop_id = await get_current_shop_id(update)

    if not shop_id:
        await query.answer()
        await view_cart(update, context)
        return

    async with async_session() as session:
        result = await session.execute(
            select(CartItem).where(CartItem.user_id == user_id, CartItem.shop_id == shop_id)
        )
        for item in result.scalars().all():
            await session.delete(item)
        await session.commit()

    await query.answer("سبد خرید خالی شد 🗑")
    await view_cart(update, context)