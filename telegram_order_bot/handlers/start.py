"""هندلر /start و منوی اصلی ربات — چندمستأجری + هوشمند."""
"""هندلر /start و منوی اصلی ربات — چندمستأجری + هوشمند."""
import json
import logging
from typing import Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
from telegram.ext import ContextTypes
import config
from database.db import async_session
from sqlalchemy import select
from database.models import Category, Shop, User, Product, ProductImage
from utils.helpers import format_price, is_super_admin
from utils.tenant import (
    ensure_shop_exists,
    get_owner_shop_id,
    get_shop,
    resolve_category_id_from_start,
    resolve_product_id_from_start,
    resolve_shop_id_from_start,
)
from utils.tg_helpers import render_view

logger = logging.getLogger(__name__)


# ─── متن‌ها و کیبوردها ────────────────────────────────────────

def _platform_welcome(first_name: str) -> tuple[str, InlineKeyboardMarkup]:
    """پیام خوش‌آمدگویی برای کاربر بدون فروشگاه فعال."""
    text = (
        f"سلام {first_name or 'دوست عزیز'} 👋\n\n"
        f"به «{config.STORE_NAME}» خوش اومدی!\n\n"
        "🛒 می‌خوای خرید کنی؟\n"
        "از لینک فروشگاهی که توی کانال یا گروه هست استفاده کن. با زدن لینک، مستقیم می‌ری به محصولات.\n\n"
        "🏪 می‌خوای فروشگاه بزنی؟\n"
        "دکمه پایین («می‌خوام فروشگاه بسازم») رو بزن. فقط ۳ سؤال کوتاهه و فروشگاهت همون لحظه فعال می‌شه.\n\n"
        "خب، از کدوم مسیر بریم؟"
    )
    keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏪 می‌خوام فروشگاه بسازم", callback_data="seller_reg:start")],
            [InlineKeyboardButton("🔍 جستجوی فروشگاه و محصول", callback_data="search:open")],
            [InlineKeyboardButton("🏬 فروشگاه‌های اخیر", callback_data="shop:recent")],
            [InlineKeyboardButton("ℹ️ درباره فروشگرام", callback_data="about")],
        ])
    return text, keyboard


def _shop_menu_text(first_name: str, shop: Shop) -> str:
    """متن منوی فروشگاه."""
    parts = [
        f"سلام {first_name or 'دوست عزیز'} 👋\n\n"
        f"به فروشگاه «{shop.name}» خوش اومدی! 🛍\n\n"
    ]
    if shop.description:
        parts.append(f"{shop.description}\n\n")
    parts.append(
        "از منوی پایین می‌تونی محصولات رو ببینی، به سبدت اضافه کنی، سفارش ثبت کنی و وضعیت سفارش‌های قبلیت رو پیگیری کنی.\n\n"
        "سوالی داشتی؟ از «💬 پرسش از فروشنده» بپرس."
    )
    return "".join(parts)


def _shop_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍 مشاهده محصولات", callback_data="cat:list")],
        [InlineKeyboardButton("🛒 سبد خرید", callback_data="cart:view"), InlineKeyboardButton("📦 سفارش‌های من", callback_data="order:history")],
        [InlineKeyboardButton("🔍 جستجو", callback_data="search:ask"), InlineKeyboardButton("❤️ علاقه‌مندی‌ها", callback_data="wishlist:view")],
        [InlineKeyboardButton("💬 پرسش از فروشنده", callback_data="support:seller"), InlineKeyboardButton("🆘 پشتیبانی فروشگرام", callback_data="support:open")],
    ])


