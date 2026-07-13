"""Deploy changed files to VPS via SOCKS5 proxy"""
import os
import paramiko
import socks  # PySocks

# SOCKS proxy
SOCKS_HOST = '127.0.0.1'
SOCKS_PORT = 10808
VPS_HOST = '185.204.168.57'
VPS_USER = 'root'
VPS_KEY = r'C:\s\ar-me-privatekey.pem'
BASE = r'T:\dars\projects\telegram\Telegramorderbot\telegram_order_bot'
REMOTE = '/opt/foroshgram/telegram_order_bot'

# Files to upload
FILES = [
    'utils/crypto.py',
    'utils/tg_helpers.py',
    'database/models.py',
    'handlers/order.py',
    'handlers/seller_panel.py',
    'handlers/seller_registration.py',
    'services/order_service.py',
]

def main():
    sock = socks.socksocket()
    sock.set_proxy(socks.SOCKS5, SOCKS_HOST, SOCKS_PORT)
    sock.connect((VPS_HOST, 22))
    
    key = paramiko.RSAKey.from_private_key_file(VPS_KEY)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VPS_HOST, username=VPS_USER, pkey=key, sock=sock)
    
    sftp = ssh.open_sftp()
    for f in FILES:
        local = os.path.join(BASE, f.replace('/', os.sep))
        remote = f"{REMOTE}/{f}"
        # Ensure remote dir exists
        remote_dir = os.path.dirname(remote)
        ssh.exec_command(f'mkdir -p {remote_dir}')
        
        sftp.put(local, remote)
        print(f'  ✓ {f}')
    sftp.close()
    
    # Restart bot
    print('\nRestarting bot container...')
    stdin, stdout, stderr = ssh.exec_command('cd /opt/foroshgram && docker restart foroshgram_bot')
    print(stdout.read().decode().strip())
    
    ssh.close()
    print('\nDone!')
