"""Qualify PC sector-image decoding against hand-authored container bytes.

Every fixture here is assembled field by field from the published structure of
its format, independently of the reader under test.
"""

from pathlib import Path
from struct import pack, pack_into
import sys
import tempfile
import unittest
from unittest.mock import patch


TOOLS = Path(__file__).resolve().parents[2] / 'tools' / 'archive'
with patch.object(sys, 'path', [str(TOOLS), *sys.path]):
    import disk_images


def fat_image(payload):
    """A minimal FAT12 volume: boot sector, one FAT, root directory, one file."""
    sector = 512
    image = bytearray(10 * sector)
    image[:11] = b'\xeb\x3c\x90ARCHTEST'
    pack_into('<HBHBHHBH', image, 11, sector, 1, 1, 1, 16, 10, 0xf0, 1)
    pack_into('<HH', image, 24, 10, 1)  # Sectors per track, then heads.
    image[sector:sector + 6] = b'\xf0\xff\xff\xff\xff\xff'
    image[2 * sector:2 * sector + 12] = b'DOCS       \x10'
    pack_into('<H', image, 2 * sector + 26, 2)
    image[3 * sector:3 * sector + 12] = b'INDEX   TXT\x20'
    pack_into('<HI', image, 3 * sector + 26, 3, len(payload))
    image[4 * sector:4 * sector + len(payload)] = payload
    return bytes(image)


def imd_file(tracks, comment=b''):
    """Assemble an ImageDisk file: identifying line, comment, 0x1A, tracks."""
    return (b'IMD 1.18: synthetic control\r\n' + comment + b'\x1a'
            + b''.join(tracks))


def imd_track(entries, cylinder=0, head=0, mode=3, size_code=2):
    """entries: (sector number, status byte, payload or None)."""
    out = bytearray([mode, cylinder, head, len(entries), size_code])
    out.extend(number for number, _, _ in entries)
    for _, marker, payload in entries:
        out.append(marker)
        if payload is not None:
            out.extend(payload)
    return bytes(out)


def td0_header(signature=b'TD', sequence=0, version=0x15, rate=2, drive=4,
               stepping=0, dos=0, sides=1, stored_crc=0):
    check = (signature[0] + signature[1] + sequence) & 0xFF
    return (signature + bytes([sequence, check, version, rate, drive, stepping,
                               dos, sides]) + pack('<H', stored_crc))


def td0_track(sectors, cylinder=0, head=0):
    """sectors: (number, size code, flags, encoding, data block)."""
    out = bytearray([len(sectors), cylinder, head, 0])
    for number, size_code, flags, encoding, block in sectors:
        out.extend([cylinder, head, number, size_code, flags, 0])
        # Flags 0x10 (skipped) and 0x20 (ID field only) carry no data header.
        if not flags & 0x30:
            out.extend(pack('<HB', len(block) + 1, encoding))
            out.extend(block)
    return bytes(out)


def copyqm_file(track_runs, sector_size=512, sectors_per_track=10, heads=1,
                cylinders=1, comment=b'', description=b'SYNTHETIC CQ CONTROL'):
    header = bytearray(133)
    header[0:3] = b'CQ\x14'
    pack_into('<HBHBHHBHHH', header, 3, sector_size, 1, 1, 1, 16,
              sectors_per_track * heads * cylinders, 0xf0, 1,
              sectors_per_track, heads)
    pack_into('<II', header, 0x14, 0, sectors_per_track * heads * cylinders)
    header[0x1C:0x1C + len(description)] = description
    header[0x58:0x5C] = bytes([0, 0, cylinders, cylinders])
    header[0x60:0x6B] = b'SYNTHETIC  '
    pack_into('<H', header, 0x6F, len(comment))
    header[0x71] = 0
    header[0x84] = (-sum(header)) & 0xFF
    return bytes(header) + comment + track_runs


