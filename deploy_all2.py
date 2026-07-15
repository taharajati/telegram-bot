"""Upload all handler files to VPS via SFTP then docker cp."""
import sys, os, socks, paramiko, time

HOST = '185.204.168.57'
USER = 'ubuntu'
KEY = 'C:/s/ar-me-privatekey.pem'
SOCKS_HOST = '127.0.0.1'
SOCKS_PORT = 10808

LOCAL_BASE = 'T:/dars/projects/telegram/Telegramorderbot/telegram_order_bot'
REMOTE_TMP = '/tmp/foroshgram_handlers'

FILES = [
    'handlers/start.py',
    'handlers/seller_registration.py',
    'handlers/order.py',
    'handlers/cart.py',
    'handlers/seller_panel.py',
    'handlers/search.py',
    'handlers/menu.py',
    'handlers/support.py',
    'handlers/help.py',
    'handlers/conversations.py',
    'handlers/wishlist.py',
    'handlers/common.py',
    'handlers/discount.py',
    'handlers/forward_products.py',
    'handlers/admin/panel.py',
    'handlers/admin/products.py',
    'handlers/admin/shops.py',
    'handlers/admin/categories.py',
    'handlers/admin/orders.py',
    'handlers/admin_approval.py',
    'services/notification_service.py',
    'services/order_service.py',
    'services/abandoned_cart.py',
    'services/event_listeners.py',
    'services/restock.py',
]

# Connect
sock = socks.socksocket()
sock.settimeout(30)
sock.set_proxy(socks.SOCKS5, SOCKS_HOST, SOCKS_PORT)
sock.connect((HOST, 22))
t = paramiko.Transport(sock)
t.start_client()
t.auth_publickey(USER, paramiko.RSAKey.from_private_key_file(KEY))
sftp = paramiko.SFTPClient.from_transport(t)

# Make remote temp dir
try: sftp.mkdir(REMOTE_TMP)
except: pass

# Upload all files
for rel_path in FILES:
    local_path = os.path.join(LOCAL_BASE, rel_path)
    remote_path = f'{REMOTE_TMP}/{os.path.basename(rel_path)}'
    if not os.path.exists(local_path):
        print(f'SKIP {rel_path} - not found')
        continue
    with open(local_path, 'rb') as lf:
        with sftp.open(remote_path, 'wb') as rf:
            rf.write(lf.read())
    print(f'OK  {rel_path}')

sftp.close()
t.close()

print(f'\nUploaded to {REMOTE_TMP}. Now docker cp...')

# Now SSH in and docker cp each file
import subprocess

# Build docker cp commands
cmds = []
for rel_path in FILES:
    basename = os.path.basename(rel_path)
    # Determine destination path
    if rel_path.startswith('services/'):
        dest = f'/app/services/{basename}'
    elif rel_path.startswith('handlers/admin/'):
        dest = f'/app/handlers/admin/{basename}'
    elif rel_path.startswith('handlers/'):
        dest = f'/app/handlers/{basename}'
    # Check which subdirectory: handlers/admin/
    cmds.append(f'docker cp {REMOTE_TMP}/{basename} foroshgram_bot:{dest}')

# Run via SSH
ssh_script = ' && '.join(cmds)
ssh_script += ' && docker exec --user root foroshgram_bot python -m py_compile /app/handlers/start.py && echo "CompileOK" && docker restart foroshgram_bot && echo "Restarted"'

result = subprocess.run(
    ['python', 'C:/s/ssh-quick.py', ssh_script],
    capture_output=True, text=True, timeout=120
)
print(result.stdout)
if result.stderr:
    print("ERR:", result.stderr[:500])
