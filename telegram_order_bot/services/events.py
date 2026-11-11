"""
رویدادهای پروژه — EventBus ساده و dataclass‌های payload.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


class Event(Enum):
    ORDER_CREATED = auto()
    ORDER_PAID = auto()
    ORDER_CONFIRMED = auto()
    ORDER_CANCELLED = auto()
    SELLER_REGISTERED = auto()
    SELLER_MESSAGE = auto()


# ─── Payloads ──────────────────────────────────────────────────

@dataclass
class OrderCreatedPayload:
    order_id: int
    shop_id: int
    tracking_code: str
    total_price: float
    buyer_name: str
    buyer_phone: str
    buyer_address: str
    items_count: int
    payment_method: str
    meta: dict = field(default_factory=dict)


@dataclass
class OrderPaidPayload:
    order_id: int
    shop_id: int
    tracking_code: str
    total_price: float
    is_first_sale: bool = False


@dataclass
class OrderCancelledPayload:
    order_id: int
    shop_id: int
    tracking_code: str
    cancelled_by: str
    reason: str = ""


@dataclass
class OrderConfirmedPayload:
    order_id: int
    shop_id: int
    tracking_code: str


@dataclass
class SellerRegisteredPayload:
    shop_id: int
    shop_name: str
    owner_user_id: int


# ─── EventBus ──────────────────────────────────────────────────

Listener = Callable[..., Awaitable[None]]


class EventBus:
    """Simple publish/subscribe event bus.

    Listeners are async callables that receive **kwargs from emit().
    Each event fires all its listeners; failures are logged individually.
    """

    def __init__(self):
        self._listeners: dict[Event, list[Listener]] = {}

    def on(self, event: Event):
        """Decorator: register a listener for *event*."""
        def decorator(fn: Listener) -> Listener:
            self._listeners.setdefault(event, []).append(fn)
            return fn
        return decorator

    def off(self, event: Event, fn: Listener) -> None:
        """Unregister a specific listener."""
        try:
            self._listeners.get(event, []).remove(fn)
        except ValueError:
            pass

    async def emit(self, event: Event, **payload) -> None:
        """Fire all listeners for *event* in sequence (ordered by registration)."""
        for fn in self._listeners.get(event, []):
            try:
                await fn(**payload)
            except Exception:
                logger.exception(f"Listener {fn.__name__} failed for {event}")

    def emit_bg(self, app: Any, event: Event, **payload) -> None:
        """Fire listeners in a background asyncio task.

        Accepts any object with a ``create_task`` method (telegram ``Application``).
        """
        app.create_task(self.emit(event, **payload))


# Singleton
event_bus = EventBus()