class IdentificationTests(unittest.TestCase):
    def test_structural_signatures_are_required(self):
        imd = imd_file([imd_track([(1, 1, b'A' * 512)])])
        self.assertEqual(disk_images.identify(imd), 'imd')
        self.assertIsNone(disk_images.identify(b'IMD but no identifying line\r\n\x1a'))
        self.assertIsNone(disk_images.identify(b'ordinary reference notes\r\n'))

    def test_teledisk_requires_a_consistent_check_byte(self):
        header = td0_header()
        self.assertEqual(disk_images.identify(header + b'\xff'), 'td0')
        self.assertEqual(disk_images.identify(td0_header(b'td') + b'\xff'), 'td0-advanced')
        broken = bytearray(header)
        broken[3] ^= 0xFF
        self.assertIsNone(disk_images.identify(bytes(broken) + b'\xff'))
        self.assertIsNone(disk_images.identify(b'TD reference notes only'))

    def test_copyqm_requires_the_zero_byte_sum(self):
        image = copyqm_file(pack('<h', 5120) + bytes(5120))
        self.assertEqual(disk_images.identify(image), 'copyqm')
        broken = bytearray(image)
        broken[0x30] ^= 0x01
        self.assertIsNone(disk_images.identify(bytes(broken)))


class ImdTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.path = self.root / 'control.imd'

    def read(self, data, **kwargs):
        self.path.write_bytes(data)
        return disk_images.read(self.path, **kwargs)

    def test_raw_fill_and_missing_sector_statuses(self):
        raw = bytes(range(256)) * 2
        volume = self.read(imd_file([imd_track([(1, 1, raw), (2, 2, b'\xe5'),
                                                (3, 0, None)])]))
        self.assertEqual((volume.status, volume.container), ('ok', 'imd'))
        self.assertEqual(volume.geometry, disk_images.Geometry(1, 1, 3, 512))
        self.assertEqual([(s.number, s.status) for s in volume.sectors],
                         [(1, 'ok'), (2, 'ok-fill'), (3, 'missing')])
        self.assertEqual(volume.sectors[0].data, raw)
        self.assertEqual(volume.sectors[1].data, b'\xe5' * 512)
        self.assertIsNone(volume.sectors[2].data)

    def test_deleted_and_read_error_markers_are_preserved(self):
        volume = self.read(imd_file([imd_track([(1, 3, b'D' * 512),
                                                (2, 5, b'E' * 512),
                                                (3, 4, b'\x00')])]))
        self.assertEqual([s.status for s in volume.sectors],
                         ['deleted-data', 'read-error', 'deleted-data-fill'])

    def test_unknown_mode_and_truncated_payload(self):
        self.assertEqual(self.read(imd_file([imd_track([(1, 1, b'A' * 512)], mode=9)])).detail,
                         'unknown-imd-mode-9')
        truncated = imd_file([imd_track([(1, 1, b'A' * 512)])])[:-40]
        volume = self.read(truncated)
        self.assertEqual((volume.status, volume.detail), ('partial', 'truncated-sector-data'))

    def test_preamble_comment_is_retained_as_metadata(self):
        volume = self.read(imd_file([imd_track([(1, 1, b'A' * 512)])],
                                    comment=b'first note\r\nsecond note\r\n'))
        self.assertEqual(volume.metadata['preamble'], 'IMD 1.18: synthetic control')
        self.assertEqual(volume.metadata['comment_lines'], 3)

    def test_normalised_image_names_its_gaps(self):
        volume = self.read(imd_file([imd_track([(1, 1, b'A' * 512), (2, 0, None),
                                                (3, 1, b'C' * 512)])]))
        image = disk_images.to_lba(volume)
        self.assertEqual((image.status, image.total_sectors, image.written),
                         ('incomplete', 3, 2))
        self.assertEqual(image.missing, (1,))
        self.assertEqual(len(image.data), 3 * 512)
        # The gap stays zeroed but is reported, never presented as verified data.
        self.assertEqual(image.data[512:1024], bytes(512))

    def test_conflicting_duplicate_sectors_are_reported(self):
        volume = self.read(imd_file([imd_track([(1, 1, b'A' * 512),
                                                (1, 1, b'B' * 512)])]))
        image = disk_images.to_lba(volume)
        self.assertEqual(image.conflicts, (0,))
        self.assertEqual(image.data[:512], b'A' * 512)

    def test_unknown_geometry_cannot_be_normalised(self):
        volume = self.read(imd_file([imd_track([(1, 1, b'A' * 512)])]))
        volume.geometry = disk_images.Geometry(None, None, None, None)
        self.assertEqual(disk_images.to_lba(volume).status, 'unknown-geometry')


class TeleDiskTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.path = self.root / 'control.td0'

    def read(self, data):
        self.path.write_bytes(data)
        return disk_images.read(self.path)

    def build(self, sectors, **header):
        return td0_header(**header) + td0_track(sectors) + b'\xff'

    def test_raw_repeat_pattern_and_rle_sectors(self):
        raw = bytes(range(128))
        literal = bytes(range(64))
        volume = self.read(self.build([
            (1, 0, 0, 0, raw),
            (2, 0, 0, 1, pack('<HH', 64, 0x1234)),
            (3, 0, 0, 2, bytes([0, 64]) + literal + bytes([16, 2]) + bytes(32)),
        ]))
        self.assertEqual(volume.status, 'ok')
        self.assertEqual(volume.geometry, disk_images.Geometry(1, 1, 3, 128))
        self.assertEqual(volume.sectors[0].data, raw)
        self.assertEqual(volume.sectors[1].data, b'\x34\x12' * 64)
        self.assertEqual(volume.sectors[2].data, literal + bytes(64))

    def test_header_metadata_and_unconfirmed_crc_observation(self):
        volume = self.read(self.build([(1, 2, 0, 0, b'Q' * 512)],
                                      version=0x16, rate=0x82, drive=2))
        self.assertEqual(volume.metadata['teledisk_version'], '1.6')
        self.assertEqual(volume.metadata['data_rate'], '500 kbps')
        self.assertTrue(volume.metadata['single_density'])
        self.assertIn('header-crc-unconfirmed-algorithm', volume.warnings)
        self.assertEqual(volume.status, 'ok')

    def test_skipped_and_id_only_sectors_carry_no_data(self):
        volume = self.read(self.build([
            (1, 0, 0x10, 0, b''),
            (2, 0, 0x20, 0, b''),
            (3, 0, 0, 0, b'Z' * 128),
        ]))
        self.assertEqual([(s.status, s.data) for s in volume.sectors],
                         [('skipped', None), ('id-only', None), ('ok', b'Z' * 128)])

    def test_advanced_variant_is_recognised_but_not_decoded(self):
        volume = self.read(td0_header(b'td') + b'\xff')
        self.assertEqual((volume.status, volume.detail),
                         ('unsupported', 'teledisk-advanced-lzss-huffman'))
        self.assertTrue(volume.metadata['advanced_compression'])
        self.assertEqual(volume.sectors, [])

    def test_malformed_encodings_and_truncation(self):
        bad = self.build([(1, 0, 0, 1, pack('<HH', 0, 0))])
        self.assertEqual(self.read(bad).status, 'partial')
        truncated = self.build([(1, 0, 0, 0, b'Q' * 128)])[:-40]
        self.assertEqual(self.read(truncated).detail, 'truncated-data-block')
        self.assertEqual(self.read(td0_header() + bytes([1, 0, 0, 0])).detail,
                         'truncated-sector-header')

    def test_missing_end_marker_is_partial_not_clean(self):
        data = td0_header() + td0_track([(1, 0, 0, 0, b'Q' * 128)])
        volume = self.read(data)
        self.assertEqual((volume.status, volume.detail), ('partial', 'missing-end-marker'))


class CopyQmTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.path = self.root / 'control.qm'

    def read(self, data):
        self.path.write_bytes(data)
        return disk_images.read(self.path)

    def test_signed_runs_decode_a_full_track(self):
        first = bytes(range(256)) * 2
        runs = pack('<h', 512) + first + pack('<h', -4608) + b'\x00'
        volume = self.read(copyqm_file(runs))
        self.assertEqual(volume.status, 'ok')
        self.assertEqual(volume.geometry, disk_images.Geometry(1, 1, 10, 512))
        self.assertEqual(len(volume.sectors), 10)
        self.assertEqual(volume.sectors[0].data, first)
        self.assertEqual(volume.sectors[9].data, bytes(512))
        self.assertEqual(volume.metadata['description'], 'SYNTHETIC CQ CONTROL')
        self.assertEqual(volume.metadata['volume_label'], 'SYNTHETIC')

    def test_comment_block_precedes_the_sectors(self):
        comment = b'qualification control\r\n'
        runs = pack('<h', -5120) + b'\x7f'
        volume = self.read(copyqm_file(runs, comment=comment))
        self.assertEqual(volume.metadata['comment'], 'qualification control')
        self.assertEqual(volume.sectors[0].data, b'\x7f' * 512)

    def test_short_payload_keeps_complete_sectors_and_names_the_rest(self):
        runs = pack('<h', -2048) + b'\x00'
        volume = self.read(copyqm_file(runs))
        self.assertEqual(volume.status, 'partial')
        self.assertTrue(volume.detail.startswith('truncated-track-0-0'))
        self.assertEqual(len(volume.sectors), 10)
        self.assertEqual([s.status for s in volume.sectors], ['ok'] * 4 + ['missing'] * 6)
        image = disk_images.to_lba(volume)
        self.assertEqual((image.status, image.written), ('incomplete', 4))
        self.assertEqual(image.missing, (4, 5, 6, 7, 8, 9))

    def test_implausible_geometry_is_rejected(self):
        data = bytearray(copyqm_file(pack('<h', -5120) + b'\x00'))
        data[0x5A] = 0
        data[0x84] = 0
        data[0x84] = (-sum(data[:133])) & 0xFF
        self.assertEqual(self.read(bytes(data)).detail, 'implausible-copyqm-geometry')


