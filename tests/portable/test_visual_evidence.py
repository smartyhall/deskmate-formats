"""Verify stable private evidence identity and original-byte deduplication."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
try:
    from PIL import Image
    from visual_evidence import scan
except ModuleNotFoundError:
    Image = None


@unittest.skipIf(Image is None, 'Pillow is optional')
class VisualEvidenceTests(unittest.TestCase):
    def test_distinct_occurrences_share_bytes_and_survive_rescan(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / 'first.png'
            second = root / 'second.png'
            with Image.new('RGB', (4, 3), 'red') as original:
                original.save(first)
            second.write_bytes(first.read_bytes())
            observed = scan({'evidence': root}, {}, {})
            self.assertEqual(observed['summary']['occurrences'], 2)
            self.assertEqual(observed['summary']['identities'], 1)
            image, = observed['images'].values()
            self.assertEqual(image['display_pixels'], [4, 3])
            repeated = scan({'evidence': root}, {}, observed)
            self.assertEqual(observed, repeated)
            second.unlink()
            latest = scan({'evidence': root}, {}, repeated)
            self.assertEqual(len(latest['unobserved_previous_occurrences']), 1)
            self.assertEqual(latest['summary']['occurrences'], 1)

    def test_still_bmp_defaults_to_one_frame(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with Image.new('RGB', (2, 2), 'navy') as image:
                image.save(root / 'still.bmp')
            observation, = scan({'bitmap': root}, {}, {})['images'].values()
            self.assertEqual((observation['format'], observation['frames']), ('BMP', 1))

    def test_reports_missing_root_and_unreadable_image(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'truncated.png').write_bytes(b'not a PNG')
            result = scan({'available': root, 'missing': root / 'missing'}, {}, {})
            self.assertEqual(result['summary']['occurrences'], 0)
            self.assertEqual(len(result['gaps']), 2)


if __name__ == '__main__':
    unittest.main()
