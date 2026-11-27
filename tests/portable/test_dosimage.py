"""Synthetic probes for DOS executable structure and address mapping.

Every specimen is generated here from a known description. No commercial
binary, emulator, Ghidra installation or private lab path is required.
"""
import importlib.util
import io
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

spec = importlib.util.spec_from_file_location(
    'inspect_dosimage', ROOT / 'tools/inspect_dosimage.py')
probe = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(ROOT / 'src'))
spec.loader.exec_module(probe)

fixtures_spec = importlib.util.spec_from_file_location(
    'dos_images', ROOT / 'tests/fixtures/synthetic/dos_images.py')
fixtures = importlib.util.module_from_spec(fixtures_spec)
fixtures_spec.loader.exec_module(fixtures)

from deskmate_formats import dosimage  # noqa: E402


class MzStructureTests(unittest.TestCase):
    def setUp(self):
        self.data, self.expected = fixtures.build_segmented_mz()
        self.mz = dosimage.MzImage.parse(self.data)

    def test_header_and_size_facts(self):
        self.assertEqual(self.mz.header_bytes, self.expected['header_bytes'])
        self.assertEqual(self.mz.declared_file_bytes, len(self.data))
        self.assertEqual(self.mz.image_bytes, self.expected['image_bytes'])
        self.assertEqual(self.mz.trailing_bytes, 0)
        self.assertEqual(self.mz.entry_cs, self.expected['entry_cs'])
        self.assertEqual(self.mz.entry_file_offset,
                         self.expected['entry_file_offset'])

    def test_relocation_site_versus_relocated_value(self):
        self.assertEqual(len(self.mz.relocations), 2)
        sites = [(r.segment, r.offset) for r in self.mz.relocations]
        self.assertEqual(sorted(sites), sorted(self.expected['relocation_sites']))
        self.assertEqual(sorted(self.mz.relocated_segments),
                         sorted(self.expected['relocated_values']))
        self.assertEqual(sorted(self.mz.relocation_site_segments), [0])
        for record in self.mz.relocations:
            self.assertEqual(record.file_offset,
                             self.expected['header_bytes'] + record.image_offset)

    def test_string_offset_is_reported_as_a_file_offset(self):
        offset = self.expected['string_file_offset']
        self.assertEqual(self.data[offset:offset + 5], b'DMDB\x00')

    def test_far_pointer_resolution_requires_a_relocation(self):
        relocated = self.mz.far_pointer_at(
            self.data, self.expected['far_pointer_file_offset']
        )
        self.assertTrue(relocated.segment_relocated)
        self.assertEqual(relocated.offset_word, 0xC000)
        self.assertEqual(relocated.segment_word, 0x0010)
        # 16 * 0010h + C000h, i.e. offset C000 in the second image segment.
        self.assertEqual(relocated.resolved_image_offset, 0xC100)
        self.assertIn('outside the stored image', relocated.resolution)

        plain = self.mz.far_pointer_at(self.data, self.expected['header_bytes'] + 0x40)
        self.assertFalse(plain.segment_relocated)
        self.assertIsNone(plain.resolved_image_offset)
        self.assertIn('no MZ relocation', plain.resolution)

    def test_relocated_pair_outside_the_image_is_flagged_not_dereferenced(self):
        pointer = self.mz.far_pointer_at(
            self.data, self.expected['header_bytes'] + 0x32
        )
        self.assertTrue(pointer.segment_relocated)
        self.assertEqual(pointer.segment_word, 0x0020)
        self.assertIn('outside the stored image', pointer.resolution)
        self.assertEqual(pointer.resolved_image_offset, 0x210)


