"""Qualify FAT32 and VFAT structural handling on independently built volumes.

Each volume here is written from the documented on-disk structures, not from a
filesystem implementation, so a test proves that the reader follows the
specification. `7z` is not used: it reads FAT for listing, but the questions
below are about damaged and divergent structures that a healthy reader hides.
"""

from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch


TOOLS = Path(__file__).resolve().parents[2] / 'tools' / 'archive'
with patch.object(sys, 'path', [str(TOOLS), *sys.path]):
    import intelligence_extract as extractor


SECTOR = 512
CLUSTER = SECTOR
RESERVED = 32
FAT_SECTORS = 512
TOTAL = 66581                      # yields 65,525 clusters, the FAT32 minimum
FIRST_DATA = RESERVED + 2 * FAT_SECTORS
DATA_START = FIRST_DATA * SECTOR
EOC = 0x0FFFFFFF
ROOT = 2


def cluster_offset(cluster):
    return DATA_START + (cluster - 2) * CLUSTER


def boot_sector(*, copies=2, ext_flags=0, fsinfo=1, backup=6):
    boot = bytearray(SECTOR)
    boot[0:3] = b'\xeb\x3c\x90'
    boot[3:11] = b'MSDOS5.0'
    struct.pack_into('<HBHBHHBHHHII', boot, 11, SECTOR, 1, RESERVED, copies, 0, 0, 0xf8,
                     FAT_SECTORS, 32, 2, 0, TOTAL)
    struct.pack_into('<IHHIHH', boot, 36, FAT_SECTORS, ext_flags, 0, ROOT, fsinfo, backup)
    boot[64] = 0x80
    boot[66] = 0x29
    struct.pack_into('<I', boot, 67, 0x12345678)
    boot[71:82] = b'CONTROL    '
    boot[82:90] = b'FAT32   '
    boot[510:512] = b'\x55\xaa'
    return bytes(boot)


def fsinfo_sector(free=65520, next_free=3, signature=True):
    sector = bytearray(SECTOR)
    if signature:
        struct.pack_into('<I', sector, 0, 0x41615252)
        struct.pack_into('<I', sector, 484, 0x61417272)
        struct.pack_into('<II', sector, 488, free, next_free)
        struct.pack_into('<I', sector, 508, 0xAA550000)
    return bytes(sector)


def short_checksum(name11):
    checksum = 0
    for byte in name11:
        checksum = (((checksum & 1) << 7) + (checksum >> 1) + byte) & 0xFF
    return checksum


def short_entry(name, cluster, size, attr=0x20):
    stem, _, extension = name.partition('.')
    raw = stem.encode('cp437').ljust(8, b' ')[:8] + extension.encode('cp437').ljust(3, b' ')[:3]
    # Attributes, NTRes, create tenths, create time/date and last access date
    # occupy offsets 11 to 19; the first cluster is split across 20 and 26.
    return (raw + bytes([attr]) + bytes(8) + struct.pack('<H', cluster >> 16)
            + bytes(4) + struct.pack('<H', cluster & 0xFFFF) + struct.pack('<I', size))


def long_name_entries(name, short_name):
    units = [name.encode('utf-16-le')[index:index + 2] for index in range(0, len(name) * 2, 2)]
    checksum = short_checksum(short_entry(short_name, 0, 0)[:11])
    slots = [units[index:index + 13] for index in range(0, len(units), 13)]
    slots[-1] = slots[-1] + [b'\0\0'] + [b'\xff\xff'] * (13 - len(slots[-1]) - 1)
    entries = b''
    # VFAT stores the slots in reverse, with the last ordinal carrying 0x40.
    for ordinal in range(len(slots), 0, -1):
        slot = slots[ordinal - 1]
        order = ordinal | (0x40 if ordinal == len(slots) else 0)
        entries += (bytes([order]) + b''.join(slot[:5]) + bytes([0x0F, 0, checksum])
                    + b''.join(slot[5:11]) + b'\0\0' + b''.join(slot[11:13]))
    return entries + short_entry(short_name, 0, 0)


def build(path, entries, *, files=None, links=None, copies=2, ext_flags=0,
          fsinfo=None, backup=None, truncate_to=None):
    """Write a FAT32 volume whose only content is the supplied entries."""
    boot = boot_sector(copies=copies, ext_flags=ext_flags)
    links = dict(links or {})
    links.setdefault(ROOT, EOC)
    fat = bytearray(FAT_SECTORS * SECTOR)
    struct.pack_into('<III', fat, 0, 0x0FFFFFF8, EOC, links[ROOT])
    for cluster, value in links.items():
        struct.pack_into('<I', fat, cluster * 4, value)
    for cluster in (files or {}):
        if cluster not in links:
            struct.pack_into('<I', fat, cluster * 4, EOC)
    fsinfo = fsinfo if fsinfo is not None else fsinfo_sector()
    backup = backup if backup is not None else boot
    with path.open('wb') as stream:
        stream.truncate(truncate_to or TOTAL * SECTOR)
        stream.seek(0)
        stream.write(boot)
        stream.write(fsinfo)
        stream.seek(6 * SECTOR)
        stream.write(backup)
        for index in range(copies):
            stream.seek((RESERVED + index * FAT_SECTORS) * SECTOR)
            stream.write(fat)
        stream.seek(cluster_offset(ROOT))
        stream.write(entries)
        for cluster, payload in (files or {}).items():
            stream.seek(cluster_offset(cluster))
            stream.write(payload)


class FatVolumeTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def extract(self, entries, name='volume.img', **options):
        target = self.root / name
        build(target, entries, **options)
        return extractor.extract(target, name, extractor.identify(target, name))

    def test_multi_slot_long_name_with_unicode_is_reconstructed(self):
        long_name = 'Synthetic quarterly r\u00e9sum\u00e9.txt'
        # The long-named entry keeps the placeholder short entry that the chain
        # names, so it is empty; the second file proves the chain did not eat
        # the next entry.
        entries = (long_name_entries(long_name, 'SYNTHQ~1.TXT')
                   + short_entry('PLAIN.BIN', 3, 4))
        result = self.extract(entries, files={3: b'data'})
        self.assertEqual([m.name for m in result.members], [long_name, 'PLAIN.BIN'])
        self.assertEqual(result.status, 'ok')
        self.assertEqual(result.members[0].data, b'')
        self.assertEqual(result.members[1].data, b'data')

    def test_declared_size_beyond_the_chain_is_an_error(self):
        result = self.extract(short_entry('SHORT.BIN', 3, 4096), files={3: b'x' * CLUSTER})
        self.assertEqual(result.members[0].status, 'read-error')

    def test_bad_cluster_marker_is_not_an_end_of_chain(self):
        result = self.extract(short_entry('BAD.BIN', 3, 1024),
                              files={3: b'a' * CLUSTER}, links={3: 0x0FFFFFF7})
        self.assertEqual(result.members[0].status, 'read-error')
        self.assertIsNone(result.members[0].data)

    def test_cyclic_chain_is_rejected(self):
        result = self.extract(short_entry('LOOP.BIN', 3, 4096),
                              files={3: b'a' * CLUSTER}, links={3: 3})
        self.assertEqual(result.members[0].status, 'read-error')

    def test_cross_linked_chains_keep_the_first_file_and_report_the_second(self):
        entries = short_entry('FIRST.BIN', 3, CLUSTER) + short_entry('SECOND.BIN', 3, CLUSTER)
        result = self.extract(entries, files={3: b'f' * CLUSTER})
        self.assertEqual([m.status for m in result.members], ['ok', 'read-error'])
        self.assertEqual(result.members[0].data, b'f' * CLUSTER)

    def test_the_active_fat_copy_is_used_when_mirroring_is_disabled(self):
        target = self.root / 'active.img'
        build(target, short_entry('COPY.BIN', 3, CLUSTER), files={3: b'c' * CLUSTER})
        # Rewrite the first copy so it no longer describes the file, and point
        # BPB_ExtFlags at the second copy.
        with target.open('r+b') as stream:
            stream.seek(RESERVED * SECTOR + 3 * 4)
            stream.write(struct.pack('<I', 0))
            stream.seek(40)
            stream.write(struct.pack('<H', 0x80 | 1))
            stream.seek(RESERVED * SECTOR + FAT_SECTORS * SECTOR + 3 * 4)
            stream.write(struct.pack('<I', EOC))
        result = extractor.extract(target, 'active.img', extractor.identify(target, 'active.img'))
        self.assertEqual([(m.name, m.status) for m in result.members], [('COPY.BIN', 'ok')])
        self.assertNotIn('fat-copy', result.detail or '')

    def test_divergent_mirrored_copies_are_reported(self):
        target = self.root / 'mirror.img'
        build(target, short_entry('COPY.BIN', 3, CLUSTER), files={3: b'c' * CLUSTER})
        with target.open('r+b') as stream:
            stream.seek((RESERVED + FAT_SECTORS) * SECTOR + 4 * 4)
            stream.write(struct.pack('<I', 0x0FFFFFF0))
        result = extractor.extract(target, 'mirror.img', extractor.identify(target, 'mirror.img'))
        self.assertIn('fat-copy-1-differs', result.detail)
        # The first copy still describes the file, so its data is readable.
        self.assertEqual(result.members[0].status, 'ok')

    def test_fsinfo_signature_and_values_are_checked(self):
        bad = self.extract(short_entry('A.BIN', 3, 1), files={3: b'a'},
                           fsinfo=fsinfo_sector(signature=False))
        self.assertIn('fsinfo-signature-invalid', bad.detail)
        implausible = self.extract(short_entry('A.BIN', 3, 1), files={3: b'a'},
                                   fsinfo=fsinfo_sector(free=999999))
        self.assertIn('fsinfo-values-implausible', implausible.detail)
        healthy = self.extract(short_entry('A.BIN', 3, 1), files={3: b'a'})
        self.assertNotIn('fsinfo', healthy.detail or '')

    def test_backup_boot_sector_is_compared_with_the_primary(self):
        differ = self.extract(short_entry('A.BIN', 3, 1), files={3: b'a'},
                              backup=boot_sector()[:-1] + b'\xbb')
        self.assertIn('backup-boot-differs', differ.detail)
        healthy = self.extract(short_entry('A.BIN', 3, 1), files={3: b'a'})
        self.assertNotIn('backup-boot', healthy.detail or '')

    def test_a_truncated_volume_is_not_read_as_a_filesystem(self):
        target = self.root / 'short.img'
        build(target, short_entry('A.BIN', 3, 1), files={3: b'a'}, truncate_to=4096)
        self.assertEqual(extractor.identify(target, 'short.img'), 'disk-image')
        result = extractor.extract(target, 'short.img', 'fat')
        self.assertEqual(result.status, 'unsupported')


if __name__ == '__main__':
    unittest.main()
