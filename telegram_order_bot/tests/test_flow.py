"""
تست داخلی: دیتابیس، هلپرها، و جریان کامل مشتری (ثبت‌نام → افزودن محصول → سبد خرید → ثبت سفارش →
تغییر وضعیت توسط ادمین → حذف محصول/دسته با ارجاعات وابسته).
این اسکریپت فقط برای اعتبارسنجی داخلیه و بخشی از تحویل نهایی نیست.
⚠️  از TEST_DATABASE_URL استفاده می‌کند. هیچ‌وقت روی دیتابیس پروداکشن اجرا نشود.
"""
import os
import sys

# ─── CRITICAL: use test DB ───
_test_db_url = os.environ.get("TEST_DATABASE_URL", "").strip()
if _test_db_url:
    os.environ["DATABASE_URL"] = _test_db_url
else:
    print("⚠️  WARNING: TEST_DATABASE_URL not set — using DATABASE_URL (production?)")

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlalchemy import select

import config
from database.db import async_session, init_db
from database.models import CartItem, Category, Order, OrderStatus, Product, User, Shop
from utils.helpers import format_price, generate_tracking_code, to_jalali, to_persian_digits

from handlers import cart, menu, order as order_handlers, start
from handlers.admin import categories as admin_categories
from handlers.admin import products as admin_products
from handlers.admin import orders as admin_orders


def fake_callback_query(data, user_id, chat_id=999):
    query = SimpleNamespace()
    query.data = data
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.message = SimpleNamespace(chat_id=chat_id, delete=AsyncMock())
    return query


def fake_update(query=None, message_text=None, user_id=1, photo=None):
    user = SimpleNamespace(id=user_id, first_name="تها", last_name=None, username="taha_test")
    update = SimpleNamespace()
    update.effective_user = user
    update.effective_chat = SimpleNamespace(id=999)
    update.callback_query = query
    if message_text is not None or photo is not None:
        msg = SimpleNamespace()
        msg.text = message_text
        msg.photo = photo or []
        msg.reply_text = AsyncMock()
        update.message = msg
    else:
        update.message = None
    return update


def fake_context():
    ctx = SimpleNamespace()
    ctx.user_data = {}
    ctx.bot = SimpleNamespace(send_message=AsyncMock(), send_photo=AsyncMock(),
                               create_task=lambda c: asyncio.create_task(c) if hasattr(c, '__await__') else None)
    return ctx


