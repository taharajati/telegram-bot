#!/usr/bin/env python3
"""Foroshgram — SCP + Deploy via SOCKS5 proxy (lightweight)"""
import paramiko
import socks
import sys
import time
import os
import posixpath

PROXY_HOST = '127.0.0.1'
PROXY_PORT = 10808
TARGET_HOST = '185.204.168.57'
USERNAME = 'ubuntu'
KEY_FILE = 'C:/s/ar-me-privatekey.pem'
LOCAL_PROJECT = 'T:/dars/projects/telegram/Telegramorderbot'
REMOTE = '/opt/foroshgram'

def connect():
    sock = socks.socksocket()
    sock.settimeout(30)
    sock.set_proxy(socks.SOCKS5, PROXY_HOST, PROXY_PORT)
    sock.connect((TARGET_HOST, 22))
    t = paramiko.Transport(sock)
    t.start_client()
    t.auth_publickey(USERNAME, paramiko.RSAKey.from_private_key_file(KEY_FILE))
    return t

def run(ch, cmd, desc="", timeout=120):
    if desc: print(f"\n▶ {desc}")
    print(f"$ {cmd}")
    ch.exec_command(cmd)
    out, err = b'', b''
    while True:
        if ch.recv_ready(): out += ch.recv(4096)
        if ch.recv_stderr_ready(): err += ch.recv_stderr(4096)
        if ch.exit_status_ready(): break
        time.sleep(0.1)
    code = ch.recv_exit_status()
    print(out.decode('utf-8', errors='replace'))
    if err: print(err.decode('utf-8', errors='replace'), file=sys.stderr)
    print("  ✅" if code == 0 else f"  ⚠️ exit={code}")
    return code

