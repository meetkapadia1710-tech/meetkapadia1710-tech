"""Generate a contribution graph directly from GitHub, without a hosted renderer."""
import argparse
from datetime import date, datetime, time, timedelta, timezone
from html import escape
import json
import math
import os
from pathlib import Path
import urllib.error
import urllib.request

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def parse_days(payload, start, end):
    """Reject failed or incomplete API responses instead of drawing fake zeroes."""
    if payload.get('errors'):
        raise ValueError('GitHub returned a contribution query error')
    try:
        weeks = payload['data']['user']['contributionsCollection']['contributionCalendar']['weeks']
        days = {}
        for week in weeks:
            for entry in week['contributionDays']:
                day = date.fromisoformat(entry['date'])
                count = entry['contributionCount']
                if type(count) is not int or count < 0:
                    raise ValueError('Invalid contribution count')
                if start <= day <= end:
                    if day in days:
                        raise ValueError('Duplicate contribution date')
                    days[day] = count
    except (KeyError, TypeError) as error:
        raise ValueError('Missing GitHub contribution data') from error
    expected = [start + timedelta(days=index) for index in range((end - start).days + 1)]
    if not expected or any(day not in days for day in expected):
        raise ValueError('Incomplete GitHub contribution calendar')
    return [(day, days[day]) for day in expected]


def fetch_days(username, token, now=None):
    if not token:
        raise ValueError('Set GITHUB_TOKEN to fetch contribution data')
    now = now or datetime.now(timezone.utc)
    end = now.date()
    start = end - timedelta(days=30)
    variables = {
        'login': username,
        'from': datetime.combine(start, time.min, timezone.utc).isoformat(),
        'to': now.isoformat(),
    }
    request = urllib.request.Request(
        'https://api.github.com/graphql',
        data=json.dumps({'query': QUERY, 'variables': variables}).encode('utf-8'),
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json',
                 'User-Agent': 'github-profile-activity-graph'},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    return parse_days(payload, start, end)


def render_graph(username, days):
    if not days:
        raise ValueError('Cannot render an empty contribution calendar')
    left, right, top, bottom = 65, 1035, 90, 235
    peak = max(count for _, count in days)
    ceiling = max(4, math.ceil(peak / 4) * 4)
    points = [
        (left + index * (right - left) / max(1, len(days) - 1),
         bottom - count * (bottom - top) / ceiling)
        for index, (_, count) in enumerate(days)
    ]
    coordinates = ' '.join(f'{x:.1f},{y:.1f}' for x, y in points)
    total = sum(count for _, count in days)
    title = f'{username} — Contribution Activity'
    description = f'{total} contributions from {days[0][0]} to {days[-1][0]} (UTC)'
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="300" '
        'viewBox="0 0 1100 300" role="img" aria-labelledby="title description">',
        f'<title id="title">{escape(title)}</title>',
        f'<desc id="description">{escape(description)}</desc>',
        '<rect width="1100" height="300" rx="12" fill="#0d1117"/>',
        '<g font-family="Segoe UI, Arial, sans-serif">',
        '<text x="35" y="37" fill="#c4b5fd" font-size="21" font-weight="600">Contribution Activity</text>',
        f'<text x="35" y="62" fill="#9ca3af" font-size="13">{escape(description)}</text>',
    ]
    for index in range(5):
        value = ceiling * index // 4
        y = bottom - index * (bottom - top) / 4
        parts.extend([
            f'<path d="M{left},{y:.1f} H{right}" stroke="#21262d" fill="none"/>',
            f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" fill="#9ca3af" font-size="12">{value}</text>',
        ])
    parts.extend([
        f'<polygon points="{left},{bottom} {coordinates} {points[-1][0]:.1f},{bottom}" fill="#8b5cf6" fill-opacity="0.12"/>',
        f'<polyline points="{coordinates}" fill="none" stroke="#a78bfa" stroke-width="2.5" stroke-linejoin="round"/>',
    ])
    for (day, count), (x, y) in zip(days, points):
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#c4b5fd"><title>{day}: {count} contributions</title></circle>')
    for index in sorted(set(range(0, len(days), 5)) | {len(days) - 1}):
        day = days[index][0]
        parts.append(f'<text x="{points[index][0]:.1f}" y="260" text-anchor="middle" fill="#9ca3af" font-size="12">{day:%d %b}</text>')
    parts.append('</g></svg>')
    return '\n'.join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('username')
    parser.add_argument('--output', type=Path, default=Path('dist/github-activity-graph.svg'))
    args = parser.parse_args()
    try:
        days = fetch_days(args.username, os.environ.get('GITHUB_TOKEN'))
        svg = render_graph(args.username, days)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(svg, encoding='utf-8')
    except (OSError, ValueError, urllib.error.URLError) as error:
        parser.exit(1, f'Activity graph generation failed: {error}\n')
    print(f'Generated {args.output} from {len(days)} days of GitHub data')


if __name__ == '__main__':
    main()
