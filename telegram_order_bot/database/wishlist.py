"""
Wishlist model — items saved for later.
"""
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models import Base, utcnow


class WishlistItem(Base):
    __tablename__ = "wishlist"
    __table_args__ = (
        UniqueConstraint("user_id", "shop_id", "product_id", name="uq_wishlist_user_shop_product"),
        Index("ix_wishlist_user_shop", "user_id", "shop_id"),
        Index("ix_wishlist_product", "product_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), index=True)
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shops.id"), index=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    product: Mapped["Product"] = relationship()