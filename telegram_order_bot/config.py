"""تنظیمات اصلی ربات — Foroshgram."""
import os
from dotenv import load_dotenv

load_dotenv()

# توکن و دسترسی‌ها
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

_admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = {int(x.strip()) for x in _admin_ids_raw.split(",") if x.strip()}

# دیتابیس
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
# دیتابیس مجزا برای تست‌ها — مهم: از دیتابیس پروداکشن جدا باشه
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "").strip() or DATABASE_URL
# اگر DATABASE_URL نداشته باشیم، برای توسعه محلی fallback به SQLite
if not DATABASE_URL:
    DB_PATH = os.getenv("DB_PATH", "data/orders.db")
    DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

# فایل‌ها
PRODUCTS_IMAGES_PATH = os.getenv("PRODUCTS_IMAGES_PATH", "data/images/")

# نوتیفیکیشن
_notif_channel_raw = os.getenv("NOTIFICATION_CHANNEL_ID", "").strip()
NOTIFICATION_CHANNEL_ID = int(_notif_channel_raw) if _notif_channel_raw else None

# ظاهر و برندینگ
STORE_NAME = os.getenv("STORE_NAME", "فروشگرام")
CURRENCY_LABEL = os.getenv("CURRENCY_LABEL", "تومان")

# پیش‌فرض
DEFAULT_SHOP_ID = int(os.getenv("DEFAULT_SHOP_ID", "1"))

# نمایش
ITEMS_PER_PAGE = 6

# Feature flag: comma-separated list of enabled payment methods
# Options: card_to_card, cod
# Default: card_to_card only for current phase
PAYMENT_METHODS_ENABLED = [
    m.strip() for m in os.getenv("PAYMENT_METHODS_ENABLED", "card_to_card").split(",")
    if m.strip()
]

# Proxy
PROXY_URL = os.getenv("PROXY_URL", "").strip()

# Website
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://telegramorder.ir").rstrip("/")

# ─── Observability ─────────────────────────────────────────────
# Sentry DSN for error tracking
SENTRY_DSN = os.getenv("SENTRY_DSN", "").strip()
SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", "production").strip()
SENTRY_TRACES_SAMPLE_RATE = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))

# Prometheus metrics
PROMETHEUS_ENABLED = os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true"
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "9090"))

# Grafana
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001").rstrip("/")

# ─── Subscription ──────────────────────────────────────────────
# Admin card info for subscription payments
ADMIN_CARD_NUMBER = os.getenv("ADMIN_CARD_NUMBER", "6219861937973138").strip()
ADMIN_CARD_HOLDER = os.getenv("ADMIN_CARD_HOLDER", "طه رجعتی").strip()

# Subscription grace period (days after expiry before forced suspend)
SUBSCRIPTION_GRACE_DAYS = int(os.getenv("SUBSCRIPTION_GRACE_DAYS", "7"))

def validate():
    if not BOT_TOKEN:
        raise RuntimeError("توکن ربات تنظیم نشده!")
    if not ADMIN_IDS:
        print("⚠️ هشدار: هیچ ADMIN_IDS ای تنظیم نشده.")