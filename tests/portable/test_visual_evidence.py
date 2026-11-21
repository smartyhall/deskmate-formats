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

    def test_disappearing_evidence_retains_metadata_across_multiple_rescans(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'evidence'
            root.mkdir()
            capture = root / 'capture.png'
            with Image.new('RGB', (5, 4), 'blue') as image:
                image.save(capture)
            first = scan({'guest': root}, {}, {})
            key, = first['occurrences']
            original = first['occurrences'][key]
            sha = original['sha256']
            capture.unlink()
            second = scan({'guest': root}, {}, first)
            third = scan({'guest': root}, {}, second)
            for result in (second, third):
                self.assertEqual(result['occurrences'][key]['sha256'], sha)
                self.assertEqual(result['occurrences'][key]['locator'], str(capture))
                self.assertFalse(result['occurrences'][key]['observed'])
                self.assertIn(sha, result['images'])
                self.assertIn(key, result['unobserved_previous_occurrences'])
                self.assertEqual(result['summary']['occurrences'], 0)
                self.assertEqual(result['summary']['retained_occurrences'], 1)
            with Image.new('RGB', (5, 4), 'blue') as image:
                image.save(capture)
            restored = scan({'guest': root}, {}, third)
            self.assertTrue(restored['occurrences'][key]['observed'])
            self.assertEqual(restored['occurrences'][key]['sha256'], sha)
            self.assertEqual(restored['unobserved_previous_occurrences'], [])

    def test_offline_root_retains_prior_identity_and_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'evidence'
            root.mkdir()
            with Image.new('RGB', (3, 3), 'red') as image:
                image.save(root / 'one.png')
            first = scan({'guest': root}, {'guest': {'machine': 'reference-guest'}}, {})
            root.rename(Path(temp) / 'offline')
            latest = scan({'guest': root}, {}, first)
            key, = first['occurrences']
            self.assertEqual(latest['occurrences'][key]['provenance'],
                             first['occurrences'][key]['provenance'])
            self.assertFalse(latest['occurrences'][key]['observed'])
            self.assertEqual(len(latest['gaps']), 1)

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