def _last_shop_keyboard(shop: Shop, bot_username: str = None) -> InlineKeyboardMarkup:
    """دکمه‌های بازگشت به آخرین فروشگاه + دعوت به ساخت فروشگاه."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"🛍 بازگشت به {shop.name}",
            callback_data=f"nav:main",  # will redirect to last_shop's menu
        )],
        [InlineKeyboardButton("🏪 می‌خوام فروشگاه بسازم", callback_data="seller_reg:start")],
        [InlineKeyboardButton("ℹ️ درباره فروشگرام", callback_data="about")],
    ])


# ─── ثبت/بروزرسانی کاربر ──────────────────────────────────────

async def _record_shop_visit(user_id: int, shop_id: int) -> None:
    """Record a shop visit — save to recent_shops JSON field (max 5)."""
    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            return
        recent = []
        if user.recent_shops:
            try:
                recent = json.loads(user.recent_shops)
            except (json.JSONDecodeError, TypeError):
                recent = []
        # Remove existing entry if present, then prepend
        recent = [s for s in recent if s != shop_id]
        recent.insert(0, shop_id)
        user.recent_shops = json.dumps(recent[:5])
        await session.commit()


async def register_user(tg_user, shop_id: int | None = None) -> None:
    """ثبت‌نام کاربر جدید یا بروزرسانی اطلاعات."""
    # فروشگاه پیش‌فرض فقط وقتی استفاده می‌شه که واقعاً وجود داشته باشه؛ توی دیتابیس تازه
    # شاپ شماره‌ی ۱ نیست و کلید خارجی users.current_shop_id کل /start رو می‌شکست.
    current_shop_id = shop_id
    if current_shop_id is None and await ensure_shop_exists(config.DEFAULT_SHOP_ID):
        current_shop_id = config.DEFAULT_SHOP_ID

    async with async_session() as session:
        user = await session.get(User, tg_user.id)
        if user is None:
            session.add(User(
                user_id=tg_user.id,
                current_shop_id=current_shop_id,
                last_shop_id=shop_id,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                username=tg_user.username,
            ))
        else:
            user.first_name = tg_user.first_name
            user.last_name = tg_user.last_name
            user.username = tg_user.username
            if shop_id:
                user.current_shop_id = shop_id
                user.last_shop_id = shop_id
        await session.commit()


# ─── Recent shops handler ─────────────────────────────────────
async def show_recent_shops(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of recently visited shops."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    async with async_session() as session:
        user = await session.get(User, user_id)
        recent_shop_ids = []
        if user and user.recent_shops:
            try:
                recent_shop_ids = json.loads(user.recent_shops)
            except (json.JSONDecodeError, TypeError):
                recent_shop_ids = []

        if not recent_shop_ids:
            await render_view(query, context, "🏪 هنوز از هیچ فروشگاهی بازدید نکردی.\n\nبه محض اینکه از لینک یه فروشگاه وارد بشی، اینجا ذخیره می‌شه تا راحت بتونی برگردی بهش.", InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="nav:main")]
            ]))
            return

        shops = []
        for sid in recent_shop_ids:
            shop = await session.get(Shop, sid)
            if shop and shop.status == "active" and shop.is_active:
                shops.append(shop)

    if not shops:
        await render_view(query, context, "🏪 فروشگاهی در تاریخچه شما نیست.", InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت", callback_data="nav:main")]
        ]))
        return

    buttons = []
    for shop in shops:
        buttons.append([InlineKeyboardButton(f"🛍 {shop.name}", callback_data=f"shop:open:{shop.id}")])
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="nav:main")])

    await render_view(query, context, "🏪 فروشگاه‌هایی که اخیراً ازشون بازدید کردی:\n\nروی اسم هرکدوم بزن تا مستقیم واردش بشی 👇", InlineKeyboardMarkup(buttons))


async def open_shop_from_recent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open a shop from recent shops list — set current_shop_id and show menu."""
    query = update.callback_query
    await query.answer()
    try:
        _, _, shop_id = query.data.split(":")
        shop_id = int(shop_id)
    except (ValueError, IndexError):
        return

    async with async_session() as session:
        user = await session.get(User, update.effective_user.id)
        if user:
            user.current_shop_id = shop_id
            await session.commit()

    # Now call main_menu_callback to show the shop menu
    await main_menu_callback(update, context)


# ─── Shop deeplink handler ──────────────────────────────────────

async def _open_shop_for_link(update: Update, shop_id: int) -> bool:
    """لینک مستقیم محصول/دسته: فروشگاه باید فعال باشه، کاربر ثبت و روی همون فروشگاه می‌شینه."""
    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
    if not shop or not shop.is_active or shop.status != "active":
        await update.message.reply_text(
            "این فروشگاه فعلاً غیرفعاله. کمی بعد دوباره امتحان کن 🙏",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 شروع", callback_data="nav:main")]]),
        )
        return False
    await register_user(update.effective_user, shop_id)
    await _record_shop_visit(update.effective_user.id, shop_id)
    return True


