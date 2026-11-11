"""
Migration 010: convert discount_value and min_order_amount from FLOAT to INTEGER.

مبالغ باید همیشه Integer باشند (تومان) — Float باعث خطای گرد کردن خاموش می‌شود.

این مایگریشن idempotent است: اگر ستون‌ها Integer باشند، کاری نمی‌کند.
برای دیتابیس‌هایی که داده Float دارند، مقادیر با ROUND() به Integer تبدیل می‌شوند.
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


async def migrate(conn):
    # 1) بررسی اینکه ستون‌ها هنوز FLOAT هستند
    result = await conn.execute(text(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'discount_codes'
          AND column_name IN ('discount_value', 'min_order_amount')
        """
    ))
    columns = {row[0]: row[1] for row in result.fetchall()}

    for col in ("discount_value", "min_order_amount"):
        if columns.get(col) != "double precision":
            logger.info(f"Migration 010: column {col} already integer-ish ({columns.get(col)}), skipping")
            continue

        logger.info(f"Migration 010: converting {col} FLOAT -> INTEGER")
        await conn.execute(text(
            f"""
            ALTER TABLE discount_codes
            ALTER COLUMN {col} TYPE INTEGER
            USING ROUND({col})::INTEGER
            """
        ))
        logger.info(f"Migration 010: column {col} converted")

    logger.info("Migration 010 done.")
