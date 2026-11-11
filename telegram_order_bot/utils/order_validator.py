"""
اعتبارسنجی متمرکز وضعیت سفارش و انتقال‌های مجاز.

یک نقطه واحد برای همه قوانین transition تا نشت منطق به handlers مختلف نداشته باشیم.
"""
from database.models import (
    ALLOWED_TRANSITIONS,
    ORDER_STATUS_LABELS,
    Order,
    OrderStatus,
)


async def can_transition(order: Order, target_status: OrderStatus, actor: str = "admin") -> tuple[bool, str]:
    """
    بررسی می‌کند آیا انتقال به وضعیت target_status مجاز است یا نه.

    Args:
        order: سفارش مورد نظر
        target_status: وضعیت مقصد
        actor: 'admin' | 'system' | 'customer'

    Returns:
        (True, "") یا (False, "دلیل عدم مجوز")
    """
    current = order.status
    allowed = ALLOWED_TRANSITIONS.get(current, [])

    if target_status not in allowed:
        return False, (
            f"تغییر از «{ORDER_STATUS_LABELS[current]}» به "
            f"«{ORDER_STATUS_LABELS[target_status]}» مجاز نیست."
        )

    # قوانین خاص نقش
    if actor == "customer":
        # مشتری فقط می‌تونه قبل از تأیید فروشنده لغو کنه
        if target_status == OrderStatus.CANCELLED:
            if current in (OrderStatus.DELIVERED, OrderStatus.REFUNDED):
                return False, "این سفارش قابل لغو نیست."
            return True, ""
        if current == OrderStatus.PENDING_PAYMENT and target_status == OrderStatus.PAID:
            return True, ""  # مشتری پرداخت رو تأیید می‌کنه
        # مشتری می‌تونه تحویل رو تأیید کنه (SHIPPED -> DELIVERED)
        if current == OrderStatus.SHIPPED and target_status == OrderStatus.DELIVERED:
            return True, ""
        # مشتری اجازه تغییر به وضعیت‌های دیگه رو نداره
        return False, "شما مجاز به تغییر این وضعیت نیستید."

    if actor in ("admin", "seller"):
        # فروشنده/ادمین همه انتقال‌های مجاز رو می‌تونه انجام بده
        return True, ""

    if actor == "system":
        return True, ""

    return False, "نقش نامعتبر"



def get_allowed_targets(order: Order, actor: str = "admin") -> list[OrderStatus]:
    """
    لیست وضعیت‌هایی که این بازیگر می‌تونه سفارش رو بهش منتقل کنه.
    """
    allowed = ALLOWED_TRANSITIONS.get(order.status, [])
    if actor == "customer":
        return [s for s in allowed if s in (OrderStatus.CANCELLED, OrderStatus.PAID)]
    return allowed
