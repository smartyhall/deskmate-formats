"""Exercise sector-image limits with small, deliberately constrained bounds.

Every case here is built to fail before it allocates: a declared geometry, a
track length or an aggregate payload is compared with the caller's bound first,
so the test suite never asks the laboratory for the memory the check exists to
prevent.
"""

from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch


TOOLS = Path(__file__).resolve().parents[2] / 'tools' / 'archive'
with patch.object(sys, 'path', [str(TOOLS), *sys.path]):
    import disk_images
    import intelligence_extract as extractor


def geometry(cylinders=80, heads=2, spt=18, size=512):
    return disk_images.Geometry(cylinders, heads, spt, size)


def sector(cylinder=0, head=0, number=1, size=512, status='ok', fill=b'A'):
    return disk_images.Sector(cylinder, head, number, size, fill * size, status)


def copyqm_header(*, sector_size=512, spt=18, heads=2, cylinders=80, comment_length=0):
    header = bytearray(disk_images.COPYQM_HEADER_BYTES)
    header[0:3] = disk_images.COPYQM_SIGNATURE
    struct.pack_into('<HBHBHHBHHH', header, 3, sector_size, 1, 1, 1, 224, 0, 0xF8, 9,
                     spt, heads)
    struct.pack_into('<II', header, 0x14, 0, 2880)
    struct.pack_into('<4B', header, 0x58, 0, 0, cylinders, cylinders)
    struct.pack_into('<I', header, 0x5C, 0)
    header[0x60:0x6B] = b'PROBE      '
    struct.pack_into('<HBBBB', header, 0x6F, comment_length, 0, 0, 0, 0)
    # The header carries a one-byte checksum: the whole 133 bytes sum to zero.
    header[132] = (-sum(header)) & 0xFF
    return bytes(header)


def copyqm_track(spt, sector_size=512):
    """One CopyQM track: signed 16-bit literal lengths followed by their bytes."""
    out = bytearray()
    for index in range(spt):
        payload = bytes(((index * 131 + offset * 7) & 0xFF) for offset in range(sector_size))
        out += struct.pack('<h', sector_size) + payload
    return bytes(out)


def copyqm_image(spt=2, cylinders=1, comment_length=0):
    header = copyqm_header(spt=spt, cylinders=cylinders, comment_length=comment_length)
    return header + copyqm_track(spt) * (cylinders * 2)


def imd_image(count=2, statuses=(1, 1)):
    data = bytearray(b'IMD 1.20: synthetic probe\r\n\x1a')
    data += bytes([5, 0, 0, count, 2])
    data += bytes(range(1, count + 1))
    for status in statuses:
        data += bytes([status]) + b'A' * 512
    return bytes(data)


class LbaImageTests(unittest.TestCase):
    def test_a_geometry_above_the_byte_budget_is_refused_before_allocating(self):
        volume = disk_images.Volume('copyqm', geometry(1000, 2, 256), [])
        image = disk_images.to_lba(volume, bounds=disk_images.Bounds(lba_bytes=65536))
        self.assertEqual(image.status, 'lba-byte-limit')
        self.assertEqual((image.data, image.total_sectors), (b'', 512_000))

    def test_implausible_geometry_fields_are_refused(self):
        for shape in (geometry(0, 2, 18), geometry(80, 5000, 18),
                      geometry(80, 2, 9000), geometry(80, 2, 18, 300)):
            with self.subTest(shape=shape):
                image = disk_images.to_lba(disk_images.Volume('imd', shape, []))
                self.assertEqual(image.status, 'invalid-geometry')
                self.assertEqual(image.data, b'')

    def test_a_read_error_sector_does_not_complete_a_verified_image(self):
        volume = disk_images.Volume('imd', geometry(1, 1, 2), [
            sector(0, 0, 1),
            sector(0, 0, 2, status='read-error', fill=b'B')])
        image = disk_images.to_lba(volume)
        self.assertEqual(image.status, 'degraded')
        self.assertEqual(image.missing, ())
        self.assertEqual(image.degraded, (1,))
        self.assertEqual(image.written, 2)
        self.assertEqual(image.data[512:], b'B' * 512)

    def test_out_of_geometry_coordinates_are_counted_not_aliased(self):
        volume = disk_images.Volume('imd', geometry(1, 1, 2), [
            sector(0, 0, 1), sector(0, 0, 2),
            sector(0, 0, 3), sector(0, 1, 1), sector(5, 0, 1)])
        image = disk_images.to_lba(volume)
        self.assertEqual(image.rejected, 3)
        self.assertEqual(image.written, 2)
        self.assertEqual(len(image.data), 1024)
        self.assertEqual(image.status, 'degraded')

    def test_an_empty_geometry_stays_unknown(self):
        image = disk_images.to_lba(disk_images.Volume('imd', geometry(None, None, None, None), []))
        self.assertEqual(image.status, 'unknown-geometry')


class ContainerReadTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_the_input_bound_is_enforced_by_the_read_itself(self):
        target = self.root / 'big.imd'
        target.write_bytes(b'IMD 1.20: probe\r\n\x1a' + b'A' * 5000)
        volume = disk_images.read(target, bounds=disk_images.Bounds(input_bytes=1024))
        self.assertEqual((volume.status, volume.detail), ('limited', 'input-byte-limit'))

    def test_an_explicit_kind_on_a_short_file_is_a_truncated_header(self):
        target = self.root / 'short.td0'
        target.write_bytes(b'TD')
        volume = disk_images.read(target, 'td0')
        self.assertEqual((volume.status, volume.detail), ('failed', 'truncated-header'))
        copyqm = self.root / 'short.qm'
        copyqm.write_bytes(disk_images.COPYQM_SIGNATURE)
        self.assertEqual(disk_images.read(copyqm, 'copyqm').detail, 'truncated-header')

    def test_a_copyqm_geometry_bomb_is_refused_before_expanding_a_track(self):
        target = self.root / 'bomb.qm'
        target.write_bytes(copyqm_header(spt=65535, sector_size=8192))
        self.assertEqual(disk_images.identify(target.read_bytes()), 'copyqm')
        volume = disk_images.read(target, 'copyqm')
        self.assertEqual((volume.status, volume.detail), ('limited', 'geometry-exceeds-bounds'))
        self.assertEqual(volume.sectors, [])

    def test_the_sector_cap_is_enforced_for_the_whole_track(self):
        target = self.root / 'wide.qm'
        target.write_bytes(copyqm_image(spt=8))
        volume = disk_images.read(target, 'copyqm',
                                  disk_images.Bounds(sectors=4, sector_bytes=4096))
        self.assertEqual((volume.status, volume.detail), ('limited', 'sector-limit'))
        self.assertLessEqual(len(volume.sectors), 4)

    def test_the_aggregate_decoded_budget_stops_a_container(self):
        target = self.root / 'aggregate.qm'
        target.write_bytes(copyqm_image(spt=8))
        volume = disk_images.read(target, 'copyqm', disk_images.Bounds(total_bytes=1024))
        self.assertEqual((volume.status, volume.detail), ('limited', 'decoded-byte-limit'))
        self.assertEqual(len(volume.sectors), 2)

    def test_the_imd_track_length_is_bounded(self):
        target = self.root / 'wide.imd'
        target.write_bytes(imd_image(count=4, statuses=(1, 1, 1, 1)))
        volume = disk_images.read(target, 'imd', disk_images.Bounds(track_sectors=2))
        self.assertEqual((volume.status, volume.detail), ('limited', 'sector-limit'))
        self.assertEqual(volume.sectors, [])

    def test_a_healthy_copyqm_track_is_still_decoded(self):
        target = self.root / 'ok.qm'
        target.write_bytes(copyqm_image(spt=2))
        volume = disk_images.read(target, 'copyqm')
        # One cylinder, two heads, two sectors per track.
        self.assertEqual((volume.status, len(volume.sectors)), ('ok', 4))
        self.assertEqual(volume.sectors[0].data, copyqm_track(2)[2:2 + 512])
        self.assertEqual(volume.sectors[1].data, copyqm_track(2)[2 + 512 + 2:2 + 1024 + 2])
        self.assertNotEqual(volume.sectors[0].data, volume.sectors[1].data)


class ExtractorLimitPropagationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_caller_limits_reach_the_container_decoder(self):
        target = self.root / 'bounded.qm'
        target.write_bytes(copyqm_image(spt=8))
        result = extractor.extract(target, 'bounded.qm', 'copyqm',
                                   extractor.Limits(total_bytes=1024))
        self.assertEqual(result.status, 'limited')
        self.assertIn('geometry-exceeds-bounds', result.detail)

    def test_a_read_error_sector_makes_the_recovery_partial(self):
        target = self.root / 'damaged.imd'
        target.write_bytes(imd_image(count=2, statuses=(1, 5)))
        result = extractor.extract(target, 'damaged.imd', 'imd')
        self.assertEqual(result.status, 'partial')
        self.assertIn('read-error-or-deleted', result.detail)
        self.assertIn('lba degraded', result.detail)


if __name__ == '__main__':
    unittest.main()