async def main():
    print("۱) ساخت جدول‌ها ...")
    await init_db()

    # Clean up any leftover data from previous runs
    async with async_session() as session:
        from database.models import Message, Conversation, CartItem, WishlistItem, OrderItem, DiscountCode, ShopOwner
        # First null out User FK references to shops
        for u in (await session.execute(select(User))).scalars().all():
            u.current_shop_id = None
            u.last_shop_id = None
        await session.flush()
        # Delete all test data in dependency order (children before parents)
        for t in [Message, Conversation, CartItem, WishlistItem, OrderItem, Order,
                  DiscountCode, Product, Category, ShopOwner, Shop, User]:
            for row in (await session.execute(select(t))).scalars().all():
                await session.delete(row)
        await session.commit()
    print("   دیتابیس تستی پاک‌سازی شد ✅")

    print("۲) تست هلپرها ...")
    assert to_persian_digits("12345") == "۱۲۳۴۵"
    price_text = format_price(150000)
    print("   format_price(150000) =", price_text)
    code = generate_tracking_code()
    print("   generate_tracking_code() =", code)
    assert len(code) == 10
    from datetime import datetime
    print("   to_jalali(now) =", to_jalali(datetime.utcnow()))

    print("۳) ثبت‌نام کاربر ...")
    ctx = fake_context()
    await start.register_user(SimpleNamespace(id=555, first_name="تها", last_name=None, username="taha"))
    async with async_session() as session:
        user = await session.get(User, 555)
        assert user is not None
    print("   کاربر با موفقیت ثبت شد ✅")

    print("۴) ساخت فروشگاه، دسته‌بندی و محصول ...")
    async with async_session() as session:
        shop = Shop(name="فروشگاه تست", description="توضیح تست", is_active=True, status="active", card_number="6037991098765432")
        session.add(shop)
        await session.commit()
        await session.refresh(shop)
        shop_id = shop.id

        cat = Category(name="خوراکی", shop_id=shop_id)
        session.add(cat)
        await session.commit()
        await session.refresh(cat)
        cat_id = cat.id

        prod = Product(name="کیک شکلاتی", description="کیک خونگی خوشمزه", price=150000, stock=5, category_id=cat_id, shop_id=shop_id)
        session.add(prod)
        await session.commit()
        await session.refresh(prod)
        prod_id = prod.id
    print(f"   فروشگاه #{shop_id} | دسته‌بندی #{cat_id} | محصول #{prod_id} ساخته شد ✅")

    # link user to shop so add_to_cart and other handlers find it
    async with async_session() as session:
        user = await session.get(User, 555)
        user.current_shop_id = shop_id
        user.last_shop_id = shop_id
        await session.commit()
    print("   فروشگاه به کاربر متصل شد ✅")

    print("۵) نمایش دسته‌بندی‌ها و محصولات (شبیه‌سازی کلیک کاربر) ...")
    q = fake_callback_query("cat:list", user_id=555)
    await menu.show_categories(fake_update(query=q, user_id=555), ctx)
    assert q.edit_message_text.called
    print("   show_categories: OK ✅")

    q2 = fake_callback_query(f"cat:open:{cat_id}:0", user_id=555)
    await menu.show_products(fake_update(query=q2, user_id=555), ctx)
    assert q2.edit_message_text.called
    print("   show_products: OK ✅")

    q3 = fake_callback_query(f"prod:open:{prod_id}:{cat_id}:0", user_id=555)
    await menu.show_product_detail(fake_update(query=q3, user_id=555), ctx)
    assert q3.edit_message_text.called
    print("   show_product_detail: OK ✅")

    print("۶) افزودن به سبد خرید (۲ عدد) ...")
    ctx.user_data["shop_id"] = shop_id
    for _ in range(2):
        q_add = fake_callback_query(f"cart:add:{prod_id}", user_id=555)
        await cart.add_to_cart(fake_update(query=q_add, user_id=555), ctx)
        assert q_add.answer.called
    async with async_session() as session:
        result = await session.execute(select(CartItem).where(CartItem.user_id == 555))
        cart_item = result.scalar_one()
        assert cart_item.quantity == 2
    print("   add_to_cart x2: OK ✅ (quantity=2)")

    q_view = fake_callback_query("cart:view", user_id=555)
    await cart.view_cart(fake_update(query=q_view, user_id=555), ctx)
    assert q_view.edit_message_text.called
    print("   view_cart: OK ✅")

    print("۷) شروع فرایند ثبت سفارش ...")
    q_start = fake_callback_query("order:start", user_id=555)
    state = await order_handlers.start_checkout(fake_update(query=q_start, user_id=555), ctx)
    assert state == order_handlers.ASK_NAME
    print("   start_checkout -> ASK_NAME: OK ✅")

    upd_name = fake_update(message_text="تها رضایی", user_id=555)
    state = await order_handlers.ask_name(upd_name, ctx)
    assert state == order_handlers.ASK_PHONE
    print("   ask_name -> ASK_PHONE: OK ✅")

    upd_phone = fake_update(message_text="09123456789", user_id=555)
    state = await order_handlers.ask_phone(upd_phone, ctx)
    assert state == order_handlers.ASK_ADDRESS
    print("   ask_phone -> ASK_ADDRESS: OK ✅")

    upd_addr = fake_update(message_text="تهران، خیابان آزادی، پلاک ۱۲۳", user_id=555)
    state = await order_handlers.ask_address(upd_addr, ctx)
    assert state == order_handlers.ASK_PAYMENT_METHOD
    print("   ask_address -> ASK_PAYMENT_METHOD: OK ✅")

    # انتخاب روش پرداخت (کارت به کارت) — چون فقط ۱ روش فعاله، skip شده و مستقیم
    # به خلاصه سفارش رفته (هنوز تو ASK_PAYMENT_METHOD state هستیم).
    # دکمه تأیید سفارش رو می‌زنیم:
    q_confirm = fake_callback_query("order:confirm_card", user_id=555)
    state = await order_handlers.confirm_card_payment(fake_update(query=q_confirm, user_id=555), ctx)
    print("   confirm_card_payment: OK ✅")

    q_confirm = fake_callback_query("order:confirm", user_id=555)
    state = await order_handlers.confirm_order(fake_update(query=q_confirm, user_id=555), ctx)
    print("   confirm_order: OK ✅")

    async with async_session() as session:
        result = await session.execute(select(Order).where(Order.user_id == 555))
        saved_order = result.scalar_one()
        assert saved_order.total_price == 300000
        assert saved_order.status == OrderStatus.PENDING_PAYMENT
        order_id = saved_order.id

        # موجودی رزرو شده باید ۲ تا افزایش پیدا کرده باشه (موجودی واقعی کم نشده)
        product_after = await session.get(Product, prod_id)
        assert product_after.stock == 5
        assert product_after.reserved_stock == 2
        assert product_after.available_stock == 3

        # سبد خرید باید خالی شده باشه
        cart_after = (await session.execute(select(CartItem).where(CartItem.user_id == 555))).scalars().all()
        assert len(cart_after) == 0
    print(f"   سفارش #{order_id} با مبلغ صحیح ثبت شد، موجودی کم شد، سبد خالی شد ✅")

    print("۸) تغییر وضعیت سفارش توسط ادمین (PENDING_PAYMENT → PAID → CONFIRMED) ...")
    admin_id = list(config.ADMIN_IDS)[0]  # use real admin ID from .env
    q_status = fake_callback_query(f"admin:orders:status:{order_id}:paid", user_id=admin_id)
    await admin_orders.change_order_status(fake_update(query=q_status, user_id=admin_id), ctx)
    async with async_session() as session:
        o = await session.get(Order, order_id)
        assert o.status == OrderStatus.PAID
    print("   change_order_status -> PAID: OK ✅")

    q_status2 = fake_callback_query(f"admin:orders:status:{order_id}:confirmed", user_id=admin_id)
    await admin_orders.change_order_status(fake_update(query=q_status2, user_id=admin_id), ctx)
    async with async_session() as session:
        o = await session.get(Order, order_id)
        assert o.status == OrderStatus.CONFIRMED
    assert ctx.bot.send_message.called  # اطلاع‌رسانی به مشتری
    print("   change_order_status -> CONFIRMED + اطلاع‌رسانی به مشتری: OK ✅")

    print("۹) حذف محصول (باید ارجاعات order_item رو null کنه، نه اینکه خطا بده) ...")
    q_del = fake_callback_query(f"admin:products:delete_final:{prod_id}", user_id=admin_id)
    await admin_products.delete_product_final(fake_update(query=q_del, user_id=admin_id), ctx)
    async with async_session() as session:
        p = await session.get(Product, prod_id)
        assert p is None
        oi = (await session.execute(select(Order).where(Order.id == order_id))).scalar_one()
        await session.refresh(oi, attribute_names=["items"])
        assert oi.items[0].product_id is None
        assert oi.items[0].product_name == "کیک شکلاتی"  # تاریخچه دست‌نخورده مونده
    print("   delete_product_final: تاریخچه‌ی سفارش سالم موند ✅")

    print("۱۰) حذف دسته‌بندی (نباید خطا بده حتی اگه محصولی نداشته باشه) ...")
    q_del_cat = fake_callback_query(f"admin:categories:delete_final:{cat_id}", user_id=admin_id)
    await admin_categories.delete_category_final(fake_update(query=q_del_cat, user_id=admin_id), ctx)
    async with async_session() as session:
        c = await session.get(Category, cat_id)
        assert c is None
    print("   delete_category_final: OK ✅")

    print("\n✅✅✅ همه‌ی تست‌ها با موفقیت پاس شدن ✅✅✅")


if __name__ == "__main__":
    asyncio.run(main())