class CoordinateTests(unittest.TestCase):
    def setUp(self):
        self.data, _ = fixtures.build_segmented_mz()
        self.mz = dosimage.MzImage.parse(self.data)

    def test_file_image_and_linear_round_trip(self):
        for file_offset in (0x40, 0x50, 0x140):
            self.assertEqual(self.mz.image_to_file(self.mz.file_to_image(file_offset)),
                             file_offset)
            linear = self.mz.file_to_linear(file_offset, 0x2000)
            self.assertEqual(self.mz.linear_to_file(linear, 0x2000), file_offset)

    def test_load_segment_changes_the_linear_address(self):
        a = self.mz.file_to_linear(0x40, 0x1000)
        b = self.mz.file_to_linear(0x40, 0x2000)
        self.assertEqual(b - a, 0x10000)

    def test_linear_to_segment_offset_is_one_valid_labelling(self):
        linear = (0x1234 << 4) + 0x0010
        self.assertEqual(dosimage.linear_to_segment_offset(linear, 0x1234),
                         (0x1234, 0x0010))
        self.assertEqual(dosimage.linear_to_segment_offset(linear, 0x1230),
                         (0x1230, 0x0050))
        with self.assertRaises(dosimage.DosImageError):
            dosimage.linear_to_segment_offset(linear, 0x2000)

    def test_segment_offset_arithmetic_is_checked(self):
        self.assertEqual(dosimage.segment_offset_to_linear(0x1000, 0x0010), 0x10010)
        with self.assertRaises(dosimage.DosImageError):
            dosimage.segment_offset_to_linear(0x10000, 0)
        with self.assertRaises(dosimage.DosImageError):
            dosimage.segment_offset_to_linear(0, 0x10000)

    def test_offsets_outside_the_image_are_rejected(self):
        with self.assertRaises(dosimage.DosImageError):
            self.mz.file_to_image(0x10)
        with self.assertRaises(dosimage.DosImageError):
            self.mz.file_to_image(len(self.data))
        with self.assertRaises(dosimage.DosImageError):
            self.mz.linear_to_file(0x1000)


class LoaderBlockTests(unittest.TestCase):
    def setUp(self):
        self.data, _ = fixtures.build_segmented_mz()
        self.mz = dosimage.MzImage.parse(self.data)

    def test_loader_segments_come_from_relocated_values(self):
        self.assertEqual(self.mz.loader_segments(0x1000), [0x1000, 0x1010, 0x1020])

    def test_blocks_cover_the_image_once(self):
        blocks = self.mz.loader_blocks(self.data, 0x1000)
        self.assertEqual(sum(b['size'] for b in blocks), self.mz.image_bytes)
        self.assertEqual(blocks[0]['image_offset'], 0)
        for previous, current in zip(blocks, blocks[1:]):
            self.assertEqual(previous['image_offset'] + previous['size'],
                             current['image_offset'])

    def test_far_return_adjustment_moves_the_split_point(self):
        blocks = self.mz.loader_blocks(self.data, 0x1000)
        self.assertEqual([b['name'] for b in blocks], ['CODE_0', 'CODE_1'])
        # Segment 0x1010 starts at image 0x100, whose first byte is CB.
        self.assertEqual(blocks[1]['image_offset'], 0x101)
        self.assertEqual(blocks[1]['start'], '1010:0001')
        self.assertEqual(blocks[0]['size'], 0x101)

    def test_segment_outside_the_stored_image_is_skipped(self):
        # 0x1020 starts past the end of a 0x200-byte image.
        blocks = self.mz.loader_blocks(self.data, 0x1000)
        self.assertNotIn('1020:', ' '.join(b['start'] for b in blocks))

    def test_block_sizes_stay_consistent_after_the_far_return_adjustment(self):
        # The adjustment moves one byte from the second block's head to the
        # first block's tail. The first block's uninitialized tail is untouched
        # and must not be decremented into a negative count.
        blocks = self.mz.loader_blocks(self.data, 0x1000)
        for block in blocks:
            self.assertGreaterEqual(block['uninitialized_size'], 0)
            self.assertGreaterEqual(block['initialized_size'], 0)
            self.assertEqual(
                block['initialized_size'] + block['uninitialized_size'],
                block['size'],
            )
        self.assertEqual(blocks[0]['uninitialized_size'], 0)
        self.assertEqual(blocks[0]['initialized_size'], 0x101)
        self.assertEqual(blocks[1]['image_offset'], 0x101)
        self.assertEqual(sum(b['size'] for b in blocks), self.mz.image_bytes)

    def test_block_model_is_independent_of_the_load_paragraph(self):
        low = self.mz.loader_blocks(self.data, 0x1000)
        high = self.mz.loader_blocks(self.data, 0x2000)
        self.assertEqual([b['size'] for b in low], [b['size'] for b in high])
        self.assertEqual(high[0]['start'], '2000:0000')


