"""Generate narration audio for promo-ig-01.html (long version) using edge-tts"""

import asyncio
import edge_tts
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), "audio")

# Scene scripts matching promo-ig-01.html (8 scenes, ~2 min)
SCENES = [
    ("s1_pain.mp3", "هر روز چند تا مشتری بهت پیام میده؟ قیمت، موجودی، شماره کارت. تکراری، خسته‌کننده، کلی وقتتو میگیره."),
    ("s2_solution.mp3", "فروشگرام میاد همه این کارا رو برات خودکار میکنه. یه فروشگاه کامل تو دل تلگرامت."),
    ("s3_register.mp3", "ثبت‌نام؟ فقط سه تا مرحله: اسم فروشگاهت، شماره تماس، شماره کارت. تموم."),
    ("s4_dashboard.mp3", "پنل مدیریت کامل: آمار فروش امروز و این هفته، محصولات پرفروش، هشدار موجودی کم."),
    ("s5_flow.mp3", "مشتری لینک رو میزنه، محصول رو میبینه، به سبد اضافه میکنه، کد تخفیف میزنه، پرداخت میکنه. همه چیز خودکار."),
    ("s6_delivery.mp3", "تو فقط میمونی و سفارش رو تأیید میکنی، آماده میکنی، کد رهگیری میدی. تموم."),
    ("s7_features.mp3", "پنل فروشنده، انبارداری، کد تخفیف، لینک اختصاصی، آلبوم محصول و کلی امکانات دیگه."),
    ("s8_cta.mp3", "فروشگرام. فروش آسان‌تر در تلگرام. Foroshgrambot"),
]

VOICE = "fa-IR-DilaraNeural"

async def generate():
    os.makedirs(OUT_DIR, exist_ok=True)
    for fname, text in SCENES:
        path = os.path.join(OUT_DIR, fname)
        print(f"🎙️  Generating {fname}...", end=" ", flush=True)
        communicate = edge_tts.Communicate(text, VOICE, rate="-5%", pitch="+0Hz")
        await communicate.save(path)
        size = os.path.getsize(path)
        print(f"✅ ({size:,} bytes)")

    # Also generate the full script as one file
    full_text = " . ".join(t for _, t in SCENES)
    full_path = os.path.join(OUT_DIR, "full_narration.mp3")
    print(f"🎙️  Generating full_narration.mp3...", end=" ", flush=True)
    communicate = edge_tts.Communicate(full_text, VOICE, rate="-5%", pitch="+0Hz")
    await communicate.save(full_path)
    size = os.path.getsize(full_path)
    print(f"✅ ({size:,} bytes)")

    print(f"\n✅ All audio saved to {OUT_DIR}")

if __name__ == "__main__":
    asyncio.run(generate())
