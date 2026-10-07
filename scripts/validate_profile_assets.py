"""Reject missing, malformed, or error-card SVGs before publishing profile assets."""
import argparse
import math
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
    r'an error occurred|invalid user|user not found|service unavailable|'
    r'failed to (?:fetch|retrieve)|bad credentials', re.IGNORECASE,
)
NON_RENDERING = {SVG + tag for tag in (
    'defs', 'symbol', 'clipPath', 'mask', 'pattern', 'marker',
    'metadata', 'title', 'desc', 'style', 'script',
)}
NUMBER = re.compile(r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?')


def has_visible_content(root):
    """Check basic SVG content, without claiming to implement a CSS renderer.

    Ignore definitions and display:none subtrees, honor inherited visibility,
    and require nonempty text or usable geometry. CSS animations are left alone:
    generated cards commonly start with opacity:0 before fading in.
    """
    identifiers = {element.get('id'): element for element in root.iter()
                   if element.get('id')}

    def visit(element, visibility='visible', active=frozenset(),
              fill='black', stroke='none', reference=False):
        if element.tag in NON_RENDERING and not reference:
            return False
        properties = dict(element.attrib)
        for declaration in element.get('style', '').split(';'):
            name, separator, value = declaration.partition(':')
            if separator:
                properties[name.strip().lower()] = value.strip().removesuffix('!important').strip()
        if properties.get('display', '').lower() == 'none':
            return False
        requested_visibility = properties.get('visibility', visibility).lower()
        if requested_visibility != 'inherit':
            visibility = requested_visibility
        requested_fill = properties.get('fill', fill).lower()
        requested_stroke = properties.get('stroke', stroke).lower()
        if requested_fill != 'inherit':
            fill = requested_fill
        if requested_stroke != 'inherit':
            stroke = requested_stroke
        painted = fill != 'none' or stroke != 'none'

        def positive(name):
            match = NUMBER.match(element.get(name, '').strip())
            return bool(match and float(match.group()) > 0
                        and math.isfinite(float(match.group())))

        if visibility not in {'hidden', 'collapse'}:
            tag = element.tag.removeprefix(SVG)
            if painted and tag in {'text', 'tspan'} and (
                (element.text or '').strip()
                or any((child.tail or '').strip() for child in element)
            ):
                return True
            if painted:
                if tag == 'rect' and positive('width') and positive('height'):
                    return True
                if tag == 'circle' and positive('r'):
                    return True
                if tag == 'ellipse' and positive('rx') and positive('ry'):
                    return True
                if tag == 'path' and re.search(r'[LlHhVvCcSsQqTtAa]', element.get('d', '')):
                    return True
                if tag in {'polygon', 'polyline'}:
                    point_values = NUMBER.findall(element.get('points', ''))
                    if len(point_values) % 2 == 0 and (
                        len(point_values) >= 6 or (len(point_values) >= 4 and stroke != 'none')
                    ):
                        return True
                if tag == 'line' and stroke != 'none' and (
                    element.get('x1', '0') != element.get('x2', '0')
                    or element.get('y1', '0') != element.get('y2', '0')
                ):
                    return True
            if tag == 'use':
                href = element.get('href', element.get('{http://www.w3.org/1999/xlink}href', ''))
                identifier = href.removeprefix('#')
                if href.startswith('#') and identifier in identifiers and identifier not in active:
                    if visit(identifiers[identifier], visibility, active | {identifier},
                             fill, stroke, reference=True):
                        return True
            if tag == 'image' and positive('width') and positive('height') and (
                element.get('href') or element.get('{http://www.w3.org/1999/xlink}href')
            ):
                return True
        return any(visit(child, visibility, active, fill, stroke) for child in element)

    return visit(root)


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
        text = ' '.join(' '.join(root.itertext()).split())
        if ERROR_MESSAGE.search(text):
            raise ValueError(f'Generated an error card instead of profile data: {path}')
        if not has_visible_content(root):
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
