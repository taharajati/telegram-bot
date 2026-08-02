"""Generate 10 color variants from promo-30s.html (robust :root replacement)."""

import os
import re

SRC = r"T:\dars\projects\telegram\Telegramorderbot\promo-30s.html"
DST_DIR = r"T:\dars\projects\telegram\Telegramorderbot\promo_variants"

with open(SRC, "r", encoding="utf-8") as f:
    html = f.read()

# Verify source is clean
assert html.count("</html>") == 1, f"Source file has {html.count('</html>')} </html> tags — must be 1"
assert html.strip().startswith("<!DOCTYPE"), "Source must start with <!DOCTYPE"

print(f"📄 Source: {len(html.splitlines())} lines, {len(html)} chars")


def hex_to_rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgba(h, a):
    r, g, b = hex_to_rgb(h)
    return f"rgba({r},{g},{b},{a})"


def lighten(h, pct):
    r, g, b = hex_to_rgb(h)
    return f"#{min(255, int(r + (255 - r) * pct)):02x}{min(255, int(g + (255 - g) * pct)):02x}{min(255, int(b + (255 - b) * pct)):02x}"


def darken(h, pct):
    r, g, b = hex_to_rgb(h)
    return f"#{max(0, int(r * (1 - pct))):02x}{max(0, int(g * (1 - pct))):02x}{max(0, int(b * (1 - pct))):02x}"


THEMES = [
    ("01", "بنفش تیره", {
        "bg": "#0a0a10", "surface": "#13131e", "border": "#262640",
        "text": "#ededf5", "text2": "#9a9ab5", "text3": "#5c5c78",
        "accent": "#6c5ce7", "accent2": "#a29bfe", "green": "#00d2a0",
        "blue": "#0984e3", "orange": "#fdcb6e", "pink": "#fd79a8", "red": "#e74c3c",
        "logo1": "#6c5ce7", "logo2": "#8b5cf6", "logo3": "#fd79a8", "dark": True}),
    ("02", "روشن", {
        "bg": "#e8e8f2", "surface": "#ffffff", "border": "#dcdce8",
        "text": "#181828", "text2": "#4a4a66", "text3": "#6e6e8a",
        "accent": "#6c5ce7", "accent2": "#8b7cf7", "green": "#00b884",
        "blue": "#0984e3", "orange": "#d46950", "pink": "#e84393", "red": "#d63031",
        "logo1": "#6c5ce7", "logo2": "#a29bfe", "logo3": "#fd79a8", "dark": False}),
    ("03", "طبیعی سبز", {
        "bg": "#e8f5e9", "surface": "#ffffff", "border": "#c8e6c9",
        "text": "#1b3a1b", "text2": "#2e5c2e", "text3": "#558b55",
        "accent": "#2e7d32", "accent2": "#43a047", "green": "#00897b",
        "blue": "#1565c0", "orange": "#bf6f00", "pink": "#ad1457", "red": "#c62828",
        "logo1": "#2e7d32", "logo2": "#43a047", "logo3": "#66bb6a", "dark": False}),
    ("04", "اقیانوس آبی", {
        "bg": "#e3f2fd", "surface": "#ffffff", "border": "#bbdefb",
        "text": "#0d2538", "text2": "#1e4d6b", "text3": "#4a7a9e",
        "accent": "#0d47a1", "accent2": "#1565c0", "green": "#00a86b",
        "blue": "#0277bd", "orange": "#e65100", "pink": "#c2185b", "red": "#b71c1c",
        "logo1": "#0d47a1", "logo2": "#1565c0", "logo3": "#42a5f5", "dark": False}),
    ("05", "غروب نارنجی", {
        "bg": "#fff3e0", "surface": "#ffffff", "border": "#ffe0b2",
        "text": "#2d1b0a", "text2": "#5a3d1e", "text3": "#8a6638",
        "accent": "#e65100", "accent2": "#ff6d00", "green": "#2e7d32",
        "blue": "#1565c0", "orange": "#bf360c", "pink": "#ad1457", "red": "#b71c1c",
        "logo1": "#e65100", "logo2": "#ff6d00", "logo3": "#ffab40", "dark": False}),
    ("06", "سبز تیره", {
        "bg": "#0a1a0a", "surface": "#0f200f", "border": "#2a4a2a",
        "text": "#e8f5e9", "text2": "#a5d6a7", "text3": "#66bb6a",
        "accent": "#4caf50", "accent2": "#66bb6a", "green": "#00e676",
        "blue": "#40c4ff", "orange": "#ffd54f", "pink": "#f48fb1", "red": "#e57373",
        "logo1": "#4caf50", "logo2": "#66bb6a", "logo3": "#a5d6a7", "dark": True}),
    ("07", "زغالی", {
        "bg": "#121212", "surface": "#1e1e1e", "border": "#333333",
        "text": "#eeeeee", "text2": "#b0b0b0", "text3": "#7a7a7a",
        "accent": "#bb86fc", "accent2": "#ce93fd", "green": "#03dac6",
        "blue": "#64b5f6", "orange": "#ffb74d", "pink": "#f06292", "red": "#ef5350",
        "logo1": "#bb86fc", "logo2": "#ce93fd", "logo3": "#e1bee7", "dark": True}),
    ("08", "رز صورتی", {
        "bg": "#fce4ec", "surface": "#ffffff", "border": "#f8bbd0",
        "text": "#2d0a1a", "text2": "#5a1e36", "text3": "#8a3858",
        "accent": "#d81b60", "accent2": "#e91e63", "green": "#00897b",
        "blue": "#1565c0", "orange": "#ef6c00", "pink": "#c2185b", "red": "#b71c1c",
        "logo1": "#d81b60", "logo2": "#e91e63", "logo3": "#f06292", "dark": False}),
    ("09", "سایبرپانک", {
        "bg": "#0a0a1a", "surface": "#12122a", "border": "#2a2a55",
        "text": "#f0f0ff", "text2": "#b0b0ee", "text3": "#7070bb",
        "accent": "#ff2d55", "accent2": "#ff6b81", "green": "#00f0ff",
        "blue": "#5856ff", "orange": "#ff9f0a", "pink": "#ff375f", "red": "#ff3b30",
        "logo1": "#ff2d55", "logo2": "#5856ff", "logo3": "#00f0ff", "dark": True}),
    ("10", "خاکستری مینیمال", {
        "bg": "#f0f0f0", "surface": "#fafafa", "border": "#d0d0d0",
        "text": "#1a1a1a", "text2": "#555555", "text3": "#888888",
        "accent": "#37474f", "accent2": "#546e7a", "green": "#2e7d32",
        "blue": "#1565c0", "orange": "#ef6c00", "pink": "#c2185b", "red": "#b71c1c",
        "logo1": "#37474f", "logo2": "#546e7a", "logo3": "#90a4ae", "dark": False}),
]