def main():
    print(f"[*] Connecting via SOCKS5 -> {TARGET_HOST}:22 ...")
    t = connect()
    print("[OK] Connected!\n")
    
    sftp = t.open_sftp_client()
    
    def scp(local, remote):
        sftp.put(local, remote)
        print(f"  📤 {os.path.basename(local)}")

    def ensure(path):
        try: sftp.stat(path)
        except: sftp.mkdir(path)

    def copy_tree(local_root, remote_root):
        for item in os.listdir(local_root):
            if item in ('.git', 'node_modules', '__pycache__', '.next', 'venv', '.turbo'): continue
            local = os.path.join(local_root, item)
            remote = posixpath.join(remote_root, item)
            if os.path.isdir(local):
                ensure(remote)
                copy_tree(local, remote)
            else:
                ensure(os.path.dirname(remote))
                scp(local, remote)

    print("📂 Copying project...")
    ensure(REMOTE)
    copy_tree(LOCAL_PROJECT, REMOTE)
    sftp.close()

    # Run deployment commands via sessions
    def sc(cmd, desc="", timeout=120):
        ch = t.open_session()
        ch.settimeout(timeout)
        code = run(ch, cmd, desc, timeout)
        ch.close()
        return code

    # Create .env files
    sc(f"echo 'BOT_TOKEN=8921572262:AAF57sD_SE_BjXUUnQqi8aT41bA90FCxeQU' | sudo tee {REMOTE}/telegram_order_bot/.env > /dev/null", "Bot .env")
    sc(f"echo 'ADMIN_IDS=8497713691' | sudo tee -a {REMOTE}/telegram_order_bot/.env > /dev/null", "Bot ADMIN_IDS")
    sc(f"echo 'DATABASE_URL=postgresql+asyncpg://foroshgram:${{POSTGRES_PASSWORD}}@postgres:5432/foroshgram' | sudo tee -a {REMOTE}/telegram_order_bot/.env > /dev/null", "Bot DATABASE_URL")
    sc(f"echo 'STORE_NAME=فروشگرام' | sudo tee -a {REMOTE}/telegram_order_bot/.env > /dev/null", "Bot STORE_NAME")
    sc(f"echo 'ZARINPAL_SANDBOX=false' | sudo tee -a {REMOTE}/telegram_order_bot/.env > /dev/null", "Bot ZARINPAL")
    sc(f"echo 'PROXY_URL=' | sudo tee -a {REMOTE}/telegram_order_bot/.env > /dev/null", "Bot PROXY_URL")

    sc(f"echo 'DATABASE_URL=postgresql://foroshgram:${{POSTGRES_PASSWORD}}@postgres:5432/foroshgram' | sudo tee {REMOTE}/telegram_order_website/.env.production > /dev/null", "Web .env.production")
    sc(f"echo 'ADMIN_USERNAME=admin' | sudo tee -a {REMOTE}/telegram_order_website/.env.production > /dev/null", "Web ADMIN_USER")
    sc(f"echo 'ADMIN_PASSWORD=CHANGE_ME_STRONG_PASSWORD' | sudo tee -a {REMOTE}/telegram_order_website/.env.production > /dev/null", "Web ADMIN_PASS")
    sc(f"echo 'NEXTAUTH_URL=https://telegramorder.ir' | sudo tee -a {REMOTE}/telegram_order_website/.env.production > /dev/null", "Web NEXTAUTH")

    # System packages
    sc("sudo apt-get update && sudo apt-get install -y docker.io docker-compose nginx certbot python3-certbot-nginx curl wget ufw", "Installing packages", timeout=300)
    sc("sudo systemctl enable docker && sudo systemctl start docker", "Starting Docker")
    
    # DB password
    sc(f"echo POSTGRES_PASSWORD=$(openssl rand -hex 16) | sudo tee {REMOTE}/.env.prod > /dev/null", "Generating DB password")

    # Nginx config via SCP
    print("\n▶ Uploading nginx.conf...")
    sftp = t.open_sftp_client()
    sftp.put(f"{LOCAL_PROJECT}/nginx.conf", "/tmp/nginx-foroshgram.conf")
    sftp.close()
    sc("sudo cp /tmp/nginx-foroshgram.conf /etc/nginx/sites-available/telegramorder.ir", "Installing nginx.conf")
    sc("sudo ln -sf /etc/nginx/sites-available/telegramorder.ir /etc/nginx/sites-enabled/ && sudo rm -f /etc/nginx/sites-enabled/default", "Enabling nginx site")

    # Build & start
    sc(f"cd {REMOTE} && sudo docker-compose -f docker-compose.yml up -d --build", "Building & starting containers", timeout=600)

    # Nginx restart (needs port 80 first)
    sc("sudo nginx -t && sudo systemctl restart nginx", "Restarting nginx")
    sc("sudo certbot --nginx -d telegramorder.ir -d www.telegramorder.ir --non-interactive --agree-tos -m admin@telegramorder.ir --redirect || echo 'SSL skipped'", "SSL cert")

    # Firewall
    sc("sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw --force enable", "Firewall")

    # systemd
    sc(f"echo '[Unit]' | sudo tee /etc/systemd/system/foroshgram.service > /dev/null", "systemd 1/4")
    sc(f"echo 'Description=Foroshgram' | sudo tee -a /etc/systemd/system/foroshgram.service > /dev/null", "systemd 2/4")
    sc(f"echo 'Requires=docker.service' | sudo tee -a /etc/systemd/system/foroshgram.service > /dev/null", "systemd 3/4")
    sc(f"printf '[Service]\\nType=oneshot\\nRemainAfterExit=yes\\nWorkingDirectory={REMOTE}\\nExecStart=/usr/bin/docker-compose -f docker-compose.yml up -d\\nExecStop=/usr/bin/docker-compose -f docker-compose.yml down\\n\\n[Install]\\nWantedBy=multi-user.target\\n' | sudo tee /etc/systemd/system/foroshgram.service > /dev/null", "systemd final")
    sc("sudo systemctl daemon-reload && sudo systemctl enable foroshgram.service", "Enabling systemd")

    # Verify
    sc("docker ps --filter name=foroshgram --format 'table {{.Names}}\\t{{.Status}}'", "Final check")

    print("\n" + "="*60)
    print("🎉 DEPLOYMENT COMPLETE!")
    print("="*60)
    print("Website: https://telegramorder.ir")
    print("Bot: @dasttiarfrooshbot")
    print("\n⚠️ Manual steps:")
    print(f"  1. ssh {USERNAME}@{TARGET_HOST}")
    print(f"  2. sudo nano {REMOTE}/telegram_order_website/.env.production  → change ADMIN_PASSWORD")
    print(f"  3. sudo nano {REMOTE}/telegram_order_bot/.env  → set PROXY_URL if needed")
    print(f"  4. sudo systemctl restart foroshgram")
    print(f"  5. docker logs -f foroshgram_bot")

    t.close()

if __name__ == '__main__':
    main()