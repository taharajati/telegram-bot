"""Payment method configuration — global + per-shop."""
from config import PAYMENT_METHODS_ENABLED
from database.models import Shop


def get_enabled_payment_methods(shop: Shop | None) -> list[str]:
    """Return enabled payment methods for a shop, considering global flags and shop config."""
    if not shop:
        return []

    methods = []

    # Card-to-card — needs card_number
    if "card_to_card" in PAYMENT_METHODS_ENABLED and shop.card_number:
        methods.append("card_to_card")

    return methods


def should_skip_payment_selection(shop: Shop | None) -> tuple[bool, str | None]:
    """If only one payment method is enabled, skip selection and return the default method."""
    methods = get_enabled_payment_methods(shop)
    if len(methods) == 1:
        return True, methods[0]
    return False, None


def get_payment_method_label(method: str, shop: Shop | None) -> str:
    labels = {
        "card_to_card": f"🧾 کارت به کارت ({shop.card_number[-4:]})" if shop and shop.card_number else "🧾 کارت به کارت",
        "cod": "🚚 پرداخت درب منزل",
    }
    return labels.get(method, method)
