"""
مدیریت محصولات (فروشنده/ادمین کل) — چندمستأجری.
هر فروشنده فقط به محصولات فروشگاه خودش دسترسی داره.
"""
import math

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import delete, select, update as sa_update

import config
from sqlalchemy.orm import selectinload

from database.db import async_session
from database.models import CartItem, Category, OrderItem, Product, ProductImage
from handlers.admin.panel import admin_only, _get_shop_id_for_admin
from utils.helpers import format_price, to_jalali
from utils.tg_helpers import render_view
from utils.image_storage import download_and_store_image, download_and_store_multiple, delete_image
from services.restock import _check_and_notify_restock

ASK_NAME, ASK_DESC, ASK_PRICE, ASK_CATEGORY, ASK_STOCK, ASK_PHOTO = range(6)

DEFAULT_CATEGORY_NAME = "محصولات"
_STOCK_PROMPT = "چند عدد ازش موجوده؟ (فقط عدد، مثال: 20)"
_PHOTO_SKIP_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("⏭ بدون عکس ثبت کن", callback_data="admin:products:add:nophoto")],
])
_PHOTO_DONE_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ ثبت محصول", callback_data="admin:products:add:done")],
])
_NUMBER_NOISE = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789", ",٬، ")


def _clean_number(text: str) -> str:
    """ارقام فارسی/عربی رو لاتین می‌کنه و جداکننده‌ی هزارگان رو برمی‌داره."""
    return (text or "").strip().translate(_NUMBER_NOISE)
EDIT_ASK_VALUE = 0
ASK_PHOTO_CHANGE = 0  # state for change photo mini-conversation
PRODUCTS_PER_PAGE = 8

FIELD_LABELS = {
    "name": "نام",
    "price": "قیمت",
    "description": "توضیحات",
    "stock": "موجودی",
}


def products_list_keyboard(page_items, page, total_pages) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"✏️ {p.name} — {format_price(p.price)}", callback_data=f"admin:products:edit:{p.id}")]
        for p in page_items
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"admin:products:list:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"admin:products:list:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("➕ افزودن محصول جدید", callback_data="admin:products:add")])
    rows.append([InlineKeyboardButton("📤 افزودن با فوروارد", callback_data="admin:products:add_forward")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin:panel")])
    return InlineKeyboardMarkup(rows)


async def _render_products_list(query, context, page: int, shop_id: int | None):
    async with async_session() as session:
        stmt = select(Product).order_by(Product.id.desc())
        if shop_id:
            stmt = stmt.where(Product.shop_id == shop_id)
        result = await session.execute(stmt)
        products = result.scalars().all()

    if not products:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ افزودن محصول جدید", callback_data="admin:products:add")],
            [InlineKeyboardButton("📤 افزودن با فوروارد", callback_data="admin:products:add_forward")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin:panel")],
        ])
        await render_view(query, context, "هنوز هیچ محصولی ثبت نکردی. با دکمه پایین اولین محصولتو اضافه کن 👇", keyboard)
        return

    total_pages = max(1, math.ceil(len(products) / PRODUCTS_PER_PAGE))
    page = max(0, min(page, total_pages - 1))
    page_items = products[page * PRODUCTS_PER_PAGE : (page + 1) * PRODUCTS_PER_PAGE]

    text = f"📦 محصولات (صفحه {page + 1} از {total_pages}) — برای ویرایش روی هرکدوم بزن:"
    await render_view(query, context, text, products_list_keyboard(page_items, page, total_pages))


@admin_only
async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)
    await _render_products_list(query, context, page, shop_id)


@admin_only
async def start_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)

    # اگه سوپر ادمین باشه و فروشگاه نداره، از اولین فروشگاه خودش برداره
    if not shop_id:
        from utils.helpers import is_super_admin
        if is_super_admin(update.effective_user.id):
            from database.models import ShopOwner
            async with async_session() as session:
                owner = (await session.execute(
                    select(ShopOwner).where(ShopOwner.user_id == update.effective_user.id).limit(1)
                )).scalar_one_or_none()
                if owner:
                    shop_id = owner.shop_id
                    context.user_data["admin_shop_id"] = shop_id

    if not shop_id:
        await render_view(query, context, "❌ به نظر می‌رسه فروشگاهی برای حساب شما ثبت نشده.\n\nاگه صاحب فروشگاه نیستی و می‌خوای بسازی، از /start شروع کن.", InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="admin:panel")]]))
        return ConversationHandler.END

    # اول چک کن دسته‌بندی داره
    async with async_session() as session:
        result = await session.execute(
            select(Category).where(Category.shop_id == shop_id).limit(1)
        )
        has_category = result.scalar_one_or_none() is not None

    if not has_category:
        # فروشنده‌ی تازه‌وارد رو برای ساختن دسته‌بندی برنمی‌گردونیم؛ یه دسته‌ی پیش‌فرض می‌سازیم
        # که بعداً از «دسته‌بندی‌ها» قابل تغییر نامه.
        async with async_session() as session:
            session.add(Category(name=DEFAULT_CATEGORY_NAME, shop_id=shop_id))
            await session.commit()

    context.user_data["new_product"] = {"shop_id": shop_id}
    await render_view(query, context, "➕ محصول جدید\n\nاسم محصول رو بفرست:\n(برای لغو /cancel)", None)
    return ASK_NAME


