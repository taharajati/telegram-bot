import paramiko
import socks
import os
import time

sock = socks.socksocket()
sock.set_proxy(socks.SOCKS5, '127.0.0.1', 10808)
sock.settimeout(30)
sock.connect(('185.204.168.57', 22))

key = paramiko.RSAKey.from_private_key_file(r'C:\s\ar-me-privatekey.pem')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('185.204.168.57', username='root', pkey=key, sock=sock)

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

for f in FILES:
    local = os.path.join(BASE, f.replace('/', os.sep))
    remote = f'/opt/foroshgram/telegram_order_bot/{f}'
    
    with open(local, 'rb') as fh:
        data = fh.read()
    
    # Write via exec_command using a simple approach
    # Split content into lines, echo each line
    lines = data.decode('utf-8').split('\n')
    
    # Use a temp file approach with base64
    import base64
    b64 = base64.b64encode(data).decode()
    
    # Write b64 in chunks via multiple exec calls
    chunk_size = 10000
    chunks = [b64[i:i+chunk_size] for i in range(0, len(b64), chunk_size)]
    
    # Write to temp file
    stdin, stdout, stderr = ssh.exec_command(f'echo -n > /tmp/_deploy_b64')
    stdout.channel.recv_exit_status()
    
    for chunk in chunks:
        stdin, stdout, stderr = ssh.exec_command(f'echo -n {chunk} >> /tmp/_deploy_b64')
        stdout.channel.recv_exit_status()
    
    # Decode and write
    stdin, stdout, stderr = ssh.exec_command(f'mkdir -p {os.path.dirname(remote)} && base64 -d /tmp/_deploy_b64 > {remote} && rm -f /tmp/_deploy_b64 && echo OK_{f}')
    out = stdout.read().decode()
    stderr_out = stderr.read().decode()
    
    if 'OK_' in out:
        print(f'  OK: {f}')
    else:
        print(f'  FAIL: {f} - {stderr_out[:100]}')

# Restart bot
print('\nRestarting bot...')
stdin, stdout, stderr = ssh.exec_command('docker restart foroshgram_bot')
print(stdout.read().decode().strip())

ssh.close()
print('Done!')
