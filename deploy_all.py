"""Deploy all updated handler files to VPS container."""
import subprocess, base64, os

HANDLERS_DIR = 'T:/dars/projects/telegram/Telegramorderbot/telegram_order_bot/handlers'
FILES = [
    'start.py',
    'seller_registration.py',
    'order.py',
    'cart.py',
    'seller_panel.py',
    'search.py',
    'menu.py',
    'support.py',
    'help.py',
    'conversations.py',
    'wishlist.py',
    'common.py',
    'discount.py',
]
ADMIN_FILES = [
    'panel.py',
    'products.py',
    'shops.py',
]
SERVICE_FILES = [
    'notification_service.py',
]

ssh_host = '185.204.168.57'
ssh_port = 22
ssh_user = 'root'

def deploy_file(local_rel_path, container_path):
    full_local = os.path.join(HANDLERS_DIR, local_rel_path)
    if not os.path.exists(full_local):
        # try admin subdir
        full_local = os.path.join(HANDLERS_DIR, 'admin', local_rel_path)
    if not os.path.exists(full_local):
        # try services
        full_local = os.path.join(HANDLERS_DIR.replace('handlers', 'services'), local_rel_path)
    if not os.path.exists(full_local):
        print(f"SKIP {local_rel_path} - not found")
        return False
    
    with open(full_local, 'rb') as f:
        content = f.read()
    encoded = base64.b64encode(content).decode()
    
    cmd = (
        f'python3 -c "import base64; f=open(\'/tmp/deploy_{local_rel_path}\',\'wb\'); '
        f'f.write(base64.b64decode(\'{encoded}\')); f.close()" '
        f'&& docker cp /tmp/deploy_{local_rel_path} foroshgram_bot:{container_path}'
    )
    result = subprocess.run(
        ['python', 'C:/s/ssh-quick.py', cmd],
        capture_output=True, text=True, timeout=60
    )
    ok = result.returncode == 0 and 'Traceback' not in result.stderr
    if ok:
        print(f"OK  {local_rel_path}")
    else:
        print(f"FAIL {local_rel_path}: {result.stdout[:200]}")
    return ok

# Deploy handler files
for f in FILES:
    deploy_file(f, f'/app/handlers/{f}')

for f in ADMIN_FILES:
    deploy_file(f, f'/app/handlers/admin/{f}')

for f in SERVICE_FILES:
    fp = os.path.join(HANDLERS_DIR.replace('handlers', 'services'), f)
    if os.path.exists(fp):
        with open(fp, 'rb') as fh:
            content = fh.read()
        encoded = base64.b64encode(content).decode()
        cmd = (
            f'python3 -c "import base64; f=open(\'/tmp/deploy_{f}\',\'wb\'); '
            f'f.write(base64.b64decode(\'{encoded}\')); f.close()" '
            f'&& docker cp /tmp/deploy_{f} foroshgram_bot:/app/services/{f}'
        )
        result = subprocess.run(
            ['python', 'C:/s/ssh-quick.py', cmd],
            capture_output=True, text=True, timeout=60
        )
        ok = result.returncode == 0 and 'Traceback' not in result.stderr
        if ok:
            print(f"OK  {f}")
        else:
            print(f"FAIL {f}: {result.stdout[:200]}")

# Also fix forward_products.py
for f in ['forward_products.py']:
    deploy_file(f, f'/app/handlers/{f}')

# Also copy to VPS disk for future docker cp
print("\nBacking up to VPS disk...")
subprocess.run(
    ['python', 'C:/s/ssh-quick.py', 
     'docker cp foroshgram_bot:/app/handlers /opt/foroshgram/telegram_order_bot/handlers_new && '
     'rm -rf /opt/foroshgram/telegram_order_bot/handlers && '
     'mv /opt/foroshgram/telegram_order_bot/handlers_new /opt/foroshgram/telegram_order_bot/handlers && '
     'echo "Disk backed up"'],
    capture_output=True, text=True, timeout=30
)

# Restart
print("\nRestarting container...")
result = subprocess.run(
    ['python', 'C:/s/ssh-quick.py', 'docker restart foroshgram_bot && echo "Restarted"'],
    capture_output=True, text=True, timeout=30
)
print(result.stdout)
print(result.stderr[:200] if result.stderr else "")

# Verify compile
result = subprocess.run(
    ['python', 'C:/s/ssh-quick.py', 
     'docker exec foroshgram_bot python -m py_compile /app/handlers/start.py && '
     'docker exec foroshgram_bot python -m py_compile /app/handlers/seller_registration.py && '
     'docker exec foroshgram_bot python -m py_compile /app/handlers/order.py && '
     'echo "All compile OK"'],
    capture_output=True, text=True, timeout=30
)
print(result.stdout)