@admin_only
async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_product"]["name"] = update.message.text.strip()
    await update.message.reply_text("یه توضیح کوتاه برای محصول بنویس (اگه نمی‌خوای، «-» بفرست):")
    return ASK_DESC


@admin_only
async def add_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text.strip()
    context.user_data["new_product"]["description"] = None if desc in ("ندارد", "-") else desc
    await update.message.reply_text("قیمت محصول به تومان چنده؟ (فقط عدد، مثال: 150000)")
    return ASK_PRICE


@admin_only
async def add_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = _clean_number(update.message.text)
    if not raw.isdigit():
        await update.message.reply_text("لطفاً فقط عدد وارد کن (مثال: 150000):")
        return ASK_PRICE
    context.user_data["new_product"]["price"] = float(raw)

    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(Category).where(Category.shop_id == shop_id).order_by(Category.name)
        )
        categories = result.scalars().all()

    if not categories:
        await update.message.reply_text(
            "هنوز هیچ دسته‌بندی‌ای نساختی. اول از بخش «مدیریت دسته‌بندی‌ها» یه دسته بساز، "
            "بعد دوباره برای افزودن محصول اقدام کن."
        )
        context.user_data.pop("new_product", None)
        return ConversationHandler.END

    if len(categories) == 1:
        context.user_data["new_product"]["category_id"] = categories[0].id
        await update.message.reply_text(_STOCK_PROMPT)
        return ASK_STOCK

    rows = [[InlineKeyboardButton(c.name, callback_data=f"admin:products:add:cat:{c.id}")] for c in categories]
    await update.message.reply_text("دسته‌بندی محصول رو انتخاب کن:", reply_markup=InlineKeyboardMarkup(rows))
    return ASK_CATEGORY


@admin_only
async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split(":")[4])
    context.user_data["new_product"]["category_id"] = cat_id
    await render_view(query, context, _STOCK_PROMPT, None)
    return ASK_STOCK


@admin_only
async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = _clean_number(update.message.text)
    if not raw.isdigit():
        await update.message.reply_text("لطفاً فقط عدد وارد کن:")
        return ASK_STOCK
    context.user_data["new_product"]["stock"] = int(raw)
    await update.message.reply_text(
        "📷 حالا عکس محصول رو بفرست (می‌تونی چندتا بفرستی).",
        reply_markup=_PHOTO_SKIP_KB,
    )
    return ASK_PHOTO


@admin_only
async def add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data.get("new_product")
    if data is None:
        await update.message.reply_text("جلسه‌ی افزودن محصول منقضی شده، دوباره شروع کن.")
        return ConversationHandler.END

    # Initialize image collection if first time (first photo is already in this message)
    if "image_file_ids" not in data:
        data["image_file_ids"] = []
        if update.message.photo:
            data["image_file_ids"].append(update.message.photo[-1].file_id)
            await update.message.reply_text(
                "✅ عکس اول ذخیره شد. اگه عکس دیگه‌ای داری بفرست، وگرنه محصول رو ثبت کن 👇",
                reply_markup=_PHOTO_DONE_KB,
            )
            return ASK_PHOTO

    if update.message.photo:
        data["image_file_ids"].append(update.message.photo[-1].file_id)
        await update.message.reply_text(
            f"✅ {len(data['image_file_ids'])} عکس ذخیره شد. عکس بعدی رو بفرست یا محصول رو ثبت کن 👇",
            reply_markup=_PHOTO_DONE_KB,
        )
        return ASK_PHOTO

    text = (update.message.text or "").strip()
    if text in ("همین کافیه", "تمام", "done"):
        pass  # proceed to save
    elif text == "رد شو":
        data["image_file_ids"] = []
    else:
        await update.message.reply_text(
            "عکس محصول رو بفرست، یا یکی از دکمه‌ها رو بزن 👇",
            reply_markup=_PHOTO_DONE_KB if data.get("image_file_ids") else _PHOTO_SKIP_KB,
        )
        return ASK_PHOTO

    return await _finish_add_product(update, context)


