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

## کانتینرها (⚠️ docker-compose v1 خراب است — فقط با `docker` خام کار کن)
| سرویس | نام کانتینر | وضعیت | پورت |
|-------|-------------|--------|------|
| PostgreSQL 16 | `f746043009ed_foroshgram_postgres` (پیشوند هش!) | healthy | 5432 |
| ربات تلگرام | `e3ae8fee6ab5_foroshgram_bot` (پیشوند هش!) | running | — |
| وبسایت Next.js | `foroshgram_website` | running | 3000 |
| Grafana | `foroshgram_grafana` | running | 3001 |
| Prometheus | `foroshgram_prometheus` | running | 9091 |

⚠️ نام دقیق کانتینرها را همیشه با `docker ps` بگیر — پستگرس و ربات پیشوند هش دارند.
⚠️ **دستور `docker-compose` نسخه 1.29 روی سرور هست ولی خراب است — استفاده نکن.**
⚠️ **شبکه داکر:** همه روی `foroshgram_default` — پستگرس با hostname `postgres` در دسترس است.

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

## دستورات دپلوی (واقعیت فعلی — docker خام، نه compose)
```bash
# روی سرور — بیلد سایت (همیشه --no-cache؛ با cache تغییرات گرفته نمی‌شود)
cd /opt/foroshgram/telegram_order_website
export JWT_SECRET=$(grep '^JWT_SECRET=' .env.production | cut -d= -f2-)
tmux kill-session -t build 2>/dev/null; tmux new-session -d -s build \
  "docker build --no-cache --build-arg JWT_SECRET=\"\$JWT_SECRET\" -t foroshgram_website:latest . > /tmp/website_build.log 2>&1"
tail -f /tmp/website_build.log | grep 'Successfully built'

# اجرای کانتینر — با --env-file (نه -e DATABASE_URL!)
docker rm -f foroshgram_website 2>/dev/null || true
docker run -d --name foroshgram_website --restart unless-stopped \
  --network foroshgram_default -p 3000:3000 \
  --env-file /opt/foroshgram/telegram_order_website/.env.production \
  -v /opt/foroshgram/data/product_images:/app/data/product_images \
  foroshgram_website:latest

# ریستارت ربات
docker restart <bot_name>   # نام را با docker ps بگیر
```

## نکات حیاتی عملیات
- **⚠️ JWT_SECRET الزامی:** وب‌سایت Next.js بدون متغیر محیطی `JWT_SECRET` (حداقل ۳۲ کاراکتر تصادفی) استارت نمی‌شود. قبل از هر بیلد/دیپلوی حتماً در `.env.production` یا Docker `--build-arg` تنظیم کن.
- **Docker Compose v1 روی سرور خراب است** — فقط از `docker` خام استفاده کن.
- **هیچ `__pycache__` یا `.next` در سرور نیست** — همه در container build می‌شود.
- **Nginx Reverse Proxy** روی سرور کانفیگ شده (`nginx.conf` با SSL، `nginx-no-ssl.conf` برای توسعه).
- **⚠️ کوکی لاگین در Route Handlers:** در Next.js 16 باید `NextResponse.cookies.set()` استفاده شود. تابع `setSessionCookie(res, payload)` در `src/lib/auth.ts` این کار را انجام می‌دهد — همیشه `await` شود.
- **⚠️ تغییر رمز:** ادمین/فروشنده در `/admin/settings` یا `/seller/settings` رمز را تغییر می‌دهند. پیام ربات «رمز موقت» به این آدرس‌ها ارجاع می‌دهد.
- **اسکریپت‌های دپلوی:** `deploy-to-vps.sh`، `deploy-via-ssh.py`، `fix-deployment.py`، `fix-nginx.py` (برخی قدیمی هستند — با دقت استفاده کن).

## عیب‌یابی سریع
| مشکل | راه‌حل |
|-------|--------|
| Env vars لود نشد | کانتینر را با `--env-file` درست بساز (نه `-e DATABASE_URL`) |
| ربات ریستارت می‌خوره | لاگ: `docker logs <bot> --tail 100` — معمولاً proxy/token یا AttributeError در handler |
| Migration دیتابیس | اسکریپت‌ها در `init-scripts/` — در container init اجرا می‌شن |
| Nginx 502 | `fix-nginx.py` روی سرور اجرا کن |
| SSL تموم شده | `certbot renew` و reload nginx |
| دیسک پر در بیلد | `sudo docker system prune -af --volumes` (active ها حذف نمی‌شن) |
| لاگین 500 | چک regex `^\d+$` قبل parseInt؛ کوکی با `await setSessionCookie` ست شود |

## استقرار فایل‌ها (Local → VPS) — روش پیشنهادی
**سرناخ پروژه لوکال کل را sync و rebuild کن** (نه scp پراکنده):

```bash
# ۱) کل پروژه (بدون node_modules/.next/.git) را tar می‌کنیم
cd T:/dars/projects/telegram/Telegramorderbot
tar --exclude='node_modules' --exclude='.next' --exclude='.git' -czf /tmp/foroshgram_sync.tar.gz .

# ۲) scp به سرور
scp -i C:/s/ar-me-privatekey.pem /tmp/foroshgram_sync.tar.gz ubuntu@185.204.168.57:/tmp/

# ۳) روی سرور extract و rebuild
ssh -i C:/s/ar-me-privatekey.pem ubuntu@185.204.168.57 "
  cd /opt/foroshgram
  tar -xzf /tmp/foroshgram_sync.tar.gz --strip-components=1
  # ... سپس بیلد سایت با --no-cache و run
"
```

برای ربات (source mount شده در کانتینر):
```bash
scp -i C:/s/ar-me-privatekey.pem \
  "T:/dars/projects/telegram/Telegramorderbot/telegram_order_bot/handlers/seller_panel.py" \
  ubuntu@185.204.168.57:/opt/foroshgram/telegram_order_bot/handlers/
docker restart <bot_name>
```
