#!/usr/bin/env python3
"""Upload order_service.py to VPS."""
import base64, subprocess

SSH = "python C:/s/ssh-quick.py"
local = r"T:\dars\projects\telegram\Telegramorderbot\telegram_order_bot\services\order_service.py"
vps = "/opt/foroshgram/telegram_order_bot/services/order_service.py"
container = "/app/services/order_service.py"

with open(local, 'rb') as f:
    data = base64.b64encode(f.read()).decode()

# Write base64 to temp file via parts
subprocess.run(f'{SSH} "rm -f /tmp/os_b64.txt"', shell=True, check=True)
for i in range(0, len(data), 4000):
    chunk = data[i:i+4000]
    # Use printf instead of echo to avoid shell interpretation issues
    cmd = f'{SSH} "printf \'{chunk}\' >> /tmp/os_b64.txt"'
    subprocess.run(cmd, shell=True, check=True)

# Decode
subprocess.run(f'{SSH} "base64 -d /tmp/os_b64.txt > {vps}"', shell=True, check=True)

# Verify
r = subprocess.run(f'{SSH} "wc -c {vps}"', shell=True, capture_output=True, text=True)
print(f"VPS: {r.stdout.strip()}")

# Docker cp
subprocess.run(f'{SSH} "docker cp {vps} foroshgram_bot:{container}"', shell=True, check=True)

# Verify in container
r = subprocess.run(f'{SSH} "docker exec foroshgram_bot wc -c {container}"', shell=True, capture_output=True, text=True)
print(f"Container: {r.stdout.strip()}")
