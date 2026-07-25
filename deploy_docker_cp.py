"""Deploy uploaded files from /tmp/foroshgram_handlers to container via paramiko+SOCKS."""
import paramiko, socks, os, base64

HOST = '185.204.168.57'
USER = 'ubuntu'
KEY = 'C:/s/ar-me-privatekey.pem'
REMOTE_TMP = '/tmp/foroshgram_handlers'

# Map basename → container destination
FILES = {
    'start.py': '/app/handlers/',
    'menu.py': '/app/handlers/',
    'forward_products.py': '/app/handlers/',
    'seller_registration.py': '/app/handlers/',
    'order.py': '/app/handlers/',
    'cart.py': '/app/handlers/',
    'seller_panel.py': '/app/handlers/',
    'search.py': '/app/handlers/',
    'support.py': '/app/handlers/',
    'help.py': '/app/handlers/',
    'conversations.py': '/app/handlers/',
    'wishlist.py': '/app/handlers/',
    'common.py': '/app/handlers/',
    'discount.py': '/app/handlers/',
    'admin_approval.py': '/app/handlers/',
    'panel.py': '/app/handlers/admin/',
    'products.py': '/app/handlers/admin/',
    'shops.py': '/app/handlers/admin/',
    'categories.py': '/app/handlers/admin/',
    'orders.py': '/app/handlers/admin/',
    'notification_service.py': '/app/services/',
    'order_service.py': '/app/services/',
    'abandoned_cart.py': '/app/services/',
    'event_listeners.py': '/app/services/',
    'restock.py': '/app/services/',
}

sock = socks.socksocket()
sock.set_proxy(socks.SOCKS5, '127.0.0.1', 10808)
sock.settimeout(30)
sock.connect((HOST, 22))

key = paramiko.RSAKey.from_private_key_file(KEY)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, pkey=key, sock=sock)

# docker cp each file
cmds = [f'docker cp {REMOTE_TMP}/{fname} foroshgram_bot:{dest}{fname}'
        for fname, dest in FILES.items()]
cmds.append('docker exec --user root foroshgram_bot python -m py_compile /app/handlers/start.py')
cmds.append('docker exec --user root foroshgram_bot python -m py_compile /app/handlers/menu.py')
cmds.append('docker restart foroshgram_bot && echo "Restarted"')

full_cmd = ' && '.join(cmds)
print("Running docker cp + verify + restart...")
stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=120)
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err:
    print("STDERR:", err[:500])
ssh.close()
print("Done!")
