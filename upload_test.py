#!/usr/bin/env python3
"""Upload test_flow.py to VPS and docker cp to container."""
import base64, subprocess, sys, os

local_path = r"T:\dars\projects\telegram\Telegramorderbot\tests\test_flow.py"
vps_path = "/opt/foroshgram/tests/test_flow.py"

with open(local_path, 'rb') as f:
    data = base64.b64encode(f.read()).decode()

# Upload to VPS via base64 in 3000-char chunks (smaller for safety)
chunks = [data[i:i+3000] for i in range(0, len(data), 3000)]

# Split into payload files to avoid cmdline length issues
import tempfile
tmpdir = tempfile.mkdtemp()
part_files = []
for i, chunk in enumerate(chunks):
    pf = os.path.join(tmpdir, f"part_{i:03d}.b64")
    with open(pf, 'w') as f:
        f.write(chunk)
    part_files.append(pf)

# Upload each part
for i, pf in enumerate(part_files):
    with open(pf, 'r') as f:
        content = f.read().strip()
    mode = '>' if i == 0 else '>>'
    cmd = f"printf '%s' '{content}' {mode} /tmp/tf_b64.txt"
    r = subprocess.run(['python', 'C:/s/ssh-quick.py', cmd], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f"Part {i} failed: {r.stderr}")
        sys.exit(1)

print(f"Uploaded {len(chunks)} parts")

# Decode on VPS
decode_cmd = "base64 -d /tmp/tf_b64.txt > /opt/foroshgram/tests/test_flow.py && wc -c /opt/foroshgram/tests/test_flow.py"
r = subprocess.run(['python', 'C:/s/ssh-quick.py', decode_cmd], capture_output=True, text=True, timeout=30)
print(f"Decode: {r.stdout} {r.stderr}")

# docker cp into container
cp_cmd = "docker cp /opt/foroshgram/tests/test_flow.py foroshgram_bot:/app/tests/test_flow.py"
r = subprocess.run(['python', 'C:/s/ssh-quick.py', cp_cmd], capture_output=True, text=True, timeout=15)
print(f"Docker cp: {r.stdout} {r.stderr}")

# Verify in container
verify_cmd = "docker exec foroshgram_bot wc -l /app/tests/test_flow.py"
r = subprocess.run(['python', 'C:/s/ssh-quick.py', verify_cmd], capture_output=True, text=True, timeout=15)
print(f"Verify: {r.stdout} {r.stderr}")
