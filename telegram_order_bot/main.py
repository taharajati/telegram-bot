"""
نقطه‌ی ورود ربات. همه‌ی هندلرها اینجا ثبت می‌شن و ربات با polling اجرا می‌شه.
"""
import asyncio
import logging
import os

from telegram import Update
from telegram.error import RetryAfter
from telegram.ext import (
    AIORateLimiter,
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import config
from database.db import init_db
from handlers.bot_commands import setup_startup_menus, set_default_menu, set_seller_menu
from services import payment as payment_svc
from services.events import Event, event_bus  # noqa: F401
from services import event_listeners  # noqa: F401
from services.monitoring import init_sentry, start_metrics_server, metrics, mark_started
from handlers import cart, menu, order, start, support
from handlers import seller_registration
from handlers import seller_panel
from handlers import subscription as subscription_h
from utils.crypto import _get_key  # pre-warm encryption key at startup to avoid blocking event loop
from handlers import admin_approval
from handlers import forward_products
from handlers import help as help_handler
from handlers import search
from handlers.admin import broadcast as admin_broadcast
from handlers.admin import categories as admin_categories
from handlers.admin import orders as admin_orders
from handlers.admin import panel as admin_panel
from handlers.admin import products as admin_products
from handlers.admin import shops as admin_shops
from handlers.common import cancel_conversation, noop_callback, about_platform
from handlers import conversations as msg

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Global error handler — logs to Sentry + Prometheus."""
    error = context.error

    # Track in Prometheus
    error_type = type(error).__name__
    metrics.track_error(error_type)

    logger.error("خطای مدیریت‌نشده رخ داد", exc_info=error)

    # Sentry will capture this automatically if initialized

    if isinstance(error, RetryAfter):
        user_msg = f"⏳ تعداد درخواست‌ها زیاد شد. لطفاً {error.retry_after} ثانیه صبر کنید."
    else:
        user_msg = "❌ یه مشکل غیرمنتظره پیش اومد. لطفاً دوباره تلاش کن یا با /start شروع کن."

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(user_msg)
        except Exception:
            logger.warning("Failed to send error message to user.")


async def _post_init(application: Application):
    # Initialize Sentry FIRST (before anything else)
    init_sentry(
        dsn=config.SENTRY_DSN,
        environment=config.SENTRY_ENVIRONMENT,
        traces_sample_rate=config.SENTRY_TRACES_SAMPLE_RATE,
    )

    # Start Prometheus metrics server
    if config.PROMETHEUS_ENABLED:
        start_metrics_server(config.PROMETHEUS_PORT)

    # Mark startup time for uptime
    mark_started()

    await init_db()
    _get_key()  # pre-warm encryption key (scrypt derivation takes ~2s)
    logger.info("پایگاه داده آماده شد ✅")

    await set_default_menu(application.bot)
    await setup_startup_menus(application.bot)
    try:
        from sqlalchemy import select
        from database.models import ShopOwner, Shop
        from database.db import async_session as _sess
        async with _sess() as session:
            result = await session.execute(
                select(ShopOwner).join(Shop, ShopOwner.shop_id == Shop.id).where(
                    Shop.status == "active", Shop.is_active == True
                )
            )
            for owner in result.scalars().all():
                try:
                    await set_seller_menu(application.bot, owner.user_id)
                except Exception:
                    continue
    except Exception as e:
        logger.warning("خطا در بازگردانی منوی فروشنده‌ها: %s", e)

    async def cleanup_task():
        # First run after 2 minutes to catch any orders already timed out at startup
        await asyncio.sleep(120)
        while True:
            try:
                await payment_svc.auto_cancel_unpaid_orders()
            except Exception as e:
                logger.error(f"خطا در auto_cancel_unpaid_orders: {e}")
            await asyncio.sleep(1800)

    asyncio.create_task(cleanup_task())
    logger.info("کرون‌جاب تمیزسازی سفارش‌های پرداخت‌نشده فعال شد ⏰")

    # Setup abandoned cart scheduler
    from services.abandoned_cart import setup_abandoned_cart_scheduler
    setup_abandoned_cart_scheduler(application)

    # Subscription expiry cron
    async def subscription_expiry_task():
        await asyncio.sleep(180)  # First run after 3 min
        while True:
            try:
                from services.subscription import auto_suspend_expired_subscriptions
                await auto_suspend_expired_subscriptions(bot=application.bot)
            except Exception as e:
                logger.error(f"خطا در auto_suspend_expired_subscriptions: {e}")
            await asyncio.sleep(86400)  # هر ۲۴ ساعت

    asyncio.create_task(subscription_expiry_task())


def _register_customer_handlers(application: Application):
    """Basic customer commands + nav + menu."""
    application.add_handler(CommandHandler("start", start.start_command))
    application.add_handler(CommandHandler("menu", menu.show_categories))
    application.add_handler(CommandHandler("cart", cart.view_cart))
    application.add_handler(CommandHandler("my_orders", order.order_history))
    application.add_handler(CommandHandler("cancel", cancel_conversation))
    application.add_handler(CommandHandler("help", help_handler.help_command))
    application.add_handler(CommandHandler("search", search.search_products))
    application.add_handler(CommandHandler("searchall", search.search_all_products))
    application.add_handler(CommandHandler("findshop", search.search_shops))

    application.add_handler(CallbackQueryHandler(menu.show_shop, pattern="^menu:shop:"))
    application.add_handler(CallbackQueryHandler(help_handler.help_callback, pattern="^help:show$"))
    application.add_handler(CallbackQueryHandler(start.main_menu_callback, pattern="^nav:main$"))
    application.add_handler(CallbackQueryHandler(menu.show_categories, pattern="^cat:list$"))
    application.add_handler(CallbackQueryHandler(menu.show_products, pattern="^cat:open:"))
    application.add_handler(CallbackQueryHandler(menu.show_products, pattern="^cat:sort:"))
    application.add_handler(CallbackQueryHandler(menu.show_products, pattern="^cat:stock:"))
    application.add_handler(CallbackQueryHandler(menu.show_products, pattern="^cat:filter:"))
    application.add_handler(CallbackQueryHandler(menu.show_product_detail, pattern="^prod:open:"))
    application.add_handler(CallbackQueryHandler(noop_callback, pattern="^noop$"))
    application.add_handler(CallbackQueryHandler(about_platform, pattern="^about$"))

    # Wishlist
    import handlers.wishlist as wishlist
    application.add_handler(CallbackQueryHandler(wishlist.view_wishlist, pattern="^wishlist:view$"))
    application.add_handler(CallbackQueryHandler(wishlist.toggle_wishlist, pattern="^wishlist:toggle:"))

    # Restock subscription
    import services.restock as restock
    application.add_handler(CallbackQueryHandler(restock.subscribe_restock, pattern="^restock:sub:"))

    # Discount codes
    import handlers.discount as discount
    discount_conv = discount.get_discount_conversation()
    application.add_handler(discount_conv)
    application.add_handler(CallbackQueryHandler(discount.list_discounts, pattern="^discount:list$"))

    # Recent shops
    application.add_handler(CallbackQueryHandler(start.show_recent_shops, pattern="^shop:recent$"))
    application.add_handler(CallbackQueryHandler(start.open_shop_from_recent, pattern="^shop:open:"))

    # Interactive search
    application.add_handler(CallbackQueryHandler(search.search_prompt, pattern="^search:ask$"))
    # Text handler for interactive search (catches text when awaiting_search is True)
    # This must be registered AFTER ConversationHandler's text handlers to avoid conflicts
    # Use a higher group number so it doesn't interfere with checkout
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, search.search_text_handler),
        group=5
    )


def _register_cart_handlers(application: Application):
    """Cart management."""
    application.add_handler(CallbackQueryHandler(cart.add_to_cart, pattern="^cart:add:"))
    application.add_handler(CallbackQueryHandler(cart.view_cart, pattern="^cart:view$"))
    application.add_handler(CallbackQueryHandler(cart.change_quantity, pattern="^cart:(inc|dec):"))
    application.add_handler(CallbackQueryHandler(cart.remove_from_cart, pattern="^cart:remove:"))
    application.add_handler(CallbackQueryHandler(cart.clear_cart, pattern="^cart:clear$"))
    application.add_handler(CallbackQueryHandler(cart.clear_cart_confirm, pattern="^cart:clear:confirm$"))


def _register_order_handlers(application: Application):
    """Order checkout conversation + history."""
    checkout_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(order.start_checkout, pattern="^order:start$")],
        states={
            order.ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, order.ask_name)],
            order.ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, order.ask_phone)],
            order.ASK_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, order.ask_address)],
            order.ASK_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, order.ask_notes)],
            order.ASK_PAYMENT_METHOD: [
                CallbackQueryHandler(order.ask_payment_method, pattern="^pay:card_to_card$"),
                CallbackQueryHandler(order.confirm_card_payment, pattern="^order:confirm_card$"),
                CallbackQueryHandler(order.cancel_order, pattern="^order:cancel$"),
                CallbackQueryHandler(order.ask_discount, pattern="^order:ask_discount$"),
            ],
            order.ASK_CARD_RECEIPT: [
                MessageHandler((filters.PHOTO | filters.TEXT) & ~filters.COMMAND, order.handle_card_receipt),
            ],
            order.CONFIRM: [
                CallbackQueryHandler(order.confirm_order, pattern="^order:confirm$"),
                CallbackQueryHandler(order.confirm_card_payment, pattern="^order:confirm_card$"),
                CallbackQueryHandler(order.cancel_order, pattern="^order:cancel$"),
                CallbackQueryHandler(order.ask_discount, pattern="^order:ask_discount$"),
            ],
            order.ASK_DISCOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, order.receive_discount),
                CallbackQueryHandler(order.cancel_order, pattern="^order:cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            CallbackQueryHandler(order.cancel_order, pattern="^order:cancel$"),
            CallbackQueryHandler(order.handle_pay_cancel, pattern="^order:pay_cancel:"),
            CallbackQueryHandler(order.start_checkout, pattern="^order:start$"),
        ],
        name="checkout_conversation",
    )
    application.add_handler(checkout_conv)
    application.add_handler(CallbackQueryHandler(order.order_history, pattern="^order:history$"))
    application.add_handler(CallbackQueryHandler(order.order_detail_customer, pattern="^order:detail:"))
    application.add_handler(CallbackQueryHandler(order.handle_reorder, pattern="^order:reorder:"))
    application.add_handler(CallbackQueryHandler(order._handle_checkout_saved, pattern="^checkout:use_saved$"))
    application.add_handler(CallbackQueryHandler(order.start_checkout, pattern="^checkout:new_info$"))

    # Seller approve/reject card receipt
    application.add_handler(CallbackQueryHandler(order.seller_approve_card_payment, pattern="^seller:payment:approve:"))
    application.add_handler(CallbackQueryHandler(order.handle_reject_card_payment, pattern="^seller:payment:reject:"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, order.seller_submit_reject_reason), group=3)
    application.add_handler(CallbackQueryHandler(order.handle_cancel_reject, pattern="^pay:cancel_reject:"))
    application.add_handler(CallbackQueryHandler(order.handle_appeal, pattern="^pay:appeal:"))
    application.add_handler(CallbackQueryHandler(order.handle_card_receipt_retry, pattern="^pay:receipt_retry:"))
    application.add_handler(CallbackQueryHandler(order.handle_pay_cancel, pattern="^pay:cancel:"))
    application.add_handler(CallbackQueryHandler(order.handle_pay_cancel, pattern="^order:pay_cancel:"))
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, order.handle_card_receipt_retry_photo), group=2)

    # Customer delivery confirmation
    application.add_handler(CallbackQueryHandler(admin_orders.customer_confirm_delivery, pattern="^customer:confirm_delivery:"))


def _register_seller_handlers(application: Application):
    """Seller registration + panel + shop management."""
    seller_conv = seller_registration.get_seller_registration_conversation()
    application.add_handler(seller_conv)

    seller_panel_conv = seller_panel.get_seller_panel_conversation()
    application.add_handler(seller_panel_conv)

    application.add_handler(CallbackQueryHandler(seller_panel.seller_delete_confirm, pattern="^seller:delete_shop$"))
    application.add_handler(CallbackQueryHandler(seller_panel.seller_delete_final, pattern="^seller:delete_final:"))
    application.add_handler(CallbackQueryHandler(seller_panel.seller_orders_pending, pattern="^seller:orders:pending$"))
    application.add_handler(CallbackQueryHandler(seller_panel.seller_orders_history, pattern="^seller:orders:history$"))
    application.add_handler(CallbackQueryHandler(seller_panel.seller_order_detail, pattern="^seller:order_detail:"))
    application.add_handler(CallbackQueryHandler(admin_panel.admin_stats, pattern="^seller:stats$"))
    application.add_handler(CommandHandler("reset_password", seller_panel.reset_password_command))

    # Seller command handlers
    application.add_handler(CommandHandler("myshop", seller_panel.seller_panel_command))
    application.add_handler(CommandHandler("neworders", seller_panel.neworders_command))
    application.add_handler(CommandHandler("my_panel", seller_panel.seller_panel_command))  # alias to myshop
    application.add_handler(CommandHandler("support", seller_panel.support_command))

    approval_conv = admin_approval.get_admin_approval_conversation()
    application.add_handler(approval_conv)
    application.add_handler(CallbackQueryHandler(admin_approval.handle_admin_approve, pattern="^admin:seller:approve:"))

    # Subscription handlers (seller side)
    from handlers import subscription as sub_h
    sub_h.register_subscription_handlers(application)


def _register_admin_handlers(application: Application):
    application.add_handler(CommandHandler("admin", admin_panel.admin_command))
    application.add_handler(CallbackQueryHandler(admin_panel.admin_panel_callback, pattern="^admin:panel$"))
    application.add_handler(CallbackQueryHandler(admin_panel.admin_stats, pattern="^admin:stats$"))
    application.add_handler(CallbackQueryHandler(admin_panel.admin_advanced_stats, pattern="^admin:stats:advanced$"))
    application.add_handler(CallbackQueryHandler(admin_panel.admin_top_products, pattern="^admin:stats:top_products$"))
    application.add_handler(CallbackQueryHandler(admin_panel.admin_weekly_sales, pattern="^admin:stats:weekly$"))

    # Forward products conversation
    fwd_conv = forward_products.get_forward_products_conversation()
    application.add_handler(fwd_conv)

    # Products
    application.add_handler(CallbackQueryHandler(admin_products.list_products, pattern="^admin:products:list:"))
    application.add_handler(CallbackQueryHandler(admin_products.open_product_edit, pattern=r"^admin:products:edit:\d+$"))
    application.add_handler(CallbackQueryHandler(admin_products.toggle_product, pattern="^admin:products:toggle:"))
    application.add_handler(CallbackQueryHandler(admin_products.product_link, pattern=r"^admin:products:link:\d+$"))
    application.add_handler(CallbackQueryHandler(admin_products.delete_product_confirm, pattern=r"^admin:products:delete:\d+$"))
    application.add_handler(CallbackQueryHandler(admin_products.delete_product, pattern="^admin:products:delete:confirm:"))

    add_product_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_products.start_add_product, pattern="^admin:products:add$")],
        states={
            admin_products.ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_products.add_name)],
            admin_products.ASK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_products.add_desc)],
            admin_products.ASK_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_products.add_price)],
            admin_products.ASK_CATEGORY: [CallbackQueryHandler(admin_products.add_category, pattern="^admin:products:add:cat:")],
            admin_products.ASK_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_products.add_stock)],
            admin_products.ASK_PHOTO: [MessageHandler((filters.PHOTO | filters.TEXT) & ~filters.COMMAND, admin_products.add_photo)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        name="add_product_conversation",
    )
    application.add_handler(add_product_conv)

    edit_field_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_products.start_edit_field, pattern="^admin:products:field:")],
        states={
            admin_products.EDIT_ASK_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_products.save_edit_field)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        name="edit_product_field_conversation",
    )
    application.add_handler(edit_field_conv)

    change_photo_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_products.start_change_photo, pattern=r"^admin:products:photo:\d+$")],
        states={
            admin_products.ASK_PHOTO_CHANGE: [MessageHandler((filters.PHOTO | filters.TEXT) & ~filters.COMMAND, admin_products.save_change_photo)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        name="change_photo_conversation",
    )
    application.add_handler(change_photo_conv)
    
    # Gallery (multi-image)
    application.add_handler(CallbackQueryHandler(admin_products.gallery_list, pattern=r"^admin:products:gallery:\d+$"))
    application.add_handler(CallbackQueryHandler(admin_products.gallery_delete_photo, pattern=r"^admin:products:gallery_del:\d+:\d+$"))
    gallery_add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_products.gallery_add_photo, pattern=r"^admin:products:gallery_add:\d+$")],
        states={
            admin_products.ASK_PHOTO_CHANGE: [MessageHandler((filters.PHOTO | filters.TEXT) & ~filters.COMMAND, admin_products.gallery_save_photo)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        name="gallery_add_photo_conversation",
    )
    application.add_handler(gallery_add_conv)

    # Categories
    application.add_handler(CallbackQueryHandler(admin_categories.list_categories, pattern="^admin:categories$"))
    application.add_handler(CallbackQueryHandler(admin_categories.delete_category_confirm, pattern=r"^admin:categories:delete:\d+$"))
    application.add_handler(CallbackQueryHandler(admin_categories.delete_category_final, pattern="^admin:categories:delete_final:"))

    add_category_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_categories.start_add_category, pattern="^admin:categories:add$")],
        states={
            admin_categories.ASK_CATEGORY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_categories.save_category)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        name="add_category_conversation",
    )
    application.add_handler(add_category_conv)

    # Orders
    application.add_handler(CommandHandler("orders", admin_orders.orders_command))
    application.add_handler(CommandHandler("orders_history", admin_orders.orders_history_command))
    application.add_handler(CallbackQueryHandler(admin_orders.list_pending_orders, pattern="^admin:orders:pending:"))
    application.add_handler(CallbackQueryHandler(admin_orders.list_all_orders, pattern="^admin:orders:history:"))
    application.add_handler(CallbackQueryHandler(admin_orders.order_detail, pattern="^admin:orders:detail:"))
    application.add_handler(CallbackQueryHandler(admin_orders.change_order_status, pattern="^admin:orders:status:"))

    # Tracking number conversation
    tracking_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_orders.ask_tracking_number, pattern="^admin:orders:tracking:")],
        states={
            admin_orders.ASK_TRACKING_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_orders.save_tracking_number)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        name="tracking_number_conversation",
    )
    application.add_handler(tracking_conv)

    # Broadcast
    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_broadcast.start_broadcast, pattern="^admin:broadcast:start$")],
        states={
            admin_broadcast.ASK_BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast.send_broadcast)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        name="broadcast_conversation",
    )
    application.add_handler(broadcast_conv)

    # Broadcast for specific shop
    broadcast_shop_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_broadcast.broadcast_shop_start, pattern="^admin:broadcast:shop:")],
        states={
            admin_broadcast.ASK_BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast.send_broadcast_shop)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        name="broadcast_shop_conversation",
    )
    application.add_handler(broadcast_shop_conv)

    # Shops
    application.add_handler(CallbackQueryHandler(admin_shops.list_shops, pattern="^admin:shops:list:"))
    application.add_handler(CallbackQueryHandler(admin_shops.list_all_shops, pattern="^admin:shops:all:"))
    application.add_handler(CallbackQueryHandler(admin_shops.edit_shop, pattern=r"^admin:shops:edit:\d+$"))
    application.add_handler(CallbackQueryHandler(admin_shops.toggle_shop, pattern="^admin:shops:toggle:"))
    application.add_handler(CallbackQueryHandler(admin_shops.delete_shop_confirm, pattern=r"^admin:shops:delete:\d+$"))
    application.add_handler(CallbackQueryHandler(admin_shops.delete_shop_final, pattern="^admin:shops:delete_final:"))

    # Subscription pending (admin)
    from handlers import subscription as sub_h
    application.add_handler(CallbackQueryHandler(sub_h.admin_list_pending, pattern="^admin:subscription:pending$"))
    application.add_handler(CallbackQueryHandler(sub_h.admin_subscription_detail, pattern="^admin:sub:detail:"))
    application.add_handler(CallbackQueryHandler(sub_h.admin_verify_subscription, pattern="^admin:sub:verify:"))
    application.add_handler(CallbackQueryHandler(sub_h.admin_reject_subscription, pattern="^admin:sub:reject:"))

    application.add_handler(CallbackQueryHandler(support.admin_support_list, pattern="^admin:support:messages$"))
    add_shop_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(admin_shops.start_add_shop, pattern="^admin:shops:add$")],
    states={
        admin_shops.ASK_SHOP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_shops.save_shop_name)],
        admin_shops.ASK_SHOP_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_shops.save_shop_desc)],
    },
    fallbacks=[CommandHandler("cancel", cancel_conversation)],
    name="add_shop_conversation",
    )
    application.add_handler(add_shop_conv)


def _register_messaging_handlers(application: Application):
    """Buyer-seller messaging + support forwarding."""
    application.add_handler(CallbackQueryHandler(msg.open_conversation, pattern="^msg:open_conv:"))
    application.add_handler(CallbackQueryHandler(msg.seller_inbox, pattern="^seller:inbox$"))
    application.add_handler(CallbackQueryHandler(msg.seller_open_conv, pattern="^msg:open:"))
    msg_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(msg.start_send_message, pattern="^msg:(send|reply):")],
    states={
        msg.ASK_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, msg.save_message)],
    },
    fallbacks=[CommandHandler("cancel", msg.cancel_message)],
    name="message_conversation",
    allow_reentry=True,
    )
    application.add_handler(msg_conv)

    # Support conversation — only enters state when user clicks support button
    support_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(support.support_start, pattern="^support:open$")],
    states={
        support.SUPPORT_WAITING: [MessageHandler(filters.TEXT & ~filters.COMMAND, support.support_receive)],
    },
    fallbacks=[CommandHandler("cancel", cancel_conversation)],
    name="support_conversation",
    allow_reentry=True,
    )
    application.add_handler(support_conv)

    # Seller support conversation — only enters state when user clicks seller support button
    seller_support_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(support.seller_support_start, pattern="^support:seller$")],
    states={
        support.SELLER_SUPPORT_WAITING: [MessageHandler(filters.TEXT & ~filters.COMMAND, support.seller_support_receive)],
    },
    fallbacks=[CommandHandler("cancel", cancel_conversation)],
    name="seller_support_conversation",
    allow_reentry=True,
    )
    application.add_handler(seller_support_conv)


def build_application() -> Application:
    proxy_url = os.getenv("PROXY_URL", "")
    builder = Application.builder().token(config.BOT_TOKEN)
    if proxy_url:
        builder = builder.proxy(proxy_url)
    builder = builder.connect_timeout(30.0).read_timeout(30.0).write_timeout(30.0).pool_timeout(30.0)

    # Persistence: ذخیره state کاربران (مکالمات، سبدهای نیمه‌کاره) در فایل پایدار
    # جلوگیری از پاک شدن state با هر ری‌استارت/دیپلوی ربات
    from telegram.ext import PicklePersistence
    persistence_file = os.getenv("BOT_PERSISTENCE_FILE", "/app/data/bot_persistence")
    builder = builder.persistence(PicklePersistence(filepath=persistence_file))

    application = (
    builder
    .rate_limiter(AIORateLimiter(max_retries=3))
    .post_init(_post_init)
    .build()
    )

    _register_customer_handlers(application)
    _register_cart_handlers(application)
    _register_order_handlers(application)
    _register_seller_handlers(application)
    _register_admin_handlers(application)
    _register_messaging_handlers(application)

    application.add_error_handler(error_handler)
    return application


def main():
    config.validate()
    application = build_application()
    logger.info(f"ربات «{config.STORE_NAME}» در حال اجراست...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, poll_interval=2.0, timeout=0, drop_pending_updates=True)
    logger.info("ربات متوقف شد.")


if __name__ == "__main__":
    main()