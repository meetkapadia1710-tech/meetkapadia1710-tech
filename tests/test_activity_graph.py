import importlib.util
import io
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

spec = importlib.util.spec_from_file_location(
    'graph', Path(__file__).resolve().parents[1] / 'scripts/generate_activity_graph.py')
graph = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graph)


def calendar(entries):
    return {'data': {'user': {'contributionsCollection': {
        'contributionCalendar': {'weeks': [{'contributionDays': entries}]}
    }}}}


class ActivityGraphTests(unittest.TestCase):
    def setUp(self):
        self.start = date(2026, 9, 8)
        self.end = date(2026, 10, 8)
        self.entries = [
            {'date': str(self.start + timedelta(days=index)), 'contributionCount': index % 5}
            for index in range(31)
        ]

    def test_calendar_is_sorted_and_padding_is_excluded(self):
        entries = list(reversed(self.entries)) + [{'date': '2026-09-07', 'contributionCount': 9}]
        days = graph.parse_days(calendar(entries), self.start, self.end)
        self.assertEqual(len(days), 31)
        self.assertEqual(days[0], (self.start, 0))
        self.assertEqual(days[-1], (self.end, 0))

    def test_failed_or_incomplete_calendars_are_rejected(self):
        for payload in [
            {'errors': [{'message': 'rate limited'}]}, {'data': {'user': None}},
            calendar([]), calendar(self.entries[:-1]),
            calendar(self.entries + [self.entries[0]]),
        ]:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    graph.parse_days(payload, self.start, self.end)

    def test_invalid_counts_are_rejected(self):
        for count in [-1, '3', True, None]:
            with self.subTest(count=count):
                entries = [dict(entry) for entry in self.entries]
                entries[0]['contributionCount'] = count
                with self.assertRaisesRegex(ValueError, 'Invalid contribution count'):
                    graph.parse_days(calendar(entries), self.start, self.end)

    def test_fetch_requests_a_31_day_utc_calendar(self):
        body = io.BytesIO(json.dumps(calendar(self.entries)).encode())
        with patch.object(graph.urllib.request, 'urlopen', return_value=body) as request:
            days = graph.fetch_days('example', 'test-token', datetime(2026, 10, 8, 12, tzinfo=timezone.utc))
        self.assertEqual(len(days), 31)
        payload = json.loads(request.call_args.args[0].data)
        self.assertEqual(payload['variables']['from'], '2026-09-08T00:00:00+00:00')
        self.assertEqual(payload['variables']['to'], '2026-10-08T12:00:00+00:00')

    def test_missing_token_fails_before_network_access(self):
        with patch.object(graph.urllib.request, 'urlopen') as request:
            with self.assertRaisesRegex(ValueError, 'GITHUB_TOKEN'):
                graph.fetch_days('example', '')
            request.assert_not_called()

    def test_graph_renders_real_values_and_escapes_text(self):
        days = graph.parse_days(calendar(self.entries), self.start, self.end)
        svg = graph.render_graph('example<&', days)
        root = ET.fromstring(svg)
        namespace = '{http://www.w3.org/2000/svg}'
        self.assertEqual(len(root.findall(namespace + 'g/' + namespace + 'circle')), 31)
        self.assertIn('example&lt;&amp;', svg)
        self.assertIn('60 contributions', svg)
        self.assertIn('2026-09-12: 4 contributions', svg)

    def test_zero_activity_is_valid_but_missing_data_is_not(self):
        svg = graph.render_graph('example', [(self.start + timedelta(days=i), 0) for i in range(31)])
        ET.fromstring(svg)
        self.assertIn('0 contributions', svg)
        self.assertNotIn('nan', svg.lower())
        self.assertNotIn('inf', svg.lower())
        with self.assertRaisesRegex(ValueError, 'empty'):
            graph.render_graph('example', [])

    def test_api_failure_preserves_existing_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp, 'graph.svg')
            output.write_text('existing graph', encoding='utf-8')
            with patch('sys.argv', ['generate_activity_graph.py', 'example', '--output', str(output)]), \
                    patch.object(graph, 'fetch_days', side_effect=ValueError('API unavailable')), \
                    patch('sys.stderr', new_callable=io.StringIO):
                with self.assertRaises(SystemExit) as error:
                    graph.main()
            self.assertEqual(error.exception.code, 1)
            self.assertEqual(output.read_text(encoding='utf-8'), 'existing graph')


if __name__ == '__main__':
    unittest.main()