async def _handle_product_deeplink(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int) -> bool:
    """/start product_N — صفحه‌ی خود محصول (عکس + قیمت + افزودن به سبد). True یعنی رسیدگی شد."""
    from handlers.menu import load_product_screen, send_product_screen

    async with async_session() as session:
        product = await session.get(Product, product_id)
    if not product or not product.is_active:
        await update.message.reply_text(
            "این محصول دیگه نیست. بقیه‌ی محصولات فروشگاه رو ببین 👇",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛍 مشاهده محصولات", callback_data="cat:list")]]),
        )
        return True
    if not await _open_shop_for_link(update, product.shop_id):
        return True

    screen = await load_product_screen(product_id, update.effective_user.id, product.category_id, 0)
    if not screen:
        return False
    await send_product_screen(context.bot, update.effective_chat.id, screen)

    # فروشنده‌ای که لینک محصول خودش رو می‌زنه، پنل رو هم می‌بینه
    owner_shop_id = await get_owner_shop_id(update.effective_user.id)
    if (is_super_admin(update.effective_user.id) or owner_shop_id) and product.shop_id == owner_shop_id:
        from handlers.admin.panel import admin_command
        await admin_command(update, context)
    return True


async def _handle_category_deeplink(update: Update, context: ContextTypes.DEFAULT_TYPE, category_id: int) -> bool:
    """/start category_N — لیست محصولات همون دسته. True یعنی رسیدگی شد."""
    from handlers.menu import build_products_view

    async with async_session() as session:
        category = await session.get(Category, category_id)
    if not category:
        await update.message.reply_text(
            "این دسته دیگه نیست.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 شروع", callback_data="nav:main")]]),
        )
        return True
    if not await _open_shop_for_link(update, category.shop_id):
        return True

    text, keyboard = await build_products_view(category.shop_id, category_id, 0, update.effective_user.id, context.user_data)
    await update.message.reply_text(text, reply_markup=keyboard)
    return True


async def _handle_shop_deeplink(update: Update, context: ContextTypes.DEFAULT_TYPE, shop_id: int) -> bool:
    """Handle /start with shop_XXX param. Returns True if handled."""
    if not await ensure_shop_exists(shop_id):
        await update.message.reply_text(
            "❌ این فروشگاه پیدا نشد یا دیگه فعال نیست. لینک رو دوباره چک کن یا با فروشنده تماس بگیر."
        )
        return True

    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
    if shop and shop.status != "active":
        status_messages = {
            "draft": "⏳ این فروشگاه هنوز توسط تیم ما بررسی و تایید نشده. کمی صبر کن، به‌زودی فعال می‌شه.",
            "suspended": "🚫 این فروشگاه موقتاً معلق شده و در حال حاضر در دسترس نیست.",
            "rejected": (
                f"❌ این فروشگاه تایید نشده."
                + (f"\nدلیل: {shop.rejection_reason}" if shop.rejection_reason else "")
            ),
        }
        text = status_messages.get(shop.status, "⚠️ فعلاً نمی‌تونیم وضعیت این فروشگاه رو مشخص کنیم. چند لحظه دیگه دوباره امتحان کن.")
        await update.message.reply_text(text)
        return True

    await register_user(update.effective_user, shop_id)
    await _record_shop_visit(update.effective_user.id, shop_id)

    # فروشنده/ادمین فقط اگه لینک خودشون نباشه → مشتری
    owner_shop_id = await get_owner_shop_id(update.effective_user.id)
    if is_super_admin(update.effective_user.id):
        if not shop_id or (owner_shop_id and shop_id == owner_shop_id):
            from handlers.admin.panel import admin_command
            await admin_command(update, context)
            return True
    elif owner_shop_id and shop_id == owner_shop_id:
        from handlers.admin.panel import admin_command
        await admin_command(update, context)
        return True

    # مشتری عادی → منوی فروشگاه با بنر
    async with async_session() as session:
        shop = await session.get(Shop, shop_id)
    if shop:
        text = _shop_menu_text(update.effective_user.first_name, shop)
        if shop.banner_image:
            await update.message.reply_photo(
                photo=shop.banner_image,
                caption=text,
                reply_markup=_shop_menu_keyboard(),
            )
        else:
            await update.message.reply_text(text, reply_markup=_shop_menu_keyboard())
    return True


