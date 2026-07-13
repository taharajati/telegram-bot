"""Deploy website security changes to VPS"""
import os
import paramiko
import socks  # PySocks

# SOCKS proxy
SOCKS_HOST = '127.0.0.1'
SOCKS_PORT = 10808
VPS_HOST = '185.204.168.57'
VPS_USER = 'root'
VPS_KEY = r'C:\s\ar-me-privatekey.pem'
BASE = r'T:\dars\projects\telegram\Telegramorderbot\telegram_order_website'
REMOTE = '/opt/foroshgram/telegram_order_website'

# Files to upload
FILES = [
    'src/lib/crypto.ts',
    'src/lib/rate-limiter.ts',
    'src/lib/auth.ts',
    'src/lib/csrf.ts',
    'src/app/api/auth/login/route.ts',
    'src/app/api/admin/toggle-shop/route.ts',
    'src/app/api/seller/toggle-product/route.ts',
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
        remote_dir = os.path.dirname(remote)
        ssh.exec_command(f'mkdir -p {remote_dir}')
        
        sftp.put(local, remote)
        print(f'  ✓ {f}')
    sftp.close()
    
    # Rebuild and restart website
    print('\nRebuilding and restarting website...')
    stdin, stdout, stderr = ssh.exec_command('cd /opt/foroshgram && docker compose build website && docker compose up -d website')
    print(stdout.read().decode().strip())
    err = stderr.read().decode().strip()
    if err:
        print(f'STDERR: {err}')
    
    ssh.close()
    print('\nDone!')

if __name__ == '__main__':
    main()