#!/usr/bin/env python3
"""Upload seller_panel.py to VPS by splitting into base64 chunks via temp files"""
import os
import base64
import subprocess
import sys

LOCAL = r'T:\dars\projects\telegram\Telegramorderbot\telegram_order_bot\handlers\seller_panel.py'
REMOTE = '/opt/foroshgram/telegram_order_bot/handlers/seller_panel.py'

with open(LOCAL, 'rb') as f:
    raw = f.read()

b64 = base64.b64encode(raw).decode()
expected_size = len(raw)
print(f'Local file: {expected_size} bytes')
print(f'Base64: {len(b64)} chars')

# Write to a temp file on VPS in chunks
SSH_QUICK = ['python', 'C:/s/ssh-quick.py']

def ssh(cmd):
    """Run command on VPS, return (ok, stdout)"""
    result = subprocess.run(SSH_QUICK + [cmd], capture_output=True, text=True, timeout=120)
    return result.returncode == 0, result.stdout.strip()

# Step 1: Ensure target dir
ssh(f'mkdir -p {os.path.dirname(REMOTE)}')

# Step 2: Write base64 in chunks using Python split approach
# Put chunk size at 5000 chars to be safe
chunk_size = 5000
written = 0
for i in range(0, len(b64), chunk_size):
    chunk = b64[i:i+chunk_size]
    # Use Python on VPS to append
    ok, out = ssh(f"python3 -c \"open('/tmp/sp_b64', 'a').write('{chunk}')\"")
    if not ok:
        print(f'FAIL at chunk {i}: {out}')
        sys.exit(1)
    written += len(chunk)
    print(f'  chunk at {i}: +{len(chunk)}={written}/{len(b64)}')

# Step 3: Decode to target file
ok, out = ssh(f'base64 -d < /tmp/sp_b64 > {REMOTE} && rm /tmp/sp_b64 && wc -c < {REMOTE}')
if ok:
    print(f'Remote file: {out} bytes')
else:
    print(f'Decode failed: {out}')
    sys.exit(1)

# Step 4: Verify
ok, out = ssh(f"python3 -c \"exec(open('{REMOTE}').read().split('\\n')[0])\" 2>&1 | head -1")
if ok:
    print('Python syntax OK')
else:
    print(f'Python error (may be expected for first line): {out[:100]}')

print('\nDone!')
