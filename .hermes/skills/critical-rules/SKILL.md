---
name: critical-rules
description: "قوانین حیاتی که هیچوقت نباید فراموش شوند — اطلاعات کاربران خط قرمز است + مرجع عملیات استقرار"
---

# قوانین حیاتی — CRITICAL RULES

## خط قرمز شماره ۱: اطلاعات کاربران

**هیچ‌وقت تست مخرب روی دیتابیس پروداکشن اجرا نکن.**

- دیتابیس تست: `foroshgram_test` (Postgres VPS)
- تست‌ها (`test_handlers_smoke.py`, `test_flow.py`) خودکار از `TEST_DATABASE_URL` استفاده می‌کنند
- قبل از هر `DELETE`/`DROP`/`UPDATE` گسترده: **چک کن که روی test DB هستی**
- اگر `TEST_DATABASE_URL` ست نبود → abort کن

## خط قرمز شماره ۲: Credentials

- هرگز توکن‌ها و رمزها رو فاش نکن
- مقادیر ماسک‌شده رو حدس نزن
- توکن ربات: در `.env` پروژه و در سرور `/opt/foroshgram/telegram_order_bot/.env`
- ADMIN_IDS: `8497713691`

---

# مرجع عملیات استقرار (Operational Reference)

## سرور VPS
- **آدرس:** `185.204.168.57:22`
- **کاربر:** `ubuntu`
- **کلید SSH:** `C:\s\ar-me-privatekey.pem`
- **پروکسی (برای کلون/پول):** SOCKS5 `127.0.0.1:10808`
- **دایرکتوری پروژه:** `/opt/foroshgram/`

## کانتینرها (Docker Compose v1 - دستور `docker-compose`)
| سرویس | نام کانتینر | وضعیت | پورت |
|-------|-------------|--------|------|
| PostgreSQL 16 | `foroshgram_postgres` | healthy | 5432 |
| ربات تلگرام | `foroshgram_bot` | running | — |
| وبسایت Next.js | `foroshgram_website` | running | 3000 |

## ربات‌ها
- **ربات اصلی:** `@Foroshgrambot` (ID: 8871159970)

## متغیرهای محیطی کلیدی
**ربات (`telegram_order_bot/.env`):**
```env
BOT_TOKEN=8871159970:...
ADMIN_IDS=8497713691
DATABASE_URL=postgresql+asyncpg://...
NOTIFICATION_CHANNEL_ID=-100...
PROXY_URL=http://user:pass@host:port
```

**وبسایت (`telegram_order_website/.env.production`):**
```env
DATABASE_URL=postgresql://...
JWT_SECRET=...
ADMIN_IDS=8497713691
```

## دستورات ربات حیاتی (BotCommandScope سه‌سطحی)
```python
# در handlers/bot_commands.py
set_default_menu(bot)        # BotCommandScopeDefault - همه کاربران
set_seller_menu(bot, chat_id)  # BotCommandScopeChat - فروشندگان
set_admin_menu(bot, chat_id)   # BotCommandScopeChat - ادمین‌ها
delete_seller_menu(bot, chat_id)  # حذف دستورات فروشنده
```
- `set_default_menu` در `_post_init` استارتاپ
- `set_admin_menu` برای هر `ADMIN_IDS` در استارتاپ
- `set_seller_menu` بعد از تایید نهایی فروشنده
- `delete_seller_menu` بعد از غیرفعال/حذف فروشگاه

## آدرس‌های مهم
- **سایت:** `https://telegramorder.ir` (یا IP سرور)
- **صفحه عمومی محصول:** `https://telegramorder.ir/product/[id]`
- **لینک مستقیم محصول در ربات:** `https://t.me/Foroshgrambot?start=product_[id]`
- **فایل اینماد:** `public/33482531.txt` در ریشه وبسایت

## دستورات دپلوی
```bash
# روی سرور
cd /opt/foroshgram
docker-compose build && docker-compose up -d

# برای reload env vars (باید rm کنیم)
docker-compose rm -f && docker-compose up -d
```

## نکات حیاتی عملیات
- **Docker Compose v1** روی سرور نصب شده (دستور `docker-compose` نه `docker compose`)
- **هیچ `__pycache__` یا `.next` در سرور نیست** — همه در container build میشه
- **Nginx Reverse Proxy** روی سرور کانفیگ شده (`nginx.conf` با SSL، `nginx-no-ssl.conf` برای توسعه)
- **اسکریپت‌های دپلوی:** `deploy-to-vps.sh`، `deploy-via-ssh.py`، `fix-deployment.py`، `fix-nginx.py`

## عیب‌یابی سریع
| مشکل | راه‌حل |
|-------|--------|
| Env vars لود نشد | `docker-compose rm -f bot website && docker-compose up -d` |
| ربات ریستارت می‌خوره | لاگ: `docker-compose logs -f bot` — معمولاً proxy یا token |
| Migration دیتابیس | اسکریپت‌ها در `init-scripts/` — در container init اجرا میشن |
| Nginx 502 | `fix-nginx.py` روی سرور اجرا کن |
| SSL تموم شده | `certbot renew` و reload nginx |

## استقرار فایل‌ها (Local → VPS)
روش استاندارد: `docker cp` فایل‌ها به `/tmp/` → `docker cp` به کانتینر → restart
```python
# نمونه: deploy_all2.py استفاده می‌کنه
# 1. base64 encode فایل
# 2. python -c "import base64; f=open('/tmp/deploy_x.py','wb'); f.write(base64.b64decode('...'))"
# 3. docker cp /tmp/deploy_x.py foroshgram_bot:/app/handlers/x.py
# 4. docker exec python -m py_compile ... && docker restart foroshgram_bot
```
