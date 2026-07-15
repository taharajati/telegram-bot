#!/usr/bin/env python3
import paramiko, socks, sys, time

sock = socks.socksocket()
sock.settimeout(30)
sock.set_proxy(socks.SOCKS5, '127.0.0.1', 10808)
sock.connect(('185.204.168.57', 22))
t = paramiko.Transport(sock)
t.start_client()
t.auth_publickey('ubuntu', paramiko.RSAKey.from_private_key_file('C:/s/ar-me-privatekey.pem'))
sftp = paramiko.SFTPClient.from_transport(t)
with open(sys.argv[1], 'rb') as lf:
    with sftp.open(sys.argv[2], 'wb') as f:
        f.write(lf.read())
        print(f'Wrote {lf.tell()} bytes')
sftp.close()
t.close()
