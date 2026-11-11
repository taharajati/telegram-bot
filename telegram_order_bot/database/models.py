"""
مدل‌های دیتابیس با SQLAlchemy 2.0 (async style).
ساختار چندمستأجری + پرداخت + تحویل مالکیت (claim).
"""
import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, Index, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    """Return current UTC datetime (naive, for DB storage)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class OrderStatus:
    PENDING_PAYMENT = "pending_payment"
    PENDING = "pending"
    PAID = "paid"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    CARD_PAYMENT_REJECTED = "card_payment_rejected"


ORDER_STATUS_LABELS = {
    OrderStatus.PENDING_PAYMENT: "⏳ در انتظار پرداخت",
    OrderStatus.PENDING: "⏳ در انتظار بررسی",
    OrderStatus.PAID: "✅ پرداخت شده",
    OrderStatus.CONFIRMED: "✅ تأیید شده",
    OrderStatus.PREPARING: "📦 در حال آماده‌سازی",
    OrderStatus.SHIPPED: "🚚 ارسال شده",
    OrderStatus.DELIVERED: "📦 تحویل داده شده",
    OrderStatus.CANCELLED: "❌ لغو شده",
    OrderStatus.REFUNDED: "↩️ بازگشت وجه",
    OrderStatus.CARD_PAYMENT_REJECTED: "❌ پرداخت رد شده",
}

ALLOWED_TRANSITIONS = {
    OrderStatus.PENDING_PAYMENT: [OrderStatus.PAID, OrderStatus.CANCELLED],
    OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
    OrderStatus.PAID: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED, OrderStatus.REFUNDED],
    OrderStatus.CONFIRMED: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
    OrderStatus.PREPARING: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
    OrderStatus.SHIPPED: [OrderStatus.DELIVERED, OrderStatus.CANCELLED],
    OrderStatus.DELIVERED: [],
    OrderStatus.CANCELLED: [],
    OrderStatus.REFUNDED: [],
    OrderStatus.CARD_PAYMENT_REJECTED: [OrderStatus.PENDING_PAYMENT, OrderStatus.CANCELLED],
}

def _status_history_default() -> str:
    return "[]"


# ─── Shop (فروشگاه) ───────────────────────────────────────────
class Shop(Base):
    __tablename__ = "shops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    channel_link: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # وضعیت فروشگاه: draft → active → suspended → rejected
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # ─── Payment configuration (per-shop) ─── enc-field
    card_number: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    card_holder_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sheba_number: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # enc-field

    # Shipping configuration
    shipping_cost: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    free_shipping_above: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Banner/cover image
    banner_image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    owners: Mapped[list["ShopOwner"]] = relationship(back_populates="shop")
    categories: Mapped[list["Category"]] = relationship(back_populates="shop")


class ShopOwner(Base):
    __tablename__ = "shop_owners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shops.id"))
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    password_salt: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    shop: Mapped["Shop"] = relationship(back_populates="owners")


class Admin(Base):
    """ادمین‌های کل سیستم"""
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ClaimCode(Base):
    """
    کد یک‌بارمصرف تحویل مالکیت فروشگاه به فروشنده.
    ادمین کل ایجاد می‌کنه → فروشنده کلیک می‌کنه → مالکیت ثبت + کد باطل.
    """
    __tablename__ = "claim_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shops.id"))
    created_by: Mapped[int] = mapped_column(BigInteger)  # ادمین کلی که ساخته
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # فروشنده‌ای که استفاده کرد
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    shop: Mapped["Shop"] = relationship()

    @property
    def is_expired(self) -> bool:
        return utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.is_used and not self.is_expired


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shops.id"), index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    shop: Mapped["Shop"] = relationship(back_populates="categories")
    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_category_id", "category_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shops.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    reserved_stock: Mapped[int] = mapped_column(Integer, default=0)
    image_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # local stored image URL
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    category: Mapped["Category"] = relationship(back_populates="products")

    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product",
        order_by="ProductImage.sort_order",
        cascade="all, delete-orphan",
    )

    @property
    def available_stock(self) -> int:
        return max(0, self.stock - self.reserved_stock)


class ProductImage(Base):
    """تصاویر اضافی محصول (گالری چندعکسی)."""
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True)
    file_id: Mapped[str] = mapped_column(String(255), nullable=False)
    local_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # local stored image URL
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped["Product"] = relationship(back_populates="images")


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    current_shop_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("shops.id"), nullable=True, index=True)
    last_shop_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("shops.id"), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    # Fast checkout: saved info from previous orders
    saved_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    saved_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    saved_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Recent shops (JSON: [shop_id, shop_id, ...] max 5)
    recent_shops: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CartItem(Base):
    __tablename__ = "cart"
    __table_args__ = (
        Index("ix_cart_user_id", "user_id"),
        Index("ix_cart_user_shop", "user_id", "shop_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shops.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    product: Mapped["Product"] = relationship()


class WishlistItem(Base):
    __tablename__ = "wishlist"
    __table_args__ = (
        Index("ix_wishlist_user_id", "user_id"),
        Index("ix_wishlist_user_shop", "user_id", "shop_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shops.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    added_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    product: Mapped["Product"] = relationship()


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_shop_status", "shop_id", "status"),
        Index("ix_orders_user_id", "user_id"),
        Index("ix_orders_status", "status"),
        Index("ix_orders_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shops.id"), index=True)
    tracking_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    total_price: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default=OrderStatus.PENDING)
    payment_method: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    payment_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    payment_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    payment_receipt_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    payment_receipt_text: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, default=None)
    payment_receipt_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Receipt hash for de-duplication (SHA-256 of file_id + caption)
    payment_receipt_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)
    receiver_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    shipping_address: Mapped[str] = mapped_column(String(500))
    phone: Mapped[str] = mapped_column(String(30))
    customer_notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, default=None)
    status_history: Mapped[str] = mapped_column(Text, default=_status_history_default)
    tracking_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default=None)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    histories: Mapped[list["OrderHistory"]] = relationship(
        back_populates="order",
        order_by="OrderHistory.changed_at",
        cascade="all, delete-orphan",
    )

    # ⚠️ وضعیت پرداخت مشتق‌شده — منبع حقیقت واحد: `status` (+ `payment_receipt_at` برای تشخیص رسید)
    # ستون `payment_status` legacy است و در حال حذف؛ کد جدید باید از این property بخواند.
    @property
    def payment_status_view(self) -> str:
        if self.status == OrderStatus.PAID:
            return "paid"
        if self.status == OrderStatus.CANCELLED:
            return "cancelled"
        if self.status == OrderStatus.PENDING_PAYMENT:
            # رسید آپلود شده → در انتظار بررسی فروشنده
            if self.payment_receipt_at is not None or self.payment_receipt_file_id:
                return "pending_review"
            return "pending"
        return self.status.lower() if self.status else ""

    def add_status_entry(self, new_status: str, by: str = "system", description: str | None = None, meta: dict | None = None, session=None):
        """
        افزودن رکورد جدول order_history.
        اگر session داده بشه، مستقیماً insert می‌کنه.
        اگر نه، فقط dict برمی‌گردونه.
        """
        entry = OrderHistory(
            order_id=self.id,
            status=new_status,
            changed_by=by,
            description=description,
            meta_json=json.dumps(meta, ensure_ascii=False) if meta else None,
        )
        if session is not None:
            session.add(entry)
        return entry

    def get_status_history(self) -> list["OrderHistory"]:
        """تاریخچه از طریق relationship — lazy load می‌شه."""
        return list(self.histories)


class Conversation(Base):
    """مکالمه بین خریدار و فروشگاه (متن‌باز)."""
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    buyer_id: Mapped[int] = mapped_column(BigInteger, index=True)
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shops.id"), index=True)
    order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("orders.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | closed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """پیام درون یک مکالمه."""
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(Integer, ForeignKey("conversations.id"), index=True)
    sender_role: Mapped[str] = mapped_column(String(10))  # buyer | seller
    content: Mapped[str] = mapped_column(Text)
    has_attachment: Mapped[bool] = mapped_column(Boolean, default=False)
    attachment_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class OrderHistory(Base):
    """تاریخچه تغییرات وضعیت سفارش — جدول جدا از Order."""
    __tablename__ = "order_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    status: Mapped[str] = mapped_column(String(50), index=True)
    changed_by: Mapped[str] = mapped_column(String(50), index=True)  # system | seller | admin | customer
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    meta_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # {"reason": "...", ...}
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    order: Mapped["Order"] = relationship(back_populates="histories")

    def get_meta(self) -> dict:
        if not self.meta_json:
            return {}
        try:
            return json.loads(self.meta_json)
        except Exception:
            return {}


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id"), nullable=True)
    product_name: Mapped[str] = mapped_column(String(150))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped[Optional["Product"]] = relationship()


# ─── Discount Code ─────────────────────────────────────────
class DiscountCode(Base):
    __tablename__ = "discount_codes"
    __table_args__ = (
        Index("ix_discount_shop_code", "shop_id", "code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shops.id"), index=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    # "percent" = 20 means 20% off, "fixed" = 100000 means 100k tomans off
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)
    discount_value: Mapped[int] = mapped_column(Integer, nullable=False)
    min_order_amount: Mapped[int] = mapped_column(Integer, default=0)
    max_uses: Mapped[int] = mapped_column(Integer, default=0)  # 0 = unlimited
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# ─── Restock Subscription ──────────────────────────────────
class RestockSubscription(Base):
    __tablename__ = "restock_subscriptions"
    __table_args__ = (
        Index("ix_restock_product_user", "product_id", "user_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shops.id"), index=True)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    subscribed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# ─── Subscription Plans ──────────────────────────────────
class SubscriptionPlan(Base):
    """پلن‌های اشتراک — seed شده توسط کانفیگ."""
    __tablename__ = "subscription_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)  # به تومان
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    @property
    def price_per_month(self) -> float:
        return self.price / (self.duration_days / 30)


# ─── Shop Subscriptions (append-only, audit trail) ────────
class ShopSubscription(Base):
    """
    هر ردیف = یه اقدام (trial, خرید, تمدید, ارتقا).
    Append-only: ردیف جدید ساخته می‌شه، ردیف قبلی با superseded_at بسته می‌شه.
    ردیف فعلی = آخرین ردیفی که superseded_at IS NULL.
    """
    __tablename__ = "shop_subscriptions"
    __table_args__ = (
        Index("ix_shop_subs_shop_id", "shop_id"),
        Index("ix_shop_subs_end_date", "end_date"),
        Index("ix_shop_subs_approval_status", "approval_status"),
        CheckConstraint(
            "(is_trial = true AND plan_id IS NULL) OR (is_trial = false AND plan_id IS NOT NULL)",
            name="ck_shop_subs_plan_or_trial",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shops.id"), nullable=False, index=True)
    plan_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("subscription_plans.id"), nullable=True)
    is_trial: Mapped[bool] = mapped_column(Boolean, default=False)

    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # وضعیت تأیید رسید توسط ادمین (expired محاسبه‌شه، ذخیره نمی‌شه)
    approval_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | approved | rejected
    receipt_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    receipt_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)
    verified_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # idempotency flag
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # ردیف قبلی رو می‌بنده وقتی ردیف جدید ساخته می‌شه
    superseded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Relationships
    shop: Mapped["Shop"] = relationship()
    plan: Mapped[Optional["SubscriptionPlan"]] = relationship()

    @property
    def is_expired(self) -> bool:
        """محاسبه لحظه‌ای — هیچ‌وقت ذخیره نمی‌شه."""
        return utcnow() > self.end_date

    @property
    def is_active(self) -> bool:
        """معتبر بودن = تأیید شده + نگذشته از end_date + بسته نشده."""
        return (
            self.approval_status == "approved"
            and not self.is_expired
            and self.superseded_at is None
        )
