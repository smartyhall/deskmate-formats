"""Exercise bounded extraction with independently authored controls."""

from dataclasses import replace
from gzip import compress
from io import BytesIO
from pathlib import Path
import stat
from struct import pack, pack_into
import sys
import tarfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile


TOOLS = Path(__file__).resolve().parents[2] / 'tools' / 'archive'
with patch.object(sys, 'path', [str(TOOLS), *sys.path]):
    import intelligence_extract as archive


def fat_image(payload):
    sector = 512
    image = bytearray(10 * sector)
    image[:11] = b'\xeb\x3c\x90ARCHTEST'
    pack_into('<HBHBHHBH', image, 11, sector, 1, 1, 1, 16, 10, 0xf0, 1)
    image[sector:sector + 6] = b'\xf0\xff\xff\xff\xff\xff'
    image[2 * sector:2 * sector + 12] = b'DOCS       \x10'
    pack_into('<H', image, 2 * sector + 26, 2)
    image[3 * sector:3 * sector + 12] = b'INDEX   TXT\x20'
    pack_into('<HI', image, 3 * sector + 26, 3, len(payload))
    image[4 * sector:4 * sector + len(payload)] = payload
    return image


def fat_short_checksum(name11):
    """VFAT checksum of an 11-byte short name, written from the algorithm."""
    checksum = 0
    for byte in name11:
        checksum = (((checksum & 1) << 7) + (checksum >> 1) + byte) & 0xFF
    return checksum


def vfat_entry(ordinal, last, units, checksum):
    """One 32-byte long-filename slot holding up to 13 UTF-16 code units."""
    entry = bytearray(32)
    entry[0] = ordinal | (0x40 if last else 0)
    entry[11] = 0x0F
    entry[13] = checksum
    padded = list(units) + [0xFFFF] * (13 - len(units))
    for index in range(5):
        pack_into('<H', entry, 1 + index * 2, padded[index])
    for index in range(6):
        pack_into('<H', entry, 14 + index * 2, padded[5 + index])
    for index in range(2):
        pack_into('<H', entry, 28 + index * 2, padded[11 + index])
    return bytes(entry)


def fat32_image(path, plain, long_payload, *, break_lfn_checksum=False):
    """A sparse FAT32 volume: cluster-based root, 32-bit links, one long name.

    Written with truncate so the 68k-cluster volume costs no real disk space,
    while still exercising the FAT32 cluster count threshold and high cluster
    words rather than a FAT16 layout that happens to parse.
    """
    sector, spc, reserved, copies, fat_sectors, total = 512, 1, 32, 1, 4200, 70000
    first_data = reserved + copies * fat_sectors
    boot = bytearray(sector)
    boot[0:3] = b'\xeb\x58\x90'
    boot[3:11] = b'ARCHTST '
    pack_into('<HBHBHHBH', boot, 11, sector, spc, reserved, copies, 0, 0, 0xf8, fat_sectors)
    pack_into('<HH', boot, 24, 18, 2)
    pack_into('<I', boot, 32, total)
    pack_into('<I', boot, 36, fat_sectors)
    pack_into('<I', boot, 44, 2)
    boot[66] = 0x29
    boot[82:90] = b'FAT32   '
    boot[510:512] = b'\x55\xaa'

    long_cluster = 0x10003
    root = bytearray(sector)
    root[0:11] = b'PLAIN   BIN'
    root[11] = 0x20
    pack_into('<HI', root, 26, 3, len(plain))
    checksum = fat_short_checksum(b'README  TXT')
    if break_lfn_checksum:
        checksum ^= 0xFF
    root[32:64] = vfat_entry(1, True, [ord(c) for c in 'Read Me.txt'] + [0], checksum)
    root[64:75] = b'README  TXT'
    root[75] = 0x20
    pack_into('<H', root, 64 + 20, long_cluster >> 16)
    pack_into('<H', root, 64 + 26, long_cluster & 0xFFFF)
    pack_into('<I', root, 64 + 28, len(long_payload))

    with open(path, 'wb') as handle:
        handle.truncate(total * sector)
        handle.write(boot)
        for cluster in (2, 3, long_cluster):
            handle.seek(reserved * sector + cluster * 4)
            handle.write(pack('<I', 0x0FFFFFFF))
        base = first_data * sector
        handle.seek(base)
        handle.write(bytes(root))
        handle.seek(base + sector)
        handle.write(plain.ljust(sector, b'\0'))
        handle.seek(base + (long_cluster - 2) * sector)
        handle.write(long_payload)