class RawGeometryTests(unittest.TestCase):
    def test_standard_capacities_and_boot_sector_evidence(self):
        geometry, source = disk_images.raw_geometry(1440 * 1024)
        self.assertEqual((geometry, source),
                         (disk_images.Geometry(80, 2, 18, 512), 'standard-capacity'))
        boot = fat_image(b'x')[:512]
        geometry, source = disk_images.raw_geometry(5120, boot)
        self.assertEqual((geometry, source),
                         (disk_images.Geometry(1, 1, 10, 512), 'bpb'))
        self.assertEqual(disk_images.raw_geometry(12345)[1], 'unknown')

    def test_unrecognised_input_is_unhandled(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'notes.imd'
            path.write_bytes(b'plain reference notes\r\n')
            volume = disk_images.read(path)
            self.assertEqual((volume.status, volume.detail),
                             ('unhandled', 'no-sector-container-signature'))


class ExtractorIntegrationTests(unittest.TestCase):
    """The container is decoded, normalised, then handed to the FAT reader."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.payload = b'SECTOR IMAGE CONTROL\r\n'

    def load(self):
        with patch.object(sys, 'path', [str(TOOLS), *sys.path]):
            import intelligence_extract
        return intelligence_extract

    def test_imd_reaches_the_filesystem_through_a_normalised_image(self):
        archive = self.load()
        volume = fat_image(self.payload)
        entries = [(number + 1, 1, volume[number * 512:(number + 1) * 512])
                   for number in range(10)]
        target = self.root / 'control.imd'
        target.write_bytes(imd_file([imd_track(entries, size_code=2)]))
        kind = archive.identify(target, 'control.imd')
        self.assertEqual(kind, 'imd')
        self.assertIn(kind, archive.CONTAINER_KINDS)
        result = archive.extract(target, 'control.imd', kind)
        self.assertEqual([(m.name, m.status, m.data) for m in result.members],
                         [('DOCS', 'directory', None), ('DOCS/INDEX.TXT', 'ok', self.payload)])
        self.assertIn('imd;', result.detail)
        self.assertIn('lba complete 10/10', result.detail)
        self.assertEqual(list(self.root.iterdir()), [target])

    def test_copyqm_reaches_the_filesystem(self):
        archive = self.load()
        volume = fat_image(self.payload)
        target = self.root / 'control.qm'
        target.write_bytes(copyqm_file(pack('<h', len(volume)) + volume))
        kind = archive.identify(target, 'control.qm')
        self.assertEqual(kind, 'copyqm')
        result = archive.extract(target, 'control.qm', kind)
        self.assertEqual(result.members[1].data, self.payload)
        self.assertIn('lba complete 10/10', result.detail)

    def test_unsupported_advanced_image_is_not_reported_as_extracted(self):
        archive = self.load()
        target = self.root / 'control.td0'
        target.write_bytes(td0_header(b'td') + b'\xff')
        kind = archive.identify(target, 'control.td0')
        self.assertEqual(kind, 'td0-advanced')
        result = archive.extract(target, 'control.td0', kind)
        self.assertEqual(result.status, 'unsupported')
        self.assertIn('teledisk-advanced-lzss-huffman', result.detail)
        self.assertEqual(result.members, [])

    def test_incomplete_image_is_reported_as_partial_after_filesystem_read(self):
        archive = self.load()
        volume = fat_image(self.payload)
        # Sector 10 is declared but absent, so the volume cannot be complete.
        entries = [(number + 1, 1, volume[number * 512:(number + 1) * 512])
                   for number in range(9)]
        entries.append((10, 0, None))
        target = self.root / 'control.imd'
        target.write_bytes(imd_file([imd_track(entries, size_code=2)]))
        result = archive.extract(target, 'control.imd', 'imd')
        self.assertEqual(result.status, 'partial')
        self.assertIn('1 missing', result.detail)


if __name__ == '__main__':
    unittest.main()