class ComAndErrorTests(unittest.TestCase):
    def test_headerless_input_is_an_unqualified_com_candidate(self):
        # Every byte sequence is a valid COM load image, so size, range and
        # hash checks cannot identify one. Without an explicit claim the result
        # must say so rather than assert a format.
        data = fixtures.build_com(code=b'\xb4\x09\xcd\x21\xc3')
        candidate = dosimage.identify(data)
        self.assertEqual(candidate['format'], 'unknown')
        self.assertTrue(candidate['com_candidate'])
        self.assertEqual(candidate['interpretation'], 'none')
        self.assertIn('no header', candidate['reason'])
        self.assertIn('not a finding', candidate['scope'])
        self.assertNotIn('entry_ip', candidate)

        claimed = dosimage.identify(data, 'com')
        self.assertEqual(claimed['format'], 'com')
        self.assertEqual(claimed['interpretation'], 'explicit')

    def test_com_origin_and_mapping(self):
        image = dosimage.identify(
            fixtures.build_com(code=b'\xb4\x09\xcd\x21\xc3'), 'com'
        )
        self.assertEqual(image['format'], 'com')
        self.assertEqual(image['entry_ip'], 0x100)
        com = dosimage.ComImage.parse(b'\xb4\x09\xcd\x21\xc3')
        self.assertEqual(com.file_to_linear(0, 0x1000), 0x10100)
        self.assertEqual(com.linear_to_file(0x10100, 0x1000), 0)

    def test_rejects_structurally_impossible_headers(self):
        data, _ = fixtures.build_segmented_mz()
        cases = [
            b'',
            b'NZ' + data[2:],
            data[:8],
        ]
        for bad in cases:
            with self.assertRaises(dosimage.DosImageError):
                dosimage.MzImage.parse(bad)

        zero_pages = bytearray(data)
        struct.pack_into('<H', zero_pages, 4, 0)
        with self.assertRaises(dosimage.DosImageError):
            dosimage.MzImage.parse(bytes(zero_pages))

        short_image = bytearray(data)
        struct.pack_into('<H', short_image, 4, 1)
        with self.assertRaises(dosimage.DosImageError):
            dosimage.MzImage.parse(bytes(short_image))

    def test_relocation_outside_image_is_rejected(self):
        data, _ = fixtures.build_segmented_mz()
        broken = bytearray(data)
        struct.pack_into('<H', broken, 0x1E, 0xFFF0)  # site offset
        with self.assertRaises(dosimage.DosImageError):
            dosimage.MzImage.parse(bytes(broken))

    def test_trailing_bytes_are_reported_not_interpreted(self):
        data = fixtures.build_mz(
            image=b'\x90' * 0x20, entry_cs=0, entry_ip=0, trailing=b'OVERLAY'
        )
        mz = dosimage.MzImage.parse(data)
        self.assertEqual(mz.trailing_bytes, len(b'OVERLAY'))
        describe = mz.describe()
        self.assertIn('no runtime', describe['scope'])


class CliTests(unittest.TestCase):
    def setUp(self):
        self.data, self.expected = fixtures.build_segmented_mz()
        handle = tempfile.NamedTemporaryFile(delete=False, suffix='.EXE')
        handle.write(self.data)
        handle.close()
        self.path = handle.name

    def tearDown(self):
        Path(self.path).unlink(missing_ok=True)

    def run_cli(self, *argv):
        buffer = io.StringIO()
        import contextlib
        with contextlib.redirect_stdout(buffer):
            code = probe.main(list(argv))
        return code, json.loads(buffer.getvalue())

    def test_identify_reports_hash_and_scope(self):
        code, payload = self.run_cli('identify', self.path)
        self.assertEqual(code, 0)
        self.assertEqual(payload['format'], 'mz')
        self.assertEqual(payload['size'], len(self.data))
        self.assertEqual(len(payload['sha256']), 64)
        self.assertEqual(payload['relocation_count'],
                         self.expected['relocation_count'])

    def test_blocks_matches_the_model(self):
        code, payload = self.run_cli('blocks', self.path, '--load-paragraph', '0x4000')
        self.assertEqual(code, 0)
        self.assertEqual(payload['block_total'], payload['image_bytes'])
        self.assertEqual(payload['blocks'][0]['start'], '4000:0000')

    def test_map_reports_every_coordinate_form(self):
        code, payload = self.run_cli(
            'map', self.path, '--file-offset', hex(self.expected['string_file_offset'])
        )
        self.assertEqual(code, 0)
        entry = payload['coordinates'][0]
        self.assertEqual(entry['image_offset'],
                         self.expected['string_file_offset'] - self.expected['header_bytes'])
        self.assertEqual(entry['linear'],
                         (0x1000 << 4) + entry['image_offset'])

    def test_far_command_marks_unrelocated_pointers(self):
        code, payload = self.run_cli(
            'far', self.path, '--offset', hex(self.expected['header_bytes'] + 0x40)
        )
        self.assertEqual(code, 0)
        self.assertFalse(payload['segment_has_mz_relocation'])
        self.assertIsNone(payload['resolved_file_offset'])

    def test_far_command_reports_outside_image_pointers_without_mapping_them(self):
        # The relocated pair resolves to image offset C100h, past a 200h-byte
        # image. It must be reported as unresolved-in-file rather than raising
        # or inventing a file offset.
        code, payload = self.run_cli(
            'far', self.path, '--offset', hex(self.expected['far_pointer_file_offset'])
        )
        self.assertEqual(code, 0)
        self.assertTrue(payload['segment_has_mz_relocation'])
        self.assertEqual(payload['resolved_image_offset'], 0xC100)
        self.assertFalse(payload['resolved_inside_image'])
        self.assertIsNone(payload['resolved_file_offset'])
        self.assertIn('no file', payload['note'])

    def test_headerless_input_needs_an_explicit_interpretation(self):
        headerless = fixtures.build_com(code=b'\xb4\x09\xcd\x21\xc3')
        handle = tempfile.NamedTemporaryFile(delete=False, suffix='.COM')
        handle.write(headerless)
        handle.close()
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)

        import contextlib
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            code = probe.main(['blocks', handle.name])
        self.assertEqual(code, 2)
        self.assertIn('interpretation', json.loads(buffer.getvalue())['error'])

        code, payload = self.run_cli(
            'blocks', handle.name, '--interpretation', 'com'
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload['format'], 'com')
        self.assertEqual(payload['interpretation'], 'com')

    def test_expect_sha256_mismatch_is_refused(self):
        import contextlib
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            code = probe.main(
                ['identify', self.path, '--expect-sha256', '0' * 64]
            )
        self.assertEqual(code, 2)
        self.assertIn('does not match', json.loads(buffer.getvalue())['error'])

    def test_out_of_range_addresses_are_refused(self):
        cases = [
            ['map', self.path, '--segment-offset', '0x10000', '0'],
            ['map', self.path, '--segment-offset', '0', '0x10000'],
            ['map', self.path, '--load-paragraph', '0x10000', '--file-offset', '0x40'],
            ['far', self.path, '--offset', '0xFFFF'],
            ['disasm', self.path, '--file-offset', '0', '--length', '0'],
            ['disasm', self.path, '--file-offset', '0', '--length', '0x200000'],
            ['disasm', self.path, '--file-offset', '0xFFFFFF', '--length', '4'],
        ]
        import contextlib
        for argv in cases:
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(probe.main(argv), 2, argv)

    def test_errors_exit_nonzero_without_traceback(self):
        import contextlib
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            code = probe.main(['identify', str(ROOT / 'does-not-exist.bin')])
        self.assertEqual(code, 2)
        self.assertIn('error', json.loads(buffer.getvalue()))


class SignatureTests(unittest.TestCase):
    def test_zm_is_the_same_header_with_the_bytes_reversed(self):
        data, expected = fixtures.build_segmented_mz()
        mirror = b'ZM' + data[2:]
        image = dosimage.MzImage.parse(mirror)
        self.assertEqual(image.signature, b'ZM')
        self.assertEqual(image.image_bytes, expected['image_bytes'])
        self.assertEqual(image.entry_file_offset, expected['entry_file_offset'])
        self.assertEqual(
            [r.image_offset for r in image.relocations],
            [entry[1] for entry in expected['relocation_sites']],
        )
        self.assertEqual(image.describe()['signature'], 'ZM')

    def test_mz_reports_its_own_signature(self):
        data, _ = fixtures.build_segmented_mz()
        self.assertEqual(dosimage.MzImage.parse(data).describe()['signature'], 'MZ')

    def test_identify_accepts_the_mirror_signature(self):
        data, _ = fixtures.build_segmented_mz()
        result = dosimage.identify(b'ZM' + data[2:])
        self.assertEqual(result['format'], 'mz')
        self.assertEqual(result['signature'], 'ZM')

    def test_a_non_signature_is_still_refused(self):
        data, _ = fixtures.build_segmented_mz()
        for bad in (b'NZ' + data[2:], b'zm' + data[2:]):
            with self.assertRaises(dosimage.DosImageError):
                dosimage.MzImage.parse(bad)


class ComExtentTests(unittest.TestCase):
    def test_the_addressable_extent_is_offsets_0100_to_ffff(self):
        self.assertEqual(dosimage.MAX_COM_BYTES, 0xFF00)
        image = dosimage.ComImage.parse(bytes(dosimage.MAX_COM_BYTES))
        self.assertEqual(image.max_representable_bytes, dosimage.MAX_COM_BYTES)
        self.assertEqual(image.describe()['max_representable_bytes'], 0xFF00)
        # The last representable byte is offset FFFF.
        self.assertEqual(
            image.file_to_linear(dosimage.MAX_COM_BYTES - 1, 0x1000), 0x1FFFF
        )

    def test_an_image_too_large_for_a_sixteen_bit_offset_is_refused(self):
        with self.assertRaises(dosimage.DosImageError) as raised:
            dosimage.ComImage.parse(bytes(dosimage.MAX_COM_BYTES + 1))
        self.assertIn('0100h', str(raised.exception))

    def test_the_com_reading_refuses_a_relocatable_image(self):
        data, _ = fixtures.build_segmented_mz()
        with self.assertRaises(dosimage.DosImageError) as raised:
            dosimage.ComImage.parse(data)
        self.assertIn('signature', str(raised.exception))