@admin_only
async def add_photo_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دکمه‌های مرحله‌ی عکس: «ثبت محصول» یا «بدون عکس»."""
    query = update.callback_query
    await query.answer()
    data = context.user_data.get("new_product")
    if data is None:
        await query.edit_message_text("جلسه‌ی افزودن محصول منقضی شده، دوباره شروع کن.")
        return ConversationHandler.END
    if query.data.endswith(":nophoto"):
        data["image_file_ids"] = []
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    return await _finish_add_product(update, context)


async def _finish_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data["new_product"]
    message = update.effective_message

    # --- Save product with image download & local storage ---
    image_ids = data.get("image_file_ids", [])
    bot_token = context.bot.token
    
    # Download and store images locally
    local_urls = []
    if image_ids:
        local_urls = await download_and_store_multiple(bot_token, image_ids)
    
    async with async_session() as session:
        product = Product(
            name=data["name"],
            description=data.get("description"),
            price=data["price"],
            category_id=data["category_id"],
            stock=data["stock"],
            image_file_id=image_ids[0] if image_ids else None,
            image_url=local_urls[0] if local_urls else None,
            shop_id=data["shop_id"],
        )
        session.add(product)
        await session.flush()
        # Save additional images as ProductImage rows
        for i, fid in enumerate(image_ids[1:], start=1):
            local_url = local_urls[i] if i < len(local_urls) else None
            session.add(ProductImage(
                product_id=product.id,
                file_id=fid,
                local_url=local_url,
                sort_order=i,
            ))
        await session.commit()

        product_id = product.id

    link = f"https://t.me/{context.bot.username}?start=product_{product_id}"
    await message.reply_text(
        f"✅ محصول «{data['name']}» اضافه شد و الان توی فروشگاهت دیده می‌شه.\n\n"
        f"🔗 لینک مستقیم محصول (برای استوری و کانال):\n{link}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ افزودن محصول بعدی", callback_data="admin:products:add")],
            [InlineKeyboardButton("📦 لیست محصولات", callback_data="admin:products:list:0")],
            [InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin:panel")],
        ]),
        disable_web_page_preview=True,
    )
    context.user_data.pop("new_product", None)
    return ConversationHandler.END


def product_edit_keyboard(product: Product, bot_username: str = "") -> InlineKeyboardMarkup:
    active_label = "🟢 فعال" if product.is_active else "🔴 غیرفعال"
    rows = [
        [
            InlineKeyboardButton("✏️ نام", callback_data=f"admin:products:field:{product.id}:name"),
            InlineKeyboardButton("✏️ قیمت", callback_data=f"admin:products:field:{product.id}:price"),
        ],
        [
            InlineKeyboardButton("✏️ توضیحات", callback_data=f"admin:products:field:{product.id}:description"),
            InlineKeyboardButton("✏️ موجودی", callback_data=f"admin:products:field:{product.id}:stock"),
        ],
        [InlineKeyboardButton("🖼 تغییر عکس اصلی", callback_data=f"admin:products:photo:{product.id}")],
        [InlineKeyboardButton("🖼🖼 گالری (چند عکس)", callback_data=f"admin:products:gallery:{product.id}")],
        [InlineKeyboardButton(f"تغییر وضعیت ({active_label})", callback_data=f"admin:products:toggle:{product.id}")],
        [InlineKeyboardButton("📋 لینک محصول", callback_data=f"admin:products:link:{product.id}")],
        [InlineKeyboardButton("🗑 حذف محصول", callback_data=f"admin:products:delete:{product.id}")],
        [InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="admin:products:list:0")],
    ]
    return InlineKeyboardMarkup(rows)


def _product_detail_text(product: Product) -> str:
    active = "🟢 فعال" if product.is_active else "🔴 غیرفعال"
    return (
        f"🏷 {product.name}\n"
        f"💰 {format_price(product.price)}\n"
        f"📦 موجودی: {product.stock} | قابل فروش: {product.available_stock}\n"
        f"🟢🟢 {active}\n"
        f"📝 {product.description or 'بدون توضیحات'}\n"
        f"📅 بروزرسانی: {to_jalali(product.updated_at)}"
    )


@admin_only
async def open_product_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[3])
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)

    async with async_session() as session:
        stmt = select(Product).where(Product.id == product_id)
        if shop_id:
            stmt = stmt.where(Product.shop_id == shop_id)
        product = (await session.execute(stmt)).scalar_one_or_none()

    if not product:
        await render_view(query, context, "این محصول پیدا نشد یا به شما تعلق نداره.",
                           InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:products:list:0")]]))
        return

    await render_view(query, context, _product_detail_text(product), product_edit_keyboard(product))


@admin_only
async def toggle_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    product_id = int(query.data.split(":")[3])
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)

    async with async_session() as session:
        stmt = select(Product).where(Product.id == product_id)
        if shop_id:
            stmt = stmt.where(Product.shop_id == shop_id)
        product = (await session.execute(stmt)).scalar_one_or_none()
        if product:
            product.is_active = not product.is_active
            await session.commit()

    await query.answer()
    await open_product_edit(update, context)


@admin_only
async def product_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لینک محصول برای کپی کردن"""
    query = update.callback_query
    product_id = int(query.data.split(":")[3])
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)

    async with async_session() as session:
        stmt = select(Product).where(Product.id == product_id)
        if shop_id:
            stmt = stmt.where(Product.shop_id == shop_id)
        product = (await session.execute(stmt)).scalar_one_or_none()

    if not product:
        await query.answer("محصول پیدا نشد", show_alert=True)
        return

    bot_username = context.bot.username
    telegram_link = f"https://t.me/{bot_username}?start=product_{product.id}"
    web_link = f"https://telegramorder.ir/product/{product.id}"

    text = (
        f"📋 لینک مستقیم محصول «{product.name}»:\n\n"
        f"🔹 لینک تلگرام:\n"
        f"{telegram_link}\n\n"
        f"🔹 لینک وبسایت:\n"
        f"{web_link}\n\n"
        "لینک تلگرام رو توی کانالت بذار — خریدار با کلیک مستقیماً میاد تو بات و صفحه خرید محصول باز میشه."
    )
    await query.answer()
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت به محصول", callback_data=f"admin:products:edit:{product.id}")]
        ]),
        parse_mode="HTML",
    )


@admin_only
async def start_change_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند تغییر عکس محصول."""
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[3])
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)

    async with async_session() as session:
        stmt = select(Product).where(Product.id == product_id)
        if shop_id:
            stmt = stmt.where(Product.shop_id == shop_id)
        product = (await session.execute(stmt)).scalar_one_or_none()

    if not product:
        await render_view(query, context, "این محصول پیدا نشد یا به شما تعلق نداره.",
                          InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:products:list:0")]]))
        return ConversationHandler.END

    context.user_data["change_photo_product_id"] = product_id
    await render_view(query, context,
        f"عکس جدید برای «{product.name}» بفرست، یا بنویس «حذف» تا عکس حذف شه، یا «انصراف» برای لغو:",
        None
    )
    return ASK_PHOTO_CHANGE


@admin_only
async def save_change_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ذخیره عکس جدید محصول + دانلود و ذخیره محلی."""
    product_id = context.user_data.get("change_photo_product_id")
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)

    if product_id is None:
        await update.message.reply_text("جلسه تغییر عکس منقضی شده، دوباره تلاش کن.")
        return ConversationHandler.END

    if update.message.text and update.message.text.strip() == "انصراف":
        context.user_data.pop("change_photo_product_id", None)
        await update.message.reply_text("تغییر عکس لغو شد.")
        return ConversationHandler.END

    bot_token = context.bot.token
    new_local_url = None
    new_file_id = None

    if update.message.photo:
        new_file_id = update.message.photo[-1].file_id
        new_local_url = await download_and_store_image(bot_token, new_file_id)
    elif update.message.text and update.message.text.strip() == "حذف":
        new_file_id = None
        new_local_url = None
    else:
        await update.message.reply_text("یه عکس بفرست، یا بنویس «حذف» / «انصراف»:")
        return ASK_PHOTO_CHANGE

    async with async_session() as session:
        stmt = select(Product).where(Product.id == product_id)
        if shop_id:
            stmt = stmt.where(Product.shop_id == shop_id)
        product = (await session.execute(stmt)).scalar_one_or_none()
        if product:
            product.image_file_id = new_file_id
            product.image_url = new_local_url
            await session.commit()

    await update.message.reply_text("عکس محصول به‌روزرسانی شد ✅")
    context.user_data.pop("change_photo_product_id", None)
    return ConversationHandler.END


