import paramiko, socks, time, os

PROXY_HOST = '127.0.0.1'
PROXY_PORT = 10808
VPS_HOST = '185.204.168.57'
SSH_USER = 'ubuntu'
KEY_FILE = 'C:/s/ar-me-privatekey.pem'
REMOTE_DIR = '/opt/foroshgram/telegram_order_bot'
LOCAL_DIR = 'T:/dars/projects/telegram/Telegramorderbot/telegram_order_bot'

def connect():
    sock = socks.socksocket()
    sock.settimeout(30)
    sock.set_proxy(socks.SOCKS5, PROXY_HOST, PROXY_PORT)
    sock.connect((VPS_HOST, 22))
    t = paramiko.Transport(sock)
    t.start_client()
    t.auth_publickey(SSH_USER, paramiko.RSAKey.from_private_key_file(KEY_FILE))
    return t

def run_cmd(t, cmd):
    ch = t.open_session()
    ch.exec_command(cmd)
    out = b''
    while True:
        if ch.recv_ready(): out += ch.recv(8192)
        if ch.recv_stderr_ready(): out += ch.recv_stderr(8192)
        if ch.exit_status_ready(): break
        time.sleep(0.3)
    ec = ch.recv_exit_status()
    ch.close()
    return out.decode(), ec

# 1. Sync files via SFTP
print("Syncing files...")
t = connect()
sftp = t.open_sftp_client()
for root, dirs, files in os.walk(LOCAL_DIR):
    dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', 'venv', 'instance')]
    for f in files:
        if f.endswith(('.pyc', '.db', '.db-shm', '.db-wal')):
            continue
        local = os.path.join(root, f)
        rel = os.path.relpath(local, LOCAL_DIR).replace('\\', '/')
        remote = REMOTE_DIR + '/' + rel
        try:
            sftp.put(local, remote)
            print(f"  ✓ {rel}")
        except Exception as e:
            print(f"  ✗ {rel}: {e}")
sftp.close()
t.close()
print("SFTP done!")

# 2. Restart bot container
print("Restarting bot...")
t = connect()
out, ec = run_cmd(t, 'docker restart foroshgram_bot 2>&1')
print(f"Restart: {out.strip()} (exit={ec})")

# 3. Check logs
time.sleep(3)
out, ec = run_cmd(t, 'docker logs --tail 5 foroshgram_bot 2>&1')
print(f"Logs:\n{out}")
t.close()
print("Deploy complete!")
