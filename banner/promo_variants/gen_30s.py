"""Generate promo-30s.html (compact 30-second version) + 10 color variants in promo_variants/"""

import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(BASE_DIR, "promo_variants", "promo-ig-01.html")

with open(SOURCE, "r", encoding="utf-8") as f:
    html = f.read()

# ─── Compress scenes into 30-second pacing ─────────────────────

# Make all sleeps faster — divide by ~3
def compress_sleep(match):
    ms = int(match.group(1))
    new_ms = max(200, int(ms / 2.6))
    return match.group(0).replace(match.group(1), str(new_ms))

html = re.sub(r"await sleep\((\d+)\)", compress_sleep, html)

# Remove typing indicators (they waste time) — replace with direct messages
html = html.replace(
    "await typing(.1,1.2);await checkPause();if(signal.aborted)return;\n    ",
    ""
)
html = re.sub(
    r"await typing\([^)]+\);await checkPause\(\);if\(signal\.aborted\)return;(?:\n\s*)?",
    "",
    html
)

# Compress scene timings — reduce animation delays
def compress_delay(match):
    d = float(match.group(1))
    new_d = round(max(0.0, d * 0.5), 2)
    return match.group(0).replace(match.group(1), str(new_d))

html = re.sub(r"animation-delay:([\d.]+)s", compress_delay, html)

# Remove intro splash fadeOut animation delay (shorten to 1.5s)
html = html.replace("animation:fadeOut 1s forwards; animation-delay:3s;", "animation:fadeOut .8s forwards; animation-delay:1.5s;")

# Make intro logo entrance faster
html = html.replace("logoEntrance .8s", "logoEntrance .4s")
html = html.replace("titleSlide .6s", "titleSlide .3s")
html = html.replace("glowPulse 2s", "glowPulse 1.2s")

# Shorten banner display time
html = html.replace("bannerOut .4s .9s", "bannerOut .3s .4s")
html = html.replace("bannerIn .5s", "bannerIn .3s")

# Remove extraneous button rows in scenes to save time
# In sceneSolution: remove "بیشتر بدونم" button
html = html.replace(
    "btns([{text:'🚀 شروع کنیم!',green:true,primary:true},{text:'بیشتر بدونم',ghost:true}],.3);await checkPause();if(signal.aborted)return;await sleep(1800);\n    user('🚀 شروع کنیم!',.2);await sleep(1000);",
    "btns([{text:'🚀 شروع کنیم!',green:true,primary:true}],.3);await checkPause();if(signal.aborted)return;await sleep(500);"
)

# In sceneRegistration: condense to 2 steps instead of 3
# Remove the phone number step 
html = html.replace(
    """bot('👍 عالیه!<br><br>📋 <b>شماره تماس فروشگاهت:</b>',0);await checkPause();if(signal.aborted)return;await sleep(600);
    user('۰۹۱۲۱۲۳۴۵۶۷',.2);await checkPause();if(signal.aborted)return;await sleep(400);""",
    ""
)
# Make second ask go directly to card
html = html.replace(
    "await sleep(700);\n    bot('✅ و آخر مرحله — شماره کارتی که مشتریا<br>باید پول رو به اون واریز کنن:',0);await checkPause();if(signal.aborted)return;await sleep(600);",
    "await sleep(200);\n    bot('✅ و آخر مرحله — شماره کارتی که مشتریا<br>باید پول رو به اون واریز کنن:',0);await checkPause();if(signal.aborted)return;await sleep(300);"
)

# In sceneRegistration: remove buttons at end (just show success)
html = html.replace(
    """btns([{text:'➕ افزودن محصول',green:true},{text:'📊 پنل مدیریت',ghost:true}],.3);await checkPause();if(signal.aborted)return;await sleep(1800);
    user('📊 پنل مدیریت',.2);await sleep(800);""",
    """await sleep(300);"""
)

