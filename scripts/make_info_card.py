#!/usr/bin/env python3
"""
make_info_card.py — hand-authored neofetch-style SVG panel.

Edit the CONTENT dict below with your own details. Each line fades and
slides in on a short stagger. Set STATIC=1 in the environment to emit a
frozen (fully-visible, non-animated) frame for local Quick Look previews.

Usage:
    python scripts/make_info_card.py [-o info-card.svg]
    STATIC=1 python scripts/make_info_card.py -o info-card-static.svg
"""
import argparse
import os

# --- Edit this section with your own details -------------------------------
CONTENT = {
    "title": "shazia@github",
    "rows": [
        ("Now", "BTech CSE (AI), University of Lucknow "),
        ("Role", "Full-Stack Web Developer (Freelance, Jan 2024 – Present)"),
        ("Stack", "Python · Flask · Next.js · React · MongoDB"),
        ("Building", "Backend systems + full-stack apps, one repo at a time"),
        ("DSA", "31 solved on LeetCode · 8-day streak"),
    ],
}
# -----------------------------------------------------------------------------

BG = "#0d1117"
BORDER = "#30363d"
TITLE_COLOR = "#58a6ff"
KEY_COLOR = "#7ee787"
VAL_COLOR = "#c9d1d9"
DIM_COLOR = "#8b949e"
FONT = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"

ROW_H = 34
PAD = 24
TITLEBAR_H = 46
CARD_W = 490
STAGGER = 0.18
DUR = 0.35


def escape_xml(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;"))


def build_svg(static: bool) -> str:
    rows = CONTENT["rows"]
    height = TITLEBAR_H + PAD + len(rows) * ROW_H + PAD

    body = []
    style = []

    # macOS-style title bar dots + title text
    body.append(f'''
  <rect x="0" y="0" width="{CARD_W}" height="{height}" rx="10" fill="{BG}" stroke="{BORDER}" stroke-width="1"/>
  <rect x="0" y="0" width="{CARD_W}" height="{TITLEBAR_H}" rx="10" fill="#161b22"/>
  <rect x="0" y="{TITLEBAR_H - 10}" width="{CARD_W}" height="10" fill="#161b22"/>
  <circle cx="24" cy="{TITLEBAR_H/2}" r="6" fill="#ff5f56"/>
  <circle cx="44" cy="{TITLEBAR_H/2}" r="6" fill="#ffbd2e"/>
  <circle cx="64" cy="{TITLEBAR_H/2}" r="6" fill="#27c93f"/>
  <text x="{CARD_W/2}" y="{TITLEBAR_H/2 + 5}" text-anchor="middle"
        font-family="{FONT}" font-size="13" fill="{DIM_COLOR}">{escape_xml(CONTENT["title"])}</text>
''')

    for i, (key, val) in enumerate(rows):
        y = TITLEBAR_H + PAD + i * ROW_H + 16
        cls = f"line{i}"
        opacity0 = "0" if not static else "1"
        transform0 = "translate(-8px,0)" if not static else "translate(0,0)"
        body.append(f'''
  <g class="{cls}" style="opacity:{opacity0};transform:{transform0}">
    <text x="{PAD}" y="{y}" font-family="{FONT}" font-size="14" fill="{KEY_COLOR}">{escape_xml(key)}</text>
    <text x="{PAD + 120}" y="{y}" font-family="{FONT}" font-size="14" fill="{VAL_COLOR}">{escape_xml(val)}</text>
  </g>
''')
        if not static:
            start = i * STAGGER
            style.append(f'''
  .{cls} {{
    animation: fadeIn{i} {DUR}s ease-out {start}s forwards;
  }}
  @keyframes fadeIn{i} {{
    from {{ opacity: 0; transform: translate(-8px,0); }}
    to   {{ opacity: 1; transform: translate(0,0); }}
  }}
''')

    svg = f'''<svg viewBox="0 0 {CARD_W} {height}" width="{CARD_W}" height="{height}"
     xmlns="http://www.w3.org/2000/svg">
  <style>
{"".join(style)}
  </style>
{"".join(body)}
</svg>
'''
    return svg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default="info-card.svg")
    args = ap.parse_args()

    static = os.environ.get("STATIC") == "1"
    svg = build_svg(static)
    with open(args.output, "w") as f:
        f.write(svg)
    print(f"wrote {args.output} (static={static})")


if __name__ == "__main__":
    main()
