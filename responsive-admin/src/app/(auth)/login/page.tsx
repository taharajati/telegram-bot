"""Generate 10 color variants from user's promo-30s.html"""

import os, re, shutil

SRC = r"C:\Users\imtah\Downloads\Telegram Desktop\promo-30s.html"
DST_DIR = r"T:\dars\projects\telegram\Telegramorderbot\promo_variants"

with open(SRC, "r", encoding="utf-8") as f:
    html = f.read()

# First, copy to root as promo-30s.html
root_dst = r"T:\dars\projects\telegram\Telegramorderbot\promo-30s.html"
with open(root_dst, "w", encoding="utf-8") as f:
    f.write(html)
print(f"✅ {root_dst}")

THEMES = [
    {
        "id": "01", "name": "بنفش تیره",
        "vars": {
            "bg": "#0a0a10", "surface": "#13131e", "surface2": "#1d1d30",
            "surface3": "#282840", "border": "#262640", "border2": "#363660",
            "text": "#ededf5", "text2": "#9a9ab5", "text3": "#5c5c78",
            "accent": "#6c5ce7", "accent2": "#a29bfe",
            "green": "#00d2a0", "greenBg": "rgba(0,210,160,.12)",
            "blue": "#0984e3", "blueBg": "rgba(9,132,227,.12)",
            "orange": "#fdcb6e", "orangeBg": "rgba(253,203,110,.12)",
            "pink": "#fd79a8", "red": "#e74c3c",
            "shadow": "0 8px 80px rgba(0,0,0,.6)", "glow": "rgba(108,92,231,.15)",
            "custBg": "#1e1e30",
            "logo1": "#6c5ce7", "logo2": "#8b5cf6", "logo3": "#fd79a8",
        }
    },
    {
        "id": "02", "name": "روشن",
        "vars": {
            "bg": "#e8e8f2", "surface": "#ffffff", "surface2": "#f2f2f8",
            "surface3": "#eaeaf4", "border": "#dcdce8", "border2": "#ccccdc",
            "text": "#181828", "text2": "#4a4a66", "text3": "#6e6e8a",
            "accent": "#6c5ce7", "accent2": "#8b7cf7",
            "green": "#00b884", "greenBg": "rgba(0,184,132,.08)",
            "blue": "#0984e3", "blueBg": "rgba(9,132,227,.06)",
            "orange": "#d46950", "orangeBg": "rgba(212,105,80,.08)",
            "pink": "#e84393", "red": "#d63031",
            "shadow": "0 12px 90px rgba(0,0,0,.18)", "glow": "rgba(108,92,231,.06)",
            "custBg": "#e4e4ee",
            "logo1": "#6c5ce7", "logo2": "#a29bfe", "logo3": "#fd79a8",
        }
    },
    {
        "id": "03", "name": "طبیعی سبز",
        "vars": {
            "bg": "#e8f5e9", "surface": "#ffffff", "surface2": "#f1f8f2",
            "surface3": "#e0ebe3", "border": "#c8e6c9", "border2": "#a5d6a7",
            "text": "#1b3a1b", "text2": "#2e5c2e", "text3": "#558b55",
            "accent": "#2e7d32", "accent2": "#43a047",
            "green": "#00897b", "greenBg": "rgba(0,137,123,.08)",
            "blue": "#1565c0", "blueBg": "rgba(21,101,192,.06)",
            "orange": "#bf6f00", "orangeBg": "rgba(191,111,0,.08)",
            "pink": "#ad1457", "red": "#c62828",
            "shadow": "0 12px 90px rgba(0,0,0,.12)", "glow": "rgba(46,125,50,.06)",
            "custBg": "#dcedc8",
            "logo1": "#2e7d32", "logo2": "#43a047", "logo3": "#66bb6a",
        }
    },
    {
        "id": "04", "name": "اقیانوس آبی",
        "vars": {
            "bg": "#e3f2fd", "surface": "#ffffff", "surface2": "#f0f8ff",
            "surface3": "#ddeeff", "border": "#bbdefb", "border2": "#90caf9",
            "text": "#0d2538", "text2": "#1e4d6b", "text3": "#4a7a9e",
            "accent": "#0d47a1", "accent2": "#1565c0",
            "green": "#00a86b", "greenBg": "rgba(0,168,107,.08)",
            "blue": "#0277bd", "blueBg": "rgba(2,119,189,.06)",
            "orange": "#e65100", "orangeBg": "rgba(230,81,0,.08)",
            "pink": "#c2185b", "red": "#b71c1c",
            "shadow": "0 12px 90px rgba(0,0,0,.14)", "glow": "rgba(13,71,161,.06)",
            "custBg": "#c8e6ff",
            "logo1": "#0d47a1", "logo2": "#1565c0", "logo3": "#42a5f5",
        }
    },
    {
        "id": "05", "name": "غروب نارنجی",
        "vars": {
            "bg": "#fff3e0", "surface": "#ffffff", "surface2": "#fff8f0",
            "surface3": "#ffebd6", "border": "#ffe0b2", "border2": "#ffcc80",
            "text": "#2d1b0a", "text2": "#5a3d1e", "text3": "#8a6638",
            "accent": "#e65100", "accent2": "#ff6d00",
            "green": "#2e7d32", "greenBg": "rgba(46,125,50,.08)",
            "blue": "#1565c0", "blueBg": "rgba(21,101,192,.06)",
            "orange": "#bf360c", "orangeBg": "rgba(191,54,12,.08)",
            "pink": "#ad1457", "red": "#b71c1c",
            "shadow": "0 12px 90px rgba(0,0,0,.15)", "glow": "rgba(230,81,0,.06)",
            "custBg": "#ffccbc",
            "logo1": "#e65100", "logo2": "#ff6d00", "logo3": "#ffab40",
        }
    },
    {
        "id": "06", "name": "سبز تیره",
        "vars": {
            "bg": "#0a1a0a", "surface": "#0f200f", "surface2": "#162816",
            "surface3": "#1d351d", "border": "#2a4a2a", "border2": "#3a5e3a",
            "text": "#e8f5e9", "text2": "#a5d6a7", "text3": "#66bb6a",
            "accent": "#4caf50", "accent2": "#66bb6a",
            "green": "#00e676", "greenBg": "rgba(0,230,118,.12)",
            "blue": "#40c4ff", "blueBg": "rgba(64,196,255,.10)",
            "orange": "#ffd54f", "orangeBg": "rgba(255,213,79,.12)",
            "pink": "#f48fb1", "red": "#e57373",
            "shadow": "0 8px 80px rgba(0,0,0,.6)", "glow": "rgba(76,175,80,.15)",
            "custBg": "#1a301a",
            "logo1": "#4caf50", "logo2": "#66bb6a", "logo3": "#a5d6a7",
        }
    },
    {
        "id": "07", "name": "زغالی",
        "vars": {
            "bg": "#121212", "surface": "#1e1e1e", "surface2": "#2a2a2a",
            "surface3": "#353535", "border": "#333333", "border2": "#454545",
            "text": "#eeeeee", "text2": "#b0b0b0", "text3": "#7a7a7a",
            "accent": "#bb86fc", "accent2": "#ce93fd",
            "green": "#03dac6", "greenBg": "rgba(3,218,198,.12)",
            "blue": "#64b5f6", "blueBg": "rgba(100,181,246,.10)",
            "orange": "#ffb74d", "orangeBg": "rgba(255,183,77,.12)",
            "pink": "#f06292", "red": "#ef5350",
            "shadow": "0 8px 80px rgba(0,0,0,.7)", "glow": "rgba(187,134,252,.12)",
            "custBg": "#292929",
            "logo1": "#bb86fc", "logo2": "#ce93fd", "logo3": "#e1bee7",
        }
    },
    {
        "id": "08", "name": "رز صورتی",
        "vars": {
            "bg": "#fce4ec", "surface": "#ffffff", "surface2": "#fdf2f6",
            "surface3": "#fadde8", "border": "#f8bbd0", "border2": "#f48fb1",
            "text": "#2d0a1a", "text2": "#5a1e36", "text3": "#8a3858",
            "accent": "#d81b60", "accent2": "#e91e63",
            "green": "#00897b", "greenBg": "rgba(0,137,123,.08)",
            "blue": "#1565c0", "blueBg": "rgba(21,101,192,.06)",
            "orange": "#ef6c00", "orangeBg": "rgba(239,108,0,.08)",
            "pink": "#c2185b", "red": "#b71c1c",
            "shadow": "0 12px 90px rgba(0,0,0,.14)", "glow": "rgba(216,27,96,.06)",
            "custBg": "#f8bbd0",
            "logo1": "#d81b60", "logo2": "#e91e63", "logo3": "#f06292",
        }
    },
    {
        "id": "09", "name": "سایبرپانک",
        "vars": {
            "bg": "#0a0a1a", "surface": "#12122a", "surface2": "#1a1a38",
            "surface3": "#222248", "border": "#2a2a55", "border2": "#3a3a6a",
            "text": "#f0f0ff", "text2": "#b0b0ee", "text3": "#7070bb",
            "accent": "#ff2d55", "accent2": "#ff6b81",
            "green": "#00f0ff", "greenBg": "rgba(0,240,255,.12)",
            "blue": "#5856ff", "blueBg": "rgba(88,86,255,.10)",
            "orange": "#ff9f0a", "orangeBg": "rgba(255,159,10,.12)",
            "pink": "#ff375f", "red": "#ff3b30",
            "shadow": "0 8px 80px rgba(255,45,85,.2)", "glow": "rgba(255,45,85,.15)",
            "custBg": "#1a1a3e",
            "logo1": "#ff2d55", "logo2": "#5856ff", "logo3": "#00f0ff",
        }
    },
    {
        "id": "10", "name": "خاکستری مینیمال",
        "vars": {
            "bg": "#f0f0f0", "surface": "#fafafa", "surface2": "#f0f0f0",
            "surface3": "#e4e4e4", "border": "#d0d0d0", "border2": "#bdbdbd",
            "text": "#1a1a1a", "text2": "#555555", "text3": "#888888",
            "accent": "#37474f", "accent2": "#546e7a",
            "green": "#2e7d32", "greenBg": "rgba(46,125,50,.08)",
            "blue": "#1565c0", "blueBg": "rgba(21,101,192,.06)",
            "orange": "#ef6c00", "orangeBg": "rgba(239,108,0,.08)",
            "pink": "#c2185b", "red": "#b71c1c",
            "shadow": "0 12px 90px rgba(0,0,0,.12)", "glow": "rgba(55,71,79,.06)",
            "custBg": "#e0e0e0",
            "logo1": "#37474f", "logo2": "#546e7a", "logo3": "#90a4ae",
        }
    },
]

