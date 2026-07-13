#!/usr/bin/env python3
"""
End-to-end test: Full payment flow with concurrency/race checks.
Tests:
  1. Card-to-Card flow: reserve → receipt → approve
  2. COD flow: reserve → seller confirm
  3. Race: two orders same product (stock=1)
  4. Race: cron cancel vs seller confirm same order
  5. Idempotency: double-click confirm
  6. Duplicate receipt upload
"""
import asyncio
import os
import sys
import random
from decimal import Decimal

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'telegram_order_bot'))

from database.db import async_session
from database.models import Product, Shop, ShopOwner, User, CartItem, Order, OrderStatus
from services.order_service import create_order_from_cart, attach_card_receipt, transition_order, cancel_order_and_release_stock
from services.payment import auto_cancel_unpaid_orders

# ───────────────── Test Helpers ─────────────────

async def clean_test_data():
    """Clean up test records."""
    async with async_session() as session:
        await session.execute(
            CartItem.__table__.delete().where(CartItem.user_id >= 999000000)
        )
        await session.execute(
            Order.__table__.delete().where(Order.user_id >= 999000000)
        )
        await session.execute(
            Product.__table__.delete().where(Product.name.like('TEST_%'))
        )
        await session.execute(
            Shop.__table__.delete().where(Shop.name.like('TEST_%'))
        )
        await session.execute(
            ShopOwner.__table__.delete().where(ShopOwner.user_id >= 999000000)
        )
        await session.execute(
            User.__table__.delete().where(User.user_id >= 999000000)
        )
        await session.commit()

async def setup_test_data():
    """Create test user, shop, owner, product with stock=1."""
    async with async_session() as session:
        # User
        user = User(user_id=999000001, first_name="TestBuyer", username="testbuyer")
        session.add(user)

        # Shop
        shop = Shop(
            name="TEST_Shop_A",
            description="Test shop for payment flow",
            phone="09120000001",
            channel_link="https://t.me/testshop",
            shipping_cost=0,
            card_number="6037991234567890",  # Will be encrypted
            card_holder_name="TEST SELLER",
            is_active=True
        )
        session.add(shop)
        await session.flush()

        # ShopOwner
        owner = ShopOwner(user_id=999000002, shop_id=shop.id)
        session.add(owner)

        # Product with stock=1 (for race test)
        product = Product(
            shop_id=shop.id,
            name="TEST_Product_Race",
            description="Test product for race condition",
            price=100000,
            stock=1,
            reserved_stock=0,
            is_active=True
        )
        session.add(product)
        await session.flush()

        await session.commit()
        return user, shop, owner, product

async def add_to_cart(user_id, shop_id, product_id, qty=1):
    async with async_session() as session:
        item = CartItem(user_id=user_id, shop_id=shop_id, product_id=product_id, quantity=qty)
        session.add(item)
        await session.commit()

async def get_order_by_tracking(tracking_code):
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(Order).where(Order.tracking_code == tracking_code)
        )
        return result.scalar_one_or_none()

# ───────────────── Test Cases ─────────────────

async def test_1_card_to_card_flow():
    """Card-to-Card: reserve → receipt → approve."""
    print("\n🧪 TEST 1: Card-to-Card full flow")
    await clean_test_data()
    user, shop, owner, product = await setup_test_data()
    await add_to_cart(user.user_id, shop.id, product.id, 1)

    # Create order
    result = await create_order_from_cart(
        user_id=user.user_id,
        shop_id=shop.id,
        customer_info={
            'receiver_name': 'Test Buyer',
            'phone': '09120000001',
            'shipping_address': 'Test Address',
        },
        payment_method='card_to_card'
    )
    order = result.order
    print(f"  ✅ Order created: {order.tracking_code} (status={order.status}, payment={order.payment_status})")
    assert order.status == OrderStatus.PENDING_PAYMENT
    assert order.payment_status == 'pending'

    # Attach receipt
    updated = await attach_card_receipt(order.id, "file_id_12345", "receipt caption")
    print(f"  ✅ Receipt attached: payment_status={updated.payment_status}")
    assert updated.payment_status == 'pending_review'

    # Approve (seller/admin)
    paid = await transition_order(order.id, OrderStatus.PAID, actor='admin')
    print(f"  ✅ Order approved: status={paid.status}, payment_status={paid.payment_status}")
    assert paid.status == OrderStatus.PAID
    assert paid.payment_status == 'paid'

    print("  🎉 TEST 1 PASSED")

