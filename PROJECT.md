# پروژه فروشگرام (Foroshgram) — Telegram Order Bot

> **نسخه:** 2.5 | **تاریخ:** ۱۴۰۵-۰۵-۲۱ (2026-08-12)  \
> **ربات:** [@Foroshgrambot](https://t.me/Foroshgrambot)   \
> **پلتفرم سفارش آنلاین چندمستأجری تلگرام**

---

## فهرست

۱. [معرفی و ویژگی‌ها](#۱-معرفی-و-ویژگی‌ها)  
۲. [معماری سیستم](#۲-معماری-سیستم)  
۳. [مدل داده‌ها](#۳-مدل-دادهها)  
۴. [احراز هویت](#۴-احراز-هویت)  
۵. [سناریوهای ربات — مشتری](#۵-سناریوهای-ربات--مشتری)  
۶. [سناریوهای ربات — ادمین](#۶-سناریوهای-ربات--ادمین)  
۷. [سناریوهای ربات — فروشنده](#۷-سناریوهای-ربات--فروشنده)  
۸. [فرآیندهای تراکنشی](#۸-فرآیندهای-تراکنشی)  
۹. [جریان کامل سفارش (End-to-End)](#۹-جریان-کامل-سفارش)  
۱۰. [کرون‌جاب‌ها](#۱۰-کرونجابها)  
۱۱. [EventBus معماری رویداد](#۱۱-eventbus-معماری-رویداد)  
۱۲. [API Reference](#۱۲-api-reference)  
۱۳. [زیرساخت و استقرار](#۱۳-زیرساخت-و-استقرار)  
۱۴. [تغییرات و نقشه راه](#۱۴-تغییرات-و-نقشه-راه)  
۱۵. [پیوست: ساختار دایرکتوری](#۱۵-پیوست-ساختار-دایرکتوری)

---

## ۱. معرفی و ویژگی‌ها

یک پلتفرم فروشگاهی تلگرامی چندمستأجری (multi-tenant) — هر فروشنده فروشگاه مجزای خودش را با دیتای جدا دارد. مشتری‌ها از طریق ربات تلگرام خرید می‌کنند و فروشنده‌ها سفارش‌ها را از ربات مدیریت می‌کنند.

### نقش‌ها

| نقش | دسترسی |
|------|--------|
| **ادمین کل (Super Admin)** | دسترسی کامل به همه فروشگاه‌ها، کاربران، سفارش‌ها، تنظیمات سیستم |
| **فروشنده (Seller)** | مدیریت فروشگاه خودش (محصولات، دسته‌بندی‌ها، سفارش‌ها) |
| **مشتری (Customer)** | مشاهده محصولات، ثبت سفارش، پیگیری سفارش |

### خصیصه‌های کلیدی

- **چندمستأجری**: هر فروشنده یک فروشگاه مجزا با دیتای جدا دارد
- **ثبت‌نام خودکار فروشنده**: ویزارد ۸ مرحله‌ای درون ربات
- **فقط یک روش پرداخت**: کارت‌به‌کارت
- **درگاه شخصی فروشنده**: پول مستقیم به حساب فروشنده می‌رود
- **لینک مستقیم محصول**: `t.me/bot?start=product_X`
- **لینک مستقیم دسته‌بندی**: `start=category_12`
- **شروع هوشمند**: `/start` → آخرین فروشگاه یا دعوت به ساخت
- **منوی سه سطحی (BotCommandScope)**: دستورات متفاوت برای مشتری/فروشنده/ادمین
- **مدیریت موجودی اتمیک**: جلوگیری از overselling با UPDATE شرطی SQL
- **تاریخچه وضعیت سفارش (OrderHistory)**: رهگیری کامل تغییرات در جدول جداگانه
- **سیستم رویداد (EventBus)**: جداسازی نوتیفیکیشن‌ها از هندلرها
- **سرویس نوتیفیکیشن متمرکز (NotificationService)**: ارسال پیام‌ها از یک نقطه
- **داشبورد فروشنده**: فروش امروز/هفته/ماه، پرفروش‌ترین، میانگین سفارش، نرخ تبدیل
- **یادآور موجودی کم**: اعلان خودکار وقتی محصول < ۵ عدد بماند
- **فیلتر و مرتب‌سازی**: ارزان‌ترین، گران‌ترین، جدیدترین + فقط موجود
- **علاقه‌مندی‌ها (Wishlist)**: افزودن محصولات مورد علاقه
- **جستجوی تعاملی**: تایپ نام محصول
- **جستجوی همگانی محصولات** (`/searchall`): سرچ در تمام فروشگاه‌های فعال
- **جستجوی فروشگاه‌ها** (`/findshop`): پیدا کردن فروشگاه با نام/یوزرنیم
- **سبد خرید رها شده**: یادآوری خودکار پس از ۱۲ ساعت
- **خرید مجدد (Reorder)**: بازگرداندن محصولات سفارش قبلی به سبد
- **کد تخفیف**: فروشنده کد درصدی/مبلغی می‌سازد، مشتری در checkout اعمال می‌کند
- **بنر فروشگاه**: عکس کاور صفحه اصلی فروشگاه
- **اعلان موجود شدن (Restock)**: subscribe + notify
- **Progress Bar سفارش**: 📦→✅→📮→🚚→📬
- **خرید سریع (Fast Checkout)**: اطلاعات ذخیره شده از خرید قبلی
- **فروشگاه‌های اخیر**: لیست ۵ فروشگاه آخر بازدید شده
- **گالری چندعکسی**: آلبوم تلگرام (send_media_group) برای محصولات با چند عکس
- **پشتیبانی (Support)**: سیستم پیام دوطرفه خریدار-فروشنده با Conversation/Message مدل
- **افزودن محصول با فوروارد**: فروشنده پیام کانال را فوروارد می‌کند
- **پیام خریدار-فروشنده (Conversations)**: مشتری از داخل جزئیات سفارش پیام بده، فروشنده اینباکس مجزا دارد
- **تایید/رد مستقیم از نوتیفیکیشن**: ادمین بدون رفتن به پنل از دکمه‌های inline می‌تواند فروشنده را تایید/رد کند
- **رمزنگاری اطلاعات بانکی**: AES-256-GCM با PBKDF2 در هر دو سمت (ربات + سایت)
- **CSRF protection**: HMAC-SHA256 double-submit cookie
- **Rate limiter توزیع‌شده**: Redis-backed با fallback in-memory
- **De-duplication رسید پرداخت**: SHA-256 hash + UNIQUE constraint
- **اجبار تغییر رمز بعد از reset**: must_change_password flag
- **کمپرس پاسخ‌های طولانی**: کاهش سایز پیام‌های تکراری
- **سیستم اشتراک فروشگاه**: پلن‌های ماهانه/فصلی/سالانه با خرید کارت‌به‌کارت و تایید ادمین
- **پیش‌فرض کارت ادمین برای اشتراک**: شماره کارت و نام صاحب در config با default مقداردهی

---

## ۲. معماری سیستم

```
┌──────────────────────────────────────────────────────────────┐
│                      Docker Network                           │
│                                                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐  │
│  │  Next.js 3000     │  │  Bot Python 3.12 │  │ PostgreSQL │  │
│  │  (Website)        │  │  PTB v22.x       │  │  Port 5432 │  │
│  │  SSR + API Routes │  │  Async SQLAlchemy│  │            │  │
│  │  Node.js 20       │  │  APScheduler     │  │            │  │
│  └────────┬─────────┘  └────────┬─────────┘  └──────┬─────┘  │
│           └────────────────┼───────────────────────┘         │
│                            │                                  │
│                      AsyncPG / asyncpg                        │
│                                                               │
│  ┌──────────────────┐  ┌──────────────────┐                   │
│  │   Prometheus     │  │    Grafana       │   Monitoring      │
│  │    Port 9091     │  │   Port 3001      │                   │
│  └──────────────────┘  └──────────────────┘                   │
└──────────────────────────────────────────────────────────────┘
```

### کانتینرها

| سرویس | نام کانتینر | Port | وابستگی |
|-------|-------------|------|---------|
| PostgreSQL 16 | `foroshgram_postgres` | ۵۴۳۲ | — |
| Next.js | `foroshgram_website` | ۳۰۰۰ | postgres (healthy) |
| Bot | `foroshgram_bot` | — | postgres (healthy) |

### تکنولوژی‌ها

- **ربات**: Python 3.12 + python-telegram-bot v22.x (async) — APScheduler
- **ORM**: SQLAlchemy 2.0 Async + asyncpg
- **سایت**: Next.js 14 (App Router, Turbopack-ready) + pg (Node.js native driver)
- **دیتابیس**: PostgreSQL 16 (تولید) / SQLite (توسعه محلی)
- **JWT**: jose (Edge Runtime compatible) — کوکی `fsh_session` (httpOnly, SameSite=Lax)
- **هش رمز**: bcrypt (ad-hoc wrapper، کتابخانه `bcrypt` روی Alpine)
- **رمزنگاری**: AES-256-GCM با `cryptography.hazmat` (Python) / `crypto` native (Node.js)
- **Proxy Bot**: HTTP proxy support برای مناطق تحریمی
- **مانیتورینگ**: Prometheus + Grafana (با `monitoring.py` ماژولار)
- **Rate Limiter**: Redis (`redis-py` / `redis` npm) + in-memory fallback

### ماژول‌های اصلی ربات

| ماژول | وظیفه | فایل |
|-------|-------|------|
| **Application** | نقطه ورود، build handler tree | `main.py` |
| **Start** | `/start` هوشمند + لینک مستقیم | `handlers/start.py` |
| **Menu** | دسته‌بندی‌ها، محصولات، گالری | `handlers/menu.py` |
| **Cart** | سبد خرید (افزودن/کم/زیاد/حذف) | `handlers/cart.py` |
| **Order** | ثبت سفارش + تاریخچه + پرداخت | `handlers/order.py` |
| **Seller Registration** | ویزارد ۸ مرحله‌ای | `handlers/seller_registration.py` |
| **Seller Panel** | پنل فروشنده + تنظیمات پرداخت | `handlers/seller_panel.py` |
| **Discount** | ساخت و مدیریت کد تخفیف | `handlers/discount.py` |
| **Wishlist** | علاقه‌مندی‌ها | `handlers/wishlist.py` |
|| **Search** | جستجوی تعاملی + همگانی + فروشگاه‌ها | `handlers/search.py` |
|| **Forward Products** | افزودن محصول با فوروارد | `handlers/forward_products.py` |
|| **Support** | پشتیبانی دوطرفه خریدار-فروشنده + ادمین | `handlers/support.py` |
|| **Help** | راهنمای نقش‌محور | `handlers/help.py` |
|| **Common** | توابع مشترک بین handlers | `handlers/common.py` |
|| **Conversations** | پیام خریدار-فروشنده (اینباکس) | `handlers/conversations.py` |
|| **Admin Approval** | تایید/رد فروشنده از دکمه inline | `handlers/admin_approval.py` |
|| **Admin Panel** | پنل ادمین | `handlers/admin/panel.py` |
|| **Admin Products** | مدیریت محصولات | `handlers/admin/products.py` |
|| **Admin Categories** | مدیریت دسته‌بندی | `handlers/admin/categories.py` |
|| **Admin Orders** | مدیریت سفارش‌ها | `handlers/admin/orders.py` |
|| **Admin Shops** | مدیریت فروشگاه‌ها | `handlers/admin/shops.py` |
|| **Admin Broadcast** | پیام همگانی | `handlers/admin/broadcast.py` |
|| **Subscription** | خرید/تمدید اشتراک + تایید/رد ادمین | `handlers/subscription.py` |
|| **Subscription Decorator** | دکوریتور `@require_active_subscription` | `handlers/subscription_decorator.py` |
|| **Crypto (Bot)** | AES-256-GCM رمزنگاری اطلاعات بانکی | `utils/crypto.py` |
|| **Payment Service** | رزرو/آزادسازی/نهایی‌سازی موجودی | `services/payment.py` |
|| **Order Service** | سرویس متمرکز سفارش | `services/order_service.py` |
|| **Subscription Service** | هسته منطق اشتراک (seed, create, verify, reject) | `services/subscription.py` |
|| **EventBus** | معماری event-driven | `services/events.py` |
|| **Notification** | سرویس متمرکز نوتیفیکیشن | `services/notification_service.py` |
|| **Restock** | اعلان موجود شدن | `services/restock.py` |
|| **Monitoring** | Metrics + Sentry + Health | `services/monitoring.py` |
|| **Abandoned Cart** | یادآوری سبد رها شده | `services/abandoned_cart.py` |

### جریان داده‌ای EventBus

```
Handler → event_bus.emit(Event.ORDER_PAID, ...)
              │
              ▼
         EventBus.dispatch()
              │
       ┌──────┼──────┐
       ▼      ▼      ▼
   Listener Listener Listener
   (notify) (first_sale) (log)
```

- رویدادها: `ORDER_PAID`, `ORDER_CONFIRMED`, `ORDER_CANCELLED`, `FIRST_SALE`
- Listenerها در `services/event_listeners.py`
- هر Listener مستقل است — خطای یکی بقیه را نمی‌شکند

---

## ۳. مدل داده‌ها

### ۳.۱. فروشگاه (Shop)

| فیلد | نوع | توضیح |
|------|------|--------|
| id | Integer PK | شناسه فروشگاه |
| name | String(150) | نام فروشگاه |
| description | String(500)? | توضیحات |
| phone | String(30)? | شماره تماس |
| channel_link | String(200)? | لینک کانال تلگرام فروشنده |
| rejection_reason | String(500)? | دلیل رد (اگر رد شده) |
| username | String(100)? Unique | یوزرنیم اختصاصی |
| is_active | Boolean | فعال/غیرفعال |
| status | String(20) | draft → active → suspended → rejected |
| created_at | DateTime | تاریخ ثبت |
| shipping_cost | Integer default=0 | هزینه ارسال (تومان) |
| zarinpal_merchant_id | String(36)? | merchant_id زین‌پال (غیرفعال) |
| card_number | Text? | شماره کارت برای کارت‌به‌کارت (AES-256-GCM ciphertext ~60 chars) |
| card_holder_name | Text? | نام صاحب کارت (AES-256-GCM ciphertext ~172 chars) |
| sheba_number | Text? | شماره شبا (AES-256-GCM ciphertext ~72 chars) |
| zarinpal_merchant_id | String(36)? | شناسه درگاه زین‌پال |
| banner_image | String(255)? | file_id عکس کاور فروشگاه |
### ۳.۲. صاحب فروشگاه (ShopOwner)

| فیلد | نوع | توضیح |
|------|------|--------|
| id | Integer PK | |
| user_id | BigInteger index | شناسه تلگرام |
| shop_id | Integer FK → shops.id | فروشگاه مرتبط |
| first_name | String(100)? | نام |
| username | String(100)? | یوزرنیم تلگرام |
| password_hash | String? | هش bcrypt رمز عبور |
| password_salt | String? | Salt رمز عبور (برای مهاجرت SHA-256) |
| must_change_password | Boolean default=False | اجبار تغییر رمز بعد از reset |
| registered_at | DateTime | تاریخ ثبت |

### ۳.۳. کد دعوت (ClaimCode)

| فیلد | نوع | توضیح |
|------|------|--------|
| id | Integer PK | |
| code | String(50) Unique | کد دعوت |
| shop_id | Integer FK → shops.id | فروشگاه |
| expires_at | DateTime? | انقضا |
| used_at | DateTime? | زمان استفاده |
| used_by | BigInteger? | کاربر استفاده‌کننده |

### ۳.۴. محصول (Product)

| فیلد | نوع | توضیح |
|------|------|--------|
| id | Integer PK | |
| shop_id | Integer FK → shops.id | فروشگاه |
| category_id | Integer FK → categories.id | دسته‌بندی |
| name | String(200) | نام محصول |
| description | Text? | توضیحات |
| price | BigInteger | قیمت به تومان |
| stock | Integer | موجودی کل |
| image_file_id | String(255)? | file_id عکس اصلی |
| reserved_stock | Integer default=0 | موجودی رزرو شده در سفارش‌های در حال پردازش |
| is_active | Boolean default=True | فعال/غیرفعال |
| has_video | Boolean default=False | آیا ویدیو دارد؟ |
| created_at | DateTime | |
| updated_at | DateTime | |
| CONSTRAINT chk_stock | CHECK | `reserved_stock >= 0 AND reserved_stock <= stock` |

**محاسبه موجودی قابل فروش:**
```python
@property
def available_stock(self) -> int:
    return max(0, self.stock - self.reserved_stock)
```

### ۳.۵. دسته‌بندی (Category)

| فیلد | نوع | توضیح |
|------|------|--------|
| id | Integer PK | |
| shop_id | Integer FK → shops.id | فروشگاه |
| name | String(100) | نام دسته |
| created_at | DateTime | |

### ۳.۶. کاربر (User)

| فیلد | نوع | توضیح |
|------|------|--------|
| id (user_id) | BigInteger PK | شناسه تلگرام |
| first_name | String(100)? | |
| last_name | String(100)? | |
| username | String(100)? | |
| phone | String(30)? | |
| address | String(500)? | آدرس پیش‌فرض |
| is_blocked | Boolean | مسدود؟ |
| saved_name | String(100)? | نام ذخیره شده برای خرید سریع |
| saved_phone | String(20)? | شماره ذخیره شده |
| saved_address | Text? | آدرس ذخیره شده |
| recent_shops | Text (JSON array of int) | `[shop_id_1, shop_id_2, ...]` — ۵ فروشگاه آخر |
| last_shop_id | Integer? | آخرین فروشگاه بازدید شده |
| registered_at | DateTime | |

### ۳.۷. ادمین کل (Admin)

| فیلد | نوع | توضیح |
|------|------|--------|
| id | Integer PK | |
| user_id | BigInteger Unique | شناسه تلگرام |
| password_hash | String(128) | هش bcrypt |
| must_change_password | Boolean default=False | اجبار تغییر رمز بعد از reset |
| created_at | DateTime | |

### ۳.۸. سبد خرید (CartItem)

| فیلد | نوع | توضیح |
|------|------|--------|
| id | Integer PK | |
| user_id | BigInteger FK → users.id | کاربر |
| shop_id | Integer FK → shops.id | فروشگاه |
| product_id | Integer FK → products.id | محصول |
| quantity | Integer default=1 | تعداد |
| created_at | DateTime | |

**UniqueConstraint**: `(user_id, product_id)` — هر محصول فقط یک رکورد در سبد.

### ۳.۹. سفارش (Order)

| فیلد | نوع | توضیح |
|------|------|--------|
| id | Integer PK | |
| shop_id | Integer FK → shops.id | فروشگاه |
| tracking_code | String(20) Unique | کد رهگیری (فرمت: `YYMMDD + 6 digit`) |
| user_id | BigInteger FK → users.id | مشتری |
| total_price | Integer | جمع کل به تومان (بعد از تخفیف، قبل از ارسال) |
| status | String(20) | `pending_payment`, `pending`, `paid`, `confirmed`, `shipped`, `delivered`, `cancelled`, `refunded` |
| payment_method | String(20)? | `card_to_card` (فقط این روش فعال) |
| payment_ref | String(100)? | شماره مرجع پرداخت (برای آینده) |
| payment_status | String(20)? | `pending`, `pending_review`, `paid`, `cancelled` |
| payment_receipt_file_id | String(255)? | file_id عکس رسید |
| payment_receipt_text | String(500)? | متن شماره تراکنش |
|| payment_receipt_at | DateTime? | زمان آپلود رسید |
|| payment_receipt_hash | String(64)? | SHA-256 hash رسید برای de-duplication |
|| receiver_name | String(150)? | نام گیرنده |
|| shipping_address | String(500) | آدرس گیرنده |
|| phone | String(30) | شماره تماس گیرنده |
|| discount_code | String(50)? | کد تخفیف اعمال شده |
|| discount_amount | Integer default=0 | مبلغ تخفیف (تومان) |
|| customer_notes | String(500)? | توضیحات اختیاری مشتری (رنگ، مشخصات و...) |
|| status_history | Text (JSON) | تاریخچه قدیمی (دیگر استفاده نمی‌شود، برای backward compatibility) |
|| cancellation_reason | String(100)? | دلیل لغو |
|| created_at | DateTime | |
|| updated_at | DateTime | |

**روابط:**
- `items: list[OrderItem]` — cascade delete
- `histories: list[OrderHistory]` — cascade delete

### ۳.۱۰. آیتم سفارش (OrderItem)

| فیلد | نوع | توضیح |
|------|------|--------|
| id | Integer PK | |
| order_id | Integer FK → orders.id | سفارش |
| product_id | Integer FK → products.id (nullable) | محصول در لحظه سفارش — اگر محصول حذف شود، NULL می‌شود |
| product_name | String(150) | نام محصول (ذخیره شده در لحظه سفارش) |
| quantity | Integer | تعداد |
| unit_price | Float | قیمت واحد در لحظه سفارش |

**روابط:**
- `product: Product` — رابطه به محصول (برای بررسی موجودی و جزئیات در زمان تایید پرداخت)

### ۳.۱۱. تاریخچه سفارش (OrderHistory)

| فیلد | نوع | توضیح |
|------|------|--------|
| id | Integer PK | |
| order_id | Integer FK → orders.id | سفارش |
| status | String(50) | وضعیت جدید |
| changed_by | String(50) | `system`, `seller`, `admin`, `customer` |
| description | String(500)? | توضیحات اختیاری |
| meta_json | Text? | JSON با اطلاعات اضافی (دلیل لغو، آدرس و...) |
| changed_at | DateTime | زمان تغییر (indexed) |

### ۳.۱۲. عکس محصول (ProductImage)

| فیلد | نوع | توضیح |
|------|------|--------|
| id | Integer PK | |
| product_id | Integer FK → products.id | محصول |
| file_id | String(255) | file_id تلگرام |
| position | Integer default=0 | ترتیب نمایش (0 = عکس اصلی) |
| created_at | DateTime | |

**چند عکس = آلبوم:** اگر `ProductImage.count > 1`، در `show_product_detail` ابتدا عکس اصلی (`product.image_file_id`) با `send_photo` فرستاده می‌شود، سپس بقیه عکس‌ها با `send_media_group` به صورت آلبوم.

### ۳.۱۳. علاقه‌مندی‌ها (WishlistItem)

| فیلد | نوع | توضیح |
|------|------|--------|
| id | Integer PK | |
| user_id | BigInteger FK → users.id | کاربر |
| shop_id | Integer FK → shops.id | فروشگاه |
| product_id | Integer FK → products.id | محصول |
| created_at | DateTime | |

**UniqueConstraint**: `(user_id, shop_id, product_id)`

### ۳.۱۴. کد تخفیف (DiscountCode)

| فیلد | نوع | توضیح |
|------|------|--------|
| id | Integer PK | |
| shop_id | Integer FK → shops.id | فروشگاه |
| code | String(50) | کد تخفیف (مثلاً SUMMER20) |
| discount_type | String(20) | `percent` یا `fixed_amount` |
| discount_value | Float | مقدار تخفیف (درصد یا مبلغ به تومان) |
| min_order_amount | Float default=0 | حداقل مبلغ سفارش برای اعمال |
| max_uses | Integer default=0 | حداکثر دفعات استفاده (0 = نامحدود) |
| used_count | Integer default=0 | دفعات استفاده شده |
| is_active | Boolean default=True | فعال/غیرفعال |
| expires_at | DateTime? | تاریخ انقضا |
| created_at | DateTime | |

**Index**: `(shop_id, code)` — ترکیبی

**نحوه اعمال در checkout:**
1. مشتری دکمه `🎁 کد تخفیف` در خلاصه سفارش می‌زند
2. کد را تایپ می‌کند → validate: فعال بودن، عدم انقضا، عدم اتمام ظرفیت، حداقل مبلغ
3. اگر `discount_type == "percent"`: `amount = total * value / 100`
4. اگر `discount_type == "fixed_amount"`: `amount = value`
5. **Clamp**: `amount = min(amount, total_price)` — مبلغ منفی غیرممکن
6. `total_price = max(0, total_price - amount)`
7. نتیجه در `context.user_data["discount_code"]` و `["discount_amount"]` ذخیره می‌شود
8. در `create_order_from_cart` پارامترهای `discount_code` و `discount_amount` دریافت و در `Order` ذخیره می‌شود
9. `DiscountCode.used_count++` بعد از ایجاد موفق سفارش

### ۳.۱۵. اعلان موجود شدن (RestockSubscription)

| فیلد | نوع | توضیح |
|------|------|--------|
| id | Integer PK | |
| product_id | Integer FK → products.id | محصول |
| user_id | BigInteger | کاربر (FK نیست برای سادگی) |
| shop_id | Integer FK → shops.id | فروشگاه |
| notified | Boolean default=False | آیا notify شده؟ |
| subscribed_at | DateTime | تاریخ ثبت‌نام |

**UniqueConstraint**: `(product_id, user_id)` — یک کاربر فقط یک بار می‌تواند برای هر محصول subscribe کند.

**رفتار subscribe:**
- اگر `notified=False` وجود دارد → "قبلاً ثبت‌نام کرده‌اید"
- اگر `notified=True` وجود دارد → `notified=False` + `subscribed_at=now` (re-activate)
- در غیر این صورت → رکورد جدید

**رفتار notify:**
- وقتی موجودی از ۰ به >۰ می‌رود (`admin/products.py:handle_product_edit_stock`)
- `_check_and_notify_restock(session, product_id, shop_id, context.bot)` صدا زده می‌شود
- برای هر subscriber با `notified=False`: پیام "🔔 ... موجود شد!" ارسال می‌شود
- بعد از ارسال، `notified=True` می‌شود

### ۳.۱۶. مکالمه (Conversation) — پشتیبانی

| فیلد | نوع | توضیح |
|------|------|--------|
|| id | Integer PK | |
|| user_id | BigInteger index | شناسه تلگرام |
|| shop_id | Integer FK → shops.id | فروشگاه مرتبط |
|| password_hash | String(128) | هش bcrypt |
|| password_salt | String(32) | Salt برای bcrypt |
|| must_change_password | Boolean default true | پس از `/reset_password` و لاگین اولیه اجباری |
|| two_factor_secret | String(32)? | (آینده) |
|| created_at | DateTime | |

### ۳.۱۷. پیام (Message) — پشتیبانی

| فیلد | نوع | توضیح |
|------|------|--------|
| id | Integer PK | |
| conversation_id | Integer FK → conversations.id | مکالمه |
| sender_role | String(10) | `buyer` / `seller` |
| content | Text | متن پیام |
| has_attachment | Boolean default=False | آیا پیوست دارد؟ |
| attachment_file_id | String(255)? | file_id پیوست |
| read_at | DateTime? | زمان خوانده شدن |
| created_at | DateTime | |

---

### ۳.۱۸. پلن اشتراک (SubscriptionPlan)

| فیلد | نوع | توضیح |
|------|------|--------|
| id | Integer PK | |
| name | String(50) | نام پلن (مثلاً "ماهانه", "۳ ماهه", "سالانه") |
| duration_days | Integer | مدت اعتبار به روز |
| price | BigInteger | قیمت به تومان |
| is_active | Boolean default=True | فعال/غیرفعال |
| created_at | DateTime | تاریخ ایجاد |

**پلن‌های پیش‌فرض (seed شده):**
- 🥈 ماهانه — ۳۰ روز — ۴۹۹,۰۰۰ تومان
- 🥇 ۳ ماهه — ۹۰ روز — ۱,۱۹۹,۰۰۰ تومان
- 💎 ۶ ماهه — ۱۸۰ روز — ۱,۹۹۹,۰۰۰ تومان
- 👑 سالانه — ۳۶۵ روز — ۳,۴۹۹,۰۰۰ تومان

---

### ۳.۱۹. اشتراک فروشگاه (ShopSubscription)

| فیلد | نوع | توضیح |
|------|------|--------|
| id | Integer PK | |
| shop_id | Integer FK → shops.id | فروشگاه |
| plan_id | Integer FK → subscription_plans.id | پلن خریداری شده (nullable برای trial) |
| is_trial | Boolean default=False | آیا آزمایشی است؟ |
| start_date | DateTime | شروع اشتراک |
| end_date | DateTime | پایان اشتراک |
| approval_status | String(20) | `pending`, `approved`, `rejected` |
| verified_at | DateTime? | زمان تأیید ادمین (idempotency flag) |
| verified_by | BigInteger? | ادمین تأییدکننده |
| rejection_reason | String(200)? | دلیل رد |
| receipt_file_id | String(255)? | file_id عکس رسید |
| receipt_hash | String(64)? | SHA-256 hash رسید برای de-duplication |
| superseded_at | DateTime? | زمان بسته شدن (وقتی ردیف جدید ساخته شود) |
| notes | String(300)? | یادداشت |
| created_at | DateTime | تاریخ ایجاد |

**CHECK Constraint:** `ck_shop_subs_plan_or_trial`
```sql
CHECK ((is_trial = true AND plan_id IS NULL) OR (is_trial = false AND plan_id IS NOT NULL))
```

**استراتژی Append-only + superseded_at:**
- هر اقدام (trial, خرید, تمدید) ردیف جدید می‌سازد
- ردیف قبلی با `superseded_at = now` بسته می‌شود
- «ردیف فعلی» = `superseded_at IS NULL` + `ORDER BY id DESC LIMIT 1`
- `is_active` property به‌صورت لحظه‌ای محاسبه می‌شود (عدم ذخیره وضعیت expiry)

**Stack vs Replace:**
- اگر همان پلن خریداری شود → `end_date` روی ردیف جدید از `end_date` قبلی extend می‌شود (stack)
- اگر پلن دیگری باشد → از `now()` شروع می‌شود (replace)

---

### ۳.۲۰. فیلد توضیحات سفارش (Order.customer_notes)

از نسخه ۲.۵، سفارش‌ها دارای فیلد `customer_notes` (VARCHAR 500) هستند:

| فیلد | نوع | توضیح |
|------|------|--------|
| customer_notes | String(500)? | توضیحات اختیاری مشتری (رنگ، مشخصات و...) |

**نحوه کار:** 
- بعد از مرحله آدرس در checkout، user می‌تواند توضیحات اضافی بنویسد (اختیاری)
- با `-` یا `/skip` می‌تواند رد کند
- در خلاصه سفارش، اعلان فروشنده و جزئیات ادمین نمایش داده می‌شود
- ذخیره جداگانه در `CustomerInfo.notes` و `create_order_from_cart`

---

## ۴. احراز هویت

| نقش | شرط | رمز | ریدایرکت |
|------|------|------|----------|
| **ادمین** | شناسه در جدول `admins` | هش bcrypt در دیتابیس | `/admin` |
| **فروشنده** | شناسه در `shop_owners` | هش bcrypt | `/seller` |
| **مشتری** | شناسه در `users` | ندارد (فقط userId کافی است) | `/` |

### ۴.۲. جزئیات فنی

- **JWT** با کتابخانه `jose` (Edge Runtime compatible) — کوکی `fsh_session` (httpOnly, SameSite=Lax)
- **bcrypt** برای هش رمز (جایگزین SHA-256 در آپدیت امنیتی)
- `ADMIN_PASSWORD` از env vars **حذف شده** — رمز ادمین در جدول `admins` با bcrypt
- **Salt جداگانه** برای هر فروشنده (`password_salt`) — برای مهاجرت از SHA-256 نگه داشته شده
- **Rate limit**: Redis-backed با fallback in-memory — ۵ تلاش ناموفق → ۱۵ دقیقه قفل
- **CSRF protection**: HMAC-SHA256 double-submit cookie pattern روی POST/PATCH/DELETE endpoints
- **رمزنگاری اطلاعات بانکی**: AES-256-GCM با PBKDF2 key derivation (کلید از `ENCRYPTION_KEY` env)
- **AJre-check وضعیت فروشگاه**: `requireSeller()` هر ریکوئست `shop.active` و `password_hash` رو از DB چک می‌کنه
- **اجبار تغییر رمز**: `must_change_password` flag بعد از `/reset_password` — login موفق redirect به `/change-password`
- **De-duplication رسید**: SHA-256 hash + UNIQUE constraint روی `payment_receipt_hash`
- **Escape HTML**: همه ورودی‌های کاربر قبل از `parse_mode=HTML` escape می‌شن (جلوگیری از injection)
- **Middleware** (Next.js): محافظت مسیرهای `/admin/*` و `/seller/*`
- **Payload JWT**: `{ userId, role, shopId?, firstName?, loginMethod }`

---

## ۵. سناریوهای ربات — مشتری

### ۵.۱. شروع کار (`/start`)

#### با پارامتر (`?start=shop_X` یا `?start=product_X` یا `?start=category_X`)

1. کاربر `/start` را می‌فرستد
2. ربات چک می‌کند کاربر بلاک نیست و `user_id` در جدول `users` وجود دارد
3. اگر `start=shop_X` (لینک فروشگاه):
   - فروشگاه وجود ندارد → `❌ فروشگاه مورد نظر یافت نشد`
   - فروشگاه غیرفعال → `🚫 این فروشگاه معلق شده`
   - OK → ثبت/بروز `last_shop_id` کاربر + نمایش منوی فروشگاه
4. اگر `start=product_X` (لینک مستقیم محصول):
   - محصول + فروشگاه مجازند → نمایش جزئیات محصول
   - `shop_id` کاربر بروز می‌شود
5. اگر `start=category_X` (لینک مستقیم دسته‌بندی):
   - دسته + فروشگاه مجازند → نمایش محصولات آن دسته
6. پارامتر نامعتبر → `❌ لینک نامعتبر`

#### بدون پارامتر (شروع هوشمند)

1. اگر `last_shop_id` دارد و فروشگاه فعال است:
   - نمایش: «آخرین باری که اینجا بودی تو فروشگاه «X» بودی.»
   - دکمه‌ها: `🛍 مشاهده محصولات` + `🛒 سبد خرید` + `📦 سفارش‌های من`
2. اگر `last_shop_id` ندارد یا فروشگاه غیرفعال:
   - پیام معرفی پلتفرم + دعوت به ساخت فروشگاه
   - دکمه‌ها: `🏪 می‌خوام فروشگاه بسازم` + `ℹ️ درباره فروشگرام`

### ۵.۲. منوی اصلی و دسته‌بندی‌ها

```
cat:list → cat:open:{id}:{page} → prod:open:{id}:{cat}:{page}
```
دسته‌بندی‌ها با دکمه نمایش داده می‌شوند. انتخاب دسته → محصولات (۸ عدد در هر صفحه با صفحه‌بندی). مرتب‌سازی: ارزان‌ترین / گران‌ترین / جدیدترین. فیلتر `فقط موجود`.

### ۵.۳. جزئیات محصول

- عکس اصلی (`product.image_file_id`) + در صورت وجود عکس‌های اضافه (`ProductImage`) → آلبوم (`send_media_group`)
- متن: نام، قیمت، توضیحات، ⭐ امتیاز (آینده)، موجودی
- دکمه‌ها:
  - `➕ افزودن به سبد خرید` — اگر موجود، با دکمه تعداد
  - `💚 افزودن به علاقه‌مندی‌ها` / اگر قبلاً اضافه شده: `💔 حذف از علاقه‌مندی‌ها`
  - `🔔 وقتی موجود شد خبرم کن` — اگر `available_stock == 0`
  - `🔙 بازگشت`
  - `🛒 مشاهده سبد خرید` (بعد از افزودن)
  - `🛍 ادامه خرید` (بعد از افزودن)
  - `🗑 حذف از سبد` (بعد از افزودن)

### ۵.۴. سبد خرید

- **افزودن**: `cart:add:{product_id}` → `+1` به تعداد / اگر موجود نیست → رکورد جدید
- **مشاهده**: `cart:view` → لیست اقلام با قیمت و جمع کل
- **تغییر تعداد**: `cart:inc:{id}` / `cart:dec:{id}`
- **حذف**: `cart:remove:{id}`
- **خالی کردن**: `cart:clear`
- **ثبت سفارش**: `order:start` → شروع ویزارد checkout

### ۵.۵. ثبت سفارش (ConversationHandler)

States در `handlers/order.py`:

| State | مقدار | Handler | توضیح |
|-------|-------|---------|--------|
| ASK_NAME | 0 | `ask_name` | دریافت نام گیرنده (۲-۱۰۰ کاراکتر) |
| ASK_PHONE | 1 | `ask_phone` | شماره تماس ۱۱ رقمی (`^09\d{9}$` با تبدیل اعداد فارسی) |
| ASK_ADDRESS | 2 | `ask_address` | آدرس (حداکثر ۵۰۰ کاراکتر) — اگر `saved_address` موجود باشد → دکمه `✅ بله، از اطلاعات قبلی` |
| ASK_PAYMENT_METHOD | 3 | `ask_payment_method` | انتخاب روش پرداخت (داینامیک بر اساس تنظیمات فروشنده) — فعلاً فقط `💳 کارت به کارت` |
| CONFIRM | 4 | `_show_order_summary` | خلاصه سفارش با دکمه‌های: `✅ ثبت نهایی`, `🎁 کد تخفیف`, `✏️ ویرایش اطلاعات`, `🔙 بازگشت` |
| ASK_CARD_RECEIPT | 5 | `handle_card_receipt` | دریافت عکس/متن رسید (برای `card_to_card`) |
| ASK_DISCOUNT | 6 | `receive_discount` | دریافت کد تخفیف متنی |

**جریان کامل:**

```
order:start → (اگر fast-checkout) ASK_NAME
  → ASK_PHONE → ASK_ADDRESS
    → [اگر saved info موجود: دکمه "استفاده از اطلاعات قبلی"]
    → ASK_PAYMENT_METHOD → CONFIRM
      → 🎁 کد تخفیف → ASK_DISCOUNT → validate → CONFIRM (با تخفیف)
      → ✅ ثبت نهایی → create_order_from_cart()
        → اگر COD: OrderStatus.PENDING → done
        → اگر card_to_card: OrderStatus.PENDING_PAYMENT → ASK_CARD_RECEIPT → ارسال عکس رسید → done
```

**دکمه‌های درون CONFIRM:**
- `order:confirm` — ثبت نهایی
- `order:ask_discount` — رفتن به ASK_DISCOUNT
- `order:change_name` / `phone` / `address` — ویرایش مرحله قبل
- `order:change_payment` — تغییر روش پرداخت
- `order:cancel` — انصراف (ConversationHandler.END)

**Fallbackهای مکالمه (هرجایی قابل استفاده):**
- `order:pay_cancel:{id}` — انصراف در مرحله پرداخت + پاک کردن state
- `order:start` — شروع مجدد checkout (اگر مکالمه گیر کرده باشد)

### ۵.۶. پرداخت کارت‌به‌کارت

1. مشتری در خلاصه سفارش `✅ ثبت نهایی` می‌زند
2. `create_order_from_cart` صدا زده می‌شود (رزرو اتمیک موجودی در تراکنش واحد)
3. ربات شماره کارت فروشنده + نام صاحب کارت + مبلغ را نمایش می‌دهد
4. مشتری عکس رسید (فایل عکس) یا شماره تراکنش (متن) می‌فرستد → `ASK_CARD_RECEIPT`
5. سفارش `PENDING_PAYMENT` + `attach_card_receipt()` → رسید ذخیره می‌شود
   - `payment_receipt_hash = SHA-256(receipt_text or file_id)` — UNIQUE constraint جلوگیری از رسید تکراری
6. فروشنده پیام حاوی رسید + دکمه‌های `✅ تایید` / `❌ رد`
   - پیام فروشنده شامل: نام/تلفن/آدرس/توضیحات خریدار + جزئیات مبلغ + شماره تراکنش
7. **تأیید**: `transition_order(PAID)` → نهایی‌سازی موجودی → نوتیفیکیشن به مشتری
8. **رد**: مشتری ۲ گزینه:
   - `pay:receipt_retry:{id}` — آپلود مجدد رسید
   - `pay:cancel:{id}` — لغو کامل (`cancel_order_and_release_stock`)
9. **عدم اقدام فروشنده تا ۱۵ دقیقه** (بدون رسید) یا **۴۸ ساعت** (بعد از رسید) → کرون‌جاب آزادسازی خودکار (`cleanup_abandoned_payments`)

#### مرحله توضیحات اختیاری (`ASK_NOTES`)
- بعد از مرحله آدرس، مشتری می‌تواند توضیحات اضافی بنویسد (مثلاً: رنگ مشکی، سایز L)
- با تایپ `-` یا `/skip` می‌تواند رد کند
- در خلاصه سفارش و پیام اعلان فروشنده نمایش داده می‌شود

### ۵.۷. تاریخچه و پیگیری سفارش

- `order:history` → لیست سفارش‌ها با کد رهگیری، وضعیت، مبلغ، تاریخ شمسی
- `order:detail:{id}` → جزئیات کامل + **Progress Bar**:
  ```
  📦 ثبت سفارش → ✅ پرداخت → 📮 آماده‌سازی → 🚚 ارسال → 📬 تحویل
  ⬜⬜⬜⬜⬜ (همه خاکستری اگر CANCELLED/REFUNDED)
  ```
  هر مرحله سپری شده: ✅ | فعلی: ⬜ | آینده: ⬜
- `order:reorder:{id}` → خرید مجدد: همه OrderItem → CartItem (اگر محصول هنوز موجود و فعال باشد)

### ۵.۸. علاقه‌مندی‌ها

- `wishlist:add:{pid}` — افزودن (اگر قبلاً نیست)
- `wishlist:remove:{pid}` — حذف
- `wishlist:view` — لیست محصولات با دکمه خرید مستقیم

### ۵.۹. جستجو

- دستور `/search` یا دکمه `🔍 جستجو`
- کاربر نام محصول را تایپ می‌کند → `LIKE %text%` جستجو در `Product.name` با شرط `shop_id`
- نتایج: هر کدام با دکمه مشاهده مستقیم
- دکمه `🔙 بازگشت` در پایین

### ۵.۱۰. جستجوی همگانی محصولات (`/searchall`)

- دستور `/searchall <query>` — سرچ در **تمام فروشگاه‌های فعال** سیستم
- جستجو در `Product.name` و `Product.description` با `ILIKE`
- محدود به ۳۰ نتیجه
- دکمه هر محصول مستقیم به جزئیات (`prod:open`)

### ۵.۱۱. جستجوی فروشگاه‌ها (`/findshop`)

- دستور `/findshop <query>` — پیدا کردن فروشگاه با نام یا یوزرنیم
- جستجو در `Shop.name` و `Shop.username` با `ILIKE`
- فقط فروشگاه‌های `status=active` و `is_active=True`
- نمایش تعداد محصولات فعال هر فروشگاه
- دکمه هر فروشگاه مستقیم به منوی آن (`menu:shop:{shop_id}`)

### ۵.۱۲. خرید سریع (Fast Checkout)

- وقتی کاربر اطلاعات قبلی دارد (`user.saved_name/phone/address`)
- بعد از ASK_ADDRESS → دکمه `✅ بله، از اطلاعات قبلی استفاده کن`
- با زدن دکمه، `context.user_data` پر می‌شود و مستقیم به CONFIRM می‌رود
- بعد از سفارش موفق، `user.saved_name/phone/address` بروز می‌شوند

### ۵.۱۱. فروشگاه‌های اخیر

- `shop:recent` → لیست ۵ فروشگاه آخر (`user.recent_shops` JSON array)
- `shop:open:{id}` → باز کردن فروشگاه (set `current_shop_id` + منوی اصلی)

### ۵.۱۲. اعمال کد تخفیف

- در CONFIRM: دکمه `🎁 اعمال کد تخفیف` (اگر قبلاً اعمال نشده باشد)
- → `ASK_DISCOUNT`: کاربر کد را تایپ می‌کند
- validate:
  - `is_active == True`
  - `expires_at` نگذشته (اگر دارد)
  - `max_uses == 0 or used_count < max_uses`
  - `total_price >= min_order_amount`
- محاسبه مقدار تخفیف، clamp روی `total_price`
- ذخیره در `context.user_data["discount_code"]` و `["discount_amount"]`
- بازگشت به CONFIRM با مبلغ جدید
- در صورت خطا: پیام خطا + دکمه `❌ انصراف`

### ۵.۱۳. پشتیبانی دوطرفه (خریدار ↔ فروشنده)

- `support:open` → مکالمه با پشتیبانی (ادمین‌ها)
- `support:seller:{shop_id}` → ورود به مکالمه مستقیم با فروشنده. یک `Conversation` (بدون `order_id`) ایجاد می‌شود.
- پیام مشتری در جدول `Message` ذخیره می‌شود و فروشنده از طریق اینباکس (`seller:inbox`) آن را می‌بیند و پاسخ می‌دهد.
- فروشنده از `msg:open:{conv_id}` مکالمه را باز می‌کند و با `msg:reply:{conv_id}` شروع به تایپ می‌کند.
- پس از پیام فروشنده، مشتری نوتیفیکیشن دریافت می‌کند با دکمه `📨 مشاهده مکالمه`.
- دکمه `🔙 بازگشت به فروشگاه` در تمام مراحل حفظ می‌شود.
- پیام‌های متنی ساده (بدون پیوست تصویری فعلاً).

---

## ۶. سناریوهای ربات — ادمین

### ۶.۱. ورود به پنل (`/admin`)

- ادمین کل → پنل مدیریت کل
- فروشنده → مستقیم به `/myshop`
- مزاحم → `❌ دسترسی ندارید`

### ۶.۲. پنل اصلی

| دکمه | Callback | توضیح |
|------|----------|-------|
| 📊 آمار | `admin:stats` | |
| 📦 مدیریت محصولات | `admin:products:list:0` | |
| 🗂 مدیریت دسته‌بندی‌ها | `admin:categories` | |
| 🧾 سفارش‌های در حال پیگیری | `admin:orders:pending:0` | |
| 📜 تاریخچه سفارش‌ها | `admin:orders:history:0` | |
| 🏬 مدیریت فروشگاه‌ها | `admin:shops:list:0` | فقط ادمین کل |
| 📣 پیام همگانی | `admin:broadcast:start` | فقط ادمین کل |
| 🔙 بازگشت | `admin:panel` | |

### ۶.۳. آمار (`admin:stats`)

**ادمین کل:** کل فروشگاه‌ها (فعال)، محصولات فعال، کل سفارش‌ها، در حال پیگیری، درآمد پرداختی  
**فروشنده:** محصولات فعال، کل سفارش‌ها، در حال پیگیری، درآمد پرداختی فروشگاه خودش

### ۶.۴. مدیریت محصولات

- لیست با صفحه‌بندی (۸ عدد در هر صفحه)
- افزودن محصول (Conversation ۶ مرحله): نام → توضیحات → قیمت → دسته‌بندی → موجودی → عکس
- ویرایش فیلد: کلیک روی `✏️ فیلد` → تایپ مقدار جدید
  - **موجودی**: `old_stock = product.stock` → `setattr(product, "stock", int(value))` → اگر `old_stock == 0 and value > 0` → `_check_and_notify_restock(product_id, shop_id, context.bot)`
- تغییر عکس: `start_change_photo` → ارسال عکس جدید / "حذف" / "انصراف"
- تغییر وضعیت: `toggle_product`
- لینک مستقیم: `product_link` → نمایش `t.me/bot?start=product_123`
- حذف: تأیید دوم → `DELETE products WHERE id=X` (قبلاً `OrderItem.product_id=NULL` شده)

### ۶.۵. مدیریت دسته‌بندی‌ها

- لیست + دکمه `➕ افزودن`
- حذف: `Category.id → products → order_items.product_id=NULL → cart_items DELETE → products DELETE → category DELETE`

### ۶.۶. مدیریت سفارش‌ها

- **در حال پیگیری**: `PENDING_PAYMENT`, `PENDING`, `PAID`, `CONFIRMED`, `SHIPPED`
- **تاریخچه کامل**: همه سفارش‌ها با صفحه‌بندی
- **جزئیات**: کد رهگیری، وضعیت، روش پرداخت، گیرنده، آدرس، تاریخ شمسی، اقلام، جمع کل، تاریخچه تغییرات
- **تغییر وضعیت**: دکمه‌های داینامیک بر اساس `can_transition()`

### ۶.۷. مدیریت فروشگاه‌ها (فقط ادمین کل)

- لیست + صفحه‌بندی
- فعال/غیرفعال کردن
- ویرایش: نام، وضعیت، توضیحات
- حذف: تأیید دوم → اخطار آبشار → حذف cascade با SQL مستقیم

### ۶.۸. پیام همگانی (Broadcast)

- دریافت متن → ارسال به همه کاربران `is_blocked=False`
- فاصله ۰.۰۴ ثانیه (Rate Limit)
- Forbidden → علامت‌گذاری کاربر `blocked`
- آمار نهایی: موفق / ناموفق / بلاک

### ۶.۹. تایید/رد فروشنده

- **تایید**: `admin:seller:approve` → `shop.status = "active"` → پیام خوش‌آمدگویی به فروشنده + لینک فروشگاه
- **رد**: `admin:seller:reject` → Conversation برای دلیل → `shop.status = "rejected"` + پیام به فروشنده

---

## ۷. سناریوهای ربات — فروشنده

### ۷.۱. `/my_panel` — تنظیمات فروشنده

| دکمه | توضیح |
|------|--------|
| `🧾 تنظیمات دریافت وجه` | تنظیم شماره کارت + نام صاحب کارت |
| `🔑 تغییر رمز عبور` | دریافت رمز جدید (≥۶ کاراکتر) |
| `📊 داشبورد فروشنده` | آمار فروش |
| `📷 تنظیم بنر` | آپلود عکس کاور فروشگاه |
| `🎁 مدیریت کدهای تخفیف` | ساخت/مشاهده کدهای تخفیف |
| `🌐 باز کردن پنل سایت` | لینک به سایت |

### ۷.۲. `/myshop` — مدیریت فروشگاه

| دکمه | توضیح |
|------|--------|
| `🗂 مدیریت دسته‌بندی‌ها` | |
| `📦 مدیریت محصولات` | |
| `🧾 سفارش‌های در حال پیگیری` | |
| `📜 تاریخچه سفارش‌ها` | |

### ۷.۳. رمز عبور

- دریافت رمز جدید (حداقل ۶ کاراکتر)
- هش bcrypt + ذخیره در `shop_owners.password_hash`
- Salt جدید هر بار تولید می‌شود
- `must_change_password = True` بعد از `/reset_password` — لاگین بعدی الزاماً به `/change-password` ریدایرکت می‌شود

### ۷.۴. کد تخفیف

1. `discount:list` → لیست کدهای موجود
2. `discount:create` → ویزارد:
   - نوع: درصدی / مبلغی
   - مقدار
   - (اختیاری) حداقل مبلغ سفارش
   - (اختیاری) حداکثر دفعات استفاده
3. `discount:toggle:{id}` → فعال/غیرفعال

### ۷.۵. بنر فروشگاه

- `shop:banner` → آپلود عکس → `shop.banner_image = file_id`
- اگر بنر فعال باشد → در `nav:main` ابتدا `send_photo` با بنر + کپشن + `📷 مشاهده محصولات`

### ۷.۶. تنظیمات پرداخت (`seller:payment_settings`)

- `🔢 تنظیم شماره کارت` → دریافت ۱۶ رقمی → AES-256-GCM رمزنگاری می‌شود
- `👤 تنظیم نام صاحب کارت` → AES-256-GCM رمزنگاری می‌شود
- `🆔 تنظیم merchant_id زین‌پال` (غیرفعال)
- رمزگشایی فقط در لحظه نمایش به مشتری در مرحله پرداخت (both bot & website)

### ۷.۷. داشبورد فروشنده

- امروز / این هفته / این ماه
- پرفروش‌ترین محصول
- کم‌فروش‌ترین محصول
- میانگین مبلغ سفارش
- نرخ تبدیل (تعداد سفارش / تعداد بازدید)

### ۷.۸. سیستم اشتراک فروشگاه (`seller:subscription:show`)

فروشنده باید اشتراک فعال داشته باشد تا بتواند از پنل خود استفاده کند.

#### ۷.۸.۱. مشاهده وضعیت اشتراک
- `seller:subscription:show` → نمایش وضعیت اشتراک فعلی (تاریخ پایان، نوع پلن)
- اگر اشتراک فعال نیست → پیام هشدار + دکمه خرید اشتراک جدید

#### ۷.۸.۲. خرید اشتراک
- انتخاب پلن: ماهانه / ۳ ماهه / ۶ ماهه / سالانه
- نمایش شماره کارت ادمین (از `config.ADMIN_CARD_NUMBER`)
- ارسال عکس رسید واریز
- ایجاد ردیف `ShopSubscription` با `approval_status=pending`
- نوتیفیکیشن به ادمین برای تایید

#### ۷.۸.۳. تایید ادمین
- `admin:sub:detail:{id}` → جزئیات درخواست اشتراک
- `admin:sub:verify:{id}` → تایید: `approval_status=approved` + `verified_at=now` + فعال‌سازی فروشگاه
- `admin:sub:reject:{id}` → رد: دلیل + `approval_status=rejected`

#### ۷.۸.۴. دکوریتور `@require_active_subscription`

دوتا دکوریتور وجود داره:

**۱. `@require_active_subscription`** — برای **مسیرهای مشتری** (مرور فروشگاه، سبد خرید، ثبت سفارش جدید)
- اگه فروشنده `suspended` باشه یا اشتراک فعال نداشته باشه → پیام خطا نشون می‌ده و اجازه ادامه نمی‌ده
- مسیرهای استثنا: خرید اشتراک، مشاهده سفارش‌های قبلی، پشتیبانی

**۲. `@require_seller_subscription`** — برای **مسیرهای مدیریتی فروشنده** (products, categories, orders, settings)
- اگه اشتراک منقضی شده → پیام هشدار + دکمه خرید اشتراک جدید
- مسیرهای استثنا: خود صفحه اشتراک و پنل پشتیبانی همیشه در دسترس هستند

هر دو در `handlers/subscription_decorator.py` تعریف شده‌اند.

---

### ۷.۹. استراتژی انقضای اشتراک (Real-time، بدون کرون)

**قرارداد صریح:** هیچ کرون‌جابی برای انقضای اشتراک وجود ندارد.

- **بررسی لحظه‌ای (Real-time):** `ShopSubscription.is_active` property محاسبه‌شده در لحظه (`end_date > utcnow()` و `approval_status == "approved"` و `superseded_at IS NULL`)
- **دکوریتور چک می‌کند:** هر بار مسیر مشتری/فروشنده صدا زده می‌شود، `has_active_subscription(shop_id)` بلافاصله در دیتابیس چک می‌شود — بدون فیلد کش‌شده در `Shop`
- **Sync با `shop.status`:** فقط در `verify_subscription` (تایید ادمین) و `reject_subscription`، `shop.status = "active"/"suspended"` ست می‌شود. انقضای طبیعی اشتراک `shop.status` را تغییر نمی‌دهد (چون real-time چک می‌شود)
- **مزیت:** هیچ حلقه‌ی جاافتاده، هیچ inconsistency بین `shop.status` و واقعیت اشتراک، مقیاس‌پذیر (خونده فقط در لحظه request)

---

## ۸. فرآیندهای تراکنشی

### ۸.۱. `create_order_from_cart` (سرویس متمرکز سفارش)

این تابع در `services/order_service.py` — **تنها مسیر ایجاد سفارش** برای هر دو روش پرداخت.

```python
async def create_order_from_cart(
    user_id, shop_id, customer_info, payment_method,
    discount_code="", discount_amount=0
) -> OrderResult:
```

**مراحل در یک تراکنش واحد:**

1. **بارگذاری سبد**: `SELECT ... FOR UPDATE` روی `Product` برای هر آیتم
2. **اعتبارسنجی**: محصول فعال است؟ shop_id درست است؟ موجودی کافی؟
3. **رزرو اتمیک**: `reserve_stock_atomic` — UPDATE شرطی با چک `stock - reserved_stock >= qty`
4. **محاسبه قیمت**: `total = sum(price * quantity) + shipping_cost` → `total = max(0, total - discount_amount)` (clamp)
5. **ساخت Order**: با `tracking_code`, `discount_code`, `discount_amount`, `receiver_name`, `phone`, `shipping_address`
6. **ساخت OrderItemها**: از داده‌های لحظه سفارش (`product_name`, `unit_price`)
7. **تاریخچه**: `order.add_status_entry(initial_status, by="system")`
8. **خالی کردن سبد**: `DELETE cart_items`
9. **commit**

**خروجی `OrderResult`:**
```python
@dataclass
class OrderResult:
    order: Order
    tracking_code: str
    total_price: int
    items_count: int
    discount_code: str = ""
    discount_amount: int = 0
```

### ۸.۲. رزرو اتمیک موجودی (`reserve_stock_atomic`)

```sql
UPDATE products 
SET reserved_stock = reserved_stock + :qty 
WHERE id = :pid AND (stock - reserved_stock) >= :qty
```

- اگر `rowcount == 0` برای هر آیتم → رول‌بک کامل
- `nowait=False` — در Deadlock منتظر می‌ماند

### ۸.۳. آزادسازی رزرو (`release_reserved_stock`)

```sql
UPDATE products 
SET reserved_stock = GREATEST(0, reserved_stock - :qty) 
WHERE id = :pid
```

- `GREATEST(0, ...)` برای جلوگیری از منفی شدن

### ۸.۴. نهایی‌سازی موجودی (`finalize_stock_deduction` — در `transition_order`)

وقتی سفارش به `PAID` (برای card_to_card) یا `CONFIRMED` (برای COD) می‌رسد:

```sql
UPDATE products 
SET stock = MAX(0, stock - :qty),
    reserved_stock = MAX(0, reserved_stock - :qty) 
WHERE id = :pid
```

**توجه**: `stock` (`Product.stock`) ستون است، نه تابع. `MAX(0, stock - qty)` در SQL `stock - qty` را محاسبه می‌کند و PostgreSQL `MAX` aggregate روی دو اسکالر کار نمی‌کند. از `GREATEST` استفاده کنید:

```python
values(stock=Product.stock - item.quantity, reserved_stock=Product.reserved_stock - item.quantity)
```
مقادیر در پایتون محاسبه می‌شوند، `GREATEST` در SQL نیست. اگر `stock` به SQL ارسال شود، مقدار محاسبه شده پایتون ارسال می‌شود — `stock - qty` ممکن است منفی شود. برای ایمنی:

```python
values(stock=func.greatest(0, Product.stock - item.quantity),
       reserved_stock=func.greatest(0, Product.reserved_stock - item.quantity))
```

### ۸.۵. `transition_order` (تغییر وضعیت مرکزی)

```python
async def transition_order(order_id, target_status, actor="admin", bot=None) -> Order:
```

- **Row-lock روی Order**: `session.get(Order, order_id, with_for_update=True)` قبل از تغییر وضعیت — جلوگیری از race با cron cleanup
- اعتبارسنجی: `can_transition(order, target_status, actor)` در `utils/order_validator.py`
- `ALLOWED_TRANSITIONS` دیکشنری وضعیت‌های مجاز
- منطق جانبی:
  - **PAID** (card_to_card): نهایی‌سازی موجودی + `_check_low_stock_after_reduction`
  - **CONFIRMED** (COD): نهایی‌سازی موجودی + `_check_low_stock_after_reduction`
  - **CANCELLED**: آزادسازی رزرو
- **Emit رویداد**: `EventBus.emit` برای ORDER_PAID / ORDER_CONFIRMED / ORDER_CANCELLED

### ۸.۶. `cancel_order_and_release_stock`

- چک می‌کند وضعیت قابل لغو است (نه DELIVERED/CANCELLED/REFUNDED)
- `release_reserved_stock`
- `order.status = CANCELLED`
- **Emit رویداد**: `Event.ORDER_CANCELLED` (اگر `bot` پاس داده شود)

### ۸.۷. فیکس‌های تراکنشی مهم (یولای ۲۰۲۶)

#### ۱. ترتیب ثابت قفل (Deadlock Prevention)
در `create_order_from_cart`، آیتم‌های سبد قبل از پردازش بر اساس `product_id` سورت می‌شوند:
```python
cart_items = sorted(cart_items, key=lambda i: i.product_id)
```
→ تضمین می‌کند همه تراکنش‌ها productها را همیشه به یک ترتیب قفل می‌کنند.

#### ۲. یکی‌سازی SELECT FOR UPDATE + UPDATE
به‌جای دو کوئری جداگانه (`SELECT ... FOR UPDATE` بعد `UPDATE`)، از `UPDATE ... WHERE ... RETURNING` استفاده می‌شود برای رزرو اتمیک:
```sql
UPDATE products 
SET reserved_stock = reserved_stock + :qty 
WHERE id = :pid AND (stock - reserved_stock) >= :qty 
RETURNING stock, reserved_stock
```
→ کاهش round-trip و window برای race.

#### ۳. Row-level lock روی Order در transition_order
```python
order = await session.get(Order, order_id, with_for_update=True)
```
→ جلوی همزمانی `transition_order` + `cleanup_abandoned_payments` (cron) می‌گیرد.

#### ۴. Idempotency دو لایه روی ایجاد سفارش
- **In-memory**: `_order_in_progress` flag در `context.user_data`
- **DB-level**: `pg_advisory_xact_lock(user_id)` در `create_order_from_cart`
→ هر دو لایه جلوگیری از double-submit می‌کنند.

#### ۵. GREATEST به‌جای MAX در SQL
`MAX(0, x)` در PostgreSQL aggregate است، روی scalar کار نمی‌کند. کد واقعی از `func.greatest(0, ...)` یا محاسبه در پایتون استفاده می‌کند:
```python
values(stock=func.greatest(0, Product.stock - item.quantity),
       reserved_stock=func.greatest(0, Product.reserved_stock - item.quantity))
```

---

## ۹. جریان کامل سفارش

### سناریوی A: مشتری — کارت‌به‌کارت

```
1. لینک فروشگاه → /start → منوی اصلی
2. 🛍 مشاهده محصولات → دسته → محصول
3. ➕ افزودن به سبد خرید
4. 🛒 سبد خرید → ✅ ثبت سفارش
5. ویزارد: نام گیرنده → شماره تماس → آدرس → 💳 کارت به کارت
6. 🎁 (اختیاری) کد تخفیف → اعمال
7. ✅ ثبت نهایی سفارش:
   ├── create_order_from_cart() → رزرو اتمیک ✅
   └── نمایش شماره کارت فروشنده + مبلغ
8. ارسال عکس رسید → attach_card_receipt() → نوتیفیکیشن به فروشنده
9. فروشنده: ✅ تایید → transition_order(PAID) → نوتیفیکیشن به مشتری
10. فروشنده ارسال می‌کند → CONFIRMED → SHIPPED → DELIVERED
```

### سناریوی B: فروشنده جدید ثبت‌نام می‌کند

```
1. 🏪 می‌خوام فروشگاه بسازم
2. نام → توضیحات → شماره تماس → لینک کانال تلگرام → شماره کارت
3. صاحب کارت → رمز عبور → تأیید و ارسال
4. ادمین پیام + دکمه ✅ تایید / ❌ رد دریافت می‌کند
5. ✅ تایید → shop.status = "active" → پیام خوش‌آمدگویی
6. فروشنده تنظیمات پرداخت + محصولات را اضافه می‌کند
```

### سناریوی C: اعلان موجود شدن

```
1. فروشنده `restock:subscribe:{pid}` → رکورد در RestockSubscription
2. فروشنده موجودی محصول را از ۰ به >۰ می‌کند
3. save_edit_field() → old_stock==0, value>0 → _check_and_notify_restock()
4. برای هر subscriber با notified=False:
   → context.bot.send_message("🔔 محصول «X» دوباره موجود شد!")
   → notified = True
```

---

## ۱۰. کرون‌جاب‌ها

### ۱۰.۱. پاک‌سازی خودکار سفارش‌های پرداخت‌نشده (APScheduler)

- `cleanup_abandoned_payments()`:
  - **بدون رسید**: ۱۵ دقیقه پس از ایجاد → CANCELLED و آزادسازی `reserved_stock`
  - **بعد از رسید**: ۴۸ ساعت (فروشنده فرصت کافی دارد)
  - **COD (PENDING)**: ۳۰ روز → CANCELLED
- اجرا: هر ۵ دقیقه (`payment._post_init`)

```python
async def cleanup_task():
    await payment_svc.cleanup_abandoned_payments()
```
- سفارش‌های بدون رسید `created_at < now - 15min` → CANCELLED
- سفارش‌های با رسید (بیش از ۴۸ ساعت) → CANCELLED
- COD سفارش‌های `PENDING` قدیمی‌تر از ۳۰ روز → CANCELLED
- موجودی رزرو شده آزاد می‌شود
- از `TIMESTAMP WITHOUT TIME ZONE` → `.replace(tzinfo=None)` برای مقایسه

### ۱۰.۲. یادآوری سبد رها شده (APScheduler)

```python
scheduler.add_job(check_abandoned_carts, "interval", minutes=30)
```

- اجرا: هر ۳۰ دقیقه
- سبدهایی که بیش از ۱۲ ساعت از آخرین بروزرسانی (آخرین آیتم) گذشته است
- به کاربر پیام یادآوری می‌فرستد
- اگر کاربر سبد را خالی کرده یا سفارش داده باشد → رد می‌شود

### ۱۰.۳. برنامه آینده

- [x] ارسال یادآوری به فروشنده برای سفارش‌های در انتظار
- [x] پشتیبان‌گیری خودکار دیتابیس — کانتینر foroshgram_backup با crond (روزانه ۳ صبح + هفتگی)
- [ ] گزارش روزانه فروش به ادمین

---

## ۱۱. EventBus معماری رویداد

### ۱۱.۱. Event enum

```python
class Event(str, Enum):  # مقدار = نام رویداد برای ارسال به listener
    ORDER_PAID = "order_paid"
    ORDER_CONFIRMED = "order_confirmed" 
    ORDER_CANCELLED = "order_cancelled"
    FIRST_SALE = "first_sale"
```

### ۱۱.۲. EventBus

```python
class EventBus:
    _listeners: dict[str, list[Callable]]
    
    def on(self, event: Event, listener):    # ثبت listener
    async def emit(self, event, **payload):  # انتشار رویداد
    
    # payload شامل: order_id, shop_id, bot, tracking_code, is_first_sale, cancelled_by
```

### ۱۱.۳. Listenerهای ثبت شده (در `event_listeners.py`)

| رویداد | Listener | توضیح |
|--------|----------|-------|
| ORDER_PAID | `notify_shop_owner_new_order` | ارسال سفارش جدید به فروشنده |
| ORDER_PAID | `notify_customer_order_paid` | پیام تأیید پرداخت برای مشتری |
| ORDER_CONFIRMED | `notify_customer_confirmed` | پیام "سفارش تأیید شد" |
| ORDER_CANCELLED | `notify_customer_cancelled` | پیام لغو سفارش |
| ORDER_CANCELLED | `notify_shop_owner_cancelled` | اطلاع به فروشنده از لغو |
| FIRST_SALE | `celebrate_first_sale` | 🎉 جشن اولین فروش |

### ۱۱.۴. جریان انتشار

```
transition_order(PAID)
  → EventBus.emit(Event.ORDER_PAID, order_id=..., shop_id=..., bot=..., is_first_sale=True|False)
    → notify_shop_owner_new_order(payload)
    → notify_customer_order_paid(payload)
    → (اگر is_first_sale) celebrate_first_sale(payload)
```

---

## ۱۲. API Reference

### ۱۲.۱. مسیرهای داخلی (Next.js API Routes)

| مسیر | متد | پارامترها | پاسخ موفق | نیاز به احراز |
|------|------|-----------|-----------|---------------|
| `/api/auth/login` | POST | `{ userId, password? }` | `{ success, role, shopId? }` | خیر |
| `/api/auth/logout` | POST | — | `{ success: true }` | خیر |
| `/api/auth/me` | GET | — | `{ userId, role, shopId? }` | بله |
| `/api/admin/create-claim-code` | POST | `{ shopId, expiresAt }` | `{ code }` | ادمین |
| `/api/admin/orders/[id]/status` | PATCH | `{ status }` | `{ success: true }` | ادمین |
| `/api/admin/toggle-shop` | POST | `{ shopId }` | `{ success }` | ادمین |
| `/api/admin/toggle-user-block` | POST | `{ userId }` | `{ success }` | ادمین |
| `/api/seller/orders/[id]/status` | PATCH | `{ status }` | `{ success }` | فروشنده |
| `/api/seller/shop-info` | GET | — | `{ shop }` | فروشنده |
| `/api/seller/toggle-product` | POST | `{ productId }` | `{ success }` | فروشنده |
| `/api/product-image/[id]` | GET | — | image file | خیر |

### ۱۲.۲. سیستم پیام خریدار-فروشنده (Conversations)

| فایل | توضیح |
|------|-------|
| `handlers/conversations.py` | ConversationHandler مجزا — مشتری از `order:conversation:{id}` شروع می‌کند |
| فروشنده اینباکس در پنل `seller:inbox` دارد |
| `Conversation` | جدول: `id`, `buyer_id`, `shop_id`, `order_id?`, `status` (open/closed) |
| `Message` | جدول: `id`, `conversation_id`, `sender_role` (buyer/seller), `content`, `has_attachment`, `attachment_file_id`, `read_at` |
| `/cancel` | لغو مکالمه فعلی |

جریان خریدار:
- از `order:detail` → `conv:open:{id}` → ارسال متن → فروشنده در `seller:inbox` می‌بیند → پاسخ می‌دهد.

جریان پشتیبانی فروشگاه (`support:seller`):
1. مشتری دکمه `💬 پیام به فروشنده` را در منوی فروشگاه می‌زند
2. `seller_support_start` یک `Conversation` جدید (بدون `order_id`) ایجاد یا دریافت می‌کند
3. مشتری پیام خود را تایپ می‌کند → `seller_support_receive` ذخیره در `Message`
4. فروشنده در `seller:inbox` پیام را می‌بیند → `msg:open:{conv_id}` باز می‌کند → `msg:reply:{conv_id}` شروع به تایپ می‌کند
5. `send_message` (در conversations.py) ذخیره می‌کند و مشتری نوتیفیکیشن می‌گیرد
6. دکمه `🔙 بازگشت به فروشگاه` در تمام مراحل حفظ می‌شود

### ۱۲.۳. Callback Pattern‌های ربات — مشتری

| Pattern | Handler | توضیح |
|---------|---------|-------|
| `nav:main` | `main_menu_callback` | بازگشت به منوی اصلی |
| `cat:list` | `show_categories` | نمایش دسته‌بندی‌ها |
| `cat:open:{id}:{page}` | `show_products` | محصولات یک دسته |
| `cat:sort:{cat_id}:{sort}` | `sort_products` | مرتب‌سازی (price_asc/price_desc/newest) |
| `cat:stock:{cat_id}` | `stock_filter` | فیلتر فقط موجود |
| `prod:open:{id}:{cat}:{page}` | `show_product_detail` | جزئیات محصول |
| `cart:add:{pid}` | `add_to_cart` | افزودن به سبد |
| `cart:view` | `view_cart` | نمایش سبد خرید |
| `cart:inc:{id}` | `change_quantity` | افزایش تعداد |
| `cart:dec:{id}` | `change_quantity` | کاهش تعداد |
| `cart:remove:{id}` | `remove_from_cart` | حذف از سبد |
| `cart:clear` | `clear_cart` | خالی کردن سبد |
| `order:start` | `start_checkout` | شروع ثبت سفارش |
| `order:confirm` | `confirm_order` | ثبت نهایی |
| `order:change_payment` | `change_payment_method` | تغییر روش پرداخت |
| `order:cancel` | `cancel_order` | انصراف |
| `order:history` | `order_history` | تاریخچه سفارش‌ها |
| `order:detail:{id}` | `order_detail_customer` | جزئیات سفارش مشتری |
| `order:reorder:{id}` | `handle_reorder` | خرید مجدد |
| `order:ask_discount` | `ask_discount` | درخواست کد تخفیف |
| `pay:card_to_card` | `ask_payment_method` | انتخاب کارت‌به‌کارت |
| `pay:verify:{id}:{authority}` | `verify_payment_callback` | تأیید پرداخت (قدیمی) |
| `pay:cancel:{id}` | `cancel_order_payment` | لغو سفارش |
| `pay:receipt_retry:{id}` | `handle_card_receipt_retry` | آپلود مجدد رسید |
| `pay:convert_cod:{id}` | `handle_convert_to_cod` | تغییر به درب منزل |
|| `wishlist:add:{pid}:{cat}:{page}` | `toggle_wishlist` | افزودن/حذف از علاقه‌مندی‌ها |
|| `wishlist:remove:{pid}:{cat}:{page}` | `toggle_wishlist` | حذف از علاقه‌مندی‌ها |
|| `wishlist:view` | `view_wishlist` | نمایش علاقه‌مندی‌ها |
| `search:start` | `start_search` | شروع جستجو |
| `search:result:{pid}` | `search_result_callback` | نتیجه جستجو |
| `restock:subscribe:{pid}` | `subscribe_restock` | سابسکرایب موجود شدن |
| `restock:unsubscribe:{pid}` | `unsubscribe_restock` | لغو سابسکرایب |
| `shop:recent` | `show_recent_shops` | فروشگاه‌های اخیر |
| `shop:open:{id}` | `open_shop_from_recent` | باز کردن فروشگاه |
| `support:open` | `support` → `support_start` | پشتیبانی — ورود به مکالمه با ادمین‌ها |
| `support:seller:{shop_id}` | `seller_support_start` | پشتیبانی فروشگاه — شروع مکالمه با فروشنده |
| `support_seller_cancel` | `seller_support_cancel` | لغو مکالمه پشتیبانی فروشنده |
| `noop` | `noop_callback` | دکمه صرفاً نمایشی |
| `order:conversation:{id}` | `open_conversation_buyer` | شروع مکالمه با فروشنده |
| `conv:back` | `back_to_order_detail` | بازگشت به جزئیات سفارش |

### ۱۲.۴. Callback Pattern‌های ربات — فروشنده

| Pattern | Handler | توضیح |
|---------|---------|-------|
| `seller_reg:start` | `seller_registration_start` | شروع ثبت‌نام فروشنده |
| `seller_reg:cancel` | `cancel_registration` | لغو ثبت‌نام |
| `seller:change_password` | `change_password_start` | تغییر رمز |
| `seller:cancel_password` | `cancel_change_password` | لغو تغییر رمز |
| `seller:payment_settings` | `payment_settings` | تنظیمات پرداخت |
| `seller:set_card` | `ask_card_number` | تنظیم شماره کارت |
| `seller:set_card_holder` | `ask_card_holder_name` | تنظیم نام صاحب کارت |
| `seller:set_banner` | `ask_banner_image` | تنظیم بنر |
| `discount:list` | `_show_discount_menu` | لیست کد تخفیف |
| `discount:create` | `apply_discount_start` | ساخت کد جدید |
| `discount:toggle:{id}` | `toggle_discount` | فعال/غیرفعال |
| `seller:panel` | `seller_panel_command` | پنل یکپارچه فروشنده (message-based) |
| `seller:panel_back` | `panel_back` | بازگشت به پنل فروشنده |
| `seller:orders:pending` | `seller_orders_pending` | سفارش‌های در انتظار |
| `seller:orders:history` | `seller_orders_history` | تاریخچه سفارش‌ها |
| `seller:inbox` | `seller_inbox` | لیست مکالمات خریداران (اینباکس) |
| `msg:open:{conv_id}` | `seller_open_conv` | باز کردن مکالمه (seller side) |
| `msg:reply:{conv_id}` | `start_send_message` | شروع ارسال پیام به مشتری |
| `send_message:{conv_id}` | `send_message` | ارسال پیام (text handler) |
| `seller:conv:back` | `back_to_inbox` | بازگشت به اینباکس |

### ۱۲.۵. Callback Pattern‌های ربات — ادمین

| Pattern | Handler | توضیح |
|---------|---------|-------|
| `admin:panel` | `admin_panel_callback` | پنل ادمین |
| `admin:stats` | `admin_stats` | آمار |
| `admin:products:list:{page}` | `list_products` | لیست محصولات |
| `admin:products:add` | `start_add_product` | افزودن محصول |
| `admin:products:edit:{id}` | `open_product_edit` | ویرایش محصول |
| `admin:products:link:{id}` | `product_link` | لینک مستقیم |
| `admin:products:toggle:{id}` | `toggle_product` | فعال/غیرفعال |
| `admin:products:delete:{id}` | `delete_product_confirm` | تأیید حذف |
| `admin:products:delete_final:{id}` | `delete_product_final` | حذف نهایی |
| `admin:products:field:{id}:{field}` | `start_edit_field` | ویرایش فیلد |
| `admin:products:photo:{id}` | `start_change_photo` | تغییر عکس |
| `admin:products:add_forward` | `start_add_forward` | افزودن محصول با فوروارد |
| `admin:categories` | `list_categories` | لیست دسته‌ها |
| `admin:categories:add` | `start_add_category` | افزودن دسته |
| `admin:categories:delete:{id}` | `delete_category_confirm` | تأیید حذف |
| `admin:categories:delete_final:{id}` | `delete_category_final` | حذف نهایی |
| `admin:orders:pending:{page}` | `list_pending_orders` | سفارش‌های جاری |
| `admin:orders:history:{page}` | `list_all_orders` | تاریخچه |
| `admin:orders:detail:{id}:{source}` | `order_detail` | جزئیات سفارش |
| `admin:orders:status:{id}:{status}` | `change_order_status` | تغییر وضعیت |
| `admin:shops:list:{page}` | `list_shops` | لیست فروشگاه‌ها |
| `admin:shops:add` | `start_add_shop` | افزودن فروشگاه |
| `admin:shops:edit:{id}` | `edit_shop` | ویرایش فروشگاه |
| `admin:shops:toggle:{id}` | `toggle_shop` | فعال/غیرفعال |
| `admin:shops:delete:{id}` | `delete_shop_confirm` | تأیید حذف |
| `admin:shops:delete_final:{id}` | `delete_shop_final` | حذف نهایی |
| `admin:broadcast:start` | `start_broadcast` | پیام همگانی |
| `admin:seller:approve:{shop_id}` | `handle_admin_approve` | تایید فروشنده |
| `admin:seller:reject:{shop_id}` | `handle_admin_reject` | رد فروشنده |

### ۱۲.۶. Command‌های ربات

**همه کاربران (پیش‌فرض):**

| دستور | Handler | توضیح |
|-------|---------|-------|
| `/start` | `start_command` | شروع + منوی هوشمند (پشتیبانی از `shop_X`, `product_X`, `category_X`) |
| `/help` | `help_command` | راهنمای نقش‌محور |
| `/menu` | `menu_command` | مشاهده دسته‌بندی‌ها (fallback به `last_shop_id`) |
| `/search` | `search_command` | جستجوی محصول |
| `/cart` | `cart_command` | مشاهده سبد خرید |
| `/my_orders` | `my_orders_command` | تاریخچه سفارش‌ها |
| `/support` | `support_command` | پشتیبانی |
| `/cancel` | `cancel_conversation` | لغو مکالمه فعلی |

**اضافی برای فروشنده‌ها:**

| دستور | توضیح |
|-------|--------|
| `/myshop` | مدیریت فروشگاه من |
| `/neworders` | سفارش‌های جدید |
| `/my_panel` | پنل فروشنده + تنظیمات پرداخت + تغییر رمز |
| `/reset_password` | بازیابی رمز عبور (رمز موقت ۸ رقمی) |

**اضافی برای ادمین‌ها:**

| دستور | توضیح |
|-------|--------|
| `/admin` | پنل مدیریت |
| `/orders` | سفارش‌های در حال پیگیری |
| `/pending_shops` | فروشگاه‌های در انتظار تایید |
| `/stats` | آمار کلی |

### ۱۲.۷. سطح‌بندی BotCommandScope

```python
set_default_menu(bot)          # BotCommandScopeDefault — همه
set_seller_menu(bot, chat_id)  # BotCommandScopeChat — فقط فروشنده
set_admin_menu(bot, chat_id)   # BotCommandScopeChat — فقط ادمین
delete_seller_menu(bot, chat_id)  # حذف دستورات فروشنده
```

- پیاده‌سازی در `handlers/bot_commands.py`
- `set_default_menu` + `set_admin_menu` در استارتاپ (`_post_init`)
- `set_seller_menu` بعد از تایید نهایی فروشنده
- همه فروشنده‌های فعال در استارتاپ بازگردانی می‌شوند

---

## ۱۳. زیرساخت و استقرار

### ۱۳.۱. VPS

| مشخصه | مقدار |
|-------|-------|
| آدرس | `185.204.168.57` (خارج ایران) |
| کاربر | `ubuntu` |
| استک | Docker Compose |

### ۱۳.۲. Docker Compose

```yaml
services:
  postgres:
    image: postgres:16-alpine
    ports: ["5432:5432"]
  bot:
    build: ./telegram_order_bot
    depends_on: [postgres]
  website:
    build: ./telegram_order_website
    ports: ["3000:3000"]
    depends_on: [postgres]
```

### ۱۳.۳. Deployment

- `deploy-to-vps.sh` — استقرار مستقیم با bash
- `deploy-via-ssh.py` — استقرار خودکار با SSH + Docker
- `fix-deployment.py` — رفع مشکلات استقرار
- `fix-nginx.py` — رفع مشکلات Nginx

### ۱۳.۴. Backup & Restore (جديد)

| فایل | توضیح |
|------|-------|
| `scripts/backup.sh` | بک‌آپ روزانه/هفتگی/ماهانه PostgreSQL با retention + sync به S3 (rclone) |
| `scripts/restore.sh` | بازیابی بک‌آپ با drop/create + اعمال init-scripts |
| `scripts/setup-rclone.sh` | راه‌اندازی rclone برای S3/MinIO/DO Spaces/B2/Wasabi |
| `scripts/Dockerfile.backup` | ایمیج بک‌آپ (Alpine + pg_dump + rclone + cron) |

**زمان‌بندی:**
- روزانه: ساعت ۰۳:۰۰ (حفظ ۷ روز)
- هفتگی: یکشنبه‌ها (حفظ ۴ هفته)
- ماهانه: اول هر ماه (حفظ ۱۲ ماه)

**استقرار در Docker Compose:**
```yaml
backup:
  build:
    context: .
    dockerfile: scripts/Dockerfile.backup
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - ./scripts:/scripts:ro
    - ./backups:/backups
    - ./init-scripts:/init-scripts:ro
    - ./rclone.conf:/config/rclone.conf:ro
  restart: unless-stopped
```

**تنظیم rclone (یک‌بار روی VPS):**
```bash
chmod +x scripts/setup-rclone.sh
./scripts/setup-rclone.sh
```

### ۱۳.۵. Nginx

- `nginx.conf` — کانفیگ کامل با SSL
- `nginx-no-ssl.conf` — کانفیگ بدون SSL (توسعه)

### ۱۳.۵. متغیرهای محیطی

**.env ربات (telegram_order_bot/.env):**
```ini
BOT_TOKEN=8871159970:...
ADMIN_IDS=8497713691
DATABASE_URL=postgresql+asyncpg://foroshgram:...@postgres/foroshgram
NOTIFICATION_CHANNEL_ID=-100...
PROXY_URL=http://user:pass@host:port
```

**.env سایت (telegram_order_website/.env.production):**
```ini
DATABASE_URL=postgresql://foroshgram:...@postgres/foroshgram
JWT_SECRET=...
ADMIN_IDS=8497713691
```

---

## ۱۴. تغییرات و نقشه راه

### ✅ پیاده‌سازی شده

#### هسته
- [x] شروع هوشمند `/start` (shop/product/category لینک + بدون پارامتر)
- [x] دسته‌بندی‌ها و محصولات با صفحه‌بندی و مرتب‌سازی
- [x] سبد خرید کامل (افزودن/کم/زیاد/حذف/خالی کردن)
- [x] ثبت سفارش ConversationHandler 5+ مرحله
- [x] پرداخت کارت‌به‌کارت (رسید + تأیید/رد فروشنده + retry)
- [x] رزرو اتمیک موجودی (UPDATE شرطی + GREATEST)
- [x] سرویس متمرکز سفارش (`create_order_from_cart` + `transition_order`)
- [x] تاریخچه وضعیت (OrderHistory جدول جداگانه)

#### پنل ادمین
- [x] مدیریت کامل محصولات (افزودن، ویرایش، حذف، تغییر عکس)
- [x] مدیریت دسته‌بندی‌ها (افزودن، حذف با آبشار)
- [x] مدیریت سفارش‌ها (جزئیات + تغییر وضعیت داینامیک)
- [x] مدیریت فروشگاه‌ها (فعال/غیرفعال + حذف)
- [x] پیام همگانی (Broadcast)
- [x] تایید/رد فروشنده توسط ادمین
- [x] داشبورد آمار (ادمین کل + فروشنده)

#### پنل فروشنده
- [x] ثبت‌نام ۸ مرحله‌ای
- [x] تغییر رمز عبور + بازیابی (`/reset_password`)
- [x] تنظیمات پرداخت (شماره کارت، نام صاحب کارت)
- [x] تنظیم بنر فروشگاه
- [x] مدیریت کد تخفیف (ساخت درصدی/مبلغی)
- [x] داشبورد فروشنده (آمار فروش)
- [x] **سیستم اشتراک**: پلن‌های ماهانه/فصلی/سالانه، خرید کارت‌به‌کارت، تایید ادمین
- [x] **دکوریتور `@require_active_subscription`**: محافظت تمام مسیرهای مدیریتی

#### ویژگی‌های پیشرفته
- [x] EventBus + NotificationService
- [x] یادآور موجودی کم (< ۵)
- [x] علاقه‌مندی‌ها (Wishlist)
- [x] جستجوی تعاملی (در فروشگاه جاری)
- [x] **جستجوی همگانی محصولات** (`/searchall`): سرچ در تمام فروشگاه‌ها
- [x] **جستجوی فروشگاه‌ها** (`/findshop`): پیدا کردن فروشگاه با نام/یوزرنیم
- [x] سبد خرید رها شده (یادآوری ۱۲ ساعت)
- [x] خرید مجدد (Reorder)
- [x] گالری چندعکسی (send_media_group)
- [x] اعلان موجود شدن (Restock Notification)
- [x] کد تخفیف (اعمال در checkout)
- [x] خرید سریع (اطلاعات ذخیره شده)
- [x] فروشگاه‌های اخیر (۵ تای آخر)
- [x] Progress Bar سفارش
- [x] بنر فروشگاه
- [x] لینک مستقیم دسته‌بندی
- [x] صفحه عمومی محصول در وبسایت (SSR + Open Graph)
- [x] افزودن محصول با فوروارد کانال
- [x] **فیلد توضیحات سفارش** (`customer_notes`): ورودی اختیاری در checkout

#### پیام‌رسانی و پشتیبانی
- [x] پیام دوطرفه خریدار-فروشنده (Conversations/Message مدل)
- [x] پشتیبانی فروشگاه از منوی اصلی (`support:seller`)
- [x] اینباکس فروشنده (`seller:inbox`) با پیام‌های خوانده/خوانده‌نشده
- [x] پاسخ فروشنده به مشتری (`msg:reply`) + نوتیفیکیشن به مشتری
- [x] پشتیبانی ادمین (`support:open`) — پیام‌ها به ادمین‌ها فوروارد می‌شود

#### امنیت و زیرساخت
- [x] لاگین نقش‌محور (ادمین/فروشنده/مشتری)
- [x] رمز bcrypt (جایگزین SHA-256)
- [x] Rate limit لاگین (۵ تلاش → ۱۵ دقیقه قفل)
- [x] Middleware محافظت مسیرهای `/admin/*` و `/seller/*`
- [x] منوی سه سطحی BotCommandScope
- [x] Docker Compose + Nginx
- [x] Prometheus + Grafana metrics
- [x] **دیتابیس تستی جدا (`foroshgram_test`)** — تمام تست‌ها (`test_flow.py`, `test_handlers_smoke.py`) روی دیتابیس جداگانه اجرا می‌شوند؛ دیتابیس پروداکشن هرگز تحت تأثیر قرار نمی‌گیرد
- [x] صفحات خطای سفارشی (۴۰۴/۵۰۰)
- [x] SEO پایه (robots.txt, sitemap.xml)
- [x] رمزنگاری اطلاعات بانکی (AES-256-GCM)
- [x] Rate limiter توزیع‌شده (Redis-backed)
- [x] Re-check وضعیت فروشگاه بعد از JWT (requireSeller)
- [x] CSRF protection (HMAC double-submit cookie)
- [x] Escape HTML ورودی کاربر (جلوگیری از injection)
- [x] De-duplication رسید پرداخت (SHA-256 hash + UNIQUE)
- [x] اجبار تغییر رمز بعد reset (must_change_password)
- [x] بک‌آپ خودکار PostgreSQL (daily/weekly/monthly + S3 آماده)

### 🔧 رفع باگ‌ها و بهبودهای اعمال شده

#### هسته و پرداخت
- [x] **رفع dead feature اعلان موجود شدن**: `_check_and_notify_restock` از هیچ‌جایی صدا زده نمی‌شد — به `save_edit_field` (admin/products.py) اضافه شد
- [x] **رفع RestockSubscription re-subscribe**: بعد از notify، کاربر نمی‌توانست دوباره subscribe کند — now re-activates با `notified=False`
- [x] **رفع `render_view`**: پارامتر `parse_mode` نداشت → لیست کد تخفیف با TypeError کرش می‌کرد
- [x] **رفع `confirm_card_payment`**: دیسکونت به `create_order_from_cart` پاس داده نمی‌شد
- [x] **رفع `cancel_order_and_release_stock`**: event emit نمی‌کرد — حالا `Event.ORDER_CANCELLED` + `bot` parameter
- [x] **رفع `handle_convert_to_cod`**: `transition_order` بدون `bot` صدا زده می‌شد
- [x] **رفع کد مرده `max_discount_amount`**: فیلد در `DiscountCode` مدل وجود نداشت — حذف شد
- [x] **رفع `MAX(0, x)` → `GREATEST(0, x)`**: PostgreSQL تابع `MAX` scalar روی دو عدد نمی‌شناسد
- [x] **رفع `ORDER_STATUS.CANCELLED`**: با دو L (cancelled) — انگلیسی بریتانیایی
- [x] **رفع `.value` روی OrderStatus**: کلاس str ساده است نه Enum
- [x] **رفع `edit_message_text` روی عکس**: `render_view` fallback به `send_message`
- [x] **رفع انصراف در مرحله پرداخت → بن‌بست**: `order:pay_cancel` و `order:start` به `fallbacks` مکالمه اضافه شد
- [x] **رفع ارور بعد از رد رسید و آپلود مجدد**: `retry_card_receipt` سفارش `CANCELLED`/`rejected` رو revive می‌کنه + رزرو مجدد موجودی
- [x] **رفع ⭐ افزودن به علاقه‌مندی**: `toggle_wishlist` unpack با `*_` برای callback 5 بخشی فیکس شد
- [x] **رفع ❤️ مشاهده علاقه‌مندی‌ها**: `selectinload(WishlistItem.product)` + حلقه داخل session (رفع lazy-load بعد از بسته شدن session)
- [x] **رفع ✅ تایید پرداخت (KeyError)**: `OrderItem.product` relationship به مدل اضافه شد
- [x] **رفع 🎉 تبریک اولین فروش → بن‌بست**: دکمه «🗂 پنل فروشنده» به دو مکان ارسال اضافه شد
- [x] **رفع `cancellation_reason` ترانکیت**: ستون `VARCHAR(100)` (بود ۲۰ — `release_reserved_stock` ۲۲ کاراکتر)
- [x] **رفع `release_reserved_stock`**: حذف پارامتر `session`
- [x] **رفع همه پیام‌های بن‌بست‌ساز**: `_NAV_KB` با ۳ دکمه (ادامه خرید، سبد خرید، شروع) به همه پیام‌های پایانی
- [x] **رفع Deadlock در رزرو چند محصولی**: `cart_items = sorted(cart_items, key=lambda i: i.product_id)` در `create_order_from_cart` — ترتیب ثابت قفل
- [x] **یکی‌سازی `SELECT FOR UPDATE` + `UPDATE`**: `UPDATE ... WHERE ... RETURNING` به‌جای دو query جداگانه برای رزرو اتمیک
- [x] **قفل row-level روی Order در `transition_order`**: `session.get(Order, order_id, with_for_update=True)` قبل از تغییر وضعیت — جلوگیری از race با cron cleanup
- [x] **Idempotency روی `order:confirm`**: `_order_in_progress` flag (in-memory) + `pg_advisory_xact_lock(user_id)` در `create_order_from_cart` (DB-level) — هر دو لایه

#### حذف تگ‌های HTML و بازطراحی پیام‌ها
- [x] **حذف ۳۳۶ تگ HTML** (`<b>`, `</b>`, `<code>`, `</code>`, `<i>`, `</i>`) از ۱۵ فایل هندلر — پیام‌ها با ایموجی + خط جدید ساختاربندی می‌شوند
- [x] **بازنویسی پیام خوش‌آمدگویی** (`_platform_welcome`): بخش خرید و فروش جداگانه، ساختار تمیز
- [x] **بازنویسی پیام فروشگاه** (`_shop_menu_text`): توضیح فروشگاه اختیاری با `parts = [] + join`
- [x] **بازنویسی پیام ثبت‌نام فروشنده** (`seller_welcome_text`): حذف تگ‌ها، لحن طبیعی، ۸ مرحله

#### باگ‌های عملیاتی (آوریل-جولای ۲۰۲۶)
- [x] **رفع FK violation حذف فروشگاه**: `wishlist` قبل از `products` حذف می‌شود (FK constraint)
- [x] **رفع ساخت کد تخفیف**: `shop_id` از `ShopOwner` خوانده می‌شود (نه `last_shop_id` قدیمی)
- [x] **رفع دکمه بازگشت کد تخفیف**: `seller:dashboard` → `seller:panel_back` (هندلر وجود نداشت)
- [x] **رفع بازگشت پشتیبانی به فروشگاه اشتباه**: `seller:panel_back` → `nav:main` (حفظ `current_shop_id`)
- [x] **رفع خطا در `seller_open_conv`**: `NameError: select` — import اضافه شد
- [x] **رفع `sf.select(sf.func.count(...))`**: `from sqlalchemy import select as sf` shadowing → اصلاح به `select(sf.count(...))`
- [x] **رفع `Message` import در `support.py`**: `from database.models import Message` اضافه شد

#### باگ‌های رفع شده در جولای ۲۰۲۶ (نسخه ۲.۵)
- [x] **رفع اعمال کد تخفیف برای خریدار**: پارامتر `user_id` به جای `shop_id` در `_validate_and_apply_discount` (قبلاً ۰ تومان می‌شد)
- [x] **رفع دوبار پرسیدن عکس در افزودن دستی**: عکس اول در بدو ورود `add_photo` ذخیره می‌شود، بعد prompt می‌دهد
- [x] **افزودن گالری چندعکسی برای محصولات دستی**: مدل `ProductImage` + هندلرهای `gallery_list`, `gallery_add_photo`, `gallery_delete_photo` + دکمه در ویرایش محصول
- [x] **رفع پنل فروشنده از پیام تبریک**: pattern `seller:(panel|panel_back)` برای دکمه `seller:panel`
- [x] **حذف کامل روش پرداخت COD**: فقط `card_to_card` باقی ماند، دکمه «تغییر روش پرداخت» حذف شد
- [x] **رفع تکرار هش رسید**: `attach_card_receipt` اول dedup check روی سفارش‌های *دیگر*، بعد `payment_receipt_hash` ست می‌شود (جلوگیری از UniqueViolationError به خاطر autoflush)
- [x] **حذف قفل سطح فروشگاه در `confirm_card_payment`**: وابستگی به `reserved_stock` اتمیک باقی ماند — چند کاربر می‌تونن همزمان بخرن تا جایی که موجودی کافیه
- [x] **فیلد توضیحات سفارش (`customer_notes`)**: ستون `VARCHAR(500)` در `Order`، state `ASK_NOTES` در checkout، نمایش در خلاصه و نوتیف فروشنده
- [x] **بهبود پیام اعلان فروشنده**: نام، تلفن، آدرس، توضیحات خریدار، جزئیات مبلغ (جمع کالاها/هزینه ارسال/مبلغ قابل پرداخت/شماره تراکنش)
- [x] **فیکس `\n` لیترال در پیام‌های اشتراک**: تمام `\\n` به newline واقعی تبدیل شدند
- [x] **پیش‌فرض کارت ادمین برای اشتراک**: `ADMIN_CARD_NUMBER` و `ADMIN_CARD_HOLDER` در `config.py` با default مقداردهی
- [x] **جستجوی همگانی محصولات** (`/searchall`): سرچ در تمام فروشگاه‌های فعال
- [x] **جستجوی فروشگاه‌ها** (`/findshop`): پیدا کردن فروشگاه با نام/یوزرنیم

#### تست‌ها
- [x] **تست جامع اسمیک هندلرها** (`tests/test_handlers_smoke.py`): ۳۰ تست که همه callback/message handlerهای ثبت‌شده را صدا می‌زند و مطمئن می‌شوند `Exception` مدیریت‌نشده نمی‌دهند. نتیجه: ✅ ۳۰/۳۰
- [x] **پاک‌سازی وابسته به ترتیب** در `test_flow.py`: `User` → `Order` → `OrderItem` → `Shop` → `Category` → `Product` (children before parents)
- [x] **تست‌های جداگانه روی `foroshgram_test`**: هر دو فایل تست قبل از هر import، `DATABASE_URL` را از `TEST_DATABASE_URL` اورراید می‌کنند؛ اگر متغیر ست نشده باشد با اخطار fallback می‌کنند

### 🔄 در حال انجام

- [x] زمان‌بندی کرون برای `scripts/backup.sh` — فعال در container
- [ ] DNS + SSL نهایی
- [ ] صفحه عمومی فروشگاه `/shop/[id]`
- [x] تست‌های خودکار مسیرهای پولی — `tests/test_flow.py` اضافه شد (۷ سناریو)
- [x] تست اسمیک هندلرها — `tests/test_handlers_smoke.py` (۳۰/۳۰ ✅)
- [ ] رفع تخصیص فروشگاه دوم (`@dasttiarfrooshbot`)
- [ ] تکمیل redemption Claim Code

### 📅 برنامه آینده

- [ ] گزارش‌گیری پیشرفته (اکسل/CSV)
- [ ] اعلان push برای سفارش جدید (فعلاً فقط در چت خصوصی)
- [ ] مدیریت چند فروشگاه برای یک فروشنده
- [ ] سیستم امتیاز و بازخورد مشتری
- [ ] ثبت‌نام فروشنده از طریق کد دعوت (Claim Code — VIP بدون تایید دستی)
- [ ] پنل مدیریت محتوای سایت (`site_content` در دیتابیس)
- [ ] تست‌های خودکار (Unit + Integration)
- [ ] CI/CD Pipeline
- [ ] لاگین با OTP تلگرام
- [ ] سبد خرید چند فروشگاهی
- [ ] اپلیکیشن موبایل (React Native)

---

## ۱۶. تحلیل و نمره‌دهی (Audit Report)

> تاریخ: ۱۴ ژوئیه ۲۰۲۶ — ارزیابی کلی پروژه Foroshgram

### نمره کلی: ۷ از ۱۰

به‌عنوان یک MVP تک‌نفره برای پلتفرم چندمستأجری.

| بخش | نمره | توضیح |
|-----|------|-------|
| معماری و جداسازی کد | ۸.۵ | لایه‌بندی handlers/services/utils تمیزه، EventBus واقعاً درست پیاده شده |
| منطق تراکنشی (رزرو موجودی) | ۷ | ایده درسته (UPDATE شرطی) ولی چند نقطه ضعف زیر داره |
| امنیت | ۶ | پایه خوبه (bcrypt، JWT edge-safe، rate limit لاگین) ولی چند سوراخ واقعی هست |
| آماده‌بودن برای Production | ۵ | همینجا بزرگ‌ترین گپ پروژه‌ست |
| کامل بودن فیچرها | ۸.۵ | خیلی جلوتر از یه بات فروشگاهی معمولیه (wishlist, restock, abandoned cart, reorder) |
| مستندسازی (خود همین فایل) | ۹ | نادره که یه پروژه solo این‌قدر مستند بشه |

### نقاط قوت واقعی

- `create_order_from_cart` به‌عنوان تنها مسیر ساخت سفارش — این تصمیم معماری درستیه. خیلی از پروژه‌های مشابه چون این مسیر رو یکی نمی‌کنن، دچار race condition و double-order می‌شن.
- رزرو اتمیک با `UPDATE ... WHERE stock - reserved_stock >= qty` — درسته، این دقیقاً همون الگویی‌ه که باید استفاده بشه به‌جای lock در سطح اپلیکیشن.
- **Deadlock prevention**: `cart_items.sort(key=lambda i: i.product_id)` قبل از حلقه رزرو — ترتیب قفل ثابت.
- **Single round-trip reserve**: `UPDATE ... RETURNING` به‌جای دو query جداگانه.
- **Race-safe state transition**: `transition_order` با `with_for_update=True` روی ردیف Order قفل می‌گیره قبل از تغییر وضعیت.
- **DB-level idempotency**: `pg_advisory_xact_lock(user_id)` در `create_order_from_cart` — تضمین می‌کنه حتی بعد از ری‌استارت یا با دو نمونه بات، یه کاربر نتونه دو تا سفارش از یه سبد بزنه.
- لیست باگ‌های رفع‌شده (GREATEST به‌جای MAX، Enum بودن غلط OrderStatus، lazy-load بعد از بسته شدن session) نشون می‌ده داری واقعاً edge caseها رو شکار می‌کنی، نه فقط happy-path رو تست می‌کنی.

### ریسک‌های واقعی — به ترتیب اولویت (بروزرسانی شده ۱۴۰۵-۰۵-۲۱)

1. **total_price نوعش Float** — تومان بدون اعشار، ولی محاسبات تخفیف (total × value / 100) می‌تونن imprecision تولید کنن → تغییر به Integer یا Numeric
2. **دوتایی status و payment_status** — دو فیلد state معنایی هم‌پوشان. ریشه خیلی از باگ‌های state-machine همین دو-منبع-حقیقت‌بودن
3. **Persistence مکالمه‌ها** — اگه PTB با PicklePersistence کانفیگ نشده باشه، هر بار دیپلوی state کاربران پاک می‌شه
4. **DNS/SSL نهایی نشده** → ⬜ باقی‌مانده — خارج از scope کد
5. **تک‌نقطه‌ای بودن زیرساخت** — Postgres + Bot + Website همه روی یک VPS. نیاز به staging + CI/CD
6. **Deploy بدون staging** — الگوی فعلی: «دیپلوی کن، اگه خراب شد فیکس کن» → نیاز به CI/CD pipeline
7. **مانیتورینگ بدون Alert** — Prometheus/Grafana داری ولی Alertmanager نیست → باید اضافه بشه

> **نکته:** تمام ضعف‌های قبلی در بخش «منطق تراکنشی» (۱ تا ۷) و «امنیت» (۱ تا ۸) در جولای ۲۰۲۶ **حل شده‌اند**. برای جزئیات فیکس‌ها به بخش ۸.۷ مراجعه کنید.

---

### ایده: verification نیمه‌خودکار رسید پرداخت

> بزرگ‌ترین bottleneck معماری: تایید دستی رسید توسط هر فروشنده یعنی این پلتفرم هیچ‌وقت واقعاً scale نمی‌شه.

لایه verification نیمه‌خودکار با vision model:
- وقتی مشتری عکس رسید می‌فرسته، قبل از رسیدن به فروشنده، عکس به مدل vision (مثلاً AvalAI) داده بشه
- استخراج مبلغ و آخرین ۴ رقم کارت مقصد + مطابقت با مبلغ سفارش + شماره کارت فروشنده
- اگه match → تایید خودکار یا badge «✅ مطابقت خودکار»
- اگه mismatch → فقط صف تایید دستی
- هم fraud کمتر (رسید تکراری/جعلی با هش عکس) هم فروشنده از گیر ۲۴ ساعته آزاد

---

### سه آیتم مهم‌تر از هر فیچر جدید

تست مسیرهای پولی، DNS+SSL، و بک‌آپ — این سه‌تا دقیقاً چیزیه که بین «پروژه شخصی روی VPS» و «پلتفرمی که می‌تونی روش فروشنده واقعی سوار کنی» فرق می‌ذاره.

---

## ۱۷. پیوست: ساختار دایرکتوری

```
Telegramorderbot/
├── PROJECT.md                        # این فایل
├── docker-compose.yml
├── nginx.conf / nginx-no-ssl.conf
├── deploy-to-vps.sh / deploy-via-ssh.py
├── fix-deployment.py / fix-nginx.py
├── init-scripts/
│   └── ...
├── telegram_order_bot/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env
│   ├── main.py                       # نقطه ورود + build handlers
│   ├── config.py                     # تنظیمات محیطی
│   ├── database/
│   │   ├── db.py                     # async_session + engine
│   │   ├── models.py                 # همه مدل‌ها (16 جدول)
│   │   └── migrate_*.py              # مهاجرت‌ها
│   ├── handlers/
│   │   ├── start.py                  # /start هوشمند + لینک مستقیم
│   │   ├── menu.py                   # دسته‌بندی + محصولات + گالری
│   │   ├── cart.py                   # سبد خرید
│   │   ├── order.py                  # ثبت سفارش + تاریخچه + پرداخت + تخفیف
│   │   ├── conversations.py          # پیام خریدار-فروشنده (اینباکس)
│   │   ├── bot_commands.py           # BotCommandScope سه سطحی
│   │   ├── seller_registration.py    # ویزارد ۸ مرحله‌ای
│   │   ├── seller_panel.py           # پنل فروشنده + تنظیمات
│   │   ├── discount.py               # کد تخفیف
│   │   ├── wishlist.py               # علاقه‌مندی‌ها
│   │   ├── search.py                 # جستجوی تعاملی
│   │   ├── forward_products.py       # افزودن با فوروارد
│   │   ├── support.py                # پشتیبانی (ConversationHandler)
│   │   ├── help.py                   # /help نقش‌محور
│   │   ├── common.py                 # توابع مشترک
│   │   ├── admin_approval.py         # تایید/رد فروشنده از نوتیفیکیشن درون‌خطی
│   │   └── admin/
│   │       ├── panel.py              # پنل ادمین
│   │       ├── products.py           # مدیریت محصولات
│   │       ├── categories.py         # مدیریت دسته‌بندی
│   │       ├── orders.py             # مدیریت سفارش‌ها
│   │       ├── shops.py              # مدیریت فروشگاه‌ها
│   │       └── broadcast.py          # پیام همگانی
│   ├── services/
│   │   ├── payment.py                # رزرو/آزادسازی/نهایی‌سازی
│   │   ├── order_service.py          # create_order_from_cart + transition_order
│   │   ├── events.py                 # EventBus + Event enum
│   │   ├── event_listeners.py        # Listenerهای رویداد
│   │   ├── notification_service.py   # NotificationService
│   │   ├── monitoring.py             # Metrics + Sentry + Prometheus
│   │   ├── restock.py                # Restock notification
│   │   └── abandoned_cart.py         # یادآوری سبد رها شده
│   ├── utils/
│   │   ├── helpers.py                # format_price, to_jalali, is_super_admin
│   │   ├── tg_helpers.py             # render_view, get_current_shop_id, escape_html
│   │   ├── crypto.py                 # AES-256-GCM رمزنگاری اطلاعات بانکی
│   │   ├── order_validator.py        # can_transition + ALLOWED_TRANSITIONS
│   │   ├── payment_config.py         # تنظیمات پرداخت per-shop
│   │   └── tenant.py                 # چندمستأجری
│   ├── tests/
│   │   ├── test_flow.py              # تست‌های جریان کامل (۷ سناریو)
│   │   └── test_handlers_smoke.py    # تست جامع اسمیک هندلرها (۳۰/۳۰)
└── telegram_order_website/
    ├── Dockerfile
    ├── next.config.ts
    ├── package.json
    ├── .env.production
    └── src/
        ├── middleware.ts              # محافظت مسیرها
        ├── app/
        │   ├── layout.tsx
        │   ├── page.tsx              # لندینگ
        │   ├── login/page.tsx
        │   ├── product/[id]/page.tsx # صفحه عمومی محصول
        │   ├── 33482531.txt          # فایل اینماد
        │   ├── not-found.tsx / error.tsx
        │   ├── admin/                # پنل ادمین
        │   │   ├── layout.tsx
        │   │   ├── page.tsx          # داشبورد
        │   │   ├── shops/page.tsx
        │   │   ├── products/page.tsx
        │   │   ├── categories/page.tsx
        │   │   ├── orders/page.tsx + [id]/page.tsx
        │   │   ├── users/page.tsx
        │   │   └── claim-codes/page.tsx
        │   ├── seller/               # پنل فروشنده
        │   │   ├── layout.tsx
        │   │   ├── page.tsx          # داشبورد
        │   │   ├── products/page.tsx
        │   │   └── orders/page.tsx + [id]/page.tsx
        │   └── api/                  # API Routes
        │       ├── auth/login|logout|me/route.ts
        │       ├── admin/create-claim-code|toggle-shop|toggle-user-block/route.ts
        │       ├── admin/orders/[id]/status/route.ts
        │       ├── seller/shop-info|toggle-product/route.ts
        │       ├── seller/orders/[id]/status/route.ts
        │       └── product-image/[id]/route.ts       # عکس محصول
        ├── components/
        │   ├── layout/ (Header, Footer, ProtectedLayout)
        │   └── shared/ (Card, ...)
        ├── lib/
        │   ├── auth.ts               # JWT + سشن + requireSeller/requireAdmin
        │   ├── crypto.ts             # AES-256-GCM (Node.js native)
        │   ├── csrf.ts               # HMAC-SHA256 double-submit
        │   ├── db.ts                 # pg Pool + query helpers
        │   ├── rate-limiter.ts       # Redis-backed + in-memory fallback
        │   └── utils.ts
        └── types/
            └── index.ts
├── scripts/
│   ├── backup.sh                 # بک‌آپ خودکار PostgreSQL
│   ├── restore.sh                # بازیابی بک‌آپ
│   ├── setup-rclone.sh           # راه‌اندازی rclone
│   ├── Dockerfile.backup         # ایمیج کانتینر بک‌آپ
│   ├── db-backup.sh              # نسخه قدیمی بک‌آپ
│   ├── migrate_passwords.py      # SHA-256 → bcrypt مهاجرت
│   └── seed_admin.py             # افزودن ادمین اولیه
├── deploy-to-vps.sh / deploy-via-ssh.py
├── fix-deployment.py / fix-nginx.py
├── deploy_bot_sftp.py            # (مختل) دیپلوی SFTP
├── deploy_bot_v2.py / deploy_bot_v3.py
├── deploy_chan.py / deploy_paramiko.py
├── upload_*.py                   # آپلود chunk شده فایل‌ها
└── .env                          # متغیرهای محیطی (رد شده در git)
```