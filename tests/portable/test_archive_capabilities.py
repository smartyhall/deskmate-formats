"""Keep the capability registry honest against the code that backs it."""

from copy import deepcopy
import bz2
from io import BytesIO
import json
import lzma
from pathlib import Path
from struct import pack, pack_into
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / 'tools' / 'archive'
with patch.object(sys, 'path', [str(TOOLS), *sys.path]):
    import capabilities
    import intelligence_extract


REGISTRY = ROOT / 'docs' / 'archive-capabilities.json'
DOCUMENT = ROOT / 'docs' / 'archive-capabilities.md'


def imd_specimen():
    track = bytearray([3, 0, 0, 1, 2, 1, 1])
    track.extend(b'IMD control sector'.ljust(512, b'\0'))
    return b'IMD 1.18: registry control\r\n\x1a' + bytes(track)


def td0_specimen():
    check = (ord('T') + ord('D') + 0) & 0xFF
    header = b'TD' + bytes([0, check, 0x15, 2, 4, 0, 0, 1]) + b'\0\0'
    sector = bytearray([0, 0, 1, 2, 0, 0])
    block = b'TD0 control sector'.ljust(512, b'\0')
    sector.extend(pack('<HB', len(block) + 1, 0))
    sector.extend(block)
    return header + bytes([1, 0, 0, 0]) + bytes(sector) + b'\xff'


def copyqm_specimen():
    header = bytearray(133)
    header[0:3] = b'CQ\x14'
    pack_into('<HBHBHHBHHH', header, 3, 512, 1, 1, 1, 16, 1, 0xf0, 1, 1, 1)
    header[0x5A] = 1
    header[0x5B] = 1
    header[0x84] = (-sum(header)) & 0xFF
    return bytes(header) + pack('<h', -512) + b'\x5a'


def fat_specimen():
    image = bytearray(10 * 512)
    image[:11] = b'\xeb\x3c\x90REGTEST1'
    pack_into('<HBHBHHBH', image, 11, 512, 1, 1, 1, 16, 10, 0xf0, 1)
    pack_into('<HH', image, 24, 10, 1)
    image[512:518] = b'\xf0\xff\xff\xff\xff\xff'
    return bytes(image)


def arc_specimen():
    payload = b'arc control'
    name = b'REG.TXT\0ABC'
    header = name + pack('<IHHHI', len(payload), 0, 0, intelligence_extract._arc_crc(payload),
                         len(payload))
    return b'\x1a\x02' + header + payload + b'\x1a\0'


def tar_specimen():
    data = BytesIO()
    with tarfile.open(fileobj=data, mode='w') as package:
        item = tarfile.TarInfo('REG.TXT')
        item.size = 4
        package.addfile(item, BytesIO(b'reg\n'))
    return data.getvalue()


def zip_specimen():
    data = BytesIO()
    with zipfile.ZipFile(data, 'w') as package:
        package.writestr('REG.TXT', b'reg\n')
    return data.getvalue()


def lzh_specimen():
    return b'\x16\x00-lh0--' + bytes(40)


# Registry id -> (specimen builder, expected identifier from identify()).
CLAIMED_IDENTIFICATION = {
    'zip': (zip_specimen, 'zip'),
    'tar': (tar_specimen, 'tar'),
    'gzip': (lambda: __import__('gzip').compress(b'reg\n', mtime=0), 'gz'),
    'arc': (arc_specimen, 'arc'),
    'lzh': (lzh_specimen, 'lzh'),
    'unix-compress': (lambda: b'\x1f\x9d\x90\x00\x00', 'unix-compress'),
    'bzip2': (lambda: bz2.compress(b'reg\n'), 'bzip2'),
    'xz': (lambda: lzma.compress(b'reg\n', format=lzma.FORMAT_XZ), 'xz'),
    'imd': (imd_specimen, 'imd'),
    'td0': (td0_specimen, 'td0'),
    'copyqm': (copyqm_specimen, 'copyqm'),
    'fat12-fat16': (fat_specimen, 'fat'),
    'pdf': (lambda: b'%PDF-1.4\ncontrol\n', 'pdf'),
    'mz': (lambda: b'MZ\0\0registry control', 'mz'),
}


class RegistryIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.registry = capabilities.load(REGISTRY)

    def test_registry_validates_and_entry_points_exist(self):
        capabilities.validate(self.registry)
        capabilities.check_implementations(self.registry, capabilities._modules())

    def test_every_claimed_identification_matches_the_implementation(self):
        records = {record['id']: record for record in self.registry['formats']}
        for identifier, (builder, expected) in CLAIMED_IDENTIFICATION.items():
            with self.subTest(format=identifier):
                self.assertIn(identifier, records)
                status = records[identifier]['operations']['identify']
                self.assertIn(status, ('qualified', 'partial'))
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / 'opaque-payload'
                    path.write_bytes(builder())
                    self.assertEqual(intelligence_extract.identify(path, 'opaque-payload'), expected)

    def test_planned_and_unimplemented_records_claim_no_capability(self):
        for record in self.registry['formats']:
            if record['implementation'] is not None:
                continue
            with self.subTest(format=record['id']):
                for operation, status in record['operations'].items():
                    self.assertIn(status, ('planned', 'blocked', 'unsupported'),
                                  msg=f'{record["id"]}.{operation} claims {status}')

    def test_blocked_record_names_its_blocker(self):
        dcf = next(record for record in self.registry['formats'] if record['id'] == 'dcf')
        self.assertIsNone(dcf['implementation'])
        self.assertIn('Blocked', dcf['limitations'])
        self.assertIn('no published byte-level specification', dcf['limitations'])

    def test_generated_document_matches_the_registry(self):
        rendered = capabilities.render_markdown(capabilities.validate(self.registry))
        self.assertEqual(DOCUMENT.read_text(encoding='utf-8'), rendered)

    def test_rendering_is_stable_and_covers_every_record(self):
        first = capabilities.render_markdown(self.registry)
        second = capabilities.render_markdown(deepcopy(self.registry))
        self.assertEqual(first, second)
        for record in self.registry['formats']:
            self.assertIn(record['title'], first)
        self.assertNotIn('\r\n', first)


class RegistryRejectionTests(unittest.TestCase):
    def setUp(self):
        self.registry = capabilities.load(REGISTRY)

    def modified(self, change):
        registry = deepcopy(self.registry)
        change(registry)
        return registry

    def test_claims_without_an_implementation_are_rejected(self):
        def strip(registry):
            registry['formats'][0]['implementation'] = None
        with self.assertRaisesRegex(ValueError, 'without an implementation'):
            capabilities.validate(self.modified(strip))

    def test_duplicate_identifier_is_rejected(self):
        def duplicate(registry):
            registry['formats'].append(deepcopy(registry['formats'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate format id'):
            capabilities.validate(self.modified(duplicate))

    def test_unknown_status_and_missing_limitations_are_rejected(self):
        def bad_status(registry):
            registry['formats'][0]['operations']['extract'] = 'probably'
        with self.assertRaisesRegex(ValueError, 'unknown status'):
            capabilities.validate(self.modified(bad_status))

        def no_limits(registry):
            del registry['formats'][0]['limitations']
        with self.assertRaisesRegex(ValueError, 'limitations statement'):
            capabilities.validate(self.modified(no_limits))

    def test_missing_identification_block_is_rejected(self):
        def no_identification(registry):
            del registry['formats'][0]['identification']
        with self.assertRaisesRegex(ValueError, 'identification block is required'):
            capabilities.validate(self.modified(no_identification))

    def test_unknown_completeness_and_method_are_rejected(self):
        def bad_completeness(registry):
            registry['formats'][0]['identification']['completeness'] = 'probably'
        with self.assertRaisesRegex(ValueError, 'unknown completeness'):
            capabilities.validate(self.modified(bad_completeness))

        def bad_method(registry):
            registry['formats'][0]['identification']['methods'] = ['telepathy']
        with self.assertRaisesRegex(ValueError, 'unknown extraction method'):
            capabilities.validate(self.modified(bad_method))

        def bad_carrier(registry):
            registry['formats'][0]['identification']['carrier'] = 'a.out'
        with self.assertRaisesRegex(ValueError, 'unknown carrier'):
            capabilities.validate(self.modified(bad_carrier))

    def test_identification_axes_are_rendered_for_every_record(self):
        rendered = capabilities.render_markdown(self.registry)
        self.assertIn('## Identification axes', rendered)
        self.assertEqual(rendered.count('- Structural identification: '),
                         len(self.registry['formats']))
        self.assertEqual(rendered.count('- Container completeness: '),
                         len(self.registry['formats']))
        # A carrier and an embedded archive appear together rather than one
        # replacing the other.
        self.assertIn('| ZIP archive | mz | zip |', rendered)

    def test_dangling_entry_point_is_rejected(self):
        def dangling(registry):
            registry['formats'][0]['implementation']['entry'] = 'not_a_real_function'
        registry = capabilities.validate(self.modified(dangling))
        with self.assertRaisesRegex(ValueError, 'does not exist'):
            capabilities.check_implementations(registry, capabilities._modules())

    def test_stale_document_is_reported_by_the_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            stale = Path(directory) / 'capabilities.md'
            stale.write_text('obsolete\n', encoding='utf-8')
            self.assertEqual(capabilities.main(['--output', str(stale)]), 1)
            self.assertEqual(capabilities.main(['--output', str(stale), '--write']), 0)
            self.assertEqual(capabilities.main(['--output', str(stale)]), 0)


if __name__ == '__main__':
    unittest.main()
