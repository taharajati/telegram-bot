"""Deploy bot files - reads each file and sends via ssh-quick base64"""
import os
import sys
import subprocess

BASE = r'T:\dars\projects\telegram\Telegramorderbot\telegram_order_bot'

# Files to deploy (local relative to BASE, absolute remote)
FILES = [
    ('handlers/seller_panel.py', '/opt/foroshgram/telegram_order_bot/handlers/seller_panel.py'),
    ('handlers/seller_registration.py', '/opt/foroshgram/telegram_order_bot/handlers/seller_registration.py'),
    ('handlers/order.py', '/opt/foroshgram/telegram_order_bot/handlers/order.py'),
    ('services/order_service.py', '/opt/foroshgram/telegram_order_bot/services/order_service.py'),
    ('utils/crypto.py', '/opt/foroshgram/telegram_order_bot/utils/crypto.py'),
    ('utils/tg_helpers.py', '/opt/foroshgram/telegram_order_bot/utils/tg_helpers.py'),
    ('database/models.py', '/opt/foroshgram/telegram_order_bot/database/models.py'),
    ('main.py', '/opt/foroshgram/telegram_order_bot/main.py'),
]

for local_rel, remote_path in FILES:
    local_abs = os.path.join(BASE, local_rel.replace('/', os.sep))
    
    # Write base64 to a temp file first, then upload via heredoc from the file
    with open(local_abs, 'rb') as f:
        import base64
        b64_data = base64.b64encode(f.read()).decode()
    
    # Upload via ssh-quick using printf with no newlines
    # Break into smaller chunks if needed
    print(f'Uploading {local_rel} ({len(b64_data)} bytes encoded)...')
    
    # Save b64 to a temp file on VPS via heredoc
    # Then decode to target
    import tempfile
    tmp_name = f'/tmp/dep_{os.urandom(4).hex()}'
    
    # Write b64 to temp file on VPS
    result = subprocess.run(
        ['python', 'C:/s/ssh-quick.py', f'cat > {tmp_name} << "B64EOF"\n{b64_data}\nB64EOF'],
        capture_output=True, text=True, timeout=60
    )
    
    if result.returncode != 0:
        print(f'  FAIL: {local_rel} - {result.stderr[:100]}')
        continue
    
    # Decode from temp file to target
    result = subprocess.run(
        ['python', 'C:/s/ssh-quick.py', f'base64 -d < {tmp_name} > {remote_path} && rm -f {tmp_name}'],
        capture_output=True, text=True, timeout=30
    )
    
    ok = result.returncode == 0
    print(f'  {"OK" if ok else "FAIL"}: {local_rel}')

print('\nBot files upload complete.')
