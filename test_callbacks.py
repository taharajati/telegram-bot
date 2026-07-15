"""Test all callback buttons in the bot to find broken ones."""
import re, os

HANDLERS_DIR = 'T:/dars/projects/telegram/Telegramorderbot/telegram_order_bot/handlers'
SERVICES_DIR = 'T:/dars/projects/telegram/Telegramorderbot/telegram_order_bot/services'

# 1. Collect all callback_data values from InlineKeyboardButton
all_callbacks = set()
for root, dirs, files in os.walk(HANDLERS_DIR):
    for f in files:
        if not f.endswith('.py'):
            continue
        path = os.path.join(root, f)
        with open(path, 'r', encoding='utf-8') as fh:
            content = fh.read()
        for m in re.finditer(r'callback_data=["\']([^"\']+)["\']', content):
            cb = m.group(1)
            # Skip parametric callbacks (contain : and then a number/variable)
            all_callbacks.add(cb)

# 2. Collect all registered patterns from CallbackQueryHandler
registered = set()
for root, dirs, files in os.walk(HANDLERS_DIR):
    for f in files:
        if not f.endswith('.py'):
            continue
        path = os.path.join(root, f)
        with open(path, 'r', encoding='utf-8') as fh:
            content = fh.read()
        for m in re.finditer(r'CallbackQueryHandler\([^)]*pattern=["\']?r?["\']?\^?([^^$\']+)', content):
            registered.add(m.group(1))

# 3. Also check patterns without ^ anchor
for root, dirs, files in os.walk(HANDLERS_DIR):
    for f in files:
        if not f.endswith('.py'):
            continue
        path = os.path.join(root, f)
        with open(path, 'r', encoding='utf-8') as fh:
            content = fh.read()
        for m in re.finditer(r'pattern=["\']?r?["\']?\^?([^\s"\']+)', content):
            registered.add(m.group(1))

# 4. Find callbacks that don't match any registered pattern
print(f'Total button callbacks used: {len(all_callbacks)}')
print(f'Total registered patterns: {len(registered)}')
print()

# Filter out parametric callbacks (ones with variables)
static_callbacks = set()
for cb in all_callbacks:
    # Skip if it contains a number at the end (like shop:open:123)
    parts = cb.split(':')
    static_callbacks.add(cb)

broken = []
for cb in sorted(static_callbacks):
    found = False
    for pattern in registered:
        if cb.startswith(pattern) or pattern in cb:
            found = True
            break
    if not found:
        broken.append(cb)

if broken:
    print(f'BROKEN callbacks ({len(broken)}):')
    for cb in broken:
        print(f'  ❌ {cb}')
else:
    print('All callbacks have matching handlers ✅')
