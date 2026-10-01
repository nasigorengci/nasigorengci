"""Render the last 31 completed days from GitHub's public contribution calendar."""

from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.request import Request, urlopen

USERNAME = "nasigorengci"
ROOT = Path(__file__).resolve().parents[1]


class Calendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.dates = {}
        self.counts = {}
        self.tip = None
        self.text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "td" and "data-date" in attrs:
            self.dates[attrs["id"]] = attrs["data-date"]
        if tag == "tool-tip":
            self.tip = attrs.get("for")
            self.text = []

    def handle_data(self, data):
        if self.tip:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == "tool-tip" and self.tip:
            match = re.match(r"\s*(No|[\d,]+) contributions?\b", "".join(self.text))
            if match:
                self.counts[self.tip] = 0 if match[1] == "No" else int(match[1].replace(",", ""))
            self.tip = None


def main():
    today = datetime.now(timezone.utc).date()
    start, end = today - timedelta(days=31), today - timedelta(days=1)
    url = f"https://github.com/users/{USERNAME}/contributions?from={start}&to={end}"
    request = Request(url, headers={"User-Agent": "profile-activity", "Accept-Language": "en-US"})
    with urlopen(request, timeout=30) as response:
        calendar = Calendar()
        calendar.feed(response.read().decode("utf-8"))
    data = {date: calendar.counts[key] for key, date in calendar.dates.items() if key in calendar.counts}
    dates = [start + timedelta(days=i) for i in range(31)]
    if any(day.isoformat() not in data for day in dates):
        raise RuntimeError("Incomplete GitHub calendar; preserving the previous graph.")
    values = [data[day.isoformat()] for day in dates]
    maximum = max(4, max(values))
    coords = [(54 + i * 21.4, 191 - value / maximum * 126) for i, value in enumerate(values)]
    points = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    svg = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 750 250" role="img" aria-labelledby="title desc">
<title id="title">{USERNAME}'s contribution activity</title>
<desc id="desc">{sum(values)} contributions from {start} through {end}. Source: GitHub public contribution calendar. Updated {today} UTC.</desc>
<rect x="0.5" y="0.5" width="749" height="249" rx="5" fill="#0d1117" stroke="#30363d"/>
<g font-family="Segoe UI,Arial,sans-serif" font-size="11" fill="#999999">
<text x="375" y="28" text-anchor="middle" font-size="14" fill="#e5e5e5">Contribution activity</text>''']
    for step in range(5):
        y = 191 - step * 31.5
        svg.append(f'<path d="M54 {y}H696" stroke="#242a2d"/><text x="42" y="{y + 4}" text-anchor="end">{maximum * step / 4:g}</text>')
    svg.append(f'<polygon points="54,191 {points} 696,191" fill="#26332a" fill-opacity="0.5"/>')
    svg.append(f'<polyline points="{points}" fill="none" stroke="#e5e5e5" stroke-width="1.8"/>')
    for day, value, (x, y) in zip(dates, values, coords):
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.3" fill="#e5e5e5"><title>{day}: {value} contributions</title></circle>')
    for i in (0, 5, 10, 15, 20, 25, 30):
        svg.append(f'<text x="{coords[i][0]:.1f}" y="213" text-anchor="middle">{dates[i]:%b %d}</text>')
    svg.append(f'<text x="375" y="236" text-anchor="middle">{sum(values)} contributions · 31 completed days · updated {today} UTC</text></g></svg>')
    output = ROOT / "assets" / "activity.svg"
    output.write_text("\n".join(svg), encoding="utf-8")
    print(f"Updated {output.name}: {start} to {end}, {sum(values)} contributions")


if __name__ == "__main__":
    main()
