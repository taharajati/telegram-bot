"""Deploy all bot security changes via SSH exec (cat heredoc)"""
import subprocess
import sys

def ssh_cmd(cmd):
    result = subprocess.run(
        ['python', 'C:/s/ssh-quick.py', cmd],
        capture_output=True, text=True, timeout=60
    )
    return result.returncode == 0, result.stdout.strip()

def upload_file(local_path, remote_path):
    """Upload file via cat heredoc through ssh-quick"""
    with open(local_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Escape single quotes in content
    escaped = content.replace("'", "'\\''")
    
    # Use base64 to avoid escaping issues
    import base64
    b64 = base64.b64encode(content.encode('utf-8')).decode()
    
    ok, out = ssh_cmd(f"echo '{b64}' | base64 -d > {remote_path}")
    status = 'OK' if ok else 'FAIL'
    print(f'  {status}: {local_path} -> {remote_path}')
    return ok

files = [
    (r'handlers\seller_panel.py', '/opt/foroshgram/telegram_order_bot/handlers/seller_panel.py'),
    (r'handlers\seller_registration.py', '/opt/foroshgram/telegram_order_bot/handlers/seller_registration.py'),
    (r'handlers\order.py', '/opt/foroshgram/telegram_order_bot/handlers/order.py'),
    (r'services\order_service.py', '/opt/foroshgram/telegram_order_bot/services/order_service.py'),
    (r'utils\crypto.py', '/opt/foroshgram/telegram_order_bot/utils/crypto.py'),
    (r'utils\tg_helpers.py', '/opt/foroshgram/telegram_order_bot/utils/tg_helpers.py'),
    (r'database\models.py', '/opt/foroshgram/telegram_order_bot/database/models.py'),
    (r'main.py', '/opt/foroshgram/telegram_order_bot/main.py'),
]

import os
base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'telegram_order_bot')

print("Deploying bot files...")
all_ok = True
for local_rel, remote_path in files:
    local_path = os.path.join(base, local_rel)
    if not os.path.exists(local_path):
        print(f'  SKIP: {local_path} not found')
        continue
    if not upload_file(local_path, remote_path):
        all_ok = False

if all_ok:
    print("\nRestarting bot...")
    ok, out = ssh_cmd("docker restart foroshgram_bot")
    print(f"  Restart: {'OK' if ok else 'FAIL'}")
else:
    print("\n⚠️ Some files failed to upload")
