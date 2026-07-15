#!/usr/bin/env python3
"""Extract all Persian UI messages from bot files into a clean output file."""
import re, os

BASE = r"T:\dars\projects\telegram\Telegramorderbot\telegram_order_bot"
OUT = r"T:\dars\projects\telegram\Telegramorderbot\MESSAGES_ALL.txt"

FILES = [
    "handlers/start.py",
    "handlers/seller_registration.py",
    "handlers/seller_panel.py",
    "handlers/order.py",
    "handlers/cart.py",
    "handlers/menu.py",
    "handlers/search.py",
    "handlers/discount.py",
    "handlers/support.py",
    "handlers/conversations.py",
    "handlers/help.py",
    "handlers/wishlist.py",
    "handlers/common.py",
    "handlers/admin_approval.py",
    "handlers/forward_products.py",
    "handlers/admin/panel.py",
    "handlers/admin/products.py",
    "handlers/admin/categories.py",
    "handlers/admin/shops.py",
    "handlers/admin/orders.py",
    "services/notification_service.py",
    "services/abandoned_cart.py",
    "services/order_service.py",
    "config.py",
    "utils/tg_helpers.py",
]

PERSIAN = re.compile(r'[\u0600-\u06FF\u200C]')

def has_persian(s):
    return bool(PERSIAN.search(s))

lines = []
lines.append("=" * 70)
lines.append("  FOROSHGRAM BOT — ALL UI MESSAGES (for review/rewrite)")
lines.append("=" * 70)
lines.append("")

for filepath in FILES:
    full = os.path.join(BASE, filepath)
    if not os.path.exists(full):
        continue
    
    with open(full, 'r', encoding='utf-8') as f:
        content = f.read()
        filelines = content.split('\n')
    
    found = []
    for i, line in enumerate(filelines, 1):
        # Skip pure comments
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('//'):
            continue
        
        # Extract all quoted strings with Persian content
        for m in re.finditer(r'[\'](.*?)[\']|[\"](.*?)[\"]', line):
            text = m.group(1) if m.group(1) is not None else m.group(2)
            if text and has_persian(text) and len(text) > 3:
                found.append((i, text))
    
    if not found:
        continue
    
    lines.append(f"## FILE: {filepath}")
    lines.append("")
    seen = set()
    for lineno, text in found:
        # deduplicate
        key = text.strip()
        if key in seen:
            continue
        seen.add(key)
        # format: line number + text
        text_clean = text.replace('\\n', '\n   ')
        lines.append(f"  [{lineno:3d}]  {text_clean}")
    lines.append("")

lines.append("=" * 70)
lines.append("END")
lines.append("=" * 70)

result = '\n'.join(lines)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(result)

print(f"Done: {OUT}")
print(f"Size: {len(result)} chars, {len(lines)} lines")
