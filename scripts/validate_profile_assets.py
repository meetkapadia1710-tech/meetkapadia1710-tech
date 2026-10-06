"""Reject missing, malformed, or error-card SVGs before publishing profile assets."""
import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path

EXPECTED_ASSETS = (
    'github-contribution-grid-snake.svg',
    'github-contribution-grid-snake-dark.svg',
    'github-stats.svg',
    'github-top-langs.svg',
    'github-streak-stats.svg',
)
SVG = '{http://www.w3.org/2000/svg}'
ERROR_MESSAGE = re.compile(
    r'something went wrong|could not fetch|api rate limit|error fetching|'
    r'an error occurred|invalid user|user not found', re.IGNORECASE,
)


def validate_assets(directory):
    for filename in EXPECTED_ASSETS:
        path = directory / filename
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f'Missing or empty profile asset: {path}')
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as error:
            raise ValueError(f'Malformed SVG: {path}') from error
        if root.tag != SVG + 'svg':
            raise ValueError(f'Expected an SVG document: {path}')
        text = ' '.join(root.itertext())
        if ERROR_MESSAGE.search(text):
            raise ValueError(f'Generated an error card instead of profile data: {path}')
        if not any(element.tag in {SVG + tag for tag in ('rect', 'path', 'text', 'circle', 'polygon', 'polyline', 'image', 'use')}
                   for element in root.iter()):
            raise ValueError(f'SVG has no visible content: {path}')
    return len(EXPECTED_ASSETS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', type=Path, default=Path('dist'))
    args = parser.parse_args()
    try:
        count = validate_assets(args.directory)
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    print(f'Validated all {count} profile SVGs')


if __name__ == '__main__':
    main()
