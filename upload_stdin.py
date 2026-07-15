#!/usr/bin/env python3
import socks, paramiko, sys, time, base64

local = sys.argv[1]
remote = sys.argv[2]

with open(local, 'rb') as f:
    b64data = base64.b64encode(f.read()).decode()

sock = socks.socksocket()
sock.settimeout(60)
sock.set_proxy(socks.SOCKS5, '127.0.0.1', 10808)
sock.connect(('185.204.168.57', 22))
t = paramiko.Transport(sock)
t.start_client()
t.auth_publickey('ubuntu', paramiko.RSAKey.from_private_key_file('C:/s/ar-me-privatekey.pem'))

ch = t.open_session()
ch.settimeout(60)
ch.exec_command(f"python3 -c 'import base64,sys; d=sys.stdin.read(); open(\"{remote}\",\"wb\").write(base64.b64decode(d)); print(len(d),\"bytes decoded\")'")
ch.send(b64data)
ch.shutdown_write()
time.sleep(2)
out = ch.recv(8192).decode().strip()
print(out)
t.close()