# In sceneSellerPanel: remove navigation sub-menus, just show dashboard
# Replace the whole function to just show the dashboard card
old_panel = """async function sceneSellerPanel(signal){
    clearMsgs();setHeader('📊 پنل مدیریت فروشگاه','م','purple','مدیر فروشگاه');updateUI(3);
    bot(`📊 <b>داشبورد فروشگاه</b><br><span class=\"badge active\">فعال</span> فروشگاه محصولات دیجیتال
      <div class=\"dash-grid\">
        <div class=\"dash-item\"><div class=\"d-icon\">📦</div><div class=\"d-num\" style=\"color:var(--accent2)\">۱۲</div><div class=\"d-label\">محصولات</div></div>
        <div class=\"dash-item\"><div class=\"d-icon\">🚚</div><div class=\"d-num\" style=\"color:var(--blue)\">۳</div><div class=\"d-label\">سفارشات فعال</div></div>
        <div class=\"dash-item\"><div class=\"d-icon\">📈</div><div class=\"d-num\" style=\"color:var(--orange)\">۷۲٪</div><div class=\"d-label\">نرخ تبدیل</div></div>
        <div class=\"dash-item\"><div class=\"d-icon\">💰</div><div class=\"d-num\" style=\"color:var(--green)\">۱۲.۸میلیون</div><div class=\"d-label\">مجموع فروش</div></div>
      </div>
      📆 امروز: ۲ سفارش | 💰 ۱,۸۰۰,۰۰۰<br>📆 این هفته: ۸ سفارش | 💰 ۶,۲۰۰,۰۰۰<br>📆 این ماه: ۲۳ سفارش | 💰 ۱۲,۸۰۰,۰۰۰
      <div style=\"margin-top:6px;padding:6px;background:var(--red);color:#fff;border-radius:8px;font-size:11px;animation:pulseBorder 2s ease infinite\">⚠️ هشدار موجودی: ساعت MI Band 8 (۲ عدد باقی)</div>`,0);
    await checkPause();if(signal.aborted)return;await sleep(1200);
    btns([{text:'📦 محصولات',primary:true},{text:'📁 دسته‌بندی',ghost:true},{text:'🏷️ تخفیف',ghost:true},{text:'📬 سفارشات',ghost:true}],.3);
    await checkPause();if(signal.aborted)return;await sleep(2000);
    user('📦 محصولات',.2);await checkPause();if(signal.aborted)return;await sleep(400);await typing(.1,.8);await checkPause();if(signal.aborted)return;await sleep(800);
    bot(`📦 <b>مدیریت محصولات</b> — ۱۲ عدد
      <div class=\"pli\"><div class=\"p-thumb\" style=\"background:linear-gradient(135deg,#1a1a3e,#2a1a5e)\">📱</div><div class=\"p-info\"><div class=\"p-name\">گلکسی S24 Ultra</div><div class=\"p-sub\">۴۵,۰۰۰,۰۰۰ تومان • موجودی: ۱۲</div></div><div class=\"p-action\">✏️</div></div>
      <div class=\"pli\"><div class=\"p-thumb\" style=\"background:linear-gradient(135deg,#1a2a3e,#2a3a5e)\">📱</div><div class=\"p-info\"><div class=\"p-name\">آیفون ۱۵ پرو</div><div class=\"p-sub\">۷۸,۰۰۰,۰۰۰ تومان • موجودی: ۵</div></div><div class=\"p-action\">✏️</div></div>
      <div class=\"pli\"><div class=\"p-thumb\" style=\"background:linear-gradient(135deg,#2a1a3e,#3a2a5e)\">⌚️</div><div class=\"p-info\"><div class=\"p-name\">ساعت MI Band 8</div><div class=\"p-sub\">۲,۸۰۰,۰۰۰ تومان • <span style=\"color:var(--red)\">موجودی: ۲ ⚠️</span></div></div><div class=\"p-action\">✏️</div></div>`,0);
    await checkPause();if(signal.aborted)return;await sleep(800);
    btns([{text:'➕ محصول جدید',green:true,small:true},{text:'🔗 لینک محصول',ghost:true,small:true}],.3);
    await checkPause();if(signal.aborted)return;await sleep(1400);
    user('📁 دسته‌بندی',.2);await checkPause();if(signal.aborted)return;await sleep(400);await typing(.1,.6);await checkPause();if(signal.aborted)return;await sleep(600);
    bot('📁 <b>دسته‌بندی محصولات</b><br><br>📱 موبایل و تبلت — ۵ محصول<br>🎧 هدفون — ۳ محصول<br>⌚️ ساعت هوشمند — ۲ محصول<br>🔌 لوازم جانبی — ۲ محصول',0);
    await checkPause();if(signal.aborted)return;await sleep(400);
    btns([{text:'➕ دسته جدید',green:true,small:true},{text:'🏷️ کد تخفیف',ghost:true,small:true}],.3);
    await checkPause();if(signal.aborted)return;await sleep(1400);
    user('🏷️ کد تخفیف',.2);await checkPause();if(signal.aborted)return;await sleep(400);await typing(.1,.6);await checkPause();if(signal.aborted)return;await sleep(600);
    bot('🏷️ <b>کدهای تخفیف فعال</b>',0);await checkPause();if(signal.aborted)return;await sleep(200);
    bot(`<div class=\"dc\"><div><div class=\"dc-code\">FOROSH20</div><div class=\"dc-info\">🎯 درصدی: ۲۰٪ تخفیف • حداقل سفارش: ۵۰,۰۰۰ تومان • استفاده: ۲۴۰/∞</div></div><span style=\"color:var(--green);font-size:13px;font-weight:600\">فعال</span></div>
    <div class=\"dc\"><div><div class=\"dc-code\">WELCOME10</div><div class=\"dc-info\">💰 مبلغی: ۱۰,۰۰۰ تومان تخفیف • بدون حداقل • استفاده: ۸۹/۵۰۰</div></div><span style=\"color:var(--green);font-size:13px;font-weight:600\">فعال</span></div>`,.2);
    await checkPause();if(signal.aborted)return;await sleep(500);
    btns([{text:'➕ کد جدید',green:true,small:true},{text:'📬 سفارشات',primary:true,small:true}],.3);
    await checkPause();if(signal.aborted)return;await sleep(1400);
    user('📬 سفارشات',.2);await checkPause();if(signal.aborted)return;await sleep(400);await typing(.1,.6);await checkPause();if(signal.aborted)return;await sleep(600);
    bot('📬 <b>مدیریت سفارشات</b><br><br>⏳ در انتظار پرداخت: ۱ عدد<br>⏳ در انتظار بررسی: ۱ عدد<br>📦 در حال آماده‌سازی: ۱ عدد<br>🚚 ارسال شده: ۲ عدد<br>✅ تحویل شده: ۱۵ عدد',0);
    await checkPause();if(signal.aborted)return;await sleep(400);
    btns([{text:'📋 جزئیات سفارشات',primary:true},{text:'🔙 پنل اصلی',ghost:true}],.3);
    await checkPause();if(signal.aborted)return;await sleep(1400);
    user('🔙 پنل اصلی',.2);await checkPause();if(signal.aborted)return;await sleep(400);await typing(.1,.6);await checkPause();if(signal.aborted)return;await sleep(600);
    btns([{text:'🧾 تنظیمات پرداخت',ghost:true},{text:'💬 پیام مشتریان',ghost:true},{text:'📷 کاور فروشگاه',ghost:true},{text:'🔑 تغییر رمز',ghost:true}],.3);
    await checkPause();if(signal.aborted)return;await sleep(1800);
    user('🧾 تنظیمات پرداخت',.2);await checkPause();if(signal.aborted)return;await sleep(400);await typing(.1,.6);await checkPause();if(signal.aborted)return;await sleep(600);
    bot(`🧾 <b>تنظیمات پرداخت</b><br><br>💳 شماره کارت: ✅ ۶۰۳۷...۷۶۶۲<br>👤 صاحب کارت: ✅ محمد رضایی<br>🏦 شبا: ✅ IR۸۲۰۱۲۰...۳۸۲۹<br>🚚 هزینه ارسال: ۵۰,۰۰۰ تومان<br>🆓 ارسال رایگان بالای ۱,۰۰۰,۰۰۰ تومان`,0);
    await checkPause();if(signal.aborted)return;await sleep(600);
    btns([{text:'✏️ شماره کارت',ghost:true,small:true},{text:'✏️ هزینه ارسال',ghost:true,small:true},{text:'🔙 پنل',ghost:true,small:true}],.3);
    await checkPause();if(signal.aborted)return;await sleep(1800);
    user('🔙 پنل',.2);await checkPause();if(signal.aborted)return;await sleep(300);await typing(.1,.4);await checkPause();if(signal.aborted)return;await sleep(400);
    btns([{text:'🔗 لینک فروشگاه',ghost:true},{text:'📷 کاور',ghost:true}],.3);
    await checkPause();if(signal.aborted)return;await sleep(1200);
    user('🔗 لینک فروشگاه',.2);await checkPause();if(signal.aborted)return;await sleep(400);await typing(.1,.6);await checkPause();if(signal.aborted)return;await sleep(600);
    bot(`🏪 <b>لینک فروشگاهت</b><br><br>🔗 t.me/Foroshgrambot?start=shop_۱۲۳۴<br><br>💡 این لینک رو برای مشتریات بفرست یا بزار تو کانالت.<br>هرکی روش کلیک کنه مستقیم میره به فروشگاه تو.`,0);
    await checkPause();if(signal.aborted)return;await sleep(800);
    btns([{text:'🔙 پنل اصلی',green:true,small:true}],.3);
    await sleep(1200);if(signal.aborted)return;
  }"""

new_panel_compact = """async function sceneSellerPanel(signal){
    clearMsgs();setHeader('📊 پنل فروشگاه','م','purple','مدیر فروشگاه');updateUI(3);
    bot(`📊 <b>داشبورد فروشگاه</b> — فروشگاه محصولات دیجیتال
      <div class=\"dash-grid\">
        <div class=\"dash-item\"><div class=\"d-icon\">📦</div><div class=\"d-num\" style=\"color:var(--accent2)\">۱۲</div><div class=\"d-label\">محصولات</div></div>
        <div class=\"dash-item\"><div class=\"d-icon\">🚚</div><div class=\"d-num\" style=\"color:var(--blue)\">۳</div><div class=\"d-label\">سفارشات فعال</div></div>
        <div class=\"dash-item\"><div class=\"d-icon\">📈</div><div class=\"d-num\" style=\"color:var(--orange)\">۷۲٪</div><div class=\"d-label\">نرخ تبدیل</div></div>
        <div class=\"dash-item\"><div class=\"d-icon\">💰</div><div class=\"d-num\" style=\"color:var(--green)\">۱۲.۸میلیون</div><div class=\"d-label\">مجموع فروش</div></div>
      </div>
      ⚠️ هشدار موجودی: ساعت MI Band 8 (۲ عدد باقی)`,0);
    await checkPause();if(signal.aborted)return;await sleep(800);
    btns([{text:'📦 محصولات',primary:true},{text:'🏷️ تخفیف',ghost:true},{text:'📬 سفارشات',ghost:true}],.3);
    await checkPause();if(signal.aborted)return;await sleep(1500);
    user('📬 سفارشات',.2);await checkPause();if(signal.aborted)return;await sleep(300);await sleep(400);
    bot(`📬 <b>سفارشات فعال</b><br><br>⏳ در انتظار پرداخت: ۱ عدد<br>📦 در حال آماده‌سازی: ۱ عدد<br>🚚 ارسال شده: ۲ عدد<br>✅ تحویل شده: ۱۵ عدد`,0);
    await checkPause();if(signal.aborted)return;await sleep(400);
    btns([{text:'⚡ مشاهده جزئیات',primary:true}],.3);
    await checkPause();if(signal.aborted)return;await sleep(1500);
  }"""
html = html.replace(old_panel, new_panel_compact)

# Compress customer flow scene — remove extraneous browse steps
old_customer = """async function sceneCustomerFlow(signal){
    clearMsgs();setHeader('🛍️ فروشگاه دیجیتال','ف','green','● آنلاین');updateUI(4);
    bot('سلام! 👋<br><br>به <b>فروشگاه محصولات دیجیتال</b> خوش اومدی!<br><br>دسته‌بندی رو انتخاب کن:',0);
    await checkPause();if(signal.aborted)return;await sleep(800);
    btns([{text:'📱 موبایل و تبلت',primary:true},{text:'🎧 هدفون',ghost:true},{text:'⌚️ ساعت',ghost:true}],.3);
    await checkPause();if(signal.aborted)return;await sleep(1400);
    user('📱 موبایل و تبلت',.2);await checkPause();if(signal.aborted)return;await sleep(400);await typing(.1,.8);await checkPause();if(signal.aborted)return;await sleep(800);
    bot(`📁 <b>موبایل و تبلت</b> — ۸ محصول<br><br>🛒 گلکسی S24 Ultra — <span class=\"price\">۴۵,۰۰۰,۰۰۰</span><br>🛒 آیفون ۱۵ پرو — <span class=\"price\">۷۸,۰۰۰,۰۰۰</span><br>🛒 شیائومی ۱۴ — <span class=\"price\">۲۵,۰۰۰,۰۰۰</span>`,0);
    await checkPause();if(signal.aborted)return;await sleep(400);
    btns([{text:'🛒 گلکسی S24 Ultra',primary:true}],.3);
    await checkPause();if(signal.aborted)return;await sleep(1400);
    user('🛒 گلکسی S24 Ultra',.2);await checkPause();if(signal.aborted)return;await sleep(400);await typing(.1,1.0);await checkPause();if(signal.aborted)return;await sleep(1000);
    bot(`<b>گلکسی S24 Ultra</b><br><br>رم ۱۲ / ۲۵۶ گیگ — سامسونگ<br><br>💰 <span class=\"price\">۴۵,۰۰۰,۰۰۰</span> تومان<br>✅ موجود در انبار (۱۲ عدد)
      <div class=\"card\"><div class=\"img-grid\"><div>📱</div><div>📸</div><div>🔋</div><div>🎨</div></div><div class=\"body\"><div class=\"n\">📸 آلبوم تصاویر</div><div class=\"d\">۵ عکس • چرخش و زوم</div></div></div>`,0);
    await checkPause();if(signal.aborted)return;await sleep(800);
    btns([{text:'🛒 افزودن به سبد خرید',green:true},{text:'⭐️ علاقه‌مندی',ghost:true}],.3);
    await checkPause();if(signal.aborted)return;await sleep(1800);
    user('🛒 افزودن به سبد خرید',.2);await checkPause();if(signal.aborted)return;await sleep(400);await typing(.1,.6);await checkPause();if(signal.aborted)return;await sleep(600);
    bot('✅ به سبد خرید اضافه شد!',0);await checkPause();if(signal.aborted)return;await sleep(200);
    bot('🛒 <b>سبد خرید</b><br><br>📱 گلکسی S24 Ultra × ۱ — <span class=\"price\">۴۵,۰۰۰,۰۰۰</span> تومان<br>📱 آیفون ۱۵ پرو × ۱ — <span class=\"price\">۷۸,۰۰۰,۰۰۰</span> تومان<br><br>💳 <b>جمع:</b> <span class=\"price\">۱۲۳,۰۰۰,۰۰۰</span> تومان<br><br>🏷️ کد تخفیف داری؟ وارد کن 👇',.2);
    await checkPause();if(signal.aborted)return;await sleep(400);
    bot(`<span class=\"code-input\">FOROSH20</span>`,.2);
    await checkPause();if(signal.aborted)return;await sleep(600);
    bot('✅ کد تخفیف اعمال شد!<br><br>🎯 ۲۰٪ تخفیف (تا ۲۴,۶۰۰,۰۰۰ تومان)',.2);
    await checkPause();if(signal.aborted)return;await sleep(400);
    btns([{text:'✅ ثبت سفارش',green:true},{text:'✏️ ویرایش سبد خرید',ghost:true}],.3);
    await checkPause();if(signal.aborted)return;await sleep(1800);
    user('✅ ثبت سفارش',.2);await checkPause();if(signal.aborted)return;await sleep(400);await typing(.1,.8);await checkPause();if(signal.aborted)return;await sleep(800);
    system('📋 اطلاعات تحویل — مرحله ۱ از ۲');await checkPause();if(signal.aborted)return;await sleep(400);
    bot('👤 <b>نام گیرنده:</b>',0);await checkPause();if(signal.aborted)return;await sleep(500);
    user('علی رضایی',.2);await checkPause();if(signal.aborted)return;await sleep(300);
    bot('📞 <b>شماره تماس:</b>',.1);await checkPause();if(signal.aborted)return;await sleep(300);
    user('۰۹۱۲۱۲۳۴۵۶۷',.2);await checkPause();if(signal.aborted)return;await sleep(300);
    bot('📍 <b>آدرس:</b>',.1);await checkPause();if(signal.aborted)return;await sleep(300);
    user('تهران، ولیعصر، پلاک ۱۰۲۴',.2);await checkPause();if(signal.aborted)return;await sleep(300);
    await typing(.1,.6);await checkPause();if(signal.aborted)return;await sleep(600);
    bot('🧾 <b>خلاصه سفارش</b>',0);await checkPause();if(signal.aborted)return;await sleep(200);
    bot(`<div class=\"receipt\"><div class=\"rl\"><span class=\"ll\">گلکسی S24 Ultra × ۱</span><span>۴۵,۰۰۰,۰۰۰</span></div><div class=\"rl\"><span class=\"ll\">آیفون ۱۵ پرو × ۱</span><span>۷۸,۰۰۰,۰۰۰</span></div><div class=\"rl\"><span class=\"ll\">🏷️ تخفیف (FOROSH20)</span><span style=\"color:var(--green)\">-۲۴,۶۰۰,۰۰۰</span></div><div class=\"rl\"><span class=\"ll\">🚚 هزینه ارسال</span><span>۵۰,۰۰۰</span></div><div class=\"rd\">━━━</div><div class=\"rl t\"><span class=\"ll\">💰 قابل پرداخت</span><span>۹۸,۴۵۰,۰۰۰</span></div></div><br>💳 روش: کارت به کارت<br>💳 شماره: ۶۰۳۷...۷۶۶۲ (محمد رضایی)`,.2);
    await checkPause();if(signal.aborted)return;await sleep(600);
    btns([{text:'💳 پرداخت کردم ✅',green:true},{text:'✏️ ویرایش',ghost:true}],.3);
    await checkPause();if(signal.aborted)return;await sleep(1800);
    user('💳 پرداخت کردم ✅',.2);await checkPause();if(signal.aborted)return;await sleep(400);await typing(.1,.8);await checkPause();if(signal.aborted)return;await sleep(800);
    bot('✅ <b>سفارش ثبت شد!</b><br><br>🧾 شماره: #۲۶۰۷۱۷۴۸۳۶۱۰<br>⏳ وضعیت: <span class=\"badge wait\">در انتظار پرداخت</span><br><br>📬 بعد از تایید فروشنده، به زودی ارسال میشه 🔜',0);
    await checkPause();if(signal.aborted)return;await sleep(800);
    btns([{text:'⭐️ افزودن به علاقه‌مندی‌ها',ghost:true}],.3);
    await sleep(1500);if(signal.aborted)return;
  }"""

new_customer_compact = """async function sceneCustomerFlow(signal){
    clearMsgs();setHeader('🛍️ فروشگاه','ف','green','● آنلاین');updateUI(4);
    bot('سلام! 👋<br><br>به فروشگاه خوش اومدی! یه نگاه به محصولات بنداز:',0);
    await checkPause();if(signal.aborted)return;await sleep(400);
    btns([{text:'📱 موبایل و تبلت',primary:true}],.2);
    await checkPause();if(signal.aborted)return;await sleep(600);
    user('📱 موبایل و تبلت',.2);await checkPause();if(signal.aborted)return;await sleep(200);
    bot(`📁 <b>موبایل</b><br><br>🛒 گلکسی S24 Ultra — <span class=\"price\">۴۵,۰۰۰,۰۰۰</span><br>🛒 آیفون ۱۵ پرو — <span class=\"price\">۷۸,۰۰۰,۰۰۰</span>`,.1);
    await checkPause();if(signal.aborted)return;await sleep(200);
    btns([{text:'🛒 گلکسی S24 Ultra',green:true}],.2);
    await checkPause();if(signal.aborted)return;await sleep(600);
    user('🛒 گلکسی S24 Ultra',.2);await checkPause();if(signal.aborted)return;await sleep(200);
    bot(`✅ به سبد خرید اضافه شد!<br><br>🛒 <b>سبد خرید</b><br>📱 گلکسی S24 Ultra — <span class=\"price\">۴۵,۰۰۰,۰۰۰</span><br><br>🏷️ کد تخفیف داری؟`,.1);
    await checkPause();if(signal.aborted)return;await sleep(200);
    bot(`<span class=\"code-input\">FOROSH20</span>`,.1);
    await checkPause();if(signal.aborted)return;await sleep(300);
    bot('✅ ۲۰٪ تخفیف اعمال شد!',.2);
    await checkPause();if(signal.aborted)return;await sleep(200);
    btns([{text:'✅ ثبت سفارش',green:true}],.2);
    await checkPause();if(signal.aborted)return;await sleep(600);
    user('✅ ثبت سفارش',.2);await checkPause();if(signal.aborted)return;await sleep(300);
    system('📋 اطلاعات تحویل');await checkPause();if(signal.aborted)return;await sleep(200);
    bot('👤 نام: علی رضایی<br>📞 تماس: ۰۹۱۲۱۲۳۴۵۶۷<br>📍 آدرس: تهران، ولیعصر، پلاک ۱۰۲۴',.1);
    await checkPause();if(signal.aborted)return;await sleep(300);
    bot(`🧾 <b>خلاصه</b><br><br>💰 مبلغ: <span class=\"price\">۹۸,۴۵۰,۰۰۰</span> تومان<br>💳 کارت به کارت — ۶۰۳۷...۷۶۶۲`,.1);
    await checkPause();if(signal.aborted)return;await sleep(300);
    bot('✅ <b>سفارش ثبت شد!</b> منتظر تایید فروشنده...',.1);
    await checkPause();if(signal.aborted)return;await sleep(600);
  }"""
html = html.replace(old_customer, new_customer_compact)

# Compress seller delivery scene
old_delivery = """async function sceneSellerDelivery(signal){
    clearMsgs();setHeader('📊 پنل مدیریت','م','purple','مدیر فروشگاه');updateUI(5);
    bot('🔔 <b>سفارش جدید!</b>',0);await checkPause();if(signal.aborted)return;await sleep(400);
    bot(`<div class=\"order-card\"><div class=\"oh\"><span>🧾 #۲۶۰۷۱۷۴۸۳۶۱۰</span><span class=\"ob pending\">⏳ در انتظار پرداخت</span></div><div class=\"or\">👤 علی رضایی — ۰۹۱۲۱۲۳۴۵۶۷</div><div class=\"or\">📍 تهران، ولیعصر، پلاک ۱۰۲۴</div><div class=\"or\">💰 <span class=\"price\">۹۸,۴۵۰,۰۰۰</span> تومان</div><div class=\"or\">📱 گلکسی S24 Ultra • آیفون ۱۵ پرو</div><div class=\"or\">💳 کارت به کارت ✅ (ارسال رسید)</div><div class=\"or\">🏷️ کد تخفیف: FOROSH20 (۲۰٪)</div></div>`,.2);
    await checkPause();if(signal.aborted)return;await sleep(600);
    btns([{text:'📋 جزئیات کامل',primary:true},{text:'✅ تایید پرداخت',green:true}],.3);
    await checkPause();if(signal.aborted)return;await sleep(1800);
    user('✅ تایید پرداخت',.2);await checkPause();if(signal.aborted)return;await sleep(400);await typing(.1,.6);await checkPause();if(signal.aborted)return;await sleep(600);
    bot('✅ <b>پرداخت تأیید شد!</b><br><br>🧾 #۲۶۰۷۱۷۴۸۳۶۱۰<br>📌 وضعیت: <span class=\"badge active\">تأیید شده</span><br><br>سفارش به مرحله آماده‌سازی رفت.',0);
    await checkPause();if(signal.aborted)return;await sleep(500);
    btns([{text:'📦 در حال آماده‌سازی',primary:true}],.3);
    await checkPause();if(signal.aborted)return;await sleep(1400);
    user('📦 در حال آماده‌سازی',.2);await checkPause();if(signal.aborted)return;await sleep(300);
    bot('📦 <b>سفارش آماده ارسال شد</b> — کد رهگیری پستی رو وارد کن:',0);
    await checkPause();if(signal.aborted)return;await sleep(500);
    user('۶۵۱۶۵۱',.2);await checkPause();if(signal.aborted)return;await sleep(300);await typing(.1,.6);await checkPause();if(signal.aborted)return;await sleep(600);
    bot('🚚 <b>سفارش ارسال شد!</b><br><br>🧾 #۲۶۰۷۱۷۴۸۳۶۱۰<br>📮 کد رهگیری: ۶۵۱۶۵۱<br>🚚 وضعیت: <span class=\"badge shipped\">ارسال شده</span><br><br>به خریدار اطلاع داده شد.',0);
    await checkPause();if(signal.aborted)return;await sleep(600);
    system('📬 اعلان به خریدار');await checkPause();if(signal.aborted)return;await sleep(400);
    bot(`📬 <b>سفارشت ارسال شد!</b> 🚚<br><br>🧾 #۲۶۰۷۱۷۴۸۳۶۱۰<br>📮 کد رهگیری پستی: ۶۵۱۶۵۱<br><br>📌 وقتی به دستت رسید، دکمه زیر رو بزن:`,0);
    await checkPause();if(signal.aborted)return;await sleep(400);
    btns([{text:'📦 بسته به دستم رسید ✅',green:true}],.3);
    await checkPause();if(signal.aborted)return;await sleep(2000);
    user('📦 بسته به دستم رسید ✅',.2);await checkPause();if(signal.aborted)return;await sleep(400);await typing(.1,.8);await checkPause();if(signal.aborted)return;await sleep(800);
    bot('✅ <b>سفارش تحویل شد!</b><br><br>🌟 از خریدت ممنونیم!<br>اگه راضی بودی به فروشگاه امتیاز بده:',0);
    await checkPause();if(signal.aborted)return;await sleep(300);
    btns([{text:'⭐⭐⭐⭐⭐',orange:true}],.3);
    await checkPause();if(signal.aborted)return;await sleep(1800);
    user('⭐⭐⭐⭐⭐',.2);await checkPause();if(signal.aborted)return;await sleep(400);
    bot('⭐️ <b>امتیاز شما ثبت شد!</b><br><br>امتیاز فعلی فروشگاه: <b>۴.۸ از ۵</b> 🌟<br><br>💎 از اینکه فروشگرام رو انتخاب کردی ممنونیم!',0);
    await sleep(2000);if(signal.aborted)return;
  }"""

new_delivery_compact = """async function sceneSellerDelivery(signal){
    clearMsgs();setHeader('📊 پنل مدیریت','م','purple','مدیر فروشگاه');updateUI(5);
    bot('🔔 <b>سفارش جدید!</b>',0);await checkPause();if(signal.aborted)return;await sleep(300);
    bot(`🧾 #۲۶۰۷۱۷۴۸۳۶۱۰ — علی رضایی<br>💰 <span class=\"price\">۹۸,۴۵۰,۰۰۰</span> تومان<br>📱 گلکسی S24 Ultra • آیفون ۱۵ پرو<br>💳 کارت به کارت ✅ رسید فرستاده`,.1);
    await checkPause();if(signal.aborted)return;await sleep(300);
    btns([{text:'✅ تایید پرداخت',green:true}],.2);
    await checkPause();if(signal.aborted)return;await sleep(600);
    user('✅ تایید پرداخت',.2);await checkPause();if(signal.aborted)return;await sleep(300);
    bot('✅ <b>پرداخت تأیید شد!</b>',.1);await checkPause();if(signal.aborted)return;await sleep(200);
    btns([{text:'🚚 ارسال شد',primary:true}],.2);
    await checkPause();if(signal.aborted)return;await sleep(600);
    user('🚚 ارسال شد',.2);await checkPause();if(signal.aborted)return;await sleep(200);
    bot('📮 کد رهگیری: ۶۵۱۶۵۱. به خریدار اطلاع داده شد.',.1);
    await checkPause();if(signal.aborted)return;await sleep(300);
    system('📬 خریدار: بسته به دستم رسید ✅');await checkPause();if(signal.aborted)return;await sleep(200);
    bot('✅ <b>سفارش تحویل شد!</b> 🌟 امتیاز ۵ ستاره گرفتی!',.1);
    await checkPause();if(signal.aborted)return;await sleep(600);
  }"""
html = html.replace(old_delivery, new_delivery_compact)

# Compress features scene
html = html.replace(
    "await checkPause();if(signal.aborted)return;await sleep(600);\n    bot('و همه اینا داخل یه ربات تلگرام!<br><br>بدون نصب اپ • بدون سایت • بدون دانش فنی',.4);\n    await sleep(2000);",
    "await checkPause();if(signal.aborted)return;await sleep(300);\n    bot('و همه اینا داخل یه ربات تلگرام!<br><br>بدون نصب اپ • بدون سایت • بدون دانش فنی',.2);\n    await sleep(800);"
)

# Compress CTA scene
html = html.replace(
    """await typing(0,1.5);await checkPause();if(signal.aborted)return;await sleep(1500);
    bot('🚀 <b>همین حالا فروشگاه خودت رو راه بنداز!</b><br><br>✅ فروشگاه اختصاصی تو توی تلگرام<br>✅ مدیریت آسون محصولات و سفارش‌ها<br>✅ پرداخت مستقیم به حساب خودت<br>✅ لینک اختصاصی برای کانالت<br>✅ کاملاً رایگان — بدون هزینه اولیه<br><br>👇 همین الان شروع کن',0);
    await checkPause();if(signal.aborted)return;await sleep(800);
    btns([{text:'🚀 شروع در تلگرام!',green:true,primary:true}],.3);
    await checkPause();if(signal.aborted)return;await sleep(2500);
    bot('💎 <b>فروشگرام</b> — فروش آسان‌تر در تلگرام<br><br>🤖 <b>@Foroshgrambot</b>',.4);
    await sleep(3000);""",
    """bot('🚀 <b>فروشگاه خودت رو راه بنداز!</b><br><br>✅ فروشگاه اختصاصی تو توی تلگرام<br>✅ مدیریت آسون محصولات و سفارش‌ها<br>✅ پرداخت مستقیم به حسابت<br>✅ کاملاً رایگان',0);
    await checkPause();if(signal.aborted)return;await sleep(400);
    btns([{text:'🚀 شروع در تلگرام!',green:true,primary:true}],.2);
    await checkPause();if(signal.aborted)return;await sleep(1200);
    bot('💎 فروشگرام — @Foroshgrambot',.2);
    await sleep(1500);"""
)

# Write promo-30s.html in root
output_path = os.path.join(BASE_DIR, "promo-30s.html")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)
print(f"✅ {output_path}")

# ─── Now generate 10 color variants ────────────────────────────

