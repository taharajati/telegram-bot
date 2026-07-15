#!/usr/bin/env python3
"""Upload order_service.py and test_flow.py to VPS and copy into docker."""
import base64
import subprocess
import sys

SSH_CMD = "python C:/s/ssh-quick.py"


def upload_file(local_path, vps_path):
    with open(local_path, 'rb') as f:
        data = base64.b64encode(f.read()).decode()
    
    # Clear and write base64 parts
    part_size = 4000
    parts = [data[i:i+part_size] for i in range(0, len(data), part_size)]
    
    # Write all parts via echo >> to a temp file
    subprocess.run(f'{SSH_CMD} "rm -f /tmp/upload_b64.txt"', shell=True, check=True)
    for i, part in enumerate(parts):
        cmd = f'{SSH_CMD} "echo -n \'{part}\' >> /tmp/upload_b64.txt"'
        subprocess.run(cmd, shell=True, check=True)
    
    # Decode
    result = subprocess.run(
        f'{SSH_CMD} "base64 -d /tmp/upload_b64.txt > {vps_path}"',
        shell=True, capture_output=True, text=True
    )
    
    # Verify
    result = subprocess.run(
        f'{SSH_CMD} "wc -c {vps_path}"',
        shell=True, capture_output=True, text=True
    )
    print(f"  Uploaded {vps_path}: {result.stdout.strip()}")
    return len(data)


def docker_cp(vps_path, container_path, container_name="foroshgram_bot"):
    cmd = f'{SSH_CMD} "docker cp {vps_path} {container_name}:{container_path}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR docker cp: {result.stderr}")
    return result.returncode == 0


if __name__ == "__main__":
    files = [
        (r"T:\dars\projects\telegram\Telegramorderbot\telegram_order_bot\services\order_service.py",
         "/opt/foroshgram/telegram_order_bot/services/order_service.py",
         "/app/services/order_service.py"),
        (r"T:\dars\projects\telegram\Telegramorderbot\tests\test_flow.py",
         "/opt/foroshgram/tests/test_flow.py",
         "/app/tests/test_flow.py"),
    ]
    
    for local, vps, container in files:
        print(f"Uploading {local.split(chr(92))[-1]}...")
        upload_file(local, vps)
        docker_cp(vps, container)
    
    print("\nDone!")
