-- Foroshgram — Initial Database Schema
-- This runs once on first Postgres startup

-- ─── Shops (فروشگاه‌ها) ───
CREATE TABLE IF NOT EXISTS shops (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    description VARCHAR(500),
    phone VARCHAR(30),
    rejection_reason VARCHAR(500),
    username VARCHAR(100) UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT NOW(),
    zarinpal_merchant_id VARCHAR(36),
    card_number VARCHAR(16),
    card_holder_name VARCHAR(100),
    sheba_number VARCHAR(26)
);

-- ─── Shop Owners (صاحبان فروشگاه) ───
CREATE TABLE IF NOT EXISTS shop_owners (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    shop_id INTEGER REFERENCES shops(id) ON DELETE CASCADE,
    first_name VARCHAR(100),
    username VARCHAR(100),
    password_hash VARCHAR(128),
    password_salt VARCHAR(32),
    must_change_password BOOLEAN DEFAULT FALSE,
    registered_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_shop_owners_user_id ON shop_owners(user_id);
CREATE INDEX IF NOT EXISTS idx_shop_owners_shop_id ON shop_owners(shop_id);

-- ─── Admins (ادمین‌های کل) ───
CREATE TABLE IF NOT EXISTS admins (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    password_hash VARCHAR(128) NOT NULL,
    must_change_password BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_admins_user_id ON admins(user_id);

-- ─── Claim Codes (کد دعوت) ───
CREATE TABLE IF NOT EXISTS claim_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    shop_id INTEGER REFERENCES shops(id),
    created_by BIGINT NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    used_by BIGINT,
    used_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_claim_codes_code ON claim_codes(code);

-- ─── Categories (دسته‌بندی) ───
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    shop_id INTEGER REFERENCES shops(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_categories_shop_id ON categories(shop_id);

-- ─── Products (محصولات) ───
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    shop_id INTEGER REFERENCES shops(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    price DOUBLE PRECISION NOT NULL,
    stock INTEGER DEFAULT 0,
    reserved_stock INTEGER DEFAULT 0,
    image_file_id VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_products_shop_id ON products(shop_id);
CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);
-- Composite index for category queries within a shop
CREATE INDEX IF NOT EXISTS idx_products_shop_category ON products(shop_id, category_id);

-- ─── Users (کاربران / مشتریان) ───
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    current_shop_id INTEGER REFERENCES shops(id),
    last_shop_id INTEGER REFERENCES shops(id),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    username VARCHAR(100),
    phone VARCHAR(30),
    address VARCHAR(500),
    is_blocked BOOLEAN DEFAULT FALSE,
    registered_at TIMESTAMP DEFAULT NOW()
);

-- ─── Cart Items (سبد خرید) ───
CREATE TABLE IF NOT EXISTS cart (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    shop_id INTEGER REFERENCES shops(id),
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    quantity INTEGER DEFAULT 1,
    added_at TIMESTAMP DEFAULT NOW()
);

-- ─── Orders (سفارش‌ها) ───
CREATE TYPE order_status AS ENUM (
    'pending_payment', 'pending', 'paid', 'confirmed',
    'shipped', 'delivered', 'cancelled', 'refunded'
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    shop_id INTEGER REFERENCES shops(id),
    tracking_code VARCHAR(20) UNIQUE NOT NULL,
    user_id BIGINT REFERENCES users(user_id),
    total_price DOUBLE PRECISION DEFAULT 0,
    status order_status DEFAULT 'pending',
    payment_method VARCHAR(20),
    payment_ref VARCHAR(100),
    payment_status VARCHAR(20),
    payment_receipt_file_id VARCHAR(255),
    payment_receipt_at TIMESTAMP,
    receiver_name VARCHAR(150),
    shipping_address VARCHAR(500) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    status_history TEXT DEFAULT '[]',
    cancellation_reason VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_orders_shop_id ON orders(shop_id);
CREATE INDEX IF NOT EXISTS idx_orders_tracking_code ON orders(tracking_code);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
-- Composite indexes for multi-tenant query performance
CREATE INDEX IF NOT EXISTS idx_orders_shop_status ON orders(shop_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_shop_created ON orders(shop_id, created_at DESC);

-- ─── Order Items (اقلام سفارش) ───
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    product_name VARCHAR(150) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);

-- ─── Site Content (محتوای داینامیک سایت) ───
CREATE TABLE IF NOT EXISTS site_content (
    id SERIAL PRIMARY KEY,
    section VARCHAR(100) NOT NULL,
    key VARCHAR(100) NOT NULL,
    value TEXT NOT NULL,
    locale VARCHAR(10) DEFAULT 'fa',
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(section, key, locale)
);

-- Insert default content
INSERT INTO site_content (section, key, value) VALUES
    ('hero', 'title', 'فروشگاه تلگرامیت رو در ۳ دقیقه راه بنداز'),
    ('hero', 'subtitle', 'با فروشگرام، هر کسب‌وکاری می‌تونه فروشگاه اختصاصی خودش رو تو تلگرام داشته باشه — سفارش‌ها رو خودکار مدیریت کن و پول رو آنلاین و امن بگیر.'),
    ('hero', 'cta_primary', 'شروع کن'),
    ('hero', 'cta_secondary', 'جستجوی محصولات'),
    ('how_it_works', 'step1_title', 'کد دعوت بگیر'),
    ('how_it_works', 'step1_desc', 'از ادمین فروشگرام یه کد دعوت بگیر'),
    ('how_it_works', 'step2_title', 'فروشگاهت رو ثبت کن'),
    ('how_it_works', 'step2_desc', 'توی ربات فروشگرام، فروشگاه اختصاصی خودتو راه بنداز'),
    ('how_it_works', 'step3_title', 'لینک بده و بفروش'),
    ('how_it_works', 'step3_desc', 'محصولاتتو اضافه کن و لینک فروشگاهتو به مشتری‌ها بده'),
    ('features', 'items', '[
        {"title":"ربات اختصاصی","desc":"هر فروشنده یه ربات اختصاصی داره","icon":"bot"},
        {"title":"درگاه پرداخت","desc":"پرداخت آنلاین با زرین‌پال","icon":"payment"},
        {"title":"داشبورد هوشمند","desc":"آمار فروش، سفارش‌ها و درآمد","icon":"dashboard"},
        {"title":"صفحه اختصاصی","desc":"هر فروشگاه لینک اختصاصی داره","icon":"link"},
        {"title":"تاریخچه وضعیت","desc":"مشتری دقیق می‌دونه سفارشش کجاست","icon":"history"},
        {"title":"امنیت کامل","desc":"اطلاعات مشتری‌ها محافظت میشه","icon":"security"}
    ]'::jsonb)
ON CONFLICT (section, key, locale) DO NOTHING;

-- ─── Page Sections (صفحات داینامیک) ───
CREATE TABLE IF NOT EXISTS page_sections (
    id SERIAL PRIMARY KEY,
    page VARCHAR(100) NOT NULL DEFAULT 'home',
    sort_order INT DEFAULT 0,
    title VARCHAR(200),
    content TEXT,
    is_visible BOOLEAN DEFAULT true,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_page_sections_page ON page_sections(page, is_visible);

-- ─── Messaging (پیام خریدار-فروشنده) ───
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    buyer_id BIGINT NOT NULL,
    shop_id INTEGER REFERENCES shops(id),
    order_id INTEGER REFERENCES orders(id),
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_conv_buyer ON conversations(buyer_id);
CREATE INDEX IF NOT EXISTS idx_conv_shop ON conversations(shop_id);

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    sender_role VARCHAR(10) NOT NULL,  -- buyer | seller
    content TEXT NOT NULL,
    has_attachment BOOLEAN DEFAULT FALSE,
    attachment_file_id VARCHAR(255),
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);