async def _handle_role_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle /start with no param for admin/seller.
    به‌جای redirect به پنل، دستورات رو نشون می‌ده."""
    tg_user = update.effective_user
    owner_shop_id = await get_owner_shop_id(tg_user.id)

    # Super admin → show admin panel
    if is_super_admin(tg_user.id):
        try:
            from handlers.bot_commands import set_admin_menu
            await set_admin_menu(context.bot, tg_user.id)
        except Exception:
            pass
        from handlers.admin.panel import admin_command
        await admin_command(update, context)
        return True

    # Seller → show welcome with commands (NOT redirect to panel)
    if owner_shop_id:
        try:
            from handlers.bot_commands import set_seller_menu
            await set_seller_menu(context.bot, tg_user.id)
        except Exception:
            pass

        async with async_session() as session:
            shop = await session.get(Shop, owner_shop_id)

        if shop and shop.status == "active":
            text = (
                f"👋 سلام {tg_user.first_name or 'فروشنده'} عزیز!\n\n"
                f"به فروشگاه «{shop.name}» خوش اومدی! 🏪\n\n"
                "برای مدیریت فروشگاه از دستورات زیر استفاده کن:\n"
                "━━━━━━━━━━━━━━━━\n"
                f"📌 /myshop — پنل مدیریت کامل (محصولات، دسته‌بندی‌ها، سفارش‌ها و تنظیمات)\n\n"
                f"📌 /neworders — سفارش‌های جدید\n"
                f"📌 /support — پیام‌های مشتریان\n"
                f"📌 /reset_password — تغییر رمز عبور\n\n"
                f"🔗 لینک فروشگاهت (برای اشتراک‌گذاری با مشتری‌ها):\n"
                f"https://t.me/{context.bot.username}?start=shop_{shop.id}\n\n"
                "👇 از دکمه زیر هم می‌تونی وارد پنل بشی:"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏪 ورود به پنل مدیریت", callback_data="seller:panel_back")],
            ])
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
        elif shop:
            status_text = {
                "draft": "⏳ در انتظار تایید ادمین",
                "rejected": f"❌ تایید نشده" + (f" ({shop.rejection_reason})" if shop.rejection_reason else ""),
                "suspended": "🚫 معلق",
            }.get(shop.status, "⚠️ نامشخص")
            text = (
                f"👋 سلام {tg_user.first_name or 'فروشنده'}!\n\n"
                f"🏪 فروشگاه «{shop.name}» — وضعیت: {status_text}\n\n"
                "تا تایید نهایی صبر کن. معمولاً کمتر از ۲۴ ساعت بررسی می‌شه.\n"
                "💬 برای پیگیری: /support"
            )
            await update.message.reply_text(text)
        else:
            # Owner record exists but no shop (shouldn't happen)
            text = "👋 سلام! برای دیدن منوی اصلی و شروع کار، دستور /start رو بزن."
            await update.message.reply_text(text)

        return True

    return False


async def _handle_customer_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start with no param for regular customers."""
    tg_user = update.effective_user
    async with async_session() as session:
        fresh_user = await session.get(User, tg_user.id)
        last_shop_id = fresh_user.last_shop_id if fresh_user else None

        last_shop = None
        if last_shop_id:
            last_shop = await session.get(Shop, last_shop_id)
            if last_shop and last_shop.status != "active":
                last_shop = None
            else:
                fresh_user.current_shop_id = last_shop_id
                await session.commit()

    if last_shop:
        text = (
            f"سلام {tg_user.first_name or 'دوست عزیز'}، خوش برگشتی 👋\n\n"
            f"آخرین باری که اومدی، تو فروشگاه «{last_shop.name}» بودی. می‌خوای همونجا رو ادامه بدی؟\n"
        )
        # Build keyboard with recent shops
        buttons = [
            [InlineKeyboardButton(f"🛍 بازگشت به {last_shop.name}", callback_data="nav:main")],
        ]
        # Add recent shops (skip the last_shop which is already shown)
        recent_shop_ids = []
        if fresh_user and fresh_user.recent_shops:
            try:
                recent_shop_ids = json.loads(fresh_user.recent_shops)
            except (json.JSONDecodeError, TypeError):
                recent_shop_ids = []

        async with async_session() as session:
            other_shops = []
            for sid in recent_shop_ids:
                if sid == last_shop_id:
                    continue
                other_shop = await session.get(Shop, sid)
                if other_shop and other_shop.status == "active" and other_shop.is_active:
                    other_shops.append(other_shop)
            if other_shops:
                buttons.append([InlineKeyboardButton("🏪 فروشگاه‌های اخیر", callback_data="shops:recent")])

        buttons.extend([
            [InlineKeyboardButton("🏪 می‌خوام فروشگاه بسازم", callback_data="seller_reg:start")],
            [InlineKeyboardButton("🔍 جستجوی فروشگاه و محصول", callback_data="search:open")],
            [InlineKeyboardButton("ℹ️ درباره فروشگرام", callback_data="about")],
        ])
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        text, keyboard = _platform_welcome(tg_user.first_name)
        await update.message.reply_text(text, reply_markup=keyboard)


