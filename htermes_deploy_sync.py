#!/usr/bin/env python3
"""Foroshgram — smart sync of changed files to VPS + restart bot"""
import paramiko, socks, time, os, sys, hashlib, posixpath

LOCAL_ROOT = 'T:/dars/projects/telegram/Telegramorderbot'
REMOTE_ROOT = '/opt/foroshgram'
KEY_FILE = 'C:/s/ar-me-privatekey.pem'
VPS_HOST = '185.204.168.57'
SSH_USER = 'ubuntu'

EXCLUDE_DIRS = {'.git', '__pycache__', 'venv', '.turbo', 'node_modules', '.next'}
EXCLUDE_FILES = {'.gitkeep', '.env', '.env.production', '.env.example', '.gitignore', '.dockerignore'}

def should_skip(name):
    if name in EXCLUDE_FILES: return True
    for s in ('.pyc', '.db', '.db-shm', '.db-wal', '.pyo', '.pem', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.woff', '.woff2', '.ttf', '.eot', '.map', '.lock'):
        if name.endswith(s) and len(s) > 0: return True
    dirs_to_skip = ('node_modules', '.git', '__pycache__', '.next', '.turbo', '.cache', 'public/favicon.svg', 'public/sql-wasm.wasm')
    return False

def connect():
    sock = socks.socksocket()
    sock.settimeout(30)
    sock.set_proxy(socks.SOCKS5, '127.0.0.1', 10808)
    sock.connect((VPS_HOST, 22))
    t = paramiko.Transport(sock)
    t.start_client()
    t.auth_publickey(SSH_USER, paramiko.RSAKey.from_private_key_file(KEY_FILE))
    return t

def run(t, cmd, timeout=60):
    ch = t.open_session(); ch.settimeout(timeout); ch.exec_command(cmd)
    out = b''
    while not ch.exit_status_ready():
        time.sleep(0.3)
        if ch.recv_ready(): out += ch.recv(8192)
    if ch.recv_ready(): out += ch.recv(8192)
    ec = ch.recv_exit_status()
    ch.close()
    return out.decode('utf-8', errors='replace'), ec

def ensure_dir(sftp, path):
    parts = path.strip('/').split('/')
    cur = ''
    for p in parts:
        if not p: continue
        cur += '/' + p
        try: sftp.stat(cur)
        except: sftp.mkdir(cur)

def main():
    print("Connecting...")
    t = connect()
    sftp = t.open_sftp_client()
    print("Connected!")

    # 1. Collect server checksums for telegram_order_bot (excluding noise)
    print("Reading server file checksums...")
    out, _ = run(t, 'find /opt/foroshgram/telegram_order_bot -type f ! -name "*.pyc" ! -path "*/__pycache__/*" ! -name ".env*" -exec md5sum {} \\; 2>/dev/null')
    server_bot = {}
    for line in out.strip().split('\n'):
        if not line.strip(): continue
        parts = line.split(None, 1)
        if len(parts) == 2: server_bot[parts[1]] = parts[0]
    print(f"  {len(server_bot)} files on server (telegram_order_bot)")

    # docker-compose.yml at root
    out, _ = run(t, 'md5sum /opt/foroshgram/docker-compose.yml 2>/dev/null')
    server_root = {}
    for line in out.strip().split('\n'):
        if not line.strip(): continue
        parts = line.split(None, 1)
        if len(parts) == 2: server_root[parts[1]] = parts[0]
    print(f"  root files: {list(server_root.keys())}")

    # 2. Walk local telegram_order_bot and find changed/new
    to_sync = []
    bot_root = os.path.join(LOCAL_ROOT, 'telegram_order_bot')
    for dirpath, dirnames, filenames in os.walk(bot_root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith('.')]
        for f in filenames:
            if f in EXCLUDE_FILES or f.endswith(('.pyc', '.db', '.db-shm', '.db-wal', '.pyo', '.lock')):
                continue
            local_path = os.path.join(dirpath, f)
            rel = os.path.relpath(local_path, LOCAL_ROOT).replace('\\', '/')
            remote_key = rel
            with open(local_path, 'rb') as fh:
                local_md5 = hashlib.md5(fh.read()).hexdigest()
            server_md5 = server_bot.get(remote_key)
            if server_md5 is None:
                print(f"  NEW: {rel}")
                to_sync.append(rel)
            elif server_md5 != local_md5:
                print(f"  CHANGED: {rel}")
                to_sync.append(rel)

    # Check docker-compose.yml
    dc_path = os.path.join(LOCAL_ROOT, 'docker-compose.yml')
    with open(dc_path, 'rb') as fh:
        dc_md5 = hashlib.md5(fh.read()).hexdigest()
    if server_root.get('/opt/foroshgram/docker-compose.yml', '') != dc_md5:
        print(f"  CHANGED: docker-compose.yml")
        to_sync.append('docker-compose.yml')

    if not to_sync:
        print("\n✅ No files to sync — everything is already up to date!")
        sftp.close()
        t.close()
        return

    print(f"\nSyncing {len(to_sync)} files...")
    for rel in to_sync:
        if rel == 'docker-compose.yml':
            local_path = os.path.join(LOCAL_ROOT, 'docker-compose.yml')
        else:
            local_path = os.path.join(LOCAL_ROOT, rel)
        remote_path = posixpath.join(REMOTE_ROOT, rel)
        try:
            ensure_dir(sftp, os.path.dirname(remote_path))
            sftp.put(local_path, remote_path)
        except Exception as e:
            print(f"  FAILED: {rel}: {e}")

    sftp.close()
    print("Sync done!")

    # 3. Restart bot
    print("\nRestarting bot container...")
    out, ec = run(t, 'docker restart foroshgram_bot 2>&1')
    print(f"  {out.strip()} (exit={ec})")

    time.sleep(2)
    out, ec = run(t, 'docker ps --filter name=foroshgram --format "table {{.Names}}\t{{.Status}}" 2>&1')
    print(f"\nContainer status:\n{out}")

    # 4. Check if docker-compose.yml changed — need rebuild
    if 'docker-compose.yml' in to_sync:
        print("\n📦 docker-compose.yml changed — rebuilding website and bot...")
        out, ec = run(t, 'cd /opt/foroshgram && docker-compose up -d --build website bot 2>&1', timeout=300)
        print(f"  Rebuild exit={ec}")
        print(out[:1000] if len(out) > 1000 else out)

    # 5. Bot logs
    time.sleep(2)
    out, ec = run(t, 'docker logs --tail 8 foroshgram_bot 2>&1')
    print(f"\nBot logs (last 8):\n{out}")

    t.close()
    print("\n🎉 Deploy complete!")

if __name__ == '__main__':
    main()
