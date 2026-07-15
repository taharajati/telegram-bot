#!/usr/bin/env python3
"""Full E2E test for Foroshgram bot - runs on VPS."""
import requests, time, json, subprocess, sys, os

TOKEN = "8871159970:AAGGYu0KboxPNEiqw29jnpAvYcdOLW5WmaQ"
BASE = f"https://api.telegram.org/bot{TOKEN}"
ADMIN_ID = 8497713691

results = []

def api(method, **kwargs):
    r = requests.post(f"{BASE}/{method}", json=kwargs, timeout=30)
    return r.json()

def send(chat_id, text):
    return api("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML")

def docker_exec(container, cmd):
    r = subprocess.run(["docker", "exec", container] + cmd, capture_output=True, text=True, timeout=15)
    return r.stdout.strip(), r.stderr.strip()

def test(name, fn):
    print(f"\n--- {name} ---")
    try:
        fn()
        results.append(("PASS", name))
    except Exception as e:
        results.append(("FAIL", name, str(e)))
        print(f"  FAIL: {e}")

print("=" * 50)
print("FOROSHGRAM BOT - COMPREHENSIVE E2E TESTS")
print("=" * 50)

# 1
def t1():
    me = api("getMe")
    assert me["ok"]
    print(f"  @{me['result']['username']} online")
test("1. Bot connectivity", t1)

# 2
def t2():
    # Flush old
    api("getUpdates", offset=0, timeout=1)
    api("getUpdates", offset=0, timeout=1)
    send(ADMIN_ID, "/start")
    time.sleep(5)
    r = api("getUpdates", offset=0, timeout=5, allowed_updates=json.dumps(["message"]))
    found = False
    if r.get("ok") and r.get("result"):
        for u in r["result"][-10:]:
            m = u.get("message",{})
            if m.get("from",{}).get("is_bot") and m["chat"]["id"] == ADMIN_ID:
                text = m.get("text","")
                kb = m.get("reply_markup",{}).get("inline_keyboard",[])
                btns = [b[0]["text"] for row in kb for b in row] if kb else []
                if "فروشگرام" in text or "سلام" in text or len(text) > 10:
                    print(f"  Bot message: {text[:80]}...")
                    if btns:
                        print(f"  Buttons: {btns}")
                    found = True
                    break
    assert found, "No welcome message found"
test("2. Admin /start", t2)

# 3
def t3():
    out, err = docker_exec("foroshgram_bot", ["python3", "-c",
        "import os; print(os.environ.get('ENCRYPTION_KEY','NOT SET')[:20])"])
    print(f"  ENCRYPTION_KEY: {out}")
    assert "NOT SET" not in out, "ENCRYPTION_KEY is NOT SET"
test("3. ENCRYPTION_KEY", t3)

# 4
def t4():
    out, err = docker_exec("foroshgram_bot", ["timeout", "10", "python3", "-c",
        "from utils.crypto import safe_encrypt; e=safe_encrypt('6037991234567890'); print('LEN:'+str(len(e)))"])
    print(f"  {out}")
    assert "LEN:" in out, f"Encryption failed: {err}"
    length = int(out.split(":")[1])
    assert length > 40, f"Encrypted too short: {length}"
test("4. safe_encrypt", t4)

# 5
def t5():
    out, _ = docker_exec("f746043009ed_foroshgram_postgres", ["psql", "-U", "foroshgram", "-At", "-c",
        "SELECT column_name FROM information_schema.columns WHERE table_name='shops' ORDER BY ordinal_position"])
    cols = set(out.split("\n"))
    req = {"card_number","card_holder_name","sheba_number","channel_link","shipping_cost","free_shipping_above","banner_image"}
    missing = req - cols
    if missing:
        assert False, f"Missing columns: {missing}"
    print(f"  All 7 columns present")
test("5. DB schema (shops)", t5)

# 6
def t6():
    # Write a tmp python file and exec it
    open("/tmp/test_imports.py","w").write("""
import asyncio
from database.db import async_session
from database.models import Shop
import sqlalchemy
print("imports OK")
""")
    out, err = docker_exec("foroshgram_bot", ["python3", "/tmp/test_imports.py"])
    print(f"  {out}")
    assert "imports OK" in out, f"Import failed: {err}"
test("6. Bot imports", t6)

# 7
def t7():
    open("/tmp/test_dbq.py","w").write("""
import asyncio
from database.db import async_session
from database.models import Shop
import sqlalchemy
async def go():
    async with async_session() as s:
        c = await s.scalar(sqlalchemy.select(sqlalchemy.func.count()).select_from(Shop))
        print(f"shop_count:{c}")
asyncio.run(go())
""")
    out, err = docker_exec("foroshgram_bot", ["python3", "/tmp/test_dbq.py"])
    print(f"  {out}")
    assert "shop_count:" in out, f"DB query failed: {err}"
test("7. Bot queries DB", t7)

# 8
def t8():
    r = subprocess.run(["curl", "-s", "-w", " HTTP:%{http_code}", "https://telegramorder.ir/api/shops"],
                      capture_output=True, text=True, timeout=15)
    print(f"  {r.stdout.strip()[:150]}")
