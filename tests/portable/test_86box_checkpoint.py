"""Portable controls for checkpoint verification and path relocation."""
import importlib.util
from pathlib import Path
import socket
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    'checkpoint', Path(__file__).resolve().parents[2] / 'tools/86box_checkpoint.py')
checkpoint = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checkpoint)


class CheckpointTests(unittest.TestCase):
    def test_seal_restore_and_mutate_independently(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'original'
            source.mkdir()
            disk = source / 'test.img'
            disk.write_bytes(b'original bytes')
            (source / '86box.cfg').write_text(
                f'[Hard disks]\nhdd_01_fn = {disk}\n', encoding='utf-8-sig')
            (source / 'nvr').mkdir()
            (source / 'nvr/cmos').write_bytes(b'synthetic CMOS')
            sealed = root / 'checkpoint'
            names = ['86box.cfg', 'nvr/cmos', 'test.img']
            checkpoint.save(source, sealed, names)
            with self.assertRaises(ValueError):
                checkpoint.save(source, sealed, names)
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            destination = root / 'clone'
            manifest = sealed / 'machine-files.csv'
            args = (sealed / 'machine', manifest, destination, source, port)
            receipt = checkpoint.restore(*args)
            self.assertEqual(receipt['verified_source_files'], 3)
            self.assertEqual(checkpoint.config(destination / '86box.cfg')['Hard disks']['hdd_01_fn'],
                             'test.img')
            (destination / 'test.img').write_bytes(b'clone bytes')
            self.assertEqual((sealed / 'machine/test.img').read_bytes(), b'original bytes')
            self.assertEqual(disk.read_bytes(), b'original bytes')
            with self.assertRaises(ValueError):
                checkpoint.restore(*args)

    def test_rejects_inventory_escapes(self):
        with tempfile.TemporaryDirectory() as temporary:
            for name in ('../outside', 'directory/../../outside', 'D:/outside', 'drive:stream'):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    checkpoint.inside(Path(temporary), name)


if __name__ == '__main__':
    unittest.main()