async def test_2_cod_flow():
    """COD: reserve → seller confirm."""
    print("\n🧪 TEST 2: COD flow")
    await clean_test_data()
    user, shop, owner, product = await setup_test_data()
    await add_to_cart(user.user_id, shop.id, product.id, 1)

    result = await create_order_from_cart(
        user_id=user.user_id,
        shop_id=shop.id,
        customer_info={
            'receiver_name': 'Test Buyer',
            'phone': '09120000001',
            'shipping_address': 'Test Address',
        },
        payment_method='cod'
    )
    order = result.order
    print(f"  ✅ COD Order created: {order.tracking_code} (status={order.status})")
    assert order.status == OrderStatus.PENDING
    assert order.payment_status == 'pending'

    # Seller confirms
    confirmed = await transition_order(order.id, OrderStatus.CONFIRMED, actor='seller')
    print(f"  ✅ Order confirmed: status={confirmed.status}, payment={confirmed.payment_status}")
    assert confirmed.status == OrderStatus.CONFIRMED
    assert confirmed.payment_status == 'paid'

    print("  🎉 TEST 2 PASSED")

async def test_3_race_two_orders_same_product():
    """Race: two concurrent orders for product with stock=1."""
    print("\n🧪 TEST 3: Race - two orders same product (stock=1)")
    await clean_test_data()
    user, shop, owner, product = await setup_test_data()

    # Two buyers
    user2 = None
    async with async_session() as session:
        user2 = User(user_id=999000003, first_name="Buyer2", username="buyer2")
        session.add(user2)
        await session.commit()

    await add_to_cart(user.user_id, shop.id, product.id, 1)
    await add_to_cart(user2.user_id, shop.id, product.id, 1)

    async def attempt_order(buyer_id, label):
        try:
            result = await create_order_from_cart(
                user_id=buyer_id,
                shop_id=shop.id,
                customer_info={
                    'receiver_name': f'Buyer {label}',
                    'phone': '09120000001',
                    'shipping_address': 'Test Address',
                },
                payment_method='card_to_card'
            )
            return ('success', result.order.tracking_code)
        except ValueError as e:
            return ('failed', str(e))

    # Run concurrently
    r1, r2 = await asyncio.gather(
        attempt_order(user.user_id, 'A'),
        attempt_order(user2.user_id, 'B')
    )

    print(f"  Buyer A: {r1[0]} - {r1[1]}")
    print(f"  Buyer B: {r2[0]} - {r2[1]}")

    # Exactly one should succeed
    successes = [r for r in [r1, r2] if r[0] == 'success']
    failures = [r for r in [r1, r2] if r[0] == 'failed']

    assert len(successes) == 1, f"Expected 1 success, got {len(successes)}"
    assert len(failures) == 1, f"Expected 1 failure, got {len(failures)}"
    assert "موجودی" in failures[0][1] or "stock" in failures[0][1].lower()

    print("  🎉 TEST 3 PASSED (exactly one order succeeded)")

async def test_4_race_cron_vs_seller_confirm():
    """Race: cron tries to cancel PENDING_PAYMENT while seller confirms COD."""
    print("\n🧪 TEST 4: Race - cron cancel vs seller confirm")
    await clean_test_data()
    user, shop, owner, product = await setup_test_data()
    await add_to_cart(user.user_id, shop.id, product.id, 1)

    result = await create_order_from_cart(
        user_id=user.user_id,
        shop_id=shop.id,
        customer_info={
            'receiver_name': 'Test Buyer',
            'phone': '09120000001',
            'shipping_address': 'Test Address',
        },
        payment_method='cod'
    )
    order = result.order
    print(f"  COD Order: {order.tracking_code}")

    # Simulate race: cron cancel (should skip COD) AND seller confirm
    # cron.cancel only touches PENDING_PAYMENT, so COD should be safe
    async def cron_cancel():
        try:
            await auto_cancel_unpaid_orders()
            return 'ran'
        except Exception as e:
            return f'error: {e}'

    async def seller_confirms():
        try:
            confirmed = await transition_order(order.id, OrderStatus.CONFIRMED, actor='seller')
            return ('confirmed', confirmed.status)
        except Exception as e:
            return ('error', str(e))

    # Run concurrently
    cron_result, confirm_result = await asyncio.gather(
        cron_cancel(),
        seller_confirms()
    )

    print(f"  Cron: {cron_result}")
    print(f"  Seller: {confirm_result}")

    # Seller should succeed, cron should not affect COD
    assert confirm_result[0] == 'confirmed'
    assert confirm_result[1] == OrderStatus.CONFIRMED

    # Verify order still exists and is CONFIRMED
    final = await get_order_by_tracking(order.tracking_code)
    assert final is not None
    assert final.status == OrderStatus.CONFIRMED

    print("  🎉 TEST 4 PASSED (COD unaffected by cron)")

