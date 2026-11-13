"""هندلرهای ویجت‌های تلگرام — باز کردن ویجت با دکمه و جواب دادن به درخواست‌های خود ویجت."""
import logging

from sqlalchemy import select
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, TypeHandler

from database.db import async_session
from database.models import Order
from services import widgets
from utils.tenant import get_owner_shop_id

logger = logging.getLogger(__name__)

_UNSUPPORTED = "این قابلیت فعلاً در تلگرام در دسترس نیست (یا تلگرامت قدیمیه). کمی بعد دوباره امتحان کن."


async def widget_query_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """widget_query هنوز در کتابخانه مدل نشده و داخل api_kwargs آپدیت می‌آد."""
    widget_query = update.api_kwargs.get("widget_query") if update.api_kwargs else None
    if widget_query:
        await widgets.handle_widget_query(context.bot, widget_query)


async def order_track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """order:track:<id> — ویجت رهگیری زنده سفارش رو برای مشتری می‌فرسته."""
    query = update.callback_query
    order_id = int(query.data.split(":")[2])

    async with async_session() as session:
        order = (await session.execute(
            select(Order).where(Order.id == order_id, Order.user_id == update.effective_user.id)
        )).scalar_one_or_none()
    if not order:
        await query.answer("این سفارش پیدا نشد.", show_alert=True)
        return

    if await widgets.send_order_tracker(context.bot, order_id, query.message.chat_id):
        await query.answer()
    else:
        await query.answer(_UNSUPPORTED, show_alert=True)


async def seller_live_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """seller:live — داشبورد زنده فروش رو برای فروشنده می‌فرسته."""
    query = update.callback_query
    shop_id = await get_owner_shop_id(update.effective_user.id)
    if not shop_id:
        await query.answer("فروشگاهی برای این حساب پیدا نشد.", show_alert=True)
        return

    if await widgets.send_seller_dashboard(context.bot, shop_id, query.message.chat_id):
        await query.answer()
    else:
        await query.answer(_UNSUPPORTED, show_alert=True)


async def seller_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """seller:inv — ویجت موجودی سریع (+ و − و مخفی‌کردن) رو برای فروشنده می‌فرسته."""
    query = update.callback_query
    shop_id = await get_owner_shop_id(update.effective_user.id)
    if not shop_id:
        await query.answer("فروشگاهی برای این حساب پیدا نشد.", show_alert=True)
        return
    if await widgets.send_seller_inventory(context.bot, shop_id, query.message.chat_id):
        await query.answer()
    else:
        await query.answer(_UNSUPPORTED, show_alert=True)


def register(application: Application) -> None:
    # گروه جدا: TypeHandler همه‌ی آپدیت‌ها رو می‌بینه و نباید جلوی هندلرهای دیگه رو بگیره
    application.add_handler(TypeHandler(Update, widget_query_router), group=-1)
    application.add_handler(CallbackQueryHandler(order_track, pattern=r"^order:track:\d+$"))
    application.add_handler(CallbackQueryHandler(seller_live_dashboard, pattern="^seller:live$"))
    application.add_handler(CallbackQueryHandler(seller_inventory, pattern="^seller:inv$"))
