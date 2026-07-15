#!/usr/bin/env python3
import subprocess, base64, sys

local = sys.argv[1]
remote = sys.argv[2]

with open(local, 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()

# Write base64 to a temp file first, then scp it
with open('/tmp/seller_reg_b64.txt', 'w') as f:
    f.write(b64)

# Use ssh-quick
import socks, paramiko, time

sock = socks.socksocket()
sock.settimeout(30)
sock.set_proxy(socks.SOCKS5, '127.0.0.1', 10808)
sock.connect(('185.204.168.57', 22))
t = paramiko.Transport(sock)
t.start_client()
t.auth_publickey('ubuntu', paramiko.RSAKey.from_private_key_file('C:/s/ar-me-privatekey.pem'))

# Create a python script that reads from stdin and writes to file
# Upload the file content via channel stdin
ch = t.open_session()
ch.exec_command(f"python3 -c 'import base64, sys; d = sys.stdin.read(); open(\"{remote}\",\"wb\").write(base64.b64decode(d)); print(\"OK\")'")
ch.send(b64.encode() + b'\n')
time.sleep(2)
output = ch.recv(8192).decode().strip()
print(f"Result: {output}")
ch.close()
t.close()
