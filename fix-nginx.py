#!/usr/bin/env python3
"""Fix nginx and enable site"""
import paramiko
import socks
import sys
import time

PROXY_HOST = '127.0.0.1'
PROXY_PORT = 10808
TARGET_HOST = '185.204.168.57'
USERNAME = 'ubuntu'
KEY_FILE = 'C:/s/ar-me-privatekey.pem'

def connect():
    sock = socks.socksocket()
    sock.settimeout(30)
    sock.set_proxy(socks.SOCKS5, PROXY_HOST, PROXY_PORT)
    sock.connect((TARGET_HOST, 22))
    t = paramiko.Transport(sock)
    t.start_client()
    t.auth_publickey(USERNAME, paramiko.RSAKey.from_private_key_file(KEY_FILE))
    return t

def run(t, cmd, desc="", timeout=60):
    ch = t.open_session()
    ch.settimeout(timeout)
    ch.exec_command(cmd)
    out = b''
    while True:
        if ch.recv_ready(): out += ch.recv(4096)
        if ch.exit_status_ready(): break
        time.sleep(0.1)
    code = ch.recv_exit_status()
    ch.close()
    print(out.decode('utf-8', errors='replace'))
    if code == 0:
        print(f"  ✅ {desc}")
    else:
        print(f"  ⚠️ exit={code} {desc}")
    return code

def main():
    t = connect()
    print("[OK] Connected!\n")
    
    # Upload nginx config without SSL
    sftp = t.open_sftp_client()
    sftp.put('T:/dars/projects/telegram/Telegramorderbot/nginx-no-ssl.conf', '/tmp/nginx-no-ssl.conf')
    sftp.close()
    
    run(t, "sudo cp /tmp/nginx-no-ssl.conf /etc/nginx/sites-available/telegramorder.ir", "Installing nginx config (no SSL)")
    run(t, "sudo nginx -t && sudo systemctl restart nginx", "Restart nginx")
    run(t, "sudo systemctl status nginx --no-pager", "Nginx status")
    
    # Test via nginx
    run(t, "curl -s -o /dev/null -w '%{http_code}' http://localhost/", "Nginx HTTP check")
    
    t.close()
    print("\n✅ Nginx fixed!")

if __name__ == '__main__':
    main()