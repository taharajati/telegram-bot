import base64, os
files = [
    'telegram_order_website/src/lib/crypto.ts',
    'telegram_order_website/src/lib/rate-limiter.ts',
    'telegram_order_website/src/lib/auth.ts',
    'telegram_order_website/src/lib/csrf.ts',
    'telegram_order_website/src/app/api/auth/login/route.ts',
    'telegram_order_website/src/app/api/admin/toggle-shop/route.ts',
    'telegram_order_website/src/app/api/seller/toggle-product/route.ts',
]
for f in files:
    local_path = os.path.join(os.getcwd(), f)
    with open(local_path, 'rb') as fh:
        data = base64.b64encode(fh.read()).decode()
    remote = '/opt/foroshgram/' + f
    cmd = f'echo {data} | base64 -d > {remote}'
    print(f'Deploying {f}...')
    ret = os.system(f'python C:/s/ssh-quick.py "{cmd}"')
    if ret == 0:
        print(f'  ✓ {f}')
    else:
        print(f'  ✗ {f} (exit {ret})')
print('\nDone!')
