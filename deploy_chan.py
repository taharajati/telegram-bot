import paramiko
import socks
import os
import sys
import time
import select

sock = socks.socksocket()
sock.set_proxy(socks.SOCKS5, '127.0.0.1', 10808)
sock.settimeout(60)
sock.connect(('185.204.168.57', 22))

key = paramiko.RSAKey.from_private_key_file(r'C:\s\ar-me-privatekey.pem')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('185.204.168.57', username='root', pkey=key, sock=sock)

# Ensure we have a working transport
transport = ssh.get_transport()
if not transport or not transport.is_active():
    print("ERROR: Transport not active")
    sys.exit(1)

BASE = r'T:\dars\projects\telegram\Telegramorderbot\telegram_order_bot'

FILES = [
    'handlers/seller_panel.py',
    'handlers/seller_registration.py',
    'handlers/order.py',
    'services/order_service.py',
    'utils/crypto.py',
    'utils/tg_helpers.py',
    'database/models.py',
    'main.py',
]

def upload_file(local_path, remote_path):
    """Upload file using paramiko channel with stdin.write"""
    with open(local_path, 'rb') as f:
        data = f.read()
    
    # Get remote dir
    rdir = os.path.dirname(remote_path)
    
    # Open channel
    chan = transport.open_session()
    chan.exec_command(f'mkdir -p {rdir}')
    chan.recv_exit_status()
    chan.close()
    
    # Use cat to write file
    chan = transport.open_session()
    chan.exec_command(f'cat > {remote_path}')
    
    # Write data in chunks via stdin
    chunk_size = 4096
    offset = 0
    while offset < len(data):
        end = min(offset + chunk_size, len(data))
        chan.sendall(data[offset:end])
        offset = end
    
    chan.shutdown_write()
    chan.recv_exit_status()
    chan.close()
    
    # Verify
    chan = transport.open_session()
    chan.exec_command(f'wc -c < {remote_path}')
    size_str = chan.recv(1024).decode().strip()
    chan.recv_exit_status()
    chan.close()
    
    return int(size_str) if size_str.isdigit() else 0

for f in FILES:
    local = os.path.join(BASE, f.replace('/', os.sep))
    remote = f'/opt/foroshgram/telegram_order_bot/{f}'
    
    size = upload_file(local, remote)
    expected = os.path.getsize(local)
    
    if size == expected:
        print(f'  OK: {f} ({size} bytes)')
    else:
        print(f'  FAIL: {f} (got {size}, expected {expected})')

# Restart
chan = transport.open_session()
chan.exec_command('docker restart foroshgram_bot')
print('\n' + chan.recv(1024).decode().strip())
chan.recv_exit_status()
chan.close()

ssh.close()
print('Done!')