def lha_member(name, data, *, crc=None):
    name = name.encode('ascii')
    crc = archive._arc_crc(data) if crc is None else crc
    header = (b'-lh0-' + pack('<IIBBB', len(data), len(data), 0, 0, 0) +
              b'\0\x20\0' + bytes([len(name)]) + name + pack('<H', crc))
    return bytes([len(header), sum(header) & 255]) + header + data


class ArchiveExtractionTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.payload = self.root / 'opaque-file'

    def classify_and_extract(self, label, **kwargs):
        kind = archive.identify(self.payload, label)
        return kind, archive.extract(self.payload, label, kind, **kwargs)

    def test_sound_sniff_distinguishes_voc_and_incidental_marker(self):
        voc = b'Creative Voice File\x1a' + bytes(40)
        self.payload.write_bytes(voc)
        self.assertEqual(archive.identify(self.payload, 'recording.snd'), 'voc')
        self.payload.write_bytes(b'RIFF\0\0\0\0WAVE' + bytes(40))
        self.assertEqual(archive.identify(self.payload, 'recording.snd'), 'wav')

        menu = b'\x1a\x01\x1e\x01' + bytes(80)
        self.payload.write_bytes(menu)
        self.assertNotEqual(archive.identify(self.payload, 'control.mnu'), 'snd')

        # A complete original descriptor can identify a candidate even when its PCM is short.
        recording = bytearray(58)
        recording[:4] = b'\x1a\x00\x01\x00'
        pack_into('<H', recording, 14, 11000)
        pack_into('<I', recording, 20, 44)
        pack_into('<I', recording, 32, 32)
        self.payload.write_bytes(recording)
        self.assertEqual(archive.identify(self.payload, 'recording.bin'), 'snd')

    def test_zip_paths_links_and_budgets(self):
        with zipfile.ZipFile(self.payload, 'w') as package:
            package.writestr('README.TXT', b'index control')
            package.writestr('d/a.txt', b'012345678901')
            package.writestr('../escape.txt', b'unreachable')
            package.writestr(r'C:\temp\escape.txt', b'unreachable')
            item = zipfile.ZipInfo('symbolic-link')
            item.create_system = 3
            item.external_attr = (stat.S_IFLNK | 0o777) << 16
            package.writestr(item, b'../escape')
        limits = replace(archive.Limits(), total_bytes=16)
        kind, result = self.classify_and_extract('mislabeled.bin', limits=limits)
        self.assertEqual(kind, 'zip')
        self.assertEqual(result.status, 'partial')
        self.assertEqual([m.status for m in result.members],
                         ['ok', 'byte-limit', 'unsafe-path', 'unsafe-path', 'non-regular'])
        self.assertEqual(result.members[0].data, b'index control')
        self.assertEqual(list(self.root.iterdir()), [self.payload])

    def test_container_failures_and_count_limit(self):
        self.payload.write_bytes(b'PK\x03\x04 invalid structure')
        self.assertEqual(self.classify_and_extract('bad.exe')[1].status, 'failed')
        with zipfile.ZipFile(self.payload, 'w') as package:
            package.writestr('1.txt', b'one')
            package.writestr('2.txt', b'two')
        limits = replace(archive.Limits(), members=1)
        _, result = self.classify_and_extract('control.zip', limits=limits)
        self.assertEqual((result.status, result.detail), ('partial', 'member-count-limit'))
        self.assertEqual(result.members[0].name, '1.txt')

    def test_legacy_zip_requires_exact_size_and_crc(self):
        payload = b'ZIP fallback control'
        with zipfile.ZipFile(self.payload, 'w') as package:
            package.writestr('INDEX.TXT', payload)
        data = bytearray(self.payload.read_bytes())
        pack_into('<H', data, 8, 6)
        pack_into('<H', data, data.index(b'PK\x01\x02') + 10, 6)
        self.payload.write_bytes(data)
        _, result = self.classify_and_extract('control.zip')
        self.assertEqual(result.members[0].status, 'unsupported-zip-method-6')
        options = {'seven_zip': self.root / '7z'}
        with patch.object(archive, '_capture', return_value=(0, payload)) as run:
            _, result = self.classify_and_extract('control.zip', **options)
        self.assertEqual(result.members[0].data, payload)
        self.assertEqual(run.call_args.args[0][-1], 'INDEX.TXT')
        with patch.object(archive, '_capture', return_value=(0, bytes(len(payload)))):
            _, result = self.classify_and_extract('control.zip', **options)
        self.assertEqual(result.members[0].status, 'read-error')

    def test_nested_gzip_tar_and_links(self):
        control = 'caf\xe9'.encode('cp437')
        data = BytesIO()
        with tarfile.open(fileobj=data, mode='w') as package:
            item = tarfile.TarInfo('docs/CONTROL.TXT')
            item.size = len(control)
            package.addfile(item, BytesIO(control))
            item = tarfile.TarInfo('docs/link')
            item.type, item.linkname = tarfile.SYMTYPE, 'CONTROL.TXT'
            package.addfile(item)
        self.payload.write_bytes(compress(data.getvalue(), mtime=0))
        kind, outer = self.classify_and_extract('outer.tgz')
        self.assertEqual(kind, 'tgz')
        child = outer.members[0]
        self.assertEqual(child.name, 'outer.tar')
        self.payload.write_bytes(child.data)
        kind, result = self.classify_and_extract(child.name)
        self.assertEqual(kind, 'tar')
        self.assertEqual(result.members[1].status, 'non-regular')
        self.payload.write_bytes(result.members[0].data)
        _, text = self.classify_and_extract('CONTROL.TXT')
        self.assertEqual((text.detail, text.documents[0].text), ('cp437-fallback', 'caf\xe9'))

    def test_fat_signature_and_directory_chain(self):
        payload = b'FAT document\r\n'
        image = fat_image(payload)
        self.payload.write_bytes(image)
        kind, result = self.classify_and_extract('not-an-image.doc')
        self.assertEqual(kind, 'fat')
        self.assertEqual([(m.name, m.status, m.data) for m in result.members],
                         [('DOCS', 'directory', None), ('DOCS/INDEX.TXT', 'ok', payload)])
        image[512 + 4:512 + 6] = b'\x3f\x00'  # Cluster 3 points to itself.
        self.payload.write_bytes(image)
        _, result = self.classify_and_extract('image.img')
        self.assertEqual((result.status, result.members[1].status), ('partial', 'read-error'))

    def test_self_extracting_archive_keeps_both_identities(self):
        package = BytesIO()
        with zipfile.ZipFile(package, 'w') as archive_file:
            archive_file.writestr('INDEX.TXT', b'index control')
        stub = bytearray(0x100)
        stub[0:2] = b'MZ'
        pack_into('<I', stub, 0x3C, 0x40)
        stub[0x40:0x44] = b'PE\0\0'
        self.payload.write_bytes(bytes(stub) + package.getvalue())

        found = archive.classify(self.payload, 'setup.exe')
        # Structural identification extracts the archive, but the executable
        # carrier and the embedded archive are both still reported.
        self.assertEqual(found.kind, 'zip')
        self.assertEqual(found.carrier, 'pe')
        self.assertEqual(found.embedded, ('zip',))
        self.assertEqual((found.extension, found.extension_kind), ('exe', 'mz'))
        self.assertFalse(found.unexpected_extension)
        self.assertEqual(archive.identify(self.payload, 'setup.exe'), 'zip')

    def test_archive_under_an_unexpected_extension_is_distinguishable(self):
        with zipfile.ZipFile(self.payload, 'w') as archive_file:
            archive_file.writestr('INDEX.TXT', b'index control')
        found = archive.classify(self.payload, 'notes.exe')
        # Same structural kind as the self-extracting case, but no carrier, so
        # a misleading name stays distinguishable from a genuine dual identity.
        self.assertEqual(found.kind, 'zip')
        self.assertIsNone(found.carrier)
        self.assertEqual(found.embedded, ())
        self.assertTrue(found.unexpected_extension)

    def test_plain_executable_reports_no_embedded_archive(self):
        stub = bytearray(0x100)
        stub[0:2] = b'MZ'
        pack_into('<I', stub, 0x3C, 0x40)
        stub[0x40:0x44] = b'PE\0\0'
        self.payload.write_bytes(bytes(stub))
        found = archive.classify(self.payload, 'setup.exe')
        self.assertEqual((found.kind, found.carrier, found.embedded), ('mz', 'pe', ()))

    def test_fat32_cluster_root_and_high_cluster_words(self):
        plain, long_payload = b'FAT32 plain control\r\n', b'Long name control\r\n'
        fat32_image(self.payload, plain, long_payload)
        kind, result = self.classify_and_extract('volume.img')
        self.assertEqual(kind, 'fat')
        self.assertEqual([(m.name, m.status, m.data) for m in result.members],
                         [('PLAIN.BIN', 'ok', plain), ('Read Me.txt', 'ok', long_payload)])

    def test_vfat_name_requires_a_matching_short_name_checksum(self):
        plain, long_payload = b'FAT32 plain control\r\n', b'Long name control\r\n'
        fat32_image(self.payload, plain, long_payload, break_lfn_checksum=True)
        _, result = self.classify_and_extract('volume.img')
        # A long name whose checksum does not cover the short name is a dangling
        # fragment, so the trustworthy short name is reported instead.
        self.assertEqual([m.name for m in result.members], ['PLAIN.BIN', 'README.TXT'])
        self.assertEqual(result.members[1].data, long_payload)

    def test_lhasa_binary_stdout_and_crc(self):
        payload = b'hello\r\nworld\n\x1a\0'
        self.assertEqual(archive._arc_crc(b'123456789'), 0xbb3d)
        self.payload.write_bytes(lha_member('INDEX.TXT', payload) +
                                 lha_member('BROKEN.TXT', payload, crc=0) +
                                 lha_member('../ESC.TXT', payload) + b'\0')
        with (patch.object(archive.os, 'name', 'nt'),
              patch.object(archive, '_capture', return_value=(0, payload.replace(b'\n', b'\r\n'))) as run):
            result = archive.extract(self.payload, 'control.epb', 'lzh', lhasa=self.root / 'lha')
        self.assertEqual(result.members[0].data, payload)
        self.assertEqual([m.status for m in result.members], ['ok', 'read-error', 'unsafe-or-unsupported-lhasa-name'])
        self.assertEqual([call.args[0][-1] for call in run.call_args_list], ['index.txt', 'broken.txt'])

    def test_arc_stored_member_and_static_method_needing_an_adapter(self):
        name = b'INDEX.TXT\0ABC'
        payload = b'stored control'
        header = name + pack('<IHHHI', len(payload), 0, 0, archive._arc_crc(payload), len(payload))
        # Method 5 is the static 12-bit form; the dynamic method 8 is native.
        self.payload.write_bytes(b'\x1a\x02' + header + payload + b'\x1a\x05' + header + payload + b'\x1a\0')
        kind, result = self.classify_and_extract('opaque.bin')
        self.assertEqual(kind, 'arc')
        self.assertEqual(result.members[0].data, payload)
        self.assertEqual(result.members[1].status, 'unsupported-arc-method-5')

    def test_html_and_pdf_page_locators(self):
        self.payload.write_bytes(b'<html><title>Reference</title><script>hidden()</script><p>Paper &amp; pen</p>')
        kind, result = self.classify_and_extract('note')
        self.assertEqual(kind, 'html')
        self.assertIn('Paper & pen', result.documents[0].text)
        self.assertNotIn('hidden()', result.documents[0].text)
        self.payload.write_bytes(b'%PDF-1.4\n test control')
        with patch.object(archive, '_capture', return_value=(0, b'first\f\fthird\f')):
            kind, result = self.classify_and_extract('catalog', pdftotext=self.root / 'pdftotext')
        self.assertEqual(kind, 'pdf')
        self.assertEqual(result.documents, [archive.Document(1, 'first'), archive.Document(3, 'third')])

    def test_pdf_worker_page_errors_and_no_text(self):
        self.payload.write_bytes(b'%PDF-1.4\nsynthetic control')
        status = (b'{"version":"control","pages":3}\n'
                  b'{"page":1,"text":"index"}\n{"page":2,"error":"DecodeError"}\n')
        with patch.object(archive, '_capture', return_value=(0, status)) as run:
            _, result = self.classify_and_extract('catalog', pdf_python=self.root / 'python')
        self.assertEqual(result.documents, [archive.Document(1, 'index')])
        self.assertEqual(result.status, 'partial')
        self.assertIn('1/3 pages with text', result.detail)
        self.assertIn('1 page errors', result.detail)
        self.assertEqual(run.call_args.args[0][1], '-I')
        status = b'{"version":"control","pages":1}\n{"page":1,"text":""}\n'
        with patch.object(archive, '_capture', return_value=(0, status)):
            _, result = self.classify_and_extract('catalog', pdf_python=self.root / 'python')
        self.assertEqual(result.status, 'unsupported')
        self.assertIn('ocr-triage', result.detail)

    def test_mz_separates_unrecognized_executable_from_container(self):
        self.payload.write_bytes(b'MZ\0\0synthetic control')
        with patch.object(archive, '_capture', return_value=(2, b'')):
            kind, result = self.classify_and_extract('module.exe', seven_zip=self.root / '7z')
        self.assertEqual(kind, 'mz')
        self.assertEqual(result.status, 'unhandled')
        listing = b'Type = PE\n\n----------\nPath = .data\nSize = 16\n'
        with patch.object(archive, '_capture', return_value=(0, listing)) as run:
            _, result = self.classify_and_extract('module.exe', seven_zip=self.root / '7z')
        self.assertEqual(result.status, 'unhandled')
        self.assertEqual(run.call_count, 1)


if __name__ == '__main__':
    unittest.main()