async def test_5_idempotent_confirm():
    """Double-click confirm should not create duplicate."""
    print("\n🧪 TEST 5: Idempotent confirm (double-click)")
    await clean_test_data()
    user, shop, owner, product = await setup_test_data()
    await add_to_cart(user.user_id, shop.id, product.id, 1)

    result = await create_order_from_cart(
        user_id=user.user_id,
        shop_id=shop.id,
        customer_info={
            'receiver_name': 'Test Buyer',
            'phone': '09120000001',
            'shipping_address': 'Test Address',
        },
        payment_method='card_to_card'
    )
    order = result.order

    # First receipt
    await attach_card_receipt(order.id, "file_id_111", "receipt 1")

    # Two concurrent approve attempts
    async def approve():
        try:
            paid = await transition_order(order.id, OrderStatus.PAID, actor='admin')
            return ('success', paid.id)
        except Exception as e:
            return ('error', str(e))

    r1, r2 = await asyncio.gather(approve(), approve())

    print(f"  Attempt 1: {r1[0]} - {r1[1]}")
    print(f"  Attempt 2: {r2[0]} - {r2[1]}")

    # One succeeds, one fails gracefully (or both succeed but same order)
    successes = [r for r in [r1, r2] if r[0] == 'success']
    assert len(successes) >= 1, "At least one should succeed"

    # Verify only ONE order exists with this tracking code
    final = await get_order_by_tracking(order.tracking_code)
    assert final is not None

    print("  🎉 TEST 5 PASSED (idempotent transition)")

async def test_6_duplicate_receipt():
    """Same receipt uploaded twice should be rejected."""
    print("\n🧪 TEST 6: Duplicate receipt upload")
    await clean_test_data()
    user, shop, owner, product = await setup_test_data()
    await add_to_cart(user.user_id, shop.id, product.id, 1)

    result = await create_order_from_cart(
        user_id=user.user_id,
        shop_id=shop.id,
        customer_info={
            'receiver_name': 'Test Buyer',
            'phone': '09120000001',
            'shipping_address': 'Test Address',
        },
        payment_method='card_to_card'
    )
    order = result.order

    # First upload
    await attach_card_receipt(order.id, "file_id_AAA", "same receipt")
    print(f"  ✅ First upload OK")

    # Second upload (same file_id + caption) on SAME order
    try:
        await attach_card_receipt(order.id, "file_id_AAA", "same receipt")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  ✅ Duplicate rejected: {e}")
        assert "قبلاً" in str(e) or "already" in str(e).lower()

    # Third upload (same file) on DIFFERENT order (if existed) — but we don't have another order
    # The constraint is per receipt_hash across ALL orders

    print("  🎉 TEST 6 PASSED (duplicate receipt rejected)")

async def test_7_stock_consistency():
    """After successful orders, stock == reserved_stock + available."""
    print("\n🧪 TEST 7: Stock consistency check")
    await clean_test_data()
    user, shop, owner, product = await setup_test_data()
    await add_to_cart(user.user_id, shop.id, product.id, 1)

    result = await create_order_from_cart(
        user_id=user.user_id,
        shop_id=shop.id,
        customer_info={
            'receiver_name': 'Test Buyer',
            'phone': '09120000001',
            'shipping_address': 'Test Address',
        },
        payment_method='cod'
    )
    order = result.order
    await transition_order(order.id, OrderStatus.CONFIRMED, actor='seller')

    async with async_session() as session:
        prod = await session.get(Product, product.id)
        print(f"  Product: stock={prod.stock}, reserved={prod.reserved_stock}, available={prod.available_stock}")
        assert prod.reserved_stock == 0
        assert prod.stock == 0  # was 1, sold 1
        assert prod.available_stock == 0

    print("  🎉 TEST 7 PASSED (stock consistent)")

# ───────────────── Main ─────────────────

async def main():
    print("=" * 60)
    print("FOROSHGRAM - End-to-End Payment Flow Tests")
    print("=" * 60)

    tests = [
        test_1_card_to_card_flow,
        test_2_cod_flow,
        test_3_race_two_orders_same_product,
        test_4_race_cron_vs_seller_confirm,
        test_5_idempotent_confirm,
        test_6_duplicate_receipt,
        test_7_stock_consistency,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            failed += 1
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())