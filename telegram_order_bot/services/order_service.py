"""
سرویس متمرکز برای مدیریت سفارش — منطق transaction واحد برای هر دو روش پرداخت.
"""
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select, text, update as sql_update
from sqlalchemy.orm import selectinload

from database.db import async_session
from database.models import (
    CartItem,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    Shop,
    User,
    utcnow,
)
from services.payment import release_reserved_stock
from utils.helpers import format_price

logger = logging.getLogger(__name__)


@dataclass
class CustomerInfo:
    """اطلاعات مشتری برای ثبت سفارش."""
    receiver_name: str
    phone: str
    shipping_address: str
    notes: str = ""


@dataclass
class OrderResult:
    """نتیجه‌ی ایجاد سفارش."""
    order: Order
    tracking_code: str
    total_price: int
    items_count: int
    discount_code: str = ""
    discount_amount: int = 0


async def _generate_tracking_code() -> str:
    """تولید کد پیگیری منحصر‌به‌فرد."""
    import random
    import string
    now = datetime.now(timezone.utc)
    prefix = now.strftime("%y%m%d")
    suffix = "".join(random.choices(string.digits, k=6))
    return f"{prefix}{suffix}"


async def create_order_from_cart(
    user_id: int,
    shop_id: int,
    customer_info: CustomerInfo,
    payment_method: str,  # "cod" | "card_to_card"
    discount_code: str = "",
    discount_amount: int = 0,
) -> OrderResult:
    """
    یک تراکنش کامل: اعتبارسنجی سبد، رزرو موجودی، ساخت سفارش، انتقال اقلام، خالی کردن سبد.
    همه در یک تراکنش اتمیک انجام می‌شود.
    """
    async with async_session() as session:
        # 0. Advisory lock per user_id — prevents race between restarts / multi-instance
        #    Released automatically on commit/rollback (no manual unlock needed)
        await session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": user_id},
        )

        # 1. لود سبد با lock روی محصولات (SELECT ... FOR UPDATE)
        cart_items = await _load_and_lock_cart_items(session, user_id, shop_id)
        if not cart_items:
            raise ValueError("سبد خرید خالی است")

        # Sort by product_id to prevent deadlock (consistent lock order)
        cart_items = sorted(cart_items, key=lambda i: i.product_id)

        # 2. اعتبارسنجی موجودی و محاسبه جمع + رزرو اتمیک با UPDATE ... RETURNING
        total_price = 0
        order_items_data = []
        for item in cart_items:
            await session.refresh(item, attribute_names=["product"])
            product: Product = item.product

            if not product or not product.is_active:
                raise ValueError(f"محصول «{item.product.name if item.product else 'نامشخص'}» دیگر در دسترس نیست")

            if product.shop_id != shop_id:
                raise ValueError("محصول از فروشگاه دیگری است")

            # Atomic reserve stock in single UPDATE + RETURNING (replaces separate SELECT FOR UPDATE + UPDATE)
            result = await session.execute(
                text("""
                    UPDATE products
                    SET reserved_stock = reserved_stock + :qty
                    WHERE id = :pid AND (stock - reserved_stock) >= :qty
                    RETURNING id, stock, reserved_stock
                """),
                {"qty": item.quantity, "pid": product.id},
            )
            row = result.fetchone()
            if not row:
                raise ValueError(
                    f"موجودی «{product.name}» هم‌زمان توسط کاربر دیگری رزرو شد"
                )
            # row = (id, stock, reserved_stock)
            product.stock = row[1]
            product.reserved_stock = row[2]

            subtotal = product.price * item.quantity
            total_price += subtotal

            order_items_data.append({
                "product_id": product.id,
                "product_name": product.name,
                "quantity": item.quantity,
                "unit_price": product.price,
            })

        # 4. اعمال تخفیف و اضافه کردن هزینه ارسال
        shop: Shop = await session.get(Shop, shop_id)
        shipping_cost = shop.shipping_cost or 0 if shop else 0
        total_price += shipping_cost

        # Clamp discount: don't let total go negative
        if discount_amount > 0:
            discount_amount = min(discount_amount, total_price)
        total_price = max(0, total_price - discount_amount)

        # 5. ساخت سفارش
        tracking_code = await _generate_tracking_code()
        initial_status = OrderStatus.PENDING_PAYMENT if payment_method == "card_to_card" else OrderStatus.PENDING

        order = Order(
            tracking_code=tracking_code,
            user_id=user_id,
            shop_id=shop_id,
            status=initial_status,
            payment_method=payment_method,
            total_price=total_price,
            receiver_name=customer_info.receiver_name,
            phone=customer_info.phone,
            shipping_address=customer_info.shipping_address,
            customer_notes=customer_info.notes,
        )
        session.add(order)
        await session.flush()  # برای گرفتن order.id

        # 6. ساخت OrderItemها
        for oi in order_items_data:
            session.add(OrderItem(
                order_id=order.id,
                product_id=oi["product_id"],
                product_name=oi["product_name"],
                quantity=oi["quantity"],
                unit_price=oi["unit_price"],
            ))

        # 7. تاریخچه وضعیت
        order.add_status_entry(initial_status, by="system", session=session)

        # 8. خالی کردن سبد خرید
        for item in cart_items:
            await session.delete(item)

        # 9. کامیت نهایی
        await session.commit()

        # Refresh برای احضار relationships
        await session.refresh(order, attribute_names=["items"])

    logger.info(f"Order {tracking_code} created for user {user_id}, shop {shop_id}, method {payment_method}")
    return OrderResult(
        order=order,
        tracking_code=tracking_code,
        total_price=total_price,
        items_count=len(order_items_data),
        discount_code=discount_code,
        discount_amount=discount_amount,
    )


async def _load_and_lock_cart_items(session, user_id: int, shop_id: int) -> list[CartItem]:
    """بارگذاری اقلام سبد — فقط لود می‌کند (قفل در create_order_from_cart با UPDATE اتمیک)."""
    result = await session.execute(
        select(CartItem)
        .where(CartItem.user_id == user_id, CartItem.shop_id == shop_id)
        .options(selectinload(CartItem.product))
    )
    return list(result.scalars().all())


async def attach_card_receipt(
    order_id: int,
    receipt_file_id: str,
    receipt_caption: str = "",
) -> Order:
    """پیوست رسید کارت به سفارش موجود — با de-duplication."""
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order:
            raise ValueError("سفارش یافت نشد")

        if order.payment_method != "card_to_card":
            raise ValueError("این سفارش برای پرداخت کارت به کارت نیست")

        # ── De-duplication: hash of file_id + caption ──
        receipt_hash = hashlib.sha256(
            f"{receipt_file_id}:{receipt_caption}".encode()
        ).hexdigest()

        # Check if this exact receipt was already used on ANOTHER order
        existing = await session.execute(
            select(Order).where(
                Order.payment_receipt_hash == receipt_hash,
                Order.id != order_id,
            )
        )
        dup = existing.scalar_one_or_none()
        if dup:
            raise ValueError(
                f"⚠️ این رسید قبلاً برای سفارش #{dup.tracking_code} استفاده شده. "
                "لطفاً رسید پرداخت مربوط به همین سفارش رو ارسال کنید."
            )

        order.payment_receipt_hash = receipt_hash

        order.payment_receipt_file_id = receipt_file_id
        order.payment_receipt_text = receipt_caption
        # بدون این، کرون «سفارش رهاشده» رسید رو نمی‌بینه و سفارش پرداخت‌شده رو بعد از ۱۵ دقیقه لغو می‌کنه
        order.payment_receipt_at = utcnow()
        order.add_status_entry("receipt_uploaded", by="customer", session=session)

        await session.commit()
        await session.refresh(order)

    logger.info(f"Card receipt attached to order {order.tracking_code}")
    return order


async def finalize_cod_stock(order_id: int) -> Order:
    """کم کردن موجودی واقعی برای COD بعد از تأیید فروشنده (CONFIRMED)."""
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order:
            raise ValueError("سفارش یافت نشد")

        if order.payment_method != "cod":
            raise ValueError("فقط برای سفارش‌های درب منزل")

        # موجودی رزرو شده قبلاً در create_order_from_cart کم شده (available_stock)
        # وضعیت با status مشخص می‌شود — payment_status legacy حذف شد
        order.add_status_entry("cod_confirmed", by="admin", session=session)

        await session.commit()
        await session.refresh(order, attribute_names=["items"])

    return order


async def cancel_order_and_release_stock(order_id: int, actor: str = "customer", bot=None) -> Order:
    """لغو سفارش و آزادسازی موجودی رزرو شده."""
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order:
            raise ValueError("سفارش یافت نشد")

        if order.status in (OrderStatus.DELIVERED, OrderStatus.CANCELLED, OrderStatus.REFUNDED):
            raise ValueError("این سفارش قابل لغو نیست")

        # آزادسازی موجودی رزرو شده
        await release_reserved_stock(order_id)

        order.status = OrderStatus.CANCELLED
        order.add_status_entry("order_cancelled", by=actor, session=session)
        order.add_status_entry(OrderStatus.CANCELLED, by=f"{actor}_cancel", session=session)

        await session.commit()
        await session.refresh(order, attribute_names=["items"])

    # ═══ Emit events ═══
    if bot:
        from services.events import event_bus, Event
        await event_bus.emit(
            Event.ORDER_CANCELLED,
            order_id=order.id,
            shop_id=order.shop_id,
            tracking_code=order.tracking_code,
            cancelled_by=actor,
            bot=bot,
        )
        await _check_first_sale(order, bot)

    return order


