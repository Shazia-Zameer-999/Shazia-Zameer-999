#!/usr/bin/env python3
"""
fetch_contributions.py — pull your real contribution calendar with no
GraphQL API and no personal access token.

GitHub serves the calendar as a public HTML fragment at:
    https://github.com/users/<username>/contributions
(the same fragment the profile page itself uses). We fetch it, parse
the day cells with BeautifulSoup, and write data/contributions.json
with raw days plus a few derived stats.

Usage:
    python scripts/fetch_contributions.py [username]
    (reads GITHUB_USERNAME env var if no argument given)
Output:
    data/contributions.json
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL_TMPL = "https://github.com/users/{username}/contributions"


def fetch_html(username: str) -> str:
    url = URL_TMPL.format(username=username)
    resp = requests.get(
        url,
        headers={"User-Agent": "profile-readme-bot (github actions)"},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.text


def parse_days(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    days = []

    # GitHub renders each day as a <td> (older markup) or a <table>-free
    # <rect>/<td class="ContributionCalendar-day"> element depending on
    # rollout. Handle both shapes defensively.
    cells = soup.select("td.ContributionCalendar-day")
    if not cells:
        cells = soup.select("rect.ContributionCalendar-day")

    for cell in cells:
        date = cell.get("data-date")
        level = cell.get("data-level")
        count_attr = cell.get("data-count")

        if date is None:
            continue

        if level is not None:
            level = int(level)
        else:
            # Fall back to parsing the tooltip text if data-level is absent.
            level = 0

        if count_attr is not None:
            count = int(count_attr)
        else:
            tooltip_id = cell.get("id")
            count = 0
            if tooltip_id:
                tip = soup.find("tool-tip", attrs={"for": tooltip_id})
                if tip and tip.text:
                    first_word = tip.text.strip().split()[0].replace(",", "")
                    if first_word.isdigit():
                        count = int(first_word)
                    elif first_word.lower() == "no":
                        count = 0

        days.append({"date": date, "count": count, "level": level})

    days.sort(key=lambda d: d["date"])
    return days


def derive_stats(days: list[dict]) -> dict:
    if not days:
        return {}

    total = sum(d["count"] for d in days)

    # Current streak: consecutive days with count > 0, ending today (or the
    # most recent day in the data if today isn't present yet).
    current_streak = 0
    for d in reversed(days):
        if d["count"] > 0:
            current_streak += 1
        else:
            break

    longest_streak = 0
    running = 0
    for d in days:
        if d["count"] > 0:
            running += 1
            longest_streak = max(longest_streak, running)
        else:
            running = 0

    best_day = max(days, key=lambda d: d["count"])

    monthly = {}
    for d in days:
        month = d["date"][:7]  # YYYY-MM
        monthly[month] = monthly.get(month, 0) + d["count"]

    return {
        "total": total,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "best_day": best_day,
        "monthly": monthly,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("username", nargs="?", default=os.environ.get("GITHUB_USERNAME"))
    ap.add_argument("-o", "--output", default="data/contributions.json")
    args = ap.parse_args()

    if not args.username:
        sys.exit("error: pass a username or set GITHUB_USERNAME")

    html = fetch_html(args.username)
    days = parse_days(html)
    if not days:
        sys.exit("error: no contribution cells parsed — GitHub markup may "
                  "have changed; inspect the fetched HTML")

    stats = derive_stats(days)

    out = {
        "username": args.username,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "days": days,
        "stats": stats,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))
    print(f"wrote {out_path} ({len(days)} days, {stats.get('total', 0)} contributions)")


if __name__ == "__main__":
    main()