# ─── هندلر /start ─────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user

    # ─── چک مسدود بودن ──────────────────────────────────
    async with async_session() as session:
        user = await session.get(User, tg_user.id)
    if user and user.is_blocked:
        await update.message.reply_text("⚠️ متأسفانه حساب کاربری‌ت مسدود شده و فعلاً امکان استفاده از ربات نیست. اگه فکر می‌کنی اشتباهی پیش اومده، با پشتیبانی تماس بگیر.")
        return

    # ─── استخراج پارامتر start ──────────────────────────
    start_param = context.args[0] if context.args else None

    # ─── لینک «فروشگاهت رو بساز» از سایت (start=newshop) ───
    if start_param == "newshop":
        await register_user(tg_user)
        await update.message.reply_text(
            f"سلام {tg_user.first_name or 'دوست عزیز'} 👋\n\n"
            "فروشگاهت با ۳ سؤال کوتاه ساخته می‌شه و همون لحظه آماده‌ی فروشه. شروع کنیم؟",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏪 ساخت فروشگاه", callback_data="seller_reg:start")],
            ]),
        )
        return

    shop_id = await resolve_shop_id_from_start(start_param)

    # ─── لینک مستقیم دسته‌بندی (category_123) ──────────
    category_id = await resolve_category_id_from_start(start_param)
    if category_id:
        if await _handle_category_deeplink(update, context, category_id):
            return

    # ─── لینک مستقیم محصول (product_123) ─────────────
    product_id = await resolve_product_id_from_start(start_param)
    if product_id:
        if await _handle_product_deeplink(update, context, product_id):
            return

    # ─── لینک فروشگاه (shop_XXX) ───────────────────────
    if shop_id:
        if await _handle_shop_deeplink(update, context, shop_id):
            return

    # ─── /start بدون پارامتر ───────────────────────────
    await register_user(tg_user)

    if await _handle_role_home(update, context):
        return

    await _handle_customer_home(update, context)


# ─── بازگشت به منوی اصلی ──────────────────────────────────────

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    async with async_session() as session:
        user = await session.get(User, update.effective_user.id)
    shop_id = user.current_shop_id if user else None
    shop = None
    if shop_id:
        shop = await get_shop(shop_id)

    if shop:
        text = _shop_menu_text(update.effective_user.first_name, shop)
        if shop.banner_image:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=shop.banner_image,
                caption=text,
                reply_markup=_shop_menu_keyboard(),
            )
            try:
                await query.message.delete()
            except Exception:
                pass
        else:
            await render_view(query, context, text, _shop_menu_keyboard())
    else:
        text, keyboard = _platform_welcome(update.effective_user.first_name)
        await render_view(query, context, text, keyboard)