async def transition_order(order_id: int, target_status: OrderStatus, actor: str = "admin", bot=None) -> Order:
    """
    تغییر وضعیت سفارش با اعتبارسنجی مركـــــــــــــــز.
    تمام تغییرات وضعیت باید از این تابع رد شوند.
    """
    from utils.order_validator import can_transition

    async with async_session() as session:
        # Lock the Order row FOR UPDATE to prevent race with cron cleanup
        order = await session.get(Order, order_id, with_for_update=True)
        if not order:
            raise ValueError("سفارش یافت نشد")

        # اعتبارسنجی با ولیدیتور مرکزی
        allowed, reason = await can_transition(order, target_status, actor=actor)
        if not allowed:
            raise ValueError(reason)

        # اعمال انتقال
        order.status = target_status
        order.add_status_entry(target_status, by=actor, session=session)

        # منطق جانبی بر اساس وضعیت مقصد
        if target_status == OrderStatus.PAID and order.payment_method in ("card_to_card",):
            # تایید پرداخت کارت: موجودی نهایی شود
            await session.refresh(order, attribute_names=["items"])
            for item in order.items:
                if item.product_id:
                    await session.execute(
                        sql_update(Product)
                        .where(Product.id == item.product_id)
                        .values(stock=Product.stock - item.quantity, reserved_stock=Product.reserved_stock - item.quantity)
                    )
            # ⚠️ Check low stock after card payment confirmation
            await _check_low_stock_after_reduction(session, order.shop_id, order.items, bot)

        elif target_status == OrderStatus.CONFIRMED and order.payment_method == "cod":
            # تایید درب منزل: موجودی نهایی شود
            await session.refresh(order, attribute_names=["items"])
            for item in order.items:
                if item.product_id:
                    await session.execute(
                        sql_update(Product)
                        .where(Product.id == item.product_id)
                        .values(stock=Product.stock - item.quantity, reserved_stock=Product.reserved_stock - item.quantity)
                    )
            # ⚠️ Check low stock after COD confirmation
            await _check_low_stock_after_reduction(session, order.shop_id, order.items, bot)

        elif target_status == OrderStatus.CANCELLED:
            # آزادسازی موجودی رزرو شده
            await release_reserved_stock(order_id)

        await session.commit()
        # Refresh relationships before session closes so _order_detail_text can access them
        await session.refresh(order, attribute_names=["items", "histories"])

    logger.info(f"Order {order_id} transitioned to {target_status} by {actor}")

    # ═══ Emit events ═══
    from services.events import event_bus, Event

    if target_status == OrderStatus.PAID:
        await _check_first_sale(order, bot)
        await event_bus.emit(
            Event.ORDER_PAID,
            order_id=order.id,
            shop_id=order.shop_id,
            bot=bot,
            is_first_sale=False,
        )
    elif target_status == OrderStatus.CANCELLED:
        await event_bus.emit(
            Event.ORDER_CANCELLED,
            order_id=order.id,
            shop_id=order.shop_id,
            tracking_code=getattr(order, "tracking_code", str(order.id)),
            cancelled_by=actor,
        )
    elif target_status == OrderStatus.CONFIRMED:
        await event_bus.emit(
            Event.ORDER_CONFIRMED,
            order_id=order.id,
            shop_id=order.shop_id,
            tracking_code=getattr(order, "tracking_code", str(order.id)),
        )

    return order


async def _check_first_sale(order: Order, bot=None):
    """اگر اولین سفارش paid این فروشگاه باشد، از طریق EventBus جشن بگیر."""
    from services.events import event_bus, Event

    if not bot:
        return

    # Check how many orders for this shop have ever reached ≥ PAID
    async with async_session() as session:
        result = await session.execute(
            select(func.count()).select_from(Order).where(
                Order.shop_id == order.shop_id,
                Order.id <= order.id,
                Order.status.in_([
                    OrderStatus.PAID,
                    OrderStatus.CONFIRMED,
                    OrderStatus.PREPARING,
                    OrderStatus.SHIPPED,
                    OrderStatus.DELIVERED,
                    OrderStatus.REFUNDED,
                ]),
            )
        )
        paid_count = result.scalar() or 0
        if paid_count == 1:
            await event_bus.emit(
                Event.ORDER_PAID,
                order_id=order.id,
                shop_id=order.shop_id,
                bot=bot,
                is_first_sale=True,
            )


async def _check_low_stock_after_reduction(
    session, shop_id: int, items: list, bot=None
):
    """Check if any product stock dropped below threshold and notify seller."""
    if not bot:
        return

    from database.models import Product
    from services.notification_service import get_notification_service

    threshold = 5  # threshold for low stock warning
    ns = get_notification_service(bot)

    for item in items:
        if not item.product_id:
            continue
        # Refresh product to get updated stock
        await session.refresh(item, attribute_names=["product"])
        product = getattr(item, "product", None)
        if not product:
            # Load product
            result = await session.execute(
                select(Product).where(Product.id == item.product_id)
            )
            product = result.scalar_one_or_none()

        if product and product.is_active and product.available_stock < threshold:
            try:
                await ns.send_to_seller(
                    shop_id,
                    f"⚠️ هشدار موجودی کم\n\n"
                    f"محصول «{product.name}»\n"
                    f"موجودی: {product.available_stock} عدد باقی‌مانده\n\n"
                    f"📦 لطفاً موجودی رو چک و آپدیت کنید.",
                )
            except Exception as e:
                logger.warning(f"Low stock notification failed for product {product.id}: {e}")
