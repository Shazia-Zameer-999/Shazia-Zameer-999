#!/usr/bin/env python3
"""
make_ascii_svg.py — convert source-prepped.png into a monochrome,
self-typing ASCII-art SVG.

Each row wipes in left-to-right (a small block cursor rides the wipe
edge), staggered top to bottom. Prints once, then freezes — no loop.
Pure SMIL/CSS animation, so GitHub renders it with no JS.

Usage:
    python scripts/make_ascii_svg.py [source-prepped.png] [-o avi-ascii.svg]
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image

# bright (sparse) -> dark (dense). Leading space clears background to nothing.
RAMP = " .`:-=+*cs#%@"

FILL_COLOR = "#9aa5b1"     # single light-gray fill — no per-char rainbow
FONT_SIZE = 8
CHAR_W = FONT_SIZE * 0.6   # monospace advance width approximation
LINE_H = FONT_SIZE * 1.0
COLS = 100
ROWS = 53
ROW_STAGGER = 0.035        # seconds between each row's animation start
ROW_DURATION = 0.5         # seconds for a single row's wipe


def image_to_ascii(img_path: Path, cols: int, rows: int) -> list[str]:
    img = Image.open(img_path).convert("L")
    img = img.resize((cols, rows), Image.LANCZOS)
    arr = np.array(img).astype(float)

    ramp_len = len(RAMP)
    idx = ((255 - arr) / 255 * (ramp_len - 1)).round().astype(int)
    idx = np.clip(idx, 0, ramp_len - 1)

    lines = []
    for r in range(rows):
        line = "".join(RAMP[i] for i in idx[r])
        lines.append(line)
    return lines


def escape_xml(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;"))


def build_svg(lines: list[str]) -> str:
    cols = max(len(l) for l in lines) if lines else COLS
    width = cols * CHAR_W + 20
    height = len(lines) * LINE_H + 20

    rows_svg = []
    style_rules = []

    for r, line in enumerate(lines):
        row_id = f"row{r}"
        text_w = len(line) * CHAR_W
        y = 10 + (r + 1) * LINE_H
        start = r * ROW_STAGGER

        # Each row: a <text> clipped by a rect that animates from 0 width
        # to full width (the wipe), plus a small cursor block that rides
        # the leading edge and disappears when the wipe completes.
        rows_svg.append(f'''
  <clipPath id="clip{row_id}">
    <rect class="{row_id}-wipe" x="0" y="{y - LINE_H}" width="0" height="{LINE_H + 4}"/>
  </clipPath>
  <g clip-path="url(#clip{row_id})">
    <text x="10" y="{y}" font-family="'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"
          font-size="{FONT_SIZE}" fill="{FILL_COLOR}" xml:space="preserve">{escape_xml(line)}</text>
  </g>
  <rect class="{row_id}-cursor" x="10" y="{y - FONT_SIZE * 0.85}" width="{CHAR_W}" height="{FONT_SIZE}" fill="{FILL_COLOR}"/>
''')

        style_rules.append(f'''
  .{row_id}-wipe {{
    animation: wipe{row_id} {ROW_DURATION}s steps(30, end) {start}s forwards;
  }}
  .{row_id}-cursor {{
    opacity: 0;
    animation: cursormove{row_id} {ROW_DURATION}s linear {start}s forwards,
               cursorfade 0.15s linear {start + ROW_DURATION}s forwards;
  }}
  @keyframes wipe{row_id} {{
    from {{ width: 0; }}
    to {{ width: {text_w}px; }}
  }}
  @keyframes cursormove{row_id} {{
    0%   {{ opacity: 1; transform: translateX(0); }}
    100% {{ opacity: 1; transform: translateX({text_w}px); }}
  }}
''')

    style_rules.append('''
  @keyframes cursorfade {
    to { opacity: 0; }
  }
''')

    svg = f'''<svg viewBox="0 0 {width:.0f} {height:.0f}" width="{width:.0f}" height="{height:.0f}"
     xmlns="http://www.w3.org/2000/svg">
  <style>
{"".join(style_rules)}
  </style>
  <rect width="100%" height="100%" fill="transparent"/>
{"".join(rows_svg)}
</svg>
'''
    return svg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?", default="source-prepped.png")
    ap.add_argument("-o", "--output", default="avi-ascii.svg")
    ap.add_argument("--cols", type=int, default=COLS)
    ap.add_argument("--rows", type=int, default=ROWS)
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        raise SystemExit(f"input not found: {in_path} (run prep_photo.py first)")

    lines = image_to_ascii(in_path, args.cols, args.rows)
    svg = build_svg(lines)
    Path(args.output).write_text(svg)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