@admin_only
async def start_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, _, _, product_id, field = query.data.split(":")
    context.user_data["edit_product_id"] = int(product_id)
    context.user_data["edit_field"] = field

    field_prompts = {
        "name": "نام جدید محصول رو بفرست:",
        "price": "قیمت جدید رو فقط با عدد بفرست:",
        "description": "توضیحات جدید رو بفرست:",
        "stock": "موجودی جدید رو فقط با عدد بفرست:",
    }
    await render_view(query, context, field_prompts[field] + "\n(برای لغو /cancel)", None)
    return EDIT_ASK_VALUE


@admin_only
async def save_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    product_id = context.user_data.get("edit_product_id")
    field = context.user_data.get("edit_field")
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)

    if product_id is None or field is None:
        await update.message.reply_text("جلسه‌ی ویرایش منقضی شده، دوباره از لیست محصولات اقدام کن.")
        return ConversationHandler.END

    value = update.message.text.strip()

    if field == "price":
        cleaned = value.replace(",", "").replace("٬", "")
        if not cleaned.isdigit():
            await update.message.reply_text("لطفاً فقط عدد وارد کن:")
            return EDIT_ASK_VALUE
        value = float(cleaned)
    elif field == "stock":
        if not value.isdigit():
            await update.message.reply_text("لطفاً فقط عدد وارد کن:")
            return EDIT_ASK_VALUE
        value = int(value)

    async with async_session() as session:
        stmt = select(Product).where(Product.id == product_id)
        if shop_id:
            stmt = stmt.where(Product.shop_id == shop_id)
        product = (await session.execute(stmt)).scalar_one_or_none()

        if product:
            old_stock = product.stock if field == 'stock' else None
            setattr(product, field, value)
            await session.commit()
            if field == 'stock' and old_stock == 0 and value > 0:
                await _check_and_notify_restock(session, product_id, product.shop_id, context.bot)
            await update.message.reply_text(f"✅ {FIELD_LABELS[field]} محصول به‌روزرسانی شد")
        else:
            await update.message.reply_text("محصول پیدا نشد.")

    context.user_data.pop("edit_product_id", None)
    context.user_data.pop("edit_field", None)
    return ConversationHandler.END


