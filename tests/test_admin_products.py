#!/usr/bin/env python3
"""
Tests for admin products handlers — especially gallery functions.
Verifies:
  1. All gallery functions are importable at module level (regression for nested-def bug)
  2. Gallery CRUD: add photo, list, delete photo
  3. Image storage utility works correctly
  4. Product edit/delete handlers are accessible
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'telegram_order_bot'))

# ─── Test 1: Import check (regression test for gallery_list AttributeError) ───

def test_gallery_functions_importable():
    """All gallery functions must be accessible as module-level attributes."""
    from handlers.admin import products

    required = [
        'gallery_list',
        'gallery_add_photo',
        'gallery_save_photo',
        'gallery_delete_photo',
    ]
    missing = [name for name in required if not hasattr(products, name)]
    assert not missing, f"Missing module-level functions: {missing}"
    print("✅ All gallery functions are importable at module level")


def test_all_admin_product_handlers_importable():
    """Verify all handlers referenced in main.py exist."""
    from handlers.admin import products

    handlers_referenced_in_main = [
        'list_products',
        'start_add_product',
        'add_name',
        'add_desc',
        'add_price',
        'add_category',
        'add_stock',
        'add_photo',
        'open_product_edit',
        'toggle_product',
        'product_link',
        'start_change_photo',
        'save_change_photo',
        'start_edit_field',
        'save_edit_field',
        'delete_product_confirm',
        'delete_product',
        'gallery_list',
        'gallery_add_photo',
        'gallery_save_photo',
        'gallery_delete_photo',
        'ASK_PHOTO_CHANGE',
    ]
    missing = [name for name in handlers_referenced_in_main if not hasattr(products, name)]
    assert not missing, f"Missing handlers: {missing}"
    print(f"✅ All {len(handlers_referenced_in_main)} admin product handlers are importable")


# ─── Test 2: Image storage utility ───

def test_image_storage_module_structure():
    """Verify image_storage module has required functions."""
    from utils import image_storage

    required = [
        'download_and_store_image',
        'download_and_store_multiple',
        'delete_image',
    ]
    missing = [name for name in required if not hasattr(image_storage, name)]
    assert not missing, f"Missing image_storage functions: {missing}"
    print("✅ image_storage module has all required functions")


def test_delete_image_nonexistent():
    """delete_image should return False for non-existent files."""
    from utils.image_storage import delete_image

    result = delete_image("/storage/products/nonexistent_99999.jpg")
    assert result is False, "delete_image should return False for non-existent file"
    print("✅ delete_image correctly returns False for non-existent file")


def test_delete_image_invalid_path():
    """delete_image should reject paths outside /storage/products/."""
    from utils.image_storage import delete_image

    result = delete_image("/etc/passwd")
    assert result is False, "delete_image should reject invalid paths"
    print("✅ delete_image correctly rejects invalid paths")


# ─── Test 3: Gallery DB operations (requires test DB) ───

async def test_gallery_crud():
    """Test gallery add/list/delete with real DB."""
    from database.db import async_session
    from database.models import Product, Shop, ShopOwner, User, ProductImage
    from sqlalchemy import select

    TEST_UID = 999999800001

    async with async_session() as session:
        # Cleanup
        await session.execute(ProductImage.__table__.delete().where(
            ProductImage.product_id.in_(
                select(Product.id).where(Product.name.like('TEST_GALLERY_%'))
            )
        ))
        await session.execute(Product.__table__.delete().where(Product.name.like('TEST_GALLERY_%')))
        await session.execute(ShopOwner.__table__.delete().where(ShopOwner.user_id == TEST_UID))
        await session.execute(Shop.__table__.delete().where(Shop.name.like('TEST_GALLERY_%')))
        await session.execute(User.__table__.delete().where(User.user_id == TEST_UID))
        await session.commit()

        # Setup
        user = User(user_id=TEST_UID, first_name="GalleryTester", username="gallerytest")
        session.add(user)

        shop = Shop(name="TEST_GALLERY_Shop", description="Gallery test",
                    phone="09000000000", shipping_cost=0,
                    card_number="6037000000000000", card_holder_name="TEST", is_active=True)
        session.add(shop)
        await session.flush()

        owner = ShopOwner(user_id=TEST_UID, shop_id=shop.id)
        session.add(owner)

        product = Product(name="TEST_GALLERY_Product", price=1000, stock=5,
                          shop_id=shop.id, category_id=None, is_active=True)
        session.add(product)
        await session.flush()

        # Add gallery images
        img1 = ProductImage(product_id=product.id, file_id="fid_1", local_url="/storage/products/test1.jpg", sort_order=0)
        img2 = ProductImage(product_id=product.id, file_id="fid_2", local_url="/storage/products/test2.jpg", sort_order=1)
        session.add_all([img1, img2])
        await session.commit()

        # Verify
        stmt = select(ProductImage).where(ProductImage.product_id == product.id).order_by(ProductImage.sort_order)
        images = (await session.execute(stmt)).scalars().all()
        assert len(images) == 2, f"Expected 2 images, got {len(images)}"
        assert images[0].sort_order == 0
        assert images[1].sort_order == 1
        print("✅ Gallery CRUD: added 2 images successfully")

        # Delete one
        await session.delete(images[0])
        await session.commit()

        remaining = (await session.execute(stmt)).scalars().all()
        assert len(remaining) == 1, f"Expected 1 image after delete, got {len(remaining)}"
        assert remaining[0].file_id == "fid_2"
        print("✅ Gallery CRUD: deleted image successfully")

        # Cleanup
        await session.execute(ProductImage.__table__.delete().where(ProductImage.product_id == product.id))
        await session.execute(Product.__table__.delete().where(Product.id == product.id))
        await session.execute(ShopOwner.__table__.delete().where(ShopOwner.user_id == TEST_UID))
        await session.execute(Shop.__table__.delete().where(Shop.id == shop.id))
        await session.execute(User.__table__.delete().where(User.user_id == TEST_UID))
        await session.commit()

    print("✅ Gallery CRUD test passed")


# ─── Test 4: Main.py handler registration (smoke test) ───

def test_main_builds_without_error():
    """Verify main.py can build application without AttributeError."""
    # This is the exact error that crashed the bot
    try:
        from handlers.admin import products
        # Simulate what main.py does
        _ = products.gallery_list
        _ = products.gallery_delete_photo
        _ = products.gallery_add_photo
        _ = products.gallery_save_photo
        _ = products.ASK_PHOTO_CHANGE
        print("✅ main.py handler references resolve correctly")
    except AttributeError as e:
        raise AssertionError(f"main.py would crash: {e}")


# ─── Runner ───

if __name__ == '__main__':
    print("=" * 60)
    print("Running Admin Products & Gallery Tests")
    print("=" * 60)

    # Sync tests
    test_gallery_functions_importable()
    test_all_admin_product_handlers_importable()
    test_image_storage_module_structure()
    test_delete_image_nonexistent()
    test_delete_image_invalid_path()
    test_main_builds_without_error()

    # Async tests
    asyncio.run(test_gallery_crud())

    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED")
    print("=" * 60)
