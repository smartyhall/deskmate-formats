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


def vfat_slot(ordinal, units, checksum, *, last=False, order_extra=0,
              reserved=0, first_cluster=0, pad=True):
    """One long-name slot laid out exactly as VFAT stores it."""
    text = list(units)
    if pad:
        text = text + [0x0000] + [0xFFFF] * (13 - len(text) - 1)
    text += [0xFFFF] * (13 - len(text))
    raw = b''.join(struct.pack('<H', unit) for unit in text[:13])
    order = ordinal | (0x40 if last else 0) | order_extra
    return (bytes([order]) + raw[0:10] + bytes([0x0F, reserved, checksum])
            + raw[10:22] + struct.pack('<H', first_cluster) + raw[22:26])


def vfat_slots(name, checksum, **options):
    """A complete descending slot chain for one long name."""
    units = [struct.unpack('<H', name.encode('utf-16-le')[index:index + 2])[0]
             for index in range(0, len(name) * 2, 2)]
    chunks = [units[index:index + 13] for index in range(0, len(units), 13)]
    out = b''
    for ordinal in range(len(chunks), 0, -1):
        out += vfat_slot(ordinal, chunks[ordinal - 1], checksum,
                         last=ordinal == len(chunks), **options)
    return out


def checksum_of(short_name):
    return short_checksum(short_entry(short_name, 0, 0)[:11])


class _VolumeCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def extract(self, entries, name='volume.img', **options):
        target = self.root / name
        build(target, entries, **options)
        return extractor.extract(target, name, extractor.identify(target, name))


class VFatSlotTests(_VolumeCase):
    """Every malformed long-name chain must leave the short name intact."""

    def test_a_checksum_mismatch_falls_back_to_the_short_name(self):
        entries = vfat_slots('Synthetic report.txt', checksum_of('OTHER~1.TXT'))
        result = self.extract(entries + short_entry('PLAIN.TXT', 3, 4), files={3: b'data'})
        self.assertEqual([m.name for m in result.members], ['PLAIN.TXT'])
        self.assertEqual(result.members[0].data, b'data')
        self.assertIn('vfat-checksum-mismatch', result.detail)

    def test_ascending_slot_ordinals_are_rejected(self):
        checksum = checksum_of('PLAIN.TXT')
        units = [ord(char) for char in 'Synthetic report.txt']
        entries = (vfat_slot(1, units[:13], checksum)
                   + vfat_slot(2, units[13:], checksum, last=True)
                   + short_entry('PLAIN.TXT', 3, 4))
        result = self.extract(entries, files={3: b'data'})
        self.assertEqual([m.name for m in result.members], ['PLAIN.TXT'])
        self.assertIn('vfat-orphan-slot', result.detail)

    def test_a_missing_last_marker_leaves_the_short_name(self):
        checksum = checksum_of('PLAIN.TXT')
        result = self.extract(vfat_slot(1, [ord('X')], checksum)
                              + short_entry('PLAIN.TXT', 3, 1), files={3: b'x'})
        self.assertEqual([m.name for m in result.members], ['PLAIN.TXT'])

    def test_a_reserved_order_bit_or_reserved_field_is_rejected(self):
        checksum = checksum_of('PLAIN.TXT')
        for options, expected in (({'order_extra': 0x80}, 'vfat-slot-reserved-bit'),
                                  ({'reserved': 1}, 'vfat-slot-reserved-field'),
                                  ({'first_cluster': 7}, 'vfat-slot-reserved-field')):
            with self.subTest(**options):
                entries = (vfat_slot(1, [ord('X')], checksum, last=True, **options)
                           + short_entry('PLAIN.TXT', 3, 1))
                result = self.extract(entries, name=f'reserved-{expected}.img', files={3: b'x'})
                self.assertEqual([m.name for m in result.members], ['PLAIN.TXT'])
                self.assertIn(expected, result.detail)

    def test_invalid_utf16_content_is_rejected(self):
        checksum = checksum_of('PLAIN.TXT')
        for units in ([0xD800, 0x41], [0x41, 0xFFFF, 0x42], [0xDC00, 0x41]):
            with self.subTest(units=units):
                entries = (vfat_slot(1, units, checksum, last=True)
                           + short_entry('PLAIN.TXT', 3, 1))
                result = self.extract(entries, name='utf16.img', files={3: b'x'})
                self.assertEqual([m.name for m in result.members], ['PLAIN.TXT'])
                self.assertIn('vfat-slot-text', result.detail)

    def test_padding_after_the_terminator_must_be_ffff(self):
        checksum = checksum_of('PLAIN.TXT')
        slot = bytearray(vfat_slot(1, [ord('X')], checksum, last=True))
        # Unit 0 is the character at bytes 1-2, unit 1 the terminator at bytes
        # 3-4, so bytes 5-6 are the first padding unit after it.
        struct.pack_into('<H', slot, 5, 0x1234)
        result = self.extract(bytes(slot) + short_entry('PLAIN.TXT', 3, 1), files={3: b'x'})
        self.assertEqual([m.name for m in result.members], ['PLAIN.TXT'])
        self.assertIn('vfat-slot-text', result.detail)

    def test_a_stale_chain_does_not_shadow_the_next_valid_one(self):
        checksum = checksum_of('GOOD~1.TXT')
        entries = (vfat_slot(5, [ord('X')], checksum, last=True)
                   + vfat_slots('Good name.txt', checksum)
                   + short_entry('GOOD~1.TXT', 3, 1))
        result = self.extract(entries, files={3: b'x'})
        self.assertEqual([m.name for m in result.members], ['Good name.txt'])
        self.assertIn('vfat-chain-interrupted', result.detail)

    def test_an_interleaved_chain_between_two_short_entries_is_discarded(self):
        first = checksum_of('ONE.TXT')
        second = checksum_of('TWO.TXT')
        entries = (vfat_slot(2, [ord('A')], first, last=True)
                   + short_entry('ONE.TXT', 3, 1)
                   + vfat_slot(1, [ord('B')], second)
                   + short_entry('TWO.TXT', 4, 1))
        result = self.extract(entries, files={3: b'a', 4: b'b'})
        self.assertEqual([m.name for m in result.members], ['ONE.TXT', 'TWO.TXT'])
        self.assertEqual([m.data for m in result.members], [b'a', b'b'])


class FatOwnershipTests(_VolumeCase):
    """Ownership is per directory entry, so equal names stay distinct."""

    def test_duplicate_names_remain_distinct_objects(self):
        entries = short_entry('SAME.BIN', 3, 4) + short_entry('SAME.BIN', 4, 4)
        result = self.extract(entries, files={3: b'aaaa', 4: b'bbbb'})
        self.assertEqual([m.name for m in result.members], ['SAME.BIN', 'SAME.BIN'])
        self.assertEqual([m.data for m in result.members], [b'aaaa', b'bbbb'])
        self.assertEqual(result.status, 'ok')

    def test_a_file_aliasing_a_directory_chain_is_a_cross_link(self):
        entries = (short_entry('SUB', 3, 0, attr=0x10)
                   + short_entry('ALIAS.BIN', 3, 4))
        result = self.extract(entries, files={3: bytes(32), 4: b'data'})
        self.assertEqual([(m.name, m.status) for m in result.members],
                         [('SUB', 'directory'), ('ALIAS.BIN', 'read-error')])

    def test_a_file_aliasing_the_fat32_root_chain_is_a_cross_link(self):
        result = self.extract(short_entry('ROOTALIAS.BIN', 2, 4))
        self.assertEqual(result.members[0].status, 'read-error')

    def test_a_directory_pointing_at_itself_is_invalid(self):
        entries = short_entry('SUB', 3, 0, attr=0x10)
        result = self.extract(entries, files={3: short_entry('LOOP', 3, 0, attr=0x10)})
        self.assertIn(('SUB/LOOP', 'invalid-directory'),
                      [(m.name, m.status) for m in result.members])

    def test_a_directory_cluster_reused_by_two_entries_is_invalid(self):
        entries = (short_entry('ONE', 3, 0, attr=0x10)
                   + short_entry('TWO', 3, 0, attr=0x10))
        result = self.extract(entries, files={3: bytes(32)})
        self.assertEqual([(m.name, m.status) for m in result.members],
                         [('ONE', 'directory'), ('TWO', 'invalid-directory')])

    def test_a_cyclic_directory_chain_is_reported(self):
        # The directory block is filled with label entries so the walk asks for
        # a second cluster and meets the loop instead of stopping early.
        inner = short_entry('LABEL', 0, 0, attr=0x08) * 16
        entries = short_entry('SUB', 3, 0, attr=0x10)
        result = self.extract(entries, files={3: inner}, links={3: 3})
        self.assertIn(('SUB', 'invalid-directory-chain'),
                      [(m.name, m.status) for m in result.members])


FAT12_SECTOR = 512
FAT12_RESERVED = 1
FAT12_FATS = 2
FAT12_FAT_SECTORS = 9
FAT12_ROOT_SECTORS = 14
FAT12_TOTAL = 2880
FAT12_FIRST_DATA = FAT12_RESERVED + FAT12_FATS * FAT12_FAT_SECTORS + FAT12_ROOT_SECTORS


def _set_fat12(fat, cluster, value):
    offset = cluster + cluster // 2
    if cluster & 1:
        fat[offset] = (fat[offset] & 0x0F) | ((value << 4) & 0xF0)
        fat[offset + 1] = (value >> 4) & 0xFF
    else:
        fat[offset] = value & 0xFF
        fat[offset + 1] = (fat[offset + 1] & 0xF0) | ((value >> 8) & 0x0F)


def build_fat12(path, entries, *, files=None, links=None):
    """A 1.44 MB FAT12 volume with a two-copy FAT and a fixed root region."""
    boot = bytearray(FAT12_SECTOR)
    boot[0:3] = b'\xeb\x3c\x90'
    boot[3:11] = b'MSDOS5.0'
    struct.pack_into('<HBHBHHBHHH', boot, 11, FAT12_SECTOR, 1, FAT12_RESERVED, FAT12_FATS,
                     224, FAT12_TOTAL, 0xF0, FAT12_FAT_SECTORS, 18, 2)
    boot[510:512] = b'\x55\xaa'
    fat = bytearray(FAT12_FAT_SECTORS * FAT12_SECTOR)
    fat[0:3] = b'\xf0\xff\xff'
    for cluster, value in (links or {}).items():
        _set_fat12(fat, cluster, value)
    with path.open('wb') as stream:
        stream.truncate(FAT12_TOTAL * FAT12_SECTOR)
        stream.write(boot)
        for index in range(FAT12_FATS):
            stream.seek((FAT12_RESERVED + index * FAT12_FAT_SECTORS) * FAT12_SECTOR)
            stream.write(fat)
        stream.seek((FAT12_RESERVED + FAT12_FATS * FAT12_FAT_SECTORS) * FAT12_SECTOR)
        stream.write(entries)
        for cluster, payload in (files or {}).items():
            stream.seek((FAT12_FIRST_DATA + cluster - 2) * FAT12_SECTOR)
            stream.write(payload)


class Fat12ChainTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_a_two_cluster_chain_is_read_through_the_fixed_root(self):
        target = self.root / 'floppy.img'
        build_fat12(target, short_entry('CHAIN.BIN', 2, 1024),
                    files={2: b'A' * 512, 3: b'B' * 512}, links={2: 3, 3: 0xFFF})
        self.assertEqual(extractor.identify(target, 'floppy.img'), 'fat')
        result = extractor.extract(target, 'floppy.img', 'fat')
        self.assertEqual([(m.name, m.status) for m in result.members], [('CHAIN.BIN', 'ok')])
        self.assertEqual(result.members[0].data, b'A' * 512 + b'B' * 512)

    def test_a_fat12_bad_cluster_marker_ends_the_read(self):
        target = self.root / 'bad.img'
        build_fat12(target, short_entry('BAD.BIN', 2, 512),
                    files={2: b'A' * 512}, links={2: 0xFF7})
        result = extractor.extract(target, 'bad.img', 'fat')
        self.assertEqual(result.members[0].status, 'read-error')

    def test_a_fat12_chain_cycle_is_rejected(self):
        target = self.root / 'loop.img'
        build_fat12(target, short_entry('LOOP.BIN', 2, 2048),
                    files={2: b'A' * 512}, links={2: 2})
        result = extractor.extract(target, 'loop.img', 'fat')
        self.assertEqual(result.members[0].status, 'read-error')


if __name__ == '__main__':
    unittest.main()
