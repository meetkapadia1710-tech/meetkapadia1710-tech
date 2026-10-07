import importlib.util
import subprocess
import sys
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
            (self.directory / filename).write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>123 contributions</text></svg>', encoding='utf-8')

    def replace(self, text):
        (self.directory / 'github-stats.svg').write_text(text, encoding='utf-8')

    def replace_content(self, content):
        self.replace(f'<svg xmlns="http://www.w3.org/2000/svg">{content}</svg>')

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

    def test_nonrendering_content_blocks_publication(self):
        for content in [
            '<text/>', '<text> \n\t </text>',
            '<defs><path d="M0 0 L10 10"/></defs>',
            '<symbol><text>123 contributions</text></symbol>',
            '<g display="none"><text>123 contributions</text></g>',
            '<g style="display: none !important"><text>123 contributions</text></g>',
            '<g visibility="hidden"><text>123 contributions</text></g>',
            '<g visibility="hidden"><text visibility="inherit">123</text></g>',
            '<text><tspan display="none">123 contributions</tspan></text>',
            '<rect width="0" height="20"/>', '<path d=""/>',
            '<path d="M0 0"/>', '<circle r="0"/>',
            '<rect width="20" height="20" fill="none"/>',
            '<g fill="none"><rect width="20" height="20"/></g>',
            '<g fill="none"><text>123 contributions</text></g>',
            '<polygon points="0,0 10,10"/>',
            '<image width="20" height="20"/>',
            '<use href="#missing"/>',
            '<defs><use id="loop" href="#loop"/></defs><use href="#loop"/>',
        ]:
            with self.subTest(content=content):
                self.replace_content(content)
                with self.assertRaisesRegex(ValueError, 'no visible content'):
                    assets.validate_assets(self.directory)

    def test_visible_svg_content_is_accepted(self):
        for content in [
            '<ellipse cx="20" cy="20" rx="10" ry="10"/>',
            '<rect width="20" height="20"/>', '<circle r="10"/>',
            '<path d="M0 0 L10 10"/>',
            '<polygon points="0,0 10,0 10,10"/>',
            '<polyline points="0,0 10,10" stroke="white" fill="none"/>',
            '<line x2="10" stroke="white"/>',
            '<g fill="none" stroke="white"><rect width="20" height="20"/></g>',
            '<image width="20" height="20" href="data:image/png;base64,test"/>',
            '<text><tspan>123 contributions</tspan></text>',
            '<g visibility="hidden"><text visibility="visible">123</text></g>',
            '<defs><path id="curve" d="M0 0 L10 10"/></defs><use href="#curve"/>',
            '<defs><symbol id="label"><text>123</text></symbol></defs><use href="#label"/>',
            '<text style="opacity:0; animation:fadein 1s forwards">123 contributions</text>',
        ]:
            with self.subTest(content=content):
                self.replace_content(content)
                self.assertEqual(assets.validate_assets(self.directory), 5)

    def test_error_messages_with_split_text_and_whitespace(self):
        for content in [
            '<text><tspan>Something went</tspan>\n  <tspan>wrong!</tspan></text>',
            '<text>API\n\t rate   limit exceeded</text>',
            '<text>Service unavailable</text>',
            '<text>Failed to retrieve contributions</text>',
            '<text>Bad credentials</text>',
        ]:
            with self.subTest(content=content):
                self.replace_content(content)
                with self.assertRaisesRegex(ValueError, 'error card'):
                    assets.validate_assets(self.directory)

    def test_cli_success_and_failure(self):
        command = [sys.executable, '-B', str(Path(assets.__file__)), str(self.directory)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Validated all 5', result.stdout)
        self.replace_content('<text/>')
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('no visible content', result.stderr)
        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