@admin_only
async def delete_product_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأیید حذف محصول."""
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[3])
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)

    async with async_session() as session:
        stmt = select(Product).where(Product.id == product_id)
        if shop_id:
            stmt = stmt.where(Product.shop_id == shop_id)
        product = (await session.execute(stmt)).scalar_one_or_none()

    if not product:
        await render_view(query, context, "این محصول پیدا نشد یا به شما تعلق نداره.",
                          InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:products:list:0")]]))
        return

    await render_view(query, context,
        f"⚠️ مطمئنی می‌خوای محصول «{product.name}» رو حذف کنی؟\nاین عملیات قابل برگشت نیست.",
        InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ بله، حذف کن", callback_data=f"admin:products:delete:confirm:{product_id}")],
            [InlineKeyboardButton("❌ انصراف", callback_data=f"admin:products:edit:{product_id}")],
        ])
    )


@admin_only
async def delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف نهایی محصول."""
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[4])
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)

    async with async_session() as session:
        stmt = select(Product).where(Product.id == product_id)
        if shop_id:
            stmt = stmt.where(Product.shop_id == shop_id)
        product = (await session.execute(stmt)).scalar_one_or_none()

        if product:
            # Delete associated images from filesystem
            if product.image_url:
                await delete_image(product.image_url)
            for img in product.images:
                if img.local_url:
                    await delete_image(img.local_url)
            
            await session.delete(product)
            await session.commit()
            await render_view(query, context, "✅ محصول حذف شد.",
                              InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="admin:products:list:0")]]))
        else:
            await render_view(query, context, "محصول پیدا نشد.",
                                          InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:products:list:0")]]))




# ─── Gallery (Multi-image) ─────────────────────────────────

@admin_only
async def gallery_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش گالری تصاویر محصول."""
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[3])
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)

    async with async_session() as session:
        stmt = select(Product).where(Product.id == product_id).options(selectinload(Product.images))
        if shop_id:
            stmt = stmt.where(Product.shop_id == shop_id)
        product = (await session.execute(stmt)).scalar_one_or_none()

    if not product:
        await render_view(query, context, "این محصول پیدا نشد یا به شما تعلق نداره.",
                          InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:products:list:0")]]))
        return

    images = sorted(product.images, key=lambda x: x.sort_order)

    if not images:
        text = f"🖼 گالری «{product.name}» خالی است."
    else:
        text = (
            f"🖼 گالری «{product.name}»: {len(images)} عکس اضافه‌ی دیگه (غیر از عکس اصلی).\n"
            "پیش‌نمایش‌شون بالاست؛ برای حذف، شماره‌ی عکس رو بزن 👇"
        )
        # پیش‌نمایش خود عکس‌ها (به‌جای نمایش مسیر فایل)
        previews = []
        for img in images[:10]:
            if img.file_id and img.file_id.startswith(("AgA", "BAAC")):
                previews.append(InputMediaPhoto(media=img.file_id))
            elif img.local_url:
                previews.append(InputMediaPhoto(
                    media=img.local_url if img.local_url.startswith("http") else config.WEBSITE_URL + img.local_url))
        if previews:
            try:
                await context.bot.send_media_group(chat_id=query.message.chat_id, media=previews)
            except Exception:
                pass

    rows = []
    if images:
        for i, img in enumerate(images):
            rows.append([InlineKeyboardButton(f"🗑 حذف عکس {i+1}", callback_data=f"admin:products:gallery_del:{product_id}:{img.id}")])
    rows.append([InlineKeyboardButton("➕ اضافه کردن عکس", callback_data=f"admin:products:gallery_add:{product_id}")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:products:edit:{product_id}")])

    await render_view(query, context, text, InlineKeyboardMarkup(rows))


@admin_only
async def gallery_add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع اضافه کردن عکس به گالری."""
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[3])
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)

    async with async_session() as session:
        stmt = select(Product).where(Product.id == product_id)
        if shop_id:
            stmt = stmt.where(Product.shop_id == shop_id)
        product = (await session.execute(stmt)).scalar_one_or_none()

    if not product:
        await render_view(query, context, "این محصول پیدا نشد یا به شما تعلق نداره.",
                          InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:products:list:0")]]))
        return ConversationHandler.END

    context.user_data["gallery_product_id"] = product_id
    await render_view(query, context,
        f"عکس جدید برای گالری «{product.name}» بفرست، یا «انصراف» برای لغو:",
        None
    )
    return ASK_PHOTO_CHANGE


@admin_only
async def gallery_save_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ذخیره عکس جدید در گالری."""
    product_id = context.user_data.get("gallery_product_id")
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)

    if product_id is None:
        await update.message.reply_text("جلسه اضافه کردن عکس منقضی شده.")
        return ConversationHandler.END

    if update.message.text and update.message.text.strip() == "انصراف":
        context.user_data.pop("gallery_product_id", None)
        await update.message.reply_text("اضافه کردن عکس لغو شد.")
        return ConversationHandler.END

    bot_token = context.bot.token
    new_local_url = None
    new_file_id = None

    if update.message.photo:
        new_file_id = update.message.photo[-1].file_id
        new_local_url = await download_and_store_image(bot_token, new_file_id)
    else:
        await update.message.reply_text("یه عکس بفرست، یا بنویس «انصراف»:")
        return ASK_PHOTO_CHANGE

    async with async_session() as session:
        # Get next sort_order
        stmt = select(ProductImage).where(ProductImage.product_id == product_id)
        existing = (await session.execute(stmt)).scalars().all()
        next_order = max([img.sort_order for img in existing], default=0) + 1

        session.add(ProductImage(
            product_id=product_id,
            file_id=new_file_id,
            local_url=new_local_url,
            sort_order=next_order,
        ))
        await session.commit()

    await update.message.reply_text("عکس به گالری اضافه شد ✅")
    context.user_data.pop("gallery_product_id", None)
    return ConversationHandler.END


@admin_only
async def gallery_delete_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف عکس از گالری."""
    query = update.callback_query
    await query.answer()
    _, _, _, product_id, image_id = query.data.split(":")
    product_id = int(product_id)
    image_id = int(image_id)
    shop_id = context.user_data.get("admin_shop_id") or await _get_shop_id_for_admin(update.effective_user.id)

    async with async_session() as session:
        stmt = select(ProductImage).where(ProductImage.id == image_id, ProductImage.product_id == product_id)
        img = (await session.execute(stmt)).scalar_one_or_none()

        if img:
            if img.local_url:
                await delete_image(img.local_url)
            await session.delete(img)
            await session.commit()
            await query.answer("عکس حذف شد ✅")
        else:
            await query.answer("عکس پیدا نشد", show_alert=True)

    await gallery_list(update, context)