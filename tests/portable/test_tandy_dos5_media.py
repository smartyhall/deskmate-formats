"""Synthetic FAT12 media controls; no original DOS files required."""
import hashlib
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('dos5_media',
    Path(__file__).resolve().parents[2] / 'tools/experimental/tandy_dos5_media.py')
media = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(media)


def synthetic():
    data = bytearray(1474560)
    struct.pack_into('<H', data, 11, 512)
    struct.pack_into('<H', data, 14, 1)
    data[16] = 2
    struct.pack_into('<H', data, 17, 224)
    struct.pack_into('<H', data, 22, 9)
    # Independently assembled occupied directory entry; preserved byte for byte.
    data[9728:9760] = b'FIXTURE TXT' + bytes([32]) + bytes(20)
    return bytes(data)


class MediaTests(unittest.TestCase):
    def test_label_changes_only_twelve_bytes_in_a_new_slot(self):
        original = synthetic()
        derived, manifest = media.add_label(original)
        self.assertEqual(original, synthetic())
        self.assertEqual(derived[:9760], original[:9760])
        self.assertEqual(derived[9760:9772], b'DISK      2\x08')
        self.assertEqual(derived[9772:], original[9772:])
        self.assertEqual(manifest['changed_offsets'], list(range(9760, 9772)))
        self.assertEqual(manifest['derived_sha256'], hashlib.sha256(derived).hexdigest())

    def test_existing_label_invalid_bpb_and_full_directory_rejected(self):
        labeled, _ = media.add_label(synthetic())
        full = bytearray(synthetic())
        for i in range(9728, 16896, 32):
            full[i] = 65
        for data in (labeled, bytes(1474560), bytes(full), b'short'):
            with self.assertRaises(ValueError):
                media.add_label(data)
        with self.assertRaises(ValueError):
            media.add_label(synthetic(), b'bad\n')

    def test_hash_failure_publishes_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'MSDOS1.img').write_bytes(synthetic())
            with self.assertRaisesRegex(ValueError, 'verification failed'):
                media.stage(root, root / 'new')
            self.assertFalse((root / 'new').exists())

    def test_staging_never_overwrites_existing_research_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, target = root / 'original', root / 'working'
            source.mkdir()
            expected = {}
            for name in ('MSDOS1.img', 'MSDOS2.img'):
                data = synthetic()
                (source / name).write_bytes(data)
                expected[name] = hashlib.sha256(data).hexdigest()
            with patch.object(media, 'EXPECTED', expected):
                media.stage(source, target)
                before = (target / 'MSDOS2-labeled.img').read_bytes()
                with self.assertRaises(FileExistsError):
                    media.stage(source, target)
                self.assertEqual((target / 'MSDOS2-labeled.img').read_bytes(), before)
                self.assertEqual((source / 'MSDOS2.img').read_bytes(), synthetic())


if __name__ == '__main__':
    unittest.main()
