"""Deploy all changed files and run migration on VPS."""
import os, sys

# Add Hermes python libs to path
sys.path.insert(0, '/c/s')

import paramiko, socks

VPS_HOST = '185.204.168.57'
VPS_USER = 'ubuntu'
KEY_PATH = '/c/s/ar-me-privatekey.pem'
LOCAL = r'T:/dars/projects/telegram/Telegramorderbot'
REMOTE = '/opt/foroshgram'

sock = socks.socksocket()
sock.settimeout(15)
sock.set_proxy(socks.SOCKS5, '127.0.0.1', 10808)
sock.connect((VPS_HOST, 22))
t = paramiko.Transport(sock)
t.start_client()
t.auth_publickey(VPS_USER, paramiko.RSAKey.from_private_key_file('/c/s/ar-me-privatekey.pem'))
sftp = paramiko.SFTPClient.from_transport(t)

count = 0
essential_files = [
    'telegram_order_bot/services/payment.py',
    'telegram_order_bot/services/order_service.py',
    'telegram_order_bot/handlers/order.py',
    'telegram_order_bot/main.py',
    'telegram_order_bot/database/migrate_v2.3.py', 
]
for rel in essential_files:
    lp = os.path.join(LOCAL, rel)
    rp = os.path.join(REMOTE, rel).replace('\\', '/')
    sftp.put(lp, rp)
    count += 1
    print(f"  [{count}] {rel}")

sftp.close()

# SSH in to run migration + restart
channel = t.open_session()
channel.get_pty()
channel.exec_command(
    'cd /opt/foroshgram && '
    'docker exec foroshgram_postgres psql -U foroshgram -c '
    '"ALTER TABLE products ADD CONSTRAINT IF NOT EXISTS products_stock_check CHECK (reserved_stock >= 0 AND reserved_stock <= stock) NOT VALID;"'
    ' 2>&1 && '
    'docker compose restart bot 2>&1'
)
stdout = channel.makefile('r', -1)
output = stdout.read().strip()
channel.close()

print("=" * 40)
print("PSQL + RESTART OUTPUT:")
print(output or "(empty)")
print("=" * 40)

# verify
channel2 = t.open_session()
channel2.get_pty()
channel2.exec_command('docker compose ps --status running 2>&1 | head -5')
print(channel2.makefile('r', -1).read().strip())
channel2.close()

t.close()
print("\nDONE")
