import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('assets', Path(__file__).resolve().parents[1] / 'scripts/validate_profile_assets.py')
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)


class ProfileAssetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        for filename in assets.EXPECTED_ASSETS:
            (self.directory / filename).write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>123 contributions</text></svg>')

    def replace(self, text):
        (self.directory / 'github-stats.svg').write_text(text)

    def test_complete_valid_assets(self):
        self.assertEqual(assets.validate_assets(self.directory), 5)

    def test_missing_asset_blocks_publication(self):
        (self.directory / assets.EXPECTED_ASSETS[0]).unlink()
        with self.assertRaisesRegex(ValueError, 'Missing or empty'):
            assets.validate_assets(self.directory)

    def test_empty_asset_blocks_publication(self):
        self.replace('')
        with self.assertRaisesRegex(ValueError, 'Missing or empty'):
            assets.validate_assets(self.directory)

    def test_malformed_xml_blocks_publication(self):
        self.replace('<svg>')
        with self.assertRaisesRegex(ValueError, 'Malformed SVG'):
            assets.validate_assets(self.directory)

    def test_html_error_page_is_not_an_svg(self):
        self.replace('<html><body>Unavailable</body></html>')
        with self.assertRaisesRegex(ValueError, 'Expected an SVG'):
            assets.validate_assets(self.directory)

    def test_well_formed_error_cards_block_publication(self):
        for message in ['Something went wrong!', 'API rate limit exceeded', 'User not found']:
            with self.subTest(message=message):
                self.replace(f'<svg xmlns="http://www.w3.org/2000/svg"><text>{message}</text></svg>')
                with self.assertRaisesRegex(ValueError, 'error card'):
                    assets.validate_assets(self.directory)

    def test_blank_svg_blocks_publication(self):
        self.replace('<svg xmlns="http://www.w3.org/2000/svg"><title>Stats</title></svg>')
        with self.assertRaisesRegex(ValueError, 'no visible content'):
            assets.validate_assets(self.directory)


if __name__ == '__main__':
    unittest.main()
