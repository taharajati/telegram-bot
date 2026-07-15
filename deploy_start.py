"""Deploy the new start.py to VPS via SSH and docker cp."""
import sys, subprocess, base64

# Read local file
with open('T:/dars/projects/telegram/Telegramorderbot/telegram_order_bot/handlers/start.py', 'rb') as f:
    content = f.read()

# Encode as base64
encoded = base64.b64encode(content).decode()

# SSH command: write file, docker cp, restart
ssh_cmd = (
    f'python3 -c "import base64; f=open(\'/tmp/start.py\',\'wb\'); '
    f'f.write(base64.b64decode(\'{encoded}\')); f.close()" '
    f'&& docker cp /tmp/start.py foroshgram_bot:/app/handlers/start.py '
    f'&& docker exec --user root foroshgram_bot python -m py_compile /app/handlers/start.py '
    f'&& docker restart foroshgram_bot '
    f'&& echo DONE'
)

result = subprocess.run(
    ['python', 'C:/s/ssh-quick.py', ssh_cmd],
    capture_output=True, text=True, timeout=120
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr[:500] if result.stderr else "")
print("RC:", result.returncode)
