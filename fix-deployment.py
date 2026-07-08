#!/usr/bin/env python3
"""Fix docker permissions and verify deployment"""
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
    
    # Fix docker group
    run(t, "sudo usermod -aG docker ubuntu", "Adding ubuntu to docker group")
    
    # Check if containers are running
    run(t, "sudo docker ps --filter name=foroshgram --format 'table {{.Names}}\\t{{.Status}}'", "Checking containers")
    
    # Check docker-compose status
    run(t, "cd /opt/foroshgram && sudo docker-compose -f docker-compose.yml ps", "docker-compose status")
    
    # If containers not running, start them
    run(t, "cd /opt/foroshgram && sudo docker-compose -f docker-compose.yml up -d", "Starting containers")
    
    # Check again
    run(t, "sudo docker ps --filter name=foroshgram --format 'table {{.Names}}\\t{{.Status}}'", "Final container check")
    
    # Check logs
    run(t, "sudo docker logs foroshgram_bot --tail 20", "Bot logs")
    run(t, "sudo docker logs foroshgram_website --tail 20", "Website logs")
    run(t, "sudo docker logs foroshgram_postgres --tail 10", "Postgres logs")
    
    # Test website
    run(t, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/", "Website HTTP check")
    
    # Restart nginx
    run(t, "sudo nginx -t && sudo systemctl restart nginx", "Restart nginx")
    
    # Try SSL if not done
    run(t, "sudo certbot --nginx -d telegramorder.ir -d www.telegramorder.ir --non-interactive --agree-tos -m admin@telegramorder.ir --redirect || echo 'SSL failed'", "SSL cert")
    
    t.close()
    print("\n✅ Fix complete!")

if __name__ == '__main__':
    main()