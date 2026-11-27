"""Keep the identification axes separate and their identifiers consistent.

A file name, a structural container, an executable carrier and an embedded
payload are four observations of one artifact. These tests pin the identifiers
each axis uses, confirm that a name disagreement is judged against every
identity the bytes carry, and confirm that a second identity never hides a
genuine discrepancy.
"""

from pathlib import Path
import io
import struct
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch


TOOLS = Path(__file__).resolve().parents[2] / 'tools' / 'archive'
with patch.object(sys, 'path', [str(TOOLS), *sys.path]):
    import intelligence_extract as extractor


def zip_payload(name='MEMBER.TXT', data=b'payload\r\n'):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr(name, data)
    return buffer.getvalue()


def self_extracting_archive():
    """An MZ/PE stub followed by a readable ZIP payload."""
    stub = bytearray(b'MZ')
    stub += bytes(0x40 - len(stub))
    struct.pack_into('<I', stub, 0x3C, 0x40)
    stub += b'PE\0\0' + bytes(64)
    return bytes(stub) + zip_payload()


def td0_header(cylinders=80):
    header = bytearray(b'TD' + bytes([0, 0x42, 0x15, 0x02, 3, 0, 0, 2]))
    header += b'\0\0'
    return bytes(header) + b'\xff'


class ClassificationAxesTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def classify(self, name, data):
        target = self.root / name
        target.write_bytes(data)
        return extractor.classify(target, name)

    def test_a_dos_com_program_keeps_its_own_identifier(self):
        found = self.classify('PROGRAM.COM', b'\xb4\x09\xba\x10\x01\xcd\x21' + b'\0' * 20)
        self.assertEqual((found.kind, found.extension_kind), ('dos-com', 'dos-com'))
        self.assertEqual(found.evidence, 'extension')
        self.assertEqual(found.confidence, 'probable')
        self.assertFalse(found.unexpected_extension)

    def test_an_mz_file_named_com_is_a_genuine_discrepancy(self):
        found = self.classify('PROGRAM.COM', b'MZ' + bytes(200))
        self.assertEqual((found.kind, found.extension_kind), ('mz', 'dos-com'))
        self.assertEqual(found.evidence, 'structure')
        self.assertEqual(found.confidence, 'certain')
        self.assertTrue(found.unexpected_extension)

    def test_a_unix_compress_stream_uses_one_identifier_everywhere(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_archive_compression import compress_stream
        found = self.classify('NOTES.TXT.Z', compress_stream(b'plain notes\r\n'))
        self.assertEqual((found.kind, found.extension_kind), ('unix-compress', 'unix-compress'))
        self.assertFalse(found.unexpected_extension)
        self.assertIn('unix-compress', extractor.CONTAINER_KINDS)

    def test_text_named_like_a_compress_stream_is_a_discrepancy(self):
        found = self.classify('notes.z', b'ordinary notes about compress\r\n')
        self.assertEqual(found.kind, 'text')
        self.assertTrue(found.unexpected_extension)

    def test_a_self_extracting_archive_keeps_carrier_and_payload(self):
        found = self.classify('SETUP.EXE', self_extracting_archive())
        self.assertEqual(found.kind, 'zip')
        self.assertEqual(found.carrier, 'pe')
        self.assertEqual(found.identities, ('zip', 'pe'))
        self.assertEqual(found.embedded, ('zip',))
        # A PE image is an MZ carrier, so neither name is a lie.
        self.assertFalse(found.unexpected_extension)

    def test_the_same_payload_named_zip_is_also_accepted(self):
        found = self.classify('SETUP.ZIP', self_extracting_archive())
        self.assertFalse(found.unexpected_extension)
        self.assertEqual(found.identities, ('zip', 'pe'))

    def test_a_plain_zip_has_no_carrier(self):
        found = self.classify('DATA.ZIP', zip_payload())
        self.assertEqual((found.kind, found.carrier, found.identities), ('zip', None, ('zip',)))
        self.assertFalse(found.unexpected_extension)

    def test_a_sector_container_named_img_is_a_disk_image(self):
        found = self.classify('DISK.IMG', td0_header())
        self.assertEqual((found.kind, found.extension_kind), ('td0', 'disk-image'))
        self.assertFalse(found.unexpected_extension)
        renamed = self.classify('DISK.TD0', td0_header())
        self.assertFalse(renamed.unexpected_extension)

    def test_a_sector_container_named_for_another_container_is_a_discrepancy(self):
        found = self.classify('DISK.IMD', td0_header())
        self.assertEqual((found.kind, found.extension_kind), ('td0', 'imd'))
        self.assertTrue(found.unexpected_extension)

    def test_a_fat_volume_named_img_is_a_disk_image(self):
        # The rule is exercised directly so the fixture does not need a
        # megabyte of zeros to be recognised as a volume.
        found = extractor.Classification('fat', 'img', 'disk-image', None, (), 'structure')
        self.assertFalse(found.unexpected_extension)
        bare = extractor.Classification('fat', 'td0', 'td0', None, (), 'structure')
        self.assertTrue(bare.unexpected_extension)

    def test_an_embedded_archive_does_not_hide_a_wrong_extension(self):
        # The payload is a genuine second identity, but it must not excuse a
        # suffix that names a third format the identities do not support.
        found = self.classify('SETUP.ARC', self_extracting_archive())
        self.assertEqual(found.identities, ('zip', 'pe'))
        self.assertEqual(found.extension_kind, 'arc')
        self.assertTrue(found.unexpected_extension)
        # A suffix outside the registry makes no claim either way.
        self.assertFalse(self.classify('SETUP.TXT', self_extracting_archive())
                         .unexpected_extension)

    def test_identities_never_collapse_into_one_label(self):
        found = self.classify('SETUP.EXE', self_extracting_archive())
        self.assertGreater(len(found.identities), 1)
        self.assertEqual(len(set(found.identities)), len(found.identities))


if __name__ == '__main__':
    unittest.main()
