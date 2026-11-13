"""
Payment service — stock management, card-to-card receipt flow, COD.
card_to_card + COD remain (Zarinpal removed).
"""
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import text, select

import config
from database.db import async_session
from database.models import Order, OrderStatus, Shop, Product, utcnow

logger = logging.getLogger(__name__)


async def reserve_stock_atomic(
    session, product_id: int, quantity: int
) -> bool:
    """Atomically reserve stock in a single UPDATE + RETURNING round-trip.

    Merges SELECT FOR UPDATE + UPDATE into one statement.
    Returns True if stock reserved, False if insufficient.
    """
    result = await session.execute(
        text("""
            UPDATE products
            SET reserved_stock = reserved_stock + :qty
            WHERE id = :pid AND (stock - reserved_stock) >= :qty
            RETURNING id, stock, reserved_stock
        """),
        {"qty": quantity, "pid": product_id},
    )
    return result.rowcount > 0


async def reserve_stock_atomic_order(order_id: int, target_status: OrderStatus = OrderStatus.PENDING_PAYMENT) -> bool:
    """Atomically reserve stock for an entire order (standalone version for backward compatibility)."""
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order:
            return False

        # Idempotency: if stock already reserved for this order, skip
        if order.status in (OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            logger.info(f"Stock reservation skipped — order {order_id} already in status {order.status}")
            return True
        if order.status == OrderStatus.CANCELLED:
            logger.warning(f"Stock reservation rejected — order {order_id} already cancelled")
            return False

        await session.refresh(order, attribute_names=["items"])

        # Check stock availability for all items
        for item in order.items:
            if not item.product_id:
                continue
            result = await session.execute(
                select(Product).where(Product.id == item.product_id).with_for_update()
            )
            product = result.scalar_one_or_none()
            if not product or product.available_stock < item.quantity:
                logger.warning(f"Insufficient stock for product_id={item.product_id} in order {order_id} (available: {product.available_stock if product else 0}, needed: {item.quantity})")
                return False

        # Reserve stock atomically
        for item in order.items:
            if not item.product_id:
                continue
            await session.execute(
                text("UPDATE products SET reserved_stock = reserved_stock + :qty WHERE id = :pid"),
                {"qty": item.quantity, "pid": item.product_id},
            )

        order.status = target_status
        order.add_status_entry("stock_reserved", by="system", session=session)
        await session.commit()

    logger.info(f"Stock reserved for order {order_id}")
    return True


async def cancel_order_with_refund(order_id: int, by: str = "system") -> bool:
    """Cancel order and release reserved stock (idempotent)."""
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order:
            return False

        # Only refund if stock was actually reserved
        if order.status not in (OrderStatus.PENDING_PAYMENT, OrderStatus.PAID, OrderStatus.CONFIRMED):
            return True  # Nothing to refund

        # Release stock
        await session.refresh(order, attribute_names=["items"])
        for item in order.items:
            if item.product_id:
                await session.execute(
                    text("UPDATE products SET reserved_stock = GREATEST(0, reserved_stock - :qty) WHERE id = :pid"),
                    {"qty": item.quantity, "pid": item.product_id},
                )

        order.status = OrderStatus.CANCELLED
        order.cancellation_reason = by
        order.add_status_entry("cancelled", by=by, session=session)
        await session.commit()

    logger.info(f"سفارش {order_id} لغو و موجودی آزاد شد — by={by}")
    return True


async def auto_cancel_unpaid_orders() -> int:
    """Cron job: cancel orders stuck beyond timeout.

    برای هر سفارش با `FOR UPDATE NOWAIT` قفل می‌گیره تا با transition_order
    همزمان race condition پیش نیاد. اگر قفل نگیره (order توی حال پردازشه)، رد می‌شه.

    تایم‌اوت‌ها:
    - کارت‌به‌کارت بدون رسید: ۱۵ دقیقه
    - کارت‌به‌کارت با رسید (در انتظار فروشنده): ۴۸ ساعت
    - COD (PENDING): ۳۰ روز — فروشنده تایید نکرده
    - COD (CONFIRMED منتظر ارسال): ۳۰ روز
    """
    card_timeout_no_receipt = timedelta(minutes=15)
    card_timeout_after_receipt = timedelta(hours=48)
    cod_pending_timeout = timedelta(days=30)  # COD سفارش‌های

    cancelled = 0
    now = utcnow()  # naive UTC، هم‌نوع با ستون‌های created_at / payment_receipt_at (aware منهای naive خطا می‌ده)

    async with async_session() as session:
        # ── ۱. PENDING_PAYMENT (همه روش‌ها) ──
        result = await session.execute(
            select(Order).where(
                Order.status == OrderStatus.PENDING_PAYMENT,
            ).with_for_update(skip_locked=True)
        )
        for order in result.scalars().all():
            if order.payment_method == "card_to_card":
                if order.payment_receipt_at is not None:
                    if now - order.payment_receipt_at > card_timeout_after_receipt:
                        await _cancel_and_release_in_session(session, order, by="auto_timeout_card_after_receipt")
                        cancelled += 1
                else:
                    if now - order.created_at > card_timeout_no_receipt:
                        await _cancel_and_release_in_session(session, order, by="auto_timeout_card_no_receipt")
                        cancelled += 1
            elif order.payment_method == "cod":
                # COD در PENDING_PAYMENT (نادر) — کلاً timeout نداره ولی احتیاطاً
                if now - order.created_at > cod_pending_timeout:
                    await _cancel_and_release_in_session(session, order, by="auto_timeout_cod_pre_confirmed")
                    cancelled += 1

        # ── ۲. PENDING (COD — فروشنده هنوز تأیید نکرده) ──
        # این سفارش‌ها reserved_stock دارن ولی هیچ‌وقت finalize نشدن
        result2 = await session.execute(
            select(Order).where(
                Order.status == OrderStatus.PENDING,
                Order.payment_method == "cod",
            ).with_for_update(skip_locked=True)
        )
        for order in result2.scalars().all():
            if now - order.created_at > cod_pending_timeout:
                await _cancel_and_release_in_session(session, order, by="auto_timeout_cod_pending")
                cancelled += 1

        await session.commit()

    logger.info(f"auto_cancel_unpaid_orders: {cancelled} سفارش لغو شد")
    return cancelled


async def _cancel_and_release_in_session(session, order: Order, by: str):
    """Cancel an order and release stock within an existing session/transaction."""
    if order.status in (OrderStatus.DELIVERED, OrderStatus.CANCELLED, OrderStatus.REFUNDED):
        return
    await session.refresh(order, attribute_names=["items"])
    for item in order.items:
        if item.product_id:
            await session.execute(
                text("UPDATE products SET reserved_stock = GREATEST(0, reserved_stock - :qty) WHERE id = :pid"),
                {"qty": item.quantity, "pid": item.product_id},
            )
    order.status = OrderStatus.CANCELLED
    order.cancellation_reason = by
    order.add_status_entry("cancelled", by=by, session=session)


# ─── RESTORED: Functions missed during Zarinpal cleanup ─────────────


async def release_reserved_stock(order_id: int) -> bool:
    """Release stock reservation for an order (idempotent)."""
    return await cancel_order_with_refund(order_id, by="release_reserved_stock")


async def finalize_card_payment(order_id: int) -> bool:
    """Finalize card payment: move order to PAID status and finalize stock deduction."""
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order:
            return False
        if order.status not in (OrderStatus.PENDING_PAYMENT,):
            logger.warning(f"finalize_card_payment: سفارش {order_id} در وضعیت {order.status} قابل تایید نیست")
            return False

        # Finalize stock: decrement stock and reserved_stock
        await session.refresh(order, attribute_names=["items"])
        for item in order.items:
            if item.product_id:
                await session.execute(
                    text("UPDATE products SET stock = GREATEST(0, stock - :qty), reserved_stock = GREATEST(0, reserved_stock - :qty) WHERE id = :pid"),
                    {"qty": item.quantity, "pid": item.product_id},
                )

        order.status = OrderStatus.PAID
        order.add_status_entry("card_payment_approved", by="seller", session=session)
        await session.commit()

    logger.info(f"پرداخت کارت‌به‌کارت سفارش {order_id} تایید شد و موجودی نهایی گردید")
    return True


async def reject_card_payment(order_id: int, reason: str = "") -> bool:
    """Reject card payment: release reserved stock and mark order so customer can retry or convert.
    Requires a reason from the seller."""
    if not reason or not reason.strip():
        raise ValueError("دلیل رد پرداخت الزامی است.")
    
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order:
            return False
        if order.status not in (OrderStatus.PENDING_PAYMENT,):
            logger.warning(f"reject_card_payment: سفارش {order_id} در وضعیت {order.status} قابل رد نیست")
            return False

        # Release reserved stock
        await session.refresh(order, attribute_names=["items"])
        for item in order.items:
            if item.product_id:
                await session.execute(
                    text("UPDATE products SET reserved_stock = GREATEST(0, reserved_stock - :qty) WHERE id = :pid"),
                    {"qty": item.quantity, "pid": item.product_id},
                )

        order.status = OrderStatus.CANCELLED
        order.add_status_entry("card_payment_rejected", by="seller", meta={"reason": reason.strip()}, session=session)
        await session.commit()

    logger.info(f"پرداخت کارت‌به‌کارت سفارش {order_id} رد شد (دلیل: {reason.strip()}) و موجودی آزاد گردید")
    return True


async def retry_card_receipt(order_id: int, file_id: str | None = None, receipt_text: str | None = None) -> bool:
    """Update receipt (photo or text) for an order (new receipt uploaded by customer)."""
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order:
            return False
        if order.status != OrderStatus.PENDING_PAYMENT:
            # Allow retry for rejected orders (seller rejected, customer re-uploading)
            # Rejected orders are CANCELLED status (payment_status was "rejected")
            if order.status == OrderStatus.CANCELLED:
                order.status = OrderStatus.PENDING_PAYMENT
                # Re-reserve stock since it was released on rejection
                await session.refresh(order, attribute_names=["items"])
                for item in order.items:
                    if item.product_id:
                        await session.execute(
                            text("UPDATE products SET reserved_stock = reserved_stock + :qty WHERE id = :pid"),
                            {"qty": item.quantity, "pid": item.product_id},
                        )
            else:
                logger.warning(f"retry_card_receipt: سفارش {order_id} در وضعیت {order.status} قابل تغییر نیست")
                return False

        if file_id:
            order.payment_receipt_file_id = file_id
            order.payment_receipt_text = None
        elif receipt_text:
            order.payment_receipt_text = receipt_text
            order.payment_receipt_file_id = None
        else:
            return False

        order.payment_receipt_at = utcnow()
        order.add_status_entry("receipt_retry_uploaded", by="customer", session=session)
        await session.commit()

    logger.info(f"رسید جدید برای سفارش {order_id} ذخیره شد")
    return True


async def convert_to_cod(order_id: int) -> bool:
    """Convert card_to_card order to COD. Keep stock reserved (just change payment method)."""
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order:
            return False
        if order.status != OrderStatus.PENDING_PAYMENT:
            logger.warning(f"convert_to_cod: سفارش {order_id} در وضعیت {order.status} قابل تبدیل نیست")
            return False

        order.payment_method = "cod"
        order.status = OrderStatus.PENDING
        order.add_status_entry("converted_to_cod", by="customer", session=session)
        await session.commit()

    logger.info(f"سفارش {order_id} به روش درب منزل تبدیل شد (موجودی رزرو شده باقی می‌ماند)")
    return True


async def finalize_stock_deduction(order_id: int) -> bool:
    """Finalize stock deduction: move reserved stock to actual stock reduction. Used by admin when confirming COD/paid orders."""
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order:
            return False
        if order.status not in (OrderStatus.PENDING, OrderStatus.PENDING_PAYMENT, OrderStatus.PAID):
            return False

        # Finalize stock: decrement stock and reserved_stock
        await session.refresh(order, attribute_names=["items"])
        for item in order.items:
            if item.product_id:
                await session.execute(
                    text("UPDATE products SET stock = GREATEST(0, stock - :qty), reserved_stock = GREATEST(0, reserved_stock - :qty) WHERE id = :pid"),
                    {"qty": item.quantity, "pid": item.product_id},
                )

        order.status = OrderStatus.CONFIRMED
        order.add_status_entry("stock_finalized", by="admin", session=session)
        await session.commit()

    logger.info(f"موجودی سفارش {order_id} نهایی شد")
    return True


async def cleanup_abandoned_payments(minutes: int = 15):
    """Cancel orders stuck in PENDING_PAYMENT for longer than `minutes`.

    ONLY cancels orders WITHOUT receipt uploaded — orders with receipt are 
    seller's responsibility (48h timeout via auto_cancel_unpaid_orders).

    Uses atomic UPDATE ... RETURNING to prevent race with transition_order
    (if seller already confirmed, the WHERE status condition fails and this
    does nothing for that order).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    async with async_session() as session:
        result = await session.execute(
            text("""
                UPDATE orders
                SET status = 'cancelled',
                    cancellation_reason = 'cleanup_abandoned',
                    updated_at = NOW()
                WHERE id IN (
                    SELECT id FROM orders
                    WHERE status = 'pending_payment'
                      AND payment_method = 'card_to_card'
                      AND payment_receipt_at IS NULL
                      AND created_at < :cutoff
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id
            """),
            {"cutoff": cutoff.replace(tzinfo=None)},
        )
        rows = result.fetchall()
        cancelled_ids = [r[0] for r in rows]

        # Release stock for each cancelled order
        for oid in cancelled_ids:
            _cancel_release_stock_inline(session, oid)

        await session.commit()

    if cancelled_ids:
        logger.info(f"cleanup_abandoned_payments: cancelled {len(cancelled_ids)} orders: {cancelled_ids}")
    else:
        logger.info("cleanup_abandoned_payments: no orders to cancel")
    return len(cancelled_ids)


def _cancel_release_stock_inline(session, order_id: int):
    """Release reserved stock for a cancelled order (inline, no session management)."""
    from sqlalchemy import text as sql_text
    session.execute(
        sql_text(
            "UPDATE products SET reserved_stock = GREATEST(0, reserved_stock - ("
            "SELECT COALESCE(SUM(oi.quantity), 0) FROM order_items oi WHERE oi.order_id = :oid AND oi.product_id = products.id"
            ")) WHERE id IN (SELECT product_id FROM order_items WHERE order_id = :oid2)"
        ),
        {"oid": order_id, "oid2": order_id},
    )
