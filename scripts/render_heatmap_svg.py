#!/usr/bin/env python3
"""
render_heatmap_svg.py — draw data/contributions.json as the classic
53-week x 7-day GitHub contribution grid: rounded, colored boxes that
slide in diagonally (line after line), then freeze. No looping "glow".

Usage:
    python scripts/render_heatmap_svg.py [-i data/contributions.json] [-o contrib-heatmap.svg]
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

# none -> brightest (level 5 is a neon top end, beyond GitHub's own scale,
# used only if a day's count is far above the norm — see level_for_count)
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]

BOX = 11
GAP = 3
CELL = BOX + GAP
LEFT_PAD = 30       # room for month labels above / day labels at left
TOP_PAD = 20
RIGHT_PAD = 10
BOTTOM_PAD = 46     # room for legend + stats footer

DAY_LABELS = ["", "Mon", "", "Wed", "", "Fri", ""]
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

STAGGER = 0.012     # seconds between successive diagonals
DUR = 0.35


def load_data(path: Path) -> dict:
    return json.loads(path.read_text())


def to_weeks(days: list[dict]) -> list[list[dict | None]]:
    """Bucket the flat day list into GitHub-style weeks (columns), each
    column being Sun..Sat. Pads the first/last week with None."""
    if not days:
        return []

    parsed = [
        {**d, "dt": datetime.strptime(d["date"], "%Y-%m-%d")}
        for d in days
    ]
    parsed.sort(key=lambda d: d["dt"])

    weeks: list[list[dict | None]] = []
    current_week: list[dict | None] = [None] * parsed[0]["dt"].weekday_sun() \
        if hasattr(parsed[0]["dt"], "weekday_sun") else None

    # datetime has no weekday_sun helper; compute Sun=0..Sat=6 manually.
    def sun_index(dt: datetime) -> int:
        return (dt.weekday() + 1) % 7  # Python: Mon=0..Sun=6 -> Sun=0..Sat=6

    current_week = [None] * sun_index(parsed[0]["dt"])
    for d in parsed:
        idx = sun_index(d["dt"])
        if idx == 0 and current_week and any(c is not None for c in current_week):
            weeks.append(current_week)
            current_week = []
        elif idx == 0 and not current_week:
            pass
        while len(current_week) < idx:
            current_week.append(None)
        current_week.append(d)
    if current_week:
        while len(current_week) < 7:
            current_week.append(None)
        weeks.append(current_week)

    return weeks


def level_for(day: dict | None) -> int:
    if day is None:
        return -1
    lvl = day.get("level")
    if lvl is not None:
        return max(0, min(lvl, 4))
    count = day.get("count", 0)
    if count == 0:
        return 0
    if count < 3:
        return 1
    if count < 6:
        return 2
    if count < 10:
        return 3
    return 4


def escape_xml(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;"))


def build_svg(data: dict, width_target: int = 860) -> str:
    weeks = to_weeks(data["days"])
    stats = data.get("stats", {})

    n_weeks = len(weeks)
    grid_w = n_weeks * CELL
    grid_h = 7 * CELL

    total_w = max(width_target, LEFT_PAD + grid_w + RIGHT_PAD)
    total_h = TOP_PAD + grid_h + BOTTOM_PAD

    boxes = []
    month_labels = []
    last_month = None

    for w_idx, week in enumerate(weeks):
        x = LEFT_PAD + w_idx * CELL
        for d_idx, day in enumerate(week):
            y = TOP_PAD + d_idx * CELL
            lvl = level_for(day)
            if lvl < 0:
                continue
            fill = PALETTE[lvl]
            diagonal = w_idx + d_idx
            delay = diagonal * STAGGER
            title = ""
            if day:
                title = f'{day.get("count", 0)} contributions on {day["date"]}'
                month = day["dt"].month if "dt" in day else int(day["date"][5:7])
                if month != last_month:
                    month_labels.append((x, MONTH_NAMES[month - 1]))
                    last_month = month

            boxes.append(f'''
    <rect class="box" x="{x}" y="{y}" width="{BOX}" height="{BOX}" rx="2" ry="2"
          fill="{fill}" style="animation-delay:{delay:.3f}s">
      <title>{escape_xml(title)}</title>
    </rect>''')

    day_label_svg = "".join(
        f'<text x="{LEFT_PAD - 8}" y="{TOP_PAD + i * CELL + BOX}" '
        f'text-anchor="end" font-size="9" fill="#8b949e" '
        f'font-family="\'SFMono-Regular\',Consolas,monospace">{lbl}</text>'
        for i, lbl in enumerate(DAY_LABELS)
    )

    month_label_svg = "".join(
        f'<text x="{x}" y="{TOP_PAD - 6}" font-size="10" fill="#8b949e" '
        f'font-family="\'SFMono-Regular\',Consolas,monospace">{name}</text>'
        for x, name in month_labels
    )

    legend_y = TOP_PAD + grid_h + 22
    legend_x = LEFT_PAD
    legend_swatches = "".join(
        f'<rect x="{legend_x + 32 + i * (BOX + 3)}" y="{legend_y - BOX + 2}" '
        f'width="{BOX}" height="{BOX}" rx="2" fill="{PALETTE[i]}"/>'
        for i in range(5)
    )

    footer_text = ""
    if stats:
        footer_text = (
            f'{stats.get("total", 0):,} contributions in the last year '
            f'\u00b7 current streak {stats.get("current_streak", 0)}d '
            f'\u00b7 longest streak {stats.get("longest_streak", 0)}d'
        )

    svg = f'''<svg viewBox="0 0 {total_w} {total_h}" width="{total_w}" height="{total_h}"
     xmlns="http://www.w3.org/2000/svg">
  <style>
    .box {{
      opacity: 0;
      transform-box: fill-box;
      transform-origin: center;
      animation: reveal {DUR}s ease-out forwards;
    }}
    @keyframes reveal {{
      from {{ opacity: 0; transform: translate(-6px, -6px) scale(0.6); }}
      to   {{ opacity: 1; transform: translate(0, 0) scale(1); }}
    }}
  </style>
  <rect width="100%" height="100%" fill="transparent"/>
{month_label_svg}
{day_label_svg}
{"".join(boxes)}
  <text x="{legend_x}" y="{legend_y + 3}" font-size="9" fill="#8b949e"
        font-family="'SFMono-Regular',Consolas,monospace">Less</text>
{legend_swatches}
  <text x="{legend_x + 32 + 5 * (BOX + 3) + 6}" y="{legend_y + 3}" font-size="9" fill="#8b949e"
        font-family="'SFMono-Regular',Consolas,monospace">More</text>
  <text x="{total_w - RIGHT_PAD}" y="{legend_y + 3}" text-anchor="end" font-size="10" fill="#c9d1d9"
        font-family="'SFMono-Regular',Consolas,monospace">{escape_xml(footer_text)}</text>
</svg>
'''
    return svg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", default="data/contributions.json")
    ap.add_argument("-o", "--output", default="contrib-heatmap.svg")
    args = ap.parse_args()

    data = load_data(Path(args.input))
    svg = build_svg(data)
    Path(args.output).write_text(svg)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()


