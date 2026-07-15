#!/usr/bin/env python3
"""Upload file to VPS by writing to remote /tmp via SSH exec, then moving.

This works around SFTP ENOENT issues by using a different approach."""
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

# Write to /tmp using heredoc
tmpfile = '/tmp/sr_upload_b64.txt'
cmd = f"cat > {tmpfile} << 'HEREDOC_END'\n{b64data}\nHEREDOC_END\npython3 -c \"import base64; d=open('{tmpfile}','r').read(); open('{remote}','wb').write(base64.b64decode(d)); print('OK',len(d))\" && rm {tmpfile}"
ch = t.open_session()
ch.settimeout(120)
ch.exec_command(cmd)
time.sleep(3)
out = ch.recv(16384).decode().strip()
print(out)
t.close()