THEMES = [
    {
        "id": "01", "name": "بنفش تیره",
        "vars": {
            "bg": "#0a0a10", "surface": "#13131e", "surface2": "#1d1d30",
            "surface3": "#282840", "border": "#262640", "border2": "#363660",
            "text": "#ededf5", "text2": "#9a9ab5", "text3": "#5c5c78",
            "accent": "#6c5ce7", "accent2": "#a29bfe",
            "green": "#00d2a0", "greenBg": "rgba(0,210,160,.12)",
            "blue": "#0984e3", "blueBg": "rgba(9,132,227,.12)",
            "orange": "#fdcb6e", "orangeBg": "rgba(253,203,110,.12)",
            "pink": "#fd79a8", "red": "#e74c3c",
            "shadow": "0 8px 80px rgba(0,0,0,.6)", "glow": "rgba(108,92,231,.15)",
            "custBg": "#1e1e30",
            "logo1": "#6c5ce7", "logo2": "#8b5cf6", "logo3": "#fd79a8",
        }
    },
    {
        "id": "02", "name": "روشن",
        "vars": {
            "bg": "#e8e8f2", "surface": "#ffffff", "surface2": "#f2f2f8",
            "surface3": "#eaeaf4", "border": "#dcdce8", "border2": "#ccccdc",
            "text": "#181828", "text2": "#4a4a66", "text3": "#6e6e8a",
            "accent": "#6c5ce7", "accent2": "#8b7cf7",
            "green": "#00b884", "greenBg": "rgba(0,184,132,.08)",
            "blue": "#0984e3", "blueBg": "rgba(9,132,227,.06)",
            "orange": "#d46950", "orangeBg": "rgba(212,105,80,.08)",
            "pink": "#e84393", "red": "#d63031",
            "shadow": "0 12px 90px rgba(0,0,0,.18)", "glow": "rgba(108,92,231,.06)",
            "custBg": "#e4e4ee",
            "logo1": "#6c5ce7", "logo2": "#a29bfe", "logo3": "#fd79a8",
        }
    },
    {
        "id": "03", "name": "طبیعی سبز",
        "vars": {
            "bg": "#e8f5e9", "surface": "#ffffff", "surface2": "#f1f8f2",
            "surface3": "#e0ebe3", "border": "#c8e6c9", "border2": "#a5d6a7",
            "text": "#1b3a1b", "text2": "#2e5c2e", "text3": "#558b55",
            "accent": "#2e7d32", "accent2": "#43a047",
            "green": "#00897b", "greenBg": "rgba(0,137,123,.08)",
            "blue": "#1565c0", "blueBg": "rgba(21,101,192,.06)",
            "orange": "#bf6f00", "orangeBg": "rgba(191,111,0,.08)",
            "pink": "#ad1457", "red": "#c62828",
            "shadow": "0 12px 90px rgba(0,0,0,.12)", "glow": "rgba(46,125,50,.06)",
            "custBg": "#dcedc8",
            "logo1": "#2e7d32", "logo2": "#43a047", "logo3": "#66bb6a",
        }
    },
    {
        "id": "04", "name": "اقیانوس آبی",
        "vars": {
            "bg": "#e3f2fd", "surface": "#ffffff", "surface2": "#f0f8ff",
            "surface3": "#ddeeff", "border": "#bbdefb", "border2": "#90caf9",
            "text": "#0d2538", "text2": "#1e4d6b", "text3": "#4a7a9e",
            "accent": "#0d47a1", "accent2": "#1565c0",
            "green": "#00a86b", "greenBg": "rgba(0,168,107,.08)",
            "blue": "#0277bd", "blueBg": "rgba(2,119,189,.06)",
            "orange": "#e65100", "orangeBg": "rgba(230,81,0,.08)",
            "pink": "#c2185b", "red": "#b71c1c",
            "shadow": "0 12px 90px rgba(0,0,0,.14)", "glow": "rgba(13,71,161,.06)",
            "custBg": "#c8e6ff",
            "logo1": "#0d47a1", "logo2": "#1565c0", "logo3": "#42a5f5",
        }
    },
    {
        "id": "05", "name": "غروب نارنجی",
        "vars": {
            "bg": "#fff3e0", "surface": "#ffffff", "surface2": "#fff8f0",
            "surface3": "#ffebd6", "border": "#ffe0b2", "border2": "#ffcc80",
            "text": "#2d1b0a", "text2": "#5a3d1e", "text3": "#8a6638",
            "accent": "#e65100", "accent2": "#ff6d00",
            "green": "#2e7d32", "greenBg": "rgba(46,125,50,.08)",
            "blue": "#1565c0", "blueBg": "rgba(21,101,192,.06)",
            "orange": "#bf360c", "orangeBg": "rgba(191,54,12,.08)",
            "pink": "#ad1457", "red": "#b71c1c",
            "shadow": "0 12px 90px rgba(0,0,0,.15)", "glow": "rgba(230,81,0,.06)",
            "custBg": "#ffccbc",
            "logo1": "#e65100", "logo2": "#ff6d00", "logo3": "#ffab40",
        }
    },
    {
        "id": "06", "name": "سبز تیره",
        "vars": {
            "bg": "#0a1a0a", "surface": "#0f200f", "surface2": "#162816",
            "surface3": "#1d351d", "border": "#2a4a2a", "border2": "#3a5e3a",
            "text": "#e8f5e9", "text2": "#a5d6a7", "text3": "#66bb6a",
            "accent": "#4caf50", "accent2": "#66bb6a",
            "green": "#00e676", "greenBg": "rgba(0,230,118,.12)",
            "blue": "#40c4ff", "blueBg": "rgba(64,196,255,.10)",
            "orange": "#ffd54f", "orangeBg": "rgba(255,213,79,.12)",
            "pink": "#f48fb1", "red": "#e57373",
            "shadow": "0 8px 80px rgba(0,0,0,.6)", "glow": "rgba(76,175,80,.15)",
            "custBg": "#1a301a",
            "logo1": "#4caf50", "logo2": "#66bb6a", "logo3": "#a5d6a7",
        }
    },
    {
        "id": "07", "name": "زغالی",
        "vars": {
            "bg": "#121212", "surface": "#1e1e1e", "surface2": "#2a2a2a",
            "surface3": "#353535", "border": "#333333", "border2": "#454545",
            "text": "#eeeeee", "text2": "#b0b0b0", "text3": "#7a7a7a",
            "accent": "#bb86fc", "accent2": "#ce93fd",
            "green": "#03dac6", "greenBg": "rgba(3,218,198,.12)",
            "blue": "#64b5f6", "blueBg": "rgba(100,181,246,.10)",
            "orange": "#ffb74d", "orangeBg": "rgba(255,183,77,.12)",
            "pink": "#f06292", "red": "#ef5350",
            "shadow": "0 8px 80px rgba(0,0,0,.7)", "glow": "rgba(187,134,252,.12)",
            "custBg": "#292929",
            "logo1": "#bb86fc", "logo2": "#ce93fd", "logo3": "#e1bee7",
        }
    },
    {
        "id": "08", "name": "رز صورتی",
        "vars": {
            "bg": "#fce4ec", "surface": "#ffffff", "surface2": "#fdf2f6",
            "surface3": "#fadde8", "border": "#f8bbd0", "border2": "#f48fb1",
            "text": "#2d0a1a", "text2": "#5a1e36", "text3": "#8a3858",
            "accent": "#d81b60", "accent2": "#e91e63",
            "green": "#00897b", "greenBg": "rgba(0,137,123,.08)",
            "blue": "#1565c0", "blueBg": "rgba(21,101,192,.06)",
            "orange": "#ef6c00", "orangeBg": "rgba(239,108,0,.08)",
            "pink": "#c2185b", "red": "#b71c1c",
            "shadow": "0 12px 90px rgba(0,0,0,.14)", "glow": "rgba(216,27,96,.06)",
            "custBg": "#f8bbd0",
            "logo1": "#d81b60", "logo2": "#e91e63", "logo3": "#f06292",
        }
    },
    {
        "id": "09", "name": "سایبرپانک",
        "vars": {
            "bg": "#0a0a1a", "surface": "#12122a", "surface2": "#1a1a38",
            "surface3": "#222248", "border": "#2a2a55", "border2": "#3a3a6a",
            "text": "#f0f0ff", "text2": "#b0b0ee", "text3": "#7070bb",
            "accent": "#ff2d55", "accent2": "#ff6b81",
            "green": "#00f0ff", "greenBg": "rgba(0,240,255,.12)",
            "blue": "#5856ff", "blueBg": "rgba(88,86,255,.10)",
            "orange": "#ff9f0a", "orangeBg": "rgba(255,159,10,.12)",
            "pink": "#ff375f", "red": "#ff3b30",
            "shadow": "0 8px 80px rgba(255,45,85,.2)", "glow": "rgba(255,45,85,.15)",
            "custBg": "#1a1a3e",
            "logo1": "#ff2d55", "logo2": "#5856ff", "logo3": "#00f0ff",
        }
    },
    {
        "id": "10", "name": "خاکستری مینیمال",
        "vars": {
            "bg": "#f0f0f0", "surface": "#fafafa", "surface2": "#f0f0f0",
            "surface3": "#e4e4e4", "border": "#d0d0d0", "border2": "#bdbdbd",
            "text": "#1a1a1a", "text2": "#555555", "text3": "#888888",
            "accent": "#37474f", "accent2": "#546e7a",
            "green": "#2e7d32", "greenBg": "rgba(46,125,50,.08)",
            "blue": "#1565c0", "blueBg": "rgba(21,101,192,.06)",
            "orange": "#ef6c00", "orangeBg": "rgba(239,108,0,.08)",
            "pink": "#c2185b", "red": "#b71c1c",
            "shadow": "0 12px 90px rgba(0,0,0,.12)", "glow": "rgba(55,71,79,.06)",
            "custBg": "#e0e0e0",
            "logo1": "#37474f", "logo2": "#546e7a", "logo3": "#90a4ae",
        }
    },
]

variant_dir = os.path.join(BASE_DIR, "promo_variants")

for t in THEMES:
    v = t["vars"]
    
    root = f""":root {{
    --bg:         {v["bg"]};
    --surface:    {v["surface"]};
    --surface2:   {v["surface2"]};
    --surface3:   {v["surface3"]};
    --border:     {v["border"]};
    --border2:    {v["border2"]};
    --text:       {v["text"]};
    --text2:      {v["text2"]};
    --text3:      {v["text3"]};
    --accent:     {v["accent"]};
    --accent2:    {v["accent2"]};
    --green:      {v["green"]};
    --greenBg:    {v["greenBg"]};
    --blue:       {v["blue"]};
    --blueBg:     {v["blueBg"]};
    --orange:     {v["orange"]};
    --orangeBg:   {v["orangeBg"]};
    --pink:       {v["pink"]};
    --red:        {v["red"]};
    --radius:     32px;
    --shadow:     {v["shadow"]};
    --glow:       {v["glow"]};
    --custBg:     {v["custBg"]};
  }}"""
    
    # Find :root block in the 30s version
    brace_depth = 0
    start_idx = html.find(":root {")
    if start_idx == -1:
        start_idx = html.find(":root{")
    idx = start_idx
    while idx < len(html):
        if html[idx] == '{':
            brace_depth += 1
        elif html[idx] == '}':
            brace_depth -= 1
            if brace_depth == 0:
                old_root_end = idx + 1
                break
        idx += 1
    
    new_html = html[:start_idx] + root + "\n" + html[old_root_end:]
    
    # Update title
    new_html = new_html.replace(
        "<title>فروشگرام — بنفش تیره</title>",
        f"<title>فروشگرام — {t['name']}</title>"
    )
    
    # Update logo gradient
    old_logo = "background:linear-gradient(135deg,#6c5ce7,#a29bfe,#fd79a8)"
    new_logo = f"background:linear-gradient(135deg,{v['logo1']},{v['logo2']},{v['logo3']})"
    new_html = new_html.replace(old_logo, new_logo)
    
    dest = os.path.join(variant_dir, f"promo-30s-{t['id']}.html")
    with open(dest, "w", encoding="utf-8") as f:
        f.write(new_html)
    print(f"✅ promo-30s-{t['id']}.html — {t['name']}")

print(f"\n✅ Done! {len(THEMES)} variants of promo-30s in promo_variants/")
