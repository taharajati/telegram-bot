#!/usr/bin/env python3
"""Upload remaining bot files"""
import os
import base64
import subprocess

BASE = r'T:\dars\projects\telegram\Telegramorderbot\telegram_order_bot'
FILES = [
    ('handlers/seller_registration.py', '/opt/foroshgram/telegram_order_bot/handlers/seller_registration.py'),
    ('handlers/order.py', '/opt/foroshgram/telegram_order_bot/handlers/order.py'),
    ('services/order_service.py', '/opt/foroshgram/telegram_order_bot/services/order_service.py'),
    ('database/models.py', '/opt/foroshgram/telegram_order_bot/database/models.py'),
]

SSH_QUICK = ['python', 'C:/s/ssh-quick.py']

def ssh(cmd):
    result = subprocess.run(SSH_QUICK + [cmd], capture_output=True, text=True, timeout=120)
    return result.returncode == 0, result.stdout.strip()

for local_rel, remote in FILES:
    local = os.path.join(BASE, local_rel.replace('/', os.sep))
    with open(local, 'rb') as f:
        raw = f.read()
    b64 = base64.b64encode(raw).decode()
    expected_size = len(raw)
    
    print(f'Uploading {local_rel} ({expected_size} bytes, {len(b64)} b64 chars)...')
    
    chunk_size = 5000
    for i in range(0, len(b64), chunk_size):
        chunk = b64[i:i+chunk_size]
        ok, out = ssh(f"python3 -c \"open('/tmp/up_b64', 'a').write('{chunk}')\"")
        if not ok:
            print(f'  FAIL at {i}: {out}')
            break
    else:
        ok, out = ssh(f'base64 -d < /tmp/up_b64 > {remote} && rm /tmp/up_b64 && wc -c < {remote}')
        if ok:
            print(f'  OK: {out} bytes')
        else:
            print(f'  Decode FAIL: {out}')

print('\nUpload complete!')
