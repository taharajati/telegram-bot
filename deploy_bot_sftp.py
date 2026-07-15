import paramiko
import socks
import os

SOCKS_HOST = '127.0.0.1'
SOCKS_PORT = 10808
VPS_HOST = '185.204.168.57'
VPS_USER = 'root'
VPS_KEY = r'C:\s\ar-me-privatekey.pem'
LOCAL_BASE = r'T:\dars\projects\telegram\Telegramorderbot'
REMOTE_BASE = '/opt/foroshgram'

FILES = [
    ('telegram_order_bot/handlers/seller_panel.py', '/opt/foroshgram/telegram_order_bot/handlers/seller_panel.py'),
    ('telegram_order_bot/handlers/seller_registration.py', '/opt/foroshgram/telegram_order_bot/handlers/seller_registration.py'),
    ('telegram_order_bot/handlers/order.py', '/opt/foroshgram/telegram_order_bot/handlers/order.py'),
    ('telegram_order_bot/services/order_service.py', '/opt/foroshgram/telegram_order_bot/services/order_service.py'),
    ('telegram_order_bot/utils/crypto.py', '/opt/foroshgram/telegram_order_bot/utils/crypto.py'),
    ('telegram_order_bot/utils/tg_helpers.py', '/opt/foroshgram/telegram_order_bot/utils/tg_helpers.py'),
    ('telegram_order_bot/database/models.py', '/opt/foroshgram/telegram_order_bot/database/models.py'),
    ('telegram_order_bot/main.py', '/opt/foroshgram/telegram_order_bot/main.py'),
]

sock = socks.socksocket()
sock.set_proxy(socks.SOCKS5, SOCKS_HOST, SOCKS_PORT)
sock.settimeout(30)
sock.connect((VPS_HOST, 22))

key = paramiko.RSAKey.from_private_key_file(VPS_KEY)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_HOST, username=VPS_USER, pkey=key, sock=sock)

sftp = ssh.open_sftp()
for local_rel, remote_path in FILES:
    local_abs = os.path.join(LOCAL_BASE, local_rel)
    remote_dir = os.path.dirname(remote_path)
    ssh.exec_command(f'mkdir -p {remote_dir}')
    sftp.put(local_abs, remote_path)
    print(f'  OK: {local_rel}')
sftp.close()

# Restart bot
print('\nRestarting bot...')
stdin, stdout, stderr = ssh.exec_command('cd /opt/foroshgram && docker restart foroshgram_bot')
print(stdout.read().decode().strip())

ssh.close()
print('\nDone!')