test("8. Website /api/shops", t8)

# 9
def t9():
    out, _ = docker_exec("f746043009ed_foroshgram_postgres", ["psql", "-U", "foroshgram", "-At", "-c",
        "SELECT count(*) FROM shop_owners"])
    print(f"  Shop owners: {out}")
    assert out.isdigit() and int(out) > 0, "No shop owners"
test("9. Shop owners", t9)

# 10
def t10():
    out, _ = docker_exec("f746043009ed_foroshgram_postgres", ["psql", "-U", "foroshgram", "-At", "-c",
        "SELECT id FROM shops ORDER BY id DESC LIMIT 1"])
    print(f"  Latest shop ID: {out}")
test("10. Latest shop", t10)

# 11
def t11():
    out, err = docker_exec("foroshgram_bot", ["python3", "-c",
        "import handlers.seller_registration; print('OK')"])
    print(f"  seller_registration: {out}")
    assert "OK" in out, f"Import failed: {err}"
test("11. seller_registration module", t11)

# 12
def t12():
    out, err = docker_exec("foroshgram_bot", ["timeout", "10", "python3", "-c",
        "from utils.crypto import safe_encrypt; e=safe_encrypt('test'); print('CRYPTO_OK')"])
    print(f"  {out}")
    assert "CRYPTO_OK" in out, f"Crypto failed: {err}"
test("12. Crypto integration", t12)

# 13
def t13():
    out, err = docker_exec("foroshgram_bot", ["python3", "-c",
        "import bcrypt; h=bcrypt.hashpw(b'test123', bcrypt.gensalt()); print('BCRYPT_OK:'+str(len(h)))"])
    print(f"  {out}")
    assert "BCRYPT_OK" in out, f"bcrypt failed: {err}"
test("13. bcrypt", t13)

# 14
def t14():
    out, err = docker_exec("foroshgram_bot", ["python3", "-c",
        "from handlers.admin_approval import get_admin_approval_conversation; print('OK')"])
    print(f"  admin_approval: {out}")
    assert "OK" in out, f"Import failed: {err}"
test("14. admin_approval module", t14)

# 15
def t15():
    out, err = docker_exec("foroshgram_bot", ["python3", "-c",
        "from services.monitoring import monitor; print('OK')"])
    print(f"  monitoring: {out}")
    assert "OK" in out, f"Import failed: {err}"
test("15. Monitoring service", t15)

# 16
def t16():
    out, _ = docker_exec("foroshgram_bot", ["python3", "-c",
        "import config; print('ADMIN_COUNT:' + str(len(config.ADMIN_IDS)) + ' STORE:' + config.STORE_NAME)"])
    print(f"  {out}")
    assert "ADMIN_COUNT:" in out, f"Config import failed"
test("16. Config module", t16)

# 17
def t17():
    out, _ = docker_exec("foroshgram_bot", ["python3", "-c",
        "from database.db import async_session; print('DB engine OK')"])
    print(f"  {out}")
    assert "DB engine OK" in out or "imports OK" in out, "DB engine import failed"
test("17. Database engine", t17)

# 18
def t18():
    out, _ = docker_exec("foroshgram_bot", ["python3", "-c",
        "from utils.tg_helpers import render_view; print('tg_helpers OK')"])
    print(f"  {out}")
    assert "OK" in out, "tg_helpers import failed"
test("18. tg_helpers module", t18)

# 19: check card_number is stored encrypted (not plaintext)
def t19():
    out, _ = docker_exec("f746043009ed_foroshgram_postgres", ["psql", "-U", "foroshgram", "-At", "-c",
        "SELECT card_number FROM shops WHERE card_number IS NOT NULL LIMIT 1"])
    if out and out != "None":
        # It should be base64, not plain digits
        is_plaintext = out.replace("-","").replace(" ","").isdigit()
        print(f"  Card stored as: {out[:30]}... (plaintext: {is_plaintext})")
        assert not is_plaintext, "Card stored as plaintext! Encryption not working!"
        print("  ✅ Card is encrypted")
    else:
        print("  No cards in DB to check")
test("19. Card encryption check", t19)

# 20: check bot webhook/polling mode
def t20():
    wh = api("getWebhookInfo")
    if wh.get("ok") and wh.get("result"):
        url = wh["result"].get("url","")
        print(f"  Webhook URL: {url or 'None (polling)'}")
test("20. Webhook/polling mode", t20)

# Summary
print(f"\n{'='*50}")
print("SUMMARY:")
passed = sum(1 for r in results if r[0] == "PASS")
failed = sum(1 for r in results if r[0] == "FAIL")
for r in results:
    symbol = "PASS" if r[0] == "PASS" else "FAIL"
    print(f"  [{symbol}] {r[1]}" + (f" - {r[2]}" if len(r) > 2 else ""))
print(f"\n  Total: {len(results)} | Passed: {passed} | Failed: {failed}")
print("=" * 50)
