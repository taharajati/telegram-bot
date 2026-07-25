"""Generate 10 themed variants of promo-demo.html for Instagram posts.
Each variant has different colors, phone styling, and accent animations.
"""
import re, os, json

BASE = "T:/dars/projects/telegram/Telegramorderbot/promo-demo.html"
OUT_DIR = "T:/dars/projects/telegram/Telegramorderbot/promo_variants"

os.makedirs(OUT_DIR, exist_ok=True)

with open(BASE, "r", encoding="utf-8") as f:
    html = f.read()

# ─── 10 themes ───────────────────────────────────────────────
THEMES = [
    {
        "id": "01",
        "name": "بنفش تیره",
        "vars": {
            "--bg": "#0a0a10", "--surface": "#13131e", "--surface2": "#1d1d30", "--surface3": "#282840",
            "--border": "#262640", "--border2": "#363660", "--text": "#ededf5", "--text2": "#9a9ab5", "--text3": "#5c5c78",
            "--accent": "#6c5ce7", "--accent2": "#a29bfe", "--green": "#00d2a0",
            "--greenBg": "rgba(0,210,160,.12)", "--blue": "#0984e3", "--blueBg": "rgba(9,132,227,.12)",
            "--orange": "#fdcb6e", "--orangeBg": "rgba(253,203,110,.12)", "--pink": "#fd79a8", "--red": "#e74c3c",
            "--glow": "rgba(108,92,231,.15)", "--shadow": "0 8px 80px rgba(0,0,0,.6)",
            "--custBg": "#1e1e30",
        },
        "radius": "32px", "notch_visible": True,
        "bg1": "radial-gradient(ellipse at 30% 40%, rgba(108,92,231,.06) 0%, transparent 60%)",
        "bg2": "radial-gradient(ellipse at 70% 60%, rgba(0,210,160,.04) 0%, transparent 50%)",
        "logo_grad": "linear-gradient(135deg,var(--accent),#8b5cf6,var(--pink))",
        "tagline": "فروشگاه اختصاصی تو در تلگرام",
    },
    {
        "id": "02",
        "name": "روشن",
        "vars": {
            "--bg": "#e8e8f2", "--surface": "#ffffff", "--surface2": "#f2f2f8", "--surface3": "#eaeaf4",
            "--border": "#dcdce8", "--border2": "#ccccdc", "--text": "#181828", "--text2": "#4a4a66", "--text3": "#6e6e8a",
            "--accent": "#6c5ce7", "--accent2": "#8b7cf7", "--green": "#00b884",
            "--greenBg": "rgba(0,184,132,.08)", "--blue": "#0984e3", "--blueBg": "rgba(9,132,227,.06)",
            "--orange": "#d46950", "--orangeBg": "rgba(212,105,80,.08)", "--pink": "#e84393", "--red": "#d63031",
            "--glow": "rgba(108,92,231,.06)", "--shadow": "0 12px 90px rgba(0,0,0,.18)",
            "--custBg": "#e4e4ee",
        },
        "radius": "28px", "notch_visible": True,
        "bg1": "radial-gradient(ellipse at 30% 40%, rgba(108,92,231,.04) 0%, transparent 60%)",
        "bg2": "radial-gradient(ellipse at 70% 60%, rgba(0,184,132,.04) 0%, transparent 50%)",
        "logo_grad": "linear-gradient(135deg,#6c5ce7,#a29bfe,#fd79a8)",
        "tagline": "فروشگاه اختصاصی تو در تلگرام",
    },
    {
        "id": "03",
        "name": "آبی نیمه‌شب",
        "vars": {
            "--bg": "#070b1a", "--surface": "#0d1330", "--surface2": "#141d40", "--surface3": "#1a2650",
            "--border": "#1d2d55", "--border2": "#2a3d70", "--text": "#e8ecff", "--text2": "#8899cc", "--text3": "#556699",
            "--accent": "#2d7dd2", "--accent2": "#5ba3f0", "--green": "#00d4aa",
            "--greenBg": "rgba(0,212,170,.1)", "--blue": "#4a9ff5", "--blueBg": "rgba(74,159,245,.1)",
            "--orange": "#ffb347", "--orangeBg": "rgba(255,179,71,.1)", "--pink": "#ff6b9d", "--red": "#ff4757",
            "--glow": "rgba(45,125,210,.12)", "--shadow": "0 8px 80px rgba(0,0,0,.7)",
            "--custBg": "#1a2040",
        },
        "radius": "30px", "notch_visible": True,
        "bg1": "radial-gradient(ellipse at 30% 40%, rgba(45,125,210,.06) 0%, transparent 60%)",
        "bg2": "radial-gradient(ellipse at 70% 60%, rgba(0,212,170,.03) 0%, transparent 50%)",
        "logo_grad": "linear-gradient(135deg,#2d7dd2,#4a9ff5,#00d4aa)",
        "tagline": "فروشگاه اختصاصی تو در تلگرام",
    },
    {
        "id": "04",
        "name": "نئون سایبر",
        "vars": {
            "--bg": "#0a0a05", "--surface": "#11110a", "--surface2": "#1a1a0e", "--surface3": "#252515",
            "--border": "#2a3a10", "--border2": "#3a5a18", "--text": "#d0ffc0", "--text2": "#8ae870", "--text3": "#4a8a30",
            "--accent": "#39ff14", "--accent2": "#70ff50", "--green": "#00ff88",
            "--greenBg": "rgba(0,255,136,.08)", "--blue": "#00d4ff", "--blueBg": "rgba(0,212,255,.08)",
            "--orange": "#ffcc00", "--orangeBg": "rgba(255,204,0,.08)", "--pink": "#ff00aa", "--red": "#ff0033",
            "--glow": "rgba(57,255,20,.12)", "--shadow": "0 8px 80px rgba(57,255,20,.08)",
            "--custBg": "#1a1a0e",
        },
        "radius": "4px", "notch_visible": False,
        "bg1": "radial-gradient(ellipse at 30% 40%, rgba(57,255,20,.04) 0%, transparent 60%)",
        "bg2": "radial-gradient(ellipse at 70% 60%, rgba(0,212,255,.04) 0%, transparent 50%)",
        "logo_grad": "linear-gradient(135deg,#39ff14,#00d4ff,#ff00aa)",
        "tagline": "فروشگاه اختصاصی تو در تلگرام",
    },
    {
        "id": "05",
        "name": "رز گلد",
        "vars": {
            "--bg": "#0f080d", "--surface": "#1a1016", "--surface2": "#25181f", "--surface3": "#301f28",
            "--border": "#402530", "--border2": "#553040", "--text": "#f5e0e8", "--text2": "#d4a0b8", "--text3": "#9a6078",
            "--accent": "#e84393", "--accent2": "#fd79a8", "--green": "#00b894",
            "--greenBg": "rgba(0,184,148,.1)", "--blue": "#6c5ce7", "--blueBg": "rgba(108,92,231,.1)",
            "--orange": "#fdcb6e", "--orangeBg": "rgba(253,203,110,.1)", "--pink": "#fd79a8", "--red": "#d63031",
            "--glow": "rgba(232,67,147,.12)", "--shadow": "0 8px 80px rgba(232,67,147,.06)",
            "--custBg": "#281822",
        },
        "radius": "36px", "notch_visible": True,
        "bg1": "radial-gradient(ellipse at 30% 40%, rgba(232,67,147,.05) 0%, transparent 60%)",
        "bg2": "radial-gradient(ellipse at 70% 60%, rgba(253,203,110,.03) 0%, transparent 50%)",
        "logo_grad": "linear-gradient(135deg,#e84393,#fd79a8,#fdcb6e)",
        "tagline": "فروشگاه اختصاصی تو در تلگرام",
    },
    {
        "id": "06",
        "name": "سفید مینیمال",
        "vars": {
            "--bg": "#e2e2ea", "--surface": "#ffffff", "--surface2": "#f0f0f6", "--surface3": "#e6e6f0",
            "--border": "#d4d4e0", "--border2": "#c0c0d0", "--text": "#111122", "--text2": "#484862", "--text3": "#6c6c88",
            "--accent": "#333355", "--accent2": "#555577", "--green": "#008866",
            "--greenBg": "rgba(0,136,102,.06)", "--blue": "#2d6a9f", "--blueBg": "rgba(45,106,159,.06)",
            "--orange": "#b06830", "--orangeBg": "rgba(176,104,48,.06)", "--pink": "#aa3366", "--red": "#aa2244",
            "--glow": "rgba(51,51,85,.04)", "--shadow": "0 10px 70px rgba(0,0,0,.15)",
            "--custBg": "#dcdce6",
        },
        "radius": "24px", "notch_visible": False,
        "bg1": "none", "bg2": "none",
        "logo_grad": "linear-gradient(135deg,#333355,#555577,#9999aa)",
        "tagline": "فروشگاه اختصاصی تو در تلگرام",
    },
    {
        "id": "07",
        "name": "اقیانوس",
        "vars": {
            "--bg": "#020d1a", "--surface": "#061a2e", "--surface2": "#0a2642", "--surface3": "#0e3256",
            "--border": "#12406a", "--border2": "#165080", "--text": "#e0f0ff", "--text2": "#80c0e0", "--text3": "#4080a0",
            "--accent": "#00b4d8", "--accent2": "#48cae4", "--green": "#00e6a0",
            "--greenBg": "rgba(0,230,160,.08)", "--blue": "#0096c7", "--blueBg": "rgba(0,150,199,.08)",
            "--orange": "#ffb703", "--orangeBg": "rgba(255,183,3,.08)", "--pink": "#ff6b6b", "--red": "#e63946",
            "--glow": "rgba(0,180,216,.1)", "--shadow": "0 8px 80px rgba(0,180,216,.05)",
            "--custBg": "#0e2440",
        },
        "radius": "32px", "notch_visible": True,
        "bg1": "radial-gradient(ellipse at 30% 40%, rgba(0,180,216,.04) 0%, transparent 60%)",
        "bg2": "radial-gradient(ellipse at 70% 60%, rgba(0,230,160,.03) 0%, transparent 50%)",
        "logo_grad": "linear-gradient(135deg,#00b4d8,#48cae4,#00e6a0)",
        "tagline": "فروشگاه اختصاصی تو در تلگرام",
    },
    {
        "id": "08",
        "name": "کهربایی",
        "vars": {
            "--bg": "#0a0805", "--surface": "#161208", "--surface2": "#221c0e", "--surface3": "#2e2614",
            "--border": "#3e3418", "--border2": "#4e4420", "--text": "#f5e8c0", "--text2": "#d4b870", "--text3": "#a08040",
            "--accent": "#e8892e", "--accent2": "#f0a84e", "--green": "#9ad04a",
            "--greenBg": "rgba(154,208,74,.08)", "--blue": "#5890d0", "--blueBg": "rgba(88,144,208,.08)",
            "--orange": "#f0a030", "--orangeBg": "rgba(240,160,48,.1)", "--pink": "#e86070", "--red": "#d04030",
            "--glow": "rgba(232,137,46,.1)", "--shadow": "0 8px 80px rgba(232,137,46,.06)",
            "--custBg": "#1e1a0e",
        },
        "radius": "28px", "notch_visible": True,
        "bg1": "radial-gradient(ellipse at 30% 40%, rgba(232,137,46,.04) 0%, transparent 60%)",
        "bg2": "radial-gradient(ellipse at 70% 60%, rgba(154,208,74,.03) 0%, transparent 50%)",
        "logo_grad": "linear-gradient(135deg,#e8892e,#f0a84e,#9ad04a)",
        "tagline": "فروشگاه اختصاصی تو در تلگرام",
    },
    {
        "id": "09",
        "name": "کهکشانی",
        "vars": {
            "--bg": "#050010", "--surface": "#0c0020", "--surface2": "#140030", "--surface3": "#1c0040",
            "--border": "#280050", "--border2": "#340060", "--text": "#e8d0ff", "--text2": "#b888f0", "--text3": "#7850b0",
            "--accent": "#9b59b6", "--accent2": "#c084fc",
            "--green": "#2ecc71", "--greenBg": "rgba(46,204,113,.08)",
            "--blue": "#3498db", "--blueBg": "rgba(52,152,219,.08)",
            "--orange": "#f39c12", "--orangeBg": "rgba(243,156,18,.08)",
            "--pink": "#e84393", "--red": "#e74c3c",
            "--glow": "rgba(155,89,182,.12)", "--shadow": "0 8px 80px rgba(155,89,182,.08)",
            "--custBg": "#140030",
        },
        "radius": "30px", "notch_visible": True,
        "bg1": "radial-gradient(ellipse at 20% 30%, rgba(155,89,182,.06) 0%, transparent 50%), radial-gradient(ellipse at 80% 70%, rgba(52,152,219,.04) 0%, transparent 50%)",
        "bg2": "radial-gradient(ellipse at 50% 50%, rgba(46,204,113,.02) 0%, transparent 40%)",
        "logo_grad": "linear-gradient(135deg,#9b59b6,#c084fc,#3498db)",
        "tagline": "فروشگاه اختصاصی تو در تلگرام",
    },
    {
        "id": "10",
        "name": "کربن مشکی",
        "vars": {
            "--bg": "#060606", "--surface": "#0d0d0d", "--surface2": "#151515", "--surface3": "#1d1d1d",
            "--border": "#252525", "--border2": "#303030", "--text": "#d0d0d0", "--text2": "#808080", "--text3": "#505050",
            "--accent": "#e0e0e0", "--accent2": "#ffffff", "--green": "#00d2a0",
            "--greenBg": "rgba(0,210,160,.06)", "--blue": "#5080c0", "--blueBg": "rgba(80,128,192,.06)",
            "--orange": "#c0a050", "--orangeBg": "rgba(192,160,80,.06)", "--pink": "#c05080", "--red": "#c04040",
            "--glow": "rgba(255,255,255,.02)", "--shadow": "0 8px 80px rgba(0,0,0,.8)",
            "--custBg": "#151515",
        },
        "radius": "2px", "notch_visible": False,
        "bg1": "none", "bg2": "none",
        "logo_grad": "linear-gradient(135deg,#505050,#909090,#e0e0e0)",
        "tagline": "فروشگاه اختصاصی تو در تلگرام",
    },
]