for t in THEMES:
    v = t["vars"]
    
    root = f""":root {{
    --bg:         {v["bg"]};
    --surface:    {v["surface"]};
    --surface2:   {v["surface2"]};
    --surface3:   {v["surface3"]};
    --border:     {v["border"]};
    --border2:    {v["border2"]};
    --text:       {v["text"]};
    --text2:      {v["text2"]};
    --text3:      {v["text3"]};
    --accent:     {v["accent"]};
    --accent2:    {v["accent2"]};
    --green:      {v["green"]};
    --greenBg:    {v["greenBg"]};
    --blue:       {v["blue"]};
    --blueBg:     {v["blueBg"]};
    --orange:     {v["orange"]};
    --orangeBg:   {v["orangeBg"]};
    --pink:       {v["pink"]};
    --red:        {v["red"]};
    --radius:     40px;
    --shadow:     {v["shadow"]};
    --glow:       {v["glow"]};
  }}"""
    
    # Replace :root block
    start_idx = html.find(":root {")
    brace_depth = 0
    idx = start_idx
    while idx < len(html):
        if html[idx] == '{': brace_depth += 1
        elif html[idx] == '}':
            brace_depth -= 1
            if brace_depth == 0:
                old_root_end = idx + 1
                break
        idx += 1
    
    new_html = html[:start_idx] + root + "\n" + html[old_root_end:]
    
    # Update title
    new_html = new_html.replace(
        "<title>فروشگرام — ۳۰ ثانیه</title>",
        f"<title>فروشگرام — {t['name']}</title>"
    )
    
    # Update logo gradient
    old_logo = "background:linear-gradient(135deg,var(--accent),#8b5cf6,var(--pink))"
    new_logo = f"background:linear-gradient(135deg,{v['logo1']},{v['logo2']},{v['logo3']})"
    new_html = new_html.replace(old_logo, new_logo)
    
    # Update animated bg radial gradients (subtle variation)
    old_rad1 = "background:radial-gradient(ellipse at 30% 40%, rgba(108,92,231,.08)"
    new_rad1 = f"background:radial-gradient(ellipse at 30% 40%, rgba({','.join(map(str,__import__('ast').literal_eval(str(v['accent']).replace('#','0x').replace('0x','').zfill(6).replace(' ','').replace('(','').replace(')',''))))},.08)"
    # Simpler approach — just update the name in :root
    
    # Write to promo_variants/promo-30s-{id}.html
    dest = os.path.join(DST_DIR, f"promo-30s-{t['id']}.html")
    with open(dest, "w", encoding="utf-8") as f:
        f.write(new_html)
    print(f"✅ promo-30s-{t['id']}.html — {t['name']}")

print("\n✅ همه ۱۰ نسخه ساخته شدند!")