class HeaderEvidenceTests(unittest.TestCase):
    def test_a_sane_header_raises_no_warnings(self):
        data, _ = fixtures.build_segmented_mz()
        self.assertEqual(dosimage.MzImage.parse(data).header_warnings(), [])

    def test_an_entry_point_outside_the_image_is_reported(self):
        data = fixtures.build_mz(
            image=b'\x90' * 0x20, entry_cs=0x0040, entry_ip=0
        )
        warnings = dosimage.MzImage.parse(data).header_warnings()
        self.assertTrue(any('entry point' in warning for warning in warnings))

    def test_contradictory_allocation_words_are_reported(self):
        data = fixtures.build_mz(
            image=b'\x90' * 0x20, entry_cs=0, entry_ip=0,
            min_alloc=0x2000, max_alloc=0x1000,
        )
        warnings = dosimage.MzImage.parse(data).header_warnings()
        self.assertTrue(any('minimum allocation' in warning for warning in warnings))

    def test_overlapping_relocation_sites_are_reported(self):
        data = fixtures.build_mz(
            image=b'\x90' * 0x40, entry_cs=0, entry_ip=0,
            relocations=((0x0000, 0x10, 0x0010), (0x0000, 0x11, 0x0010)),
        )
        warnings = dosimage.MzImage.parse(data).header_warnings()
        self.assertTrue(any('overlapping words' in warning for warning in warnings))

    def test_trailing_bytes_are_classified_as_possibly_an_overlay(self):
        data = fixtures.build_mz(
            image=b'\x90' * 0x20, entry_cs=0, entry_ip=0, trailing=b'OVERLAY'
        )
        overlay = dosimage.MzImage.parse(data).describe()['overlay']
        self.assertEqual(overlay['status'], 'possible')
        self.assertEqual(overlay['trailing_bytes'], len(b'OVERLAY'))
        self.assertIn('requires separate evidence', overlay['note'])

    def test_a_file_ending_at_its_declared_image_has_no_overlay(self):
        data, _ = fixtures.build_segmented_mz()
        overlay = dosimage.MzImage.parse(data).describe()['overlay']
        self.assertEqual(overlay['status'], 'none')
        self.assertEqual(overlay['trailing_bytes'], 0)

    def test_a_header_offset_is_not_reported_as_an_image_offset(self):
        data, expected = fixtures.build_segmented_mz()
        mz = dosimage.MzImage.parse(data)
        with self.assertRaises(dosimage.DosImageError) as raised:
            mz.file_to_image(0x10)
        message = str(raised.exception)
        self.assertIn('inside the MZ header', message)
        self.assertIn(f'{expected["header_bytes"]:#x}', message)

    def test_a_relocation_offset_names_the_load_image(self):
        data, _ = fixtures.build_segmented_mz()
        for record in dosimage.MzImage.parse(data).relocations:
            self.assertEqual(record.image_relative_offset, record.image_offset)
            self.assertFalse(hasattr(record, 'linear_offset'))


class SegmentLabelTests(unittest.TestCase):
    def setUp(self):
        self.data, self.expected = fixtures.build_segmented_mz()
        handle = tempfile.NamedTemporaryFile(delete=False, suffix='.EXE')
        handle.write(self.data)
        handle.close()
        self.path = handle.name

    def tearDown(self):
        Path(self.path).unlink(missing_ok=True)

    def run_cli(self, *argv):
        import contextlib
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = probe.main(list(argv))
        return code, json.loads(buffer.getvalue())

    def test_an_explicit_segment_zero_is_honoured(self):
        # Segment 0000h is a real real-mode segment. Treating it as "unset"
        # silently relabels the address with the load paragraph instead.
        offset = self.expected['string_file_offset']
        code, payload = self.run_cli(
            'map', self.path, '--file-offset', hex(offset),
            '--load-paragraph', '0', '--segment', '0'
        )
        self.assertEqual(code, 0)
        entry = payload['coordinates'][0]
        self.assertEqual(entry['segment'], 0)
        self.assertEqual(entry['offset'], entry['linear'])

    def test_a_segment_that_cannot_label_the_address_is_refused(self):
        # With the default synthetic load paragraph the address is 1000h-based,
        # so segment 0000h has no window over it. Refusing is honest; silently
        # substituting 1000h would answer a question nobody asked.
        offset = self.expected['string_file_offset']
        import contextlib
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            code = probe.main(
                ['map', self.path, '--file-offset', hex(offset), '--segment', '0']
            )
        self.assertEqual(code, 2)
        self.assertIn('64 KiB window', json.loads(buffer.getvalue())['error'])

    def test_an_absent_segment_falls_back_to_the_load_paragraph(self):
        offset = self.expected['string_file_offset']
        code, payload = self.run_cli(
            'map', self.path, '--file-offset', hex(offset), '--load-paragraph', '0x2000'
        )
        self.assertEqual(code, 0)
        entry = payload['coordinates'][0]
        self.assertEqual(entry['segment'], 0x2000)
        self.assertEqual(entry['offset'], entry['linear'] - 0x20000)


if __name__ == '__main__':
    unittest.main()
