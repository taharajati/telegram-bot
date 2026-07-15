#!/usr/bin/env python3
"""End-to-end test for Foroshgram bot via Telegram Bot API."""
import requests
import time
import json
import sys

TOKEN = "8871159970:AAGGYu0KboxPNEiqw29jnpAvYcdOLW5WmaQ"
BASE = f"https://api.telegram.org/bot{TOKEN}"
CHAT_ID = 8497713691  # admin

offset = 0
last_msg_id = 0

def api(method, **kwargs):
    r = requests.post(f"{BASE}/{method}", json=kwargs, timeout=30)
    return r.json()

def send(text):
    r = api("sendMessage", chat_id=CHAT_ID, text=text)
    print(f"  → Sent: {text}")
    return r

def get_updates():
    global offset
    r = api("getUpdates", offset=offset, timeout=5, allowed_updates=json.dumps(["message","callback_query"]))
    if r.get("result"):
        offset = r["result"][-1]["update_id"] + 1
    return r.get("result", [])

def wait_for_reply(seconds=5):
    """Wait and collect all updates."""
    time.sleep(seconds)
    updates = get_updates()
    msgs = []
    for u in updates:
        if "message" in u:
            m = u["message"]
            if m.get("from",{}).get("id") == 777000:  # telegram service
                continue
            text = m.get("text","")
            msgs.append({"type":"text","text":text,"chat_id":m["chat"]["id"]})
        elif "callback_query" in u:
            cq = u["callback_query"]
            data = cq.get("data","")
            msgs.append({"type":"callback","data":data,"chat_id":cq["message"]["chat"]["id"]})
    return msgs

def click_button(data):
    r = api("answerCallbackQuery", callback_query_id="test")
    # We need the actual callback_query_id, so let's use a different approach
    # Send as a callback via the update - actually we can't fake callbacks
    # Instead, let's look at what buttons are available and use send_message with the callback data
    print(f"  → Need to click: {data}")
    return data

print("=" * 60)
print("Foroshgram Bot E2E Test")
print("=" * 60)

# Flush old updates
print("\n[0] Flushing old updates...")
old = get_updates()
print(f"  Flushed {len(old)} old updates")

# Test 1: /start command
print("\n[1] Testing /start command...")
r = send("/start")
time.sleep(3)
msgs = get_updates()
print(f"  Got {len(msgs)} updates")
for m in msgs:
    if m.get("message",{}).get("text"):
        t = m["message"]["text"][:200]
        print(f"  Bot: {t}")
    if m.get("message",{}).get("reply_markup"):
        buttons = m["message"]["reply_markup"].get("inline_keyboard",[])
        print(f"  Buttons: {[row[0].get('text','?') for row in buttons if row]}")

print("\nDone with test 1. Check bot logs for errors.")