def apply_theme(html, theme):
    """Replace CSS variables, phone radius, logo gradient, and other theme properties."""
    result = html

    # 1. Replace CSS custom properties in :root
    for key, val in theme["vars"].items():
        result = re.sub(rf'({key}\s*:\s*)[^;]+;', rf'\g<1>{val};', result)

    # 2. Phone border-radius — replace var(--radius) with actual value
    result = re.sub(r'border-radius:\s*var\(--radius\);', f'border-radius: {theme["radius"]};', result)

    # 3. Logo gradient
    result = re.sub(
        r'background:linear-gradient\(135deg,var\(--accent\),#8b5cf6,var\(--pink\)\)',
        f'background:{theme["logo_grad"]}', result)

    # 4. Tagline
    result = re.sub(r'<p>فروشگاه اختصاصی تو در تلگرام</p>', f'<p>{theme["tagline"]}</p>', result)

    # 5. Animated BG section — completely replace the body::before/after + @keyframes block.
    # The @keyframes bgDrift line is on a single line, so we can match it cleanly.
    bg_section_re = (
        r'/\* ── Animated BG ── \*/'
        r'[\s\S]*?'                # body::before, body::after { ... }
        r'@keyframes bgDrift [^\n]*'  # rest of the @keyframes line
    )
    result = re.sub(bg_section_re, '', result)

    # Now add the new BG section (after the body rule) if theme has gradients
    if theme["bg1"] != "none":
        bg_css = f'''  /* ── Animated BG ── */
  body::before, body::after {{
    content:''; position:fixed; top:-50%; left:-50%; width:200%; height:200%;
    pointer-events:none; z-index:0;
    background:{theme["bg1"]};
    animation:bgDrift 20s ease infinite;
  }}
  body::after {{
    background:{theme["bg2"]};
    animation:bgDrift 25s ease infinite reverse;
    z-index:0;
  }}
  @keyframes bgDrift {{ 0%{{transform:translate(0,0)}} 50%{{transform:translate(3%,-2%)}} 100%{{transform:translate(0,0)}} }}
'''
        # Insert after the real body { ... } rule (must start a line)
        result = re.sub(r'(^body\s*\{[^}]*\})', lambda m: m.group(0) + '\n' + bg_css, result, flags=re.MULTILINE)

    # 6. Notch visibility
    if not theme["notch_visible"]:
        # Replace entire .notch rule
        result = re.sub(r'\.notch\s*\{[^}]*\}', '.notch { display:none; }', result)
        # Move bars up — use plain-string regex to avoid f-string brace confusion
        for cls, new_top in [('status-bar', '10px'), ('chat-header', '46px'), ('messages', '103px')]:
            class_re = cls.replace('-', r'\-')
            result = re.sub(
                class_re + r'\s*\{[^}]*top:\s*(\d+px)',
                lambda m, n=new_top: m.group(0).replace(m.group(1), n),
                result
            )

    # 7. Title
    result = re.sub(
        r'<title>فروشگرام — دموی تبلیغاتی</title>',
        f'<title>فروشگرام — {theme["name"]}</title>',
        result)

    return result


for theme in THEMES:
    themed = apply_theme(html, theme)
    fname = f"promo-ig-{theme['id']}.html"
    fpath = os.path.join(OUT_DIR, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(themed)
    size_kb = len(themed.encode('utf-8')) / 1024
    print(f'  ✓ {fname} — {theme["name"]} ({size_kb:.0f}KB)')

print(f"\nDone — {len(THEMES)} variants in {OUT_DIR}")