# Find the :root{...} or :root {...} block using regex (handles both formats)
root_pattern = re.compile(r":root\s*\{[^}]*\}", re.DOTALL)
root_match = root_pattern.search(html)
assert root_match, "Could not find :root{...} block in source HTML"
root_start = root_match.start()
root_end = root_match.end()
print(f"🎯 Found :root block at chars {root_start}-{root_end}")

# Everything before and after :root
html_before = html[:root_start]
html_after = html[root_end:]

# Also find the logo gradient to replace
# Looking for: background:linear-gradient(135deg,var(--accent),#8b5cf6,var(--pink))
# or similar patterns with hardcoded colors

for fid, fname, v in THEMES:
    bg = v["bg"]
    is_dark = v["dark"]

    s2 = lighten(bg, 0.12) if is_dark else darken(bg, 0.04)
    s3 = lighten(bg, 0.22) if is_dark else darken(bg, 0.10)
    b2 = lighten(v["border"], 0.15) if is_dark else darken(v["border"], 0.08)
    r, g, b = hex_to_rgb(bg)
    shadow = f"0 8px 80px rgba({r},{g},{b},.6)" if is_dark else f"0 12px 90px rgba({r},{g},{b},.14)"

    new_root = (
        f":root{{"
        f"--bg:{bg};"
        f"--surface:{v['surface']};"
        f"--surface2:{s2};"
        f"--surface3:{s3};"
        f"--border:{v['border']};"
        f"--border2:{b2};"
        f"--text:{v['text']};"
        f"--text2:{v['text2']};"
        f"--text3:{v['text3']};"
        f"--accent:{v['accent']};"
        f"--accent2:{v['accent2']};"
        f"--green:{v['green']};"
        f"--greenBg:{rgba(v['green'], '.12')};"
        f"--blue:{v['blue']};"
        f"--blueBg:{rgba(v['blue'], '.12')};"
        f"--orange:{v['orange']};"
        f"--orangeBg:{rgba(v['orange'], '.12')};"
        f"--pink:{v['pink']};"
        f"--red:{v['red']};"
        f"--radius:40px;"
        f"--shadow:{shadow};"
        f"--glow:{rgba(v['accent'], '.15')}"
        f"}}"
    )

    new_html = html_before + new_root + html_after

    # Replace hardcoded rgba values from the original (accent-based gradients in body::before/after)
    new_html = new_html.replace("rgba(108,92,231,.08)", rgba(v["accent"], ".08"))
    new_html = new_html.replace("rgba(0,210,160,.05)", rgba(v["green"], ".05"))
    new_html = new_html.replace("rgba(108,92,231,.2)", rgba(v["accent"], ".2"))
    new_html = new_html.replace("rgba(108,92,231,.5)", rgba(v["accent"], ".5"))

    # Logo gradient — replace any hardcoded gradient on the .logo element
    # Pattern: background:linear-gradient(135deg,#xxx,#xxx,#xxx)
    logo_pattern = re.compile(
        r"(#s2\s+\.logo\{[^}]*?background:linear-gradient\(135deg,)[^)]*(\))",
        re.DOTALL
    )
    logo_replacement = rf"\g<1>{v['logo1']},{v['logo2']},{v['logo3']}\g<2>"
    new_html = logo_pattern.sub(logo_replacement, new_html)

    # Title
    new_html = new_html.replace(
        "<title>فروشگرام — ۳۰ ثانیه</title>",
        f"<title>فروشگرام — {fname}</title>",
    )

    # Safety: ensure exactly one </html>
    assert new_html.count("</html>") == 1, f"promo-30s-{fid}: has {new_html.count('</html>')} </html> tags"

    dest = os.path.join(DST_DIR, f"promo-30s-{fid}.html")
    with open(dest, "w", encoding="utf-8") as f:
        f.write(new_html)
    line_count = len(new_html.splitlines())
    print(f"✅ promo-30s-{fid}.html — {fname} ({line_count} lines)")

print(f"\n✅ همه ۱۰ نسخه در {DST_DIR}")
