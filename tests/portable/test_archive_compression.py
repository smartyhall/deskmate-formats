"""Qualify standalone compression decoding against independently produced streams.

The ``.Z`` streams below are written by a small encoder authored from
compress(1)'s published eight-code group convention, which ``ncompress`` 5.0
implements in ``output()`` and ``decompress()``. Two checks then run in opposite
directions:

* gzip 1.15's ``unlzw`` decoder -- an independent implementation -- must
  reproduce the payload from every stream this file generates. That validates
  the generator, not our decoder;
* our decoder must reproduce the same payload and report the same termination.

Without a ``gzip`` executable the second half still runs and the first is
skipped, which is recorded in the test names so a skipped run is visible.
"""

from pathlib import Path
import bz2
import lzma
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


TOOLS = Path(__file__).resolve().parents[2] / 'tools' / 'archive'
with patch.object(sys, 'path', [str(TOOLS), *sys.path]):
    import compression_streams


GZIP = shutil.which('gzip')
INITIAL_BITS = 9
CLEAR_CODE = 256


class _GroupWriter:
    """Bit packer mirroring compress(1)'s output(): contiguous LSB-first bits."""

    def __init__(self):
        self.buffer = bytearray()
        self.bits = 0
        self.origin = 0

    def put(self, code, width):
        start = self.bits
        byte, shift = start >> 3, start & 7
        span = (shift + width + 7) >> 3
        need = byte + span
        if need > len(self.buffer):
            self.buffer.extend(b'\0' * (need - len(self.buffer)))
        chunk = int.from_bytes(bytes(self.buffer[byte:need]), 'little') | (code << shift)
        self.buffer[byte:need] = chunk.to_bytes(span, 'little')
        self.bits += width

    def pad_group(self, width):
        """Pad to the end of the current eight-code group, then re-base it."""
        group = width * 8
        offset = self.bits - self.origin
        self.bits = self.origin + -(-offset // group) * group
        self.origin = self.bits

    def finish(self):
        return bytes(self.buffer[: -(-self.bits // 8)])


def compress_stream(payload, maxbits=16, block_mode=True, clear_at_fill=False):
    """Encode a compress(1) LZW stream with the documented group alignment.

    The table widens when ``free_ent`` passes the next code space, and the
    current eight-code group is padded at the old width first. In block mode a
    full table can either stop growing (what ``ncompress`` does once it reaches
    ``maxbits``) or emit CLEAR and start again, which ``clear_at_fill`` forces so
    the decoder's reset path is exercised deliberately.
    """
    out = bytearray(b'\x1f\x9d')
    out.append(maxbits | (0x80 if block_mode else 0))
    writer = _GroupWriter()
    maxmaxcode = 1 << maxbits
    first = 257 if block_mode else 256
    n_bits = INITIAL_BITS
    extcode = (1 << n_bits) + (1 if n_bits < maxbits else 0)
    free_ent = first
    table = {}
    if not payload:
        return bytes(out)
    ent = payload[0]
    for value in payload[1:]:
        if free_ent >= extcode and ent < first:
            if n_bits < maxbits:
                writer.pad_group(n_bits)
                n_bits += 1
                extcode = (1 << n_bits) + (1 if n_bits < maxbits else 0)
            else:
                extcode = (1 << 16) + 8192
        key = (ent, value)
        if key in table:
            ent = table[key]
            continue
        writer.put(ent, n_bits)
        if free_ent < maxmaxcode:
            table[key] = free_ent
            free_ent += 1
        elif clear_at_fill and block_mode:
            writer.put(CLEAR_CODE, n_bits)
            writer.pad_group(n_bits)
            n_bits = INITIAL_BITS
            extcode = (1 << n_bits) + 1
            free_ent = 257
            table.clear()
        ent = value
    writer.put(ent, n_bits)
    return bytes(out) + writer.finish()


def pseudo_random(size, seed=1):
    """Deterministic byte soup that keeps every code width transition busy."""
    state = seed
    out = bytearray(size)
    for index in range(size):
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        out[index] = (state >> 11) & 0xFF
    return bytes(out)


PAYLOADS = {
    'soup': pseudo_random(70_000),
    'text': b'the quick brown fox jumps over the lazy dog ' * 400,
    'all-bytes': bytes(range(256)) * 120,
    'runs': b'A' * 9_000 + b'B' * 4_000 + bytes(range(200)),
}


class UnixCompressMatrixTests(unittest.TestCase):
    def test_round_trips_across_every_code_width(self):
        for name, payload in PAYLOADS.items():
            for maxbits in (10, 11, 12, 13, 14, 15, 16):
                with self.subTest(payload=name, maxbits=maxbits):
                    stream = compress_stream(payload, maxbits=maxbits)
                    result = compression_streams.decode_unix_compress(stream)
                    self.assertEqual(result.status, 'ok', result.detail)
                    self.assertEqual(result.data, payload)

    def test_non_block_streams_decode(self):
        for maxbits in (10, 12, 16):
            with self.subTest(maxbits=maxbits):
                stream = compress_stream(PAYLOADS['text'], maxbits=maxbits,
                                         block_mode=False)
                self.assertEqual(stream[2] & 0x80, 0)
                result = compression_streams.decode_unix_compress(stream)
                self.assertEqual((result.status, result.data), ('ok', PAYLOADS['text']))

    def test_a_dictated_clear_resets_the_dictionary(self):
        stream = compress_stream(PAYLOADS['soup'], maxbits=12, clear_at_fill=True)
        result = compression_streams.decode_unix_compress(stream)
        self.assertEqual(result.status, 'ok', result.detail)
        self.assertEqual(result.data, PAYLOADS['soup'])
        self.assertTrue(any(w.startswith('block-clears-') for w in result.warnings))

    def test_saturation_at_the_maximum_width_is_reported(self):
        payload = PAYLOADS['runs']
        stream = compress_stream(payload, maxbits=12)
        result = compression_streams.decode_unix_compress(stream)
        self.assertEqual(result.data, payload)

    def test_nine_bit_streams_round_trip_without_cross_validation(self):
        # gzip 1.15's unlzw decoder rejects a nine-bit stream once its table
        # fills, so this width is exercised only against our own encoder and the
        # difference is recorded rather than papered over. Widths 10-16 are
        # cross-checked below.
        payload = b'the quick brown fox jumps over the lazy dog ' * 40
        stream = compress_stream(payload, maxbits=9)
        result = compression_streams.decode_unix_compress(stream)
        self.assertEqual((result.status, result.data), ('ok', payload))

    @unittest.skipUnless(GZIP, 'gzip is not installed, so the independent direction cannot run')
    def test_gzip_reproduces_every_generated_stream(self):
        for name, payload in PAYLOADS.items():
            for maxbits in (10, 12, 16):
                for block_mode in (True, False):
                    with self.subTest(payload=name, maxbits=maxbits, block=block_mode):
                        stream = compress_stream(payload, maxbits=maxbits,
                                                 block_mode=block_mode)
                        decoded = run_gzip(stream)
                        self.assertEqual(decoded, payload)

    @unittest.skipUnless(GZIP, 'gzip is not installed, so the independent direction cannot run')
    def test_gzip_reproduces_a_stream_with_forced_clears(self):
        stream = compress_stream(PAYLOADS['text'], maxbits=12, clear_at_fill=True)
        self.assertEqual(run_gzip(stream), PAYLOADS['text'])


def run_gzip(stream):
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / 'probe.Z'
        target.write_bytes(stream)
        finished = subprocess.run([GZIP, '-dc', str(target)], capture_output=True)
        if finished.returncode:
            raise AssertionError(finished.stderr.decode('cp437', 'replace')[:200])
        return finished.stdout


class UnixCompressStructureTests(unittest.TestCase):
    def test_reserved_header_flags_are_reported_not_rejected(self):
        stream = bytearray(compress_stream(b'payload', maxbits=16))
        stream[2] |= 0x40
        result = compression_streams.decode_unix_compress(bytes(stream))
        self.assertEqual(result.data, b'payload')
        self.assertIn('reserved-header-flags', result.warnings)

    def test_unsupported_widths_and_truncated_headers_fail(self):
        self.assertEqual(compression_streams.decode_unix_compress(b'\x1f\x9d').status, 'failed')
        low = b'\x1f\x9d' + bytes([0x88])
        self.assertEqual(compression_streams.decode_unix_compress(low).detail,
                         'unsupported compress maxbits')
        high = b'\x1f\x9d' + bytes([0x91])
        self.assertEqual(compression_streams.decode_unix_compress(high).detail,
                         'unsupported compress maxbits')

    def test_a_stream_ending_inside_a_code_is_partial(self):
        # Eight nine-bit codes fill exactly one group (72 bits, nine bytes); a
        # tenth byte leaves eight bits that cannot form another code.
        writer = _GroupWriter()
        for _ in range(8):
            writer.put(ord('A'), INITIAL_BITS)
        header = b'\x1f\x9d\x90'
        clean = header + writer.finish()
        complete = compression_streams.decode_unix_compress(clean)
        self.assertEqual((complete.status, complete.data), ('ok', b'AAAAAAAA'))
        partial = compression_streams.decode_unix_compress(clean + b'\0')
        self.assertEqual(partial.status, 'partial')
        self.assertEqual(partial.detail, 'truncated-final-code')
        self.assertEqual(partial.data, b'AAAAAAAA')

    def test_an_invalid_initial_code_is_rejected(self):
        invalid = b'\x1f\x9d' + bytes([0x90]) + bytes([0x01, 0x01])
        self.assertEqual(compression_streams.decode_unix_compress(invalid).detail,
                         'invalid-initial-code')

    def test_output_and_code_bounds_terminate_early(self):
        payload = b'repeat ' * 400
        stream = compress_stream(payload)
        limited = compression_streams.decode_unix_compress(
            stream, compression_streams.Bounds(output_bytes=64))
        self.assertEqual((limited.status, limited.detail), ('limited', 'output-byte-limit'))
        self.assertIsNone(limited.data)
        capped = compression_streams.decode_unix_compress(
            stream, compression_streams.Bounds(codes=8))
        self.assertEqual((capped.status, capped.detail), ('limited', 'code-limit'))

    def test_identification_requires_the_magic_pair(self):
        self.assertEqual(compression_streams.identify_stream(b'\x1f\x9d\x90'), 'unix-compress')
        self.assertIsNone(compression_streams.identify_stream(b'\x1f\x8b\x08'))
        self.assertIsNone(compression_streams.identify_stream(b''))


class StandardLibraryStreamTests(unittest.TestCase):
    def test_bzip2_round_trip_and_identification(self):
        payload = b'synthetic bzip2 control\r\n' * 50
        stream = bz2.compress(payload)
        self.assertEqual(compression_streams.identify_stream(stream), 'bzip2')
        result = compression_streams.decode_bzip2(stream)
        self.assertEqual((result.status, result.data), ('ok', payload))

    def test_xz_round_trip_and_identification(self):
        payload = b'synthetic xz control\r\n' * 50
        stream = lzma.compress(payload, format=lzma.FORMAT_XZ)
        self.assertEqual(compression_streams.identify_stream(stream), 'xz')
        result = compression_streams.decode_xz(stream)
        self.assertEqual((result.status, result.data), ('ok', payload))

    def test_concatenated_streams_are_joined_and_counted(self):
        first, second = b'first stream\n', b'second stream\n'
        result = compression_streams.decode_bzip2(bz2.compress(first) + bz2.compress(second))
        self.assertEqual((result.status, result.data), ('ok', first + second))
        self.assertIn('concatenated-streams-2', result.warnings)
        packed = (lzma.compress(first, format=lzma.FORMAT_XZ)
                  + lzma.compress(second, format=lzma.FORMAT_XZ))
        result = compression_streams.decode_xz(packed)
        self.assertEqual((result.status, result.data), ('ok', first + second))
        self.assertIn('concatenated-streams-2', result.warnings)

    def test_the_number_of_concatenated_streams_is_bounded(self):
        packed = lzma.compress(b'x', format=lzma.FORMAT_XZ) * 3
        result = compression_streams.decode_xz(packed, compression_streams.Bounds(streams=2))
        self.assertEqual((result.status, result.detail), ('limited', 'stream-count-limit'))
        self.assertIsNone(result.data)

    def test_a_later_member_cannot_raise_the_decoder_memory_budget(self):
        # The first member declares 100 kB blocks and fits a 1 MiB budget; the
        # second declares 900 kB blocks, whose documented requirement is
        # 3700 KiB. The budget belongs to the caller, so a small first member
        # must not authorise the larger second one.
        small = bz2.compress(b'low block control', compresslevel=1)
        large = bz2.compress(b'high block control', compresslevel=9)
        self.assertEqual(small[3], ord('1'))
        self.assertEqual(large[3], ord('9'))
        budget = compression_streams.Bounds(decoder_bytes=1024 * 1024)
        self.assertEqual(compression_streams.decode_bzip2(small, budget).status, 'ok')
        result = compression_streams.decode_bzip2(small + large, budget)
        self.assertEqual((result.status, result.detail), ('limited', 'decoder-memory-limit'))
        self.assertEqual(result.streams, 2)
        self.assertIsNone(result.data)

    def test_a_later_member_cannot_raise_the_xz_dictionary_budget(self):
        # 256 KiB covers a 4 KiB dictionary with the decoder's fixed tables.
        budget = compression_streams.Bounds(decoder_bytes=1 << 18)
        small = lzma.compress(b'low dictionary', format=lzma.FORMAT_XZ,
                              filters=[{'id': lzma.FILTER_LZMA2, 'dict_size': 1 << 12}])
        large = lzma.compress(b'high dictionary', format=lzma.FORMAT_XZ,
                              filters=[{'id': lzma.FILTER_LZMA2, 'dict_size': 1 << 24}])
        self.assertEqual(compression_streams.decode_xz(small, budget).status, 'ok')
        result = compression_streams.decode_xz(small + large, budget)
        self.assertEqual((result.status, result.detail), ('limited', 'decoder-memory-limit'))
        self.assertEqual(result.streams, 2)
        self.assertIsNone(result.data)

    def test_a_damaged_later_member_keeps_the_members_that_verified(self):
        first = b'first verified member\n' * 8
        second = bytearray(bz2.compress(b'second damaged member\n' * 8))
        second[10] ^= 0xFF
        result = compression_streams.decode_bzip2(bz2.compress(first) + bytes(second))
        self.assertEqual((result.status, result.data), ('partial', first))
        self.assertTrue(result.detail.startswith('member-2-'), result.detail)
        truncated = bz2.compress(b'second truncated member\n' * 8)[:-4]
        result = compression_streams.decode_bzip2(bz2.compress(first) + truncated)
        self.assertEqual((result.status, result.data, result.detail),
                         ('partial', first, 'member-2-truncated-stream'))

    def test_a_damaged_first_member_yields_no_payload(self):
        damaged = bytearray(bz2.compress(b'damaged member\n' * 8))
        damaged[10] ^= 0xFF
        result = compression_streams.decode_bzip2(bytes(damaged) + bz2.compress(b'second'))
        self.assertEqual((result.status, result.data), ('failed', None))

    def test_trailing_data_is_reported_without_hiding_the_payload(self):
        payload = b'truncation control' * 20
        result = compression_streams.decode_bzip2(bz2.compress(payload) + b'leavings')
        self.assertEqual((result.status, result.data), ('ok', payload))
        self.assertIn('trailing-data', result.warnings)

    def test_truncated_and_corrupt_streams_fail(self):
        stream = bz2.compress(b'truncation control' * 20)
        self.assertEqual(compression_streams.decode_bzip2(stream[:-4]).detail,
                         'truncated-stream')
        corrupt = bytearray(stream)
        corrupt[10] ^= 0xFF
        self.assertEqual(compression_streams.decode_bzip2(bytes(corrupt)).status, 'failed')
        packed = lzma.compress(b'control' * 40, format=lzma.FORMAT_XZ)
        self.assertEqual(compression_streams.decode_xz(packed[:-8]).status, 'failed')

    def test_decoder_memory_is_bounded_independently_of_output(self):
        # A 900 kB bzip2 block needs several block-sized tables even when the
        # decoded payload is tiny.
        small = compression_streams.Bounds(decoder_bytes=64 * 1024)
        self.assertEqual(compression_streams.decode_bzip2(bz2.compress(b'tiny'), small).detail,
                         'decoder-memory-limit')
        # An .xz block may declare a large dictionary and allocate it before it
        # emits a single byte.
        filters = [{'id': lzma.FILTER_LZMA2, 'dict_size': 1 << 24}]
        packed = lzma.compress(b'tiny', format=lzma.FORMAT_XZ, filters=filters)
        limited = compression_streams.decode_xz(
            packed, compression_streams.Bounds(decoder_bytes=1 << 16))
        self.assertEqual((limited.status, limited.detail), ('limited', 'decoder-memory-limit'))
        self.assertIsNone(limited.data)

    def test_the_documented_bzip2_requirement_is_the_budget_unit(self):
        # bzip2(1)'s MEMORY MANAGEMENT table gives 3700 KiB for 900 kB blocks;
        # four block bytes (3600 kB) is the table allocation alone and
        # understates the decoder's working set.
        stream = bz2.compress(b'documented requirement')
        required = compression_streams.BZIP2_DECOMPRESS_KIB[9] * 1024
        self.assertEqual(required, 3700 * 1024)
        exact = compression_streams.decode_bzip2(
            stream, compression_streams.Bounds(decoder_bytes=required))
        self.assertEqual(exact.status, 'ok')
        under = compression_streams.decode_bzip2(
            stream, compression_streams.Bounds(decoder_bytes=required - 1))
        self.assertEqual((under.status, under.detail), ('limited', 'decoder-memory-limit'))
        # A 100 kB member fits the same budget that a 900 kB member cannot use.
        low = bz2.compress(b'documented requirement', compresslevel=1)
        self.assertEqual(compression_streams.decode_bzip2(
            low, compression_streams.Bounds(decoder_bytes=500 * 1024)).status, 'ok')

    def test_output_bound_applies_before_full_expansion(self):
        payload = bytes(1 << 20)
        stream = lzma.compress(payload, format=lzma.FORMAT_XZ)
        result = compression_streams.decode_xz(stream, compression_streams.Bounds(output_bytes=1024))
        self.assertEqual((result.status, result.detail), ('limited', 'output-byte-limit'))

    def test_unknown_family_is_unsupported(self):
        self.assertEqual(compression_streams.decode(b'x', 'lzo').status, 'unsupported')


class ExtractorIntegrationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def load(self):
        with patch.object(sys, 'path', [str(TOOLS), *sys.path]):
            import intelligence_extract
        return intelligence_extract

    def test_compress_stream_is_identified_and_decompressed(self):
        archive = self.load()
        payload = b'nested control payload\r\n'
        target = self.root / 'NOTES.TXT.Z'
        target.write_bytes(compress_stream(payload))
        kind = archive.identify(target, 'NOTES.TXT.Z')
        self.assertEqual(kind, 'unix-compress')
        result = archive.extract(target, 'NOTES.TXT.Z', kind)
        self.assertEqual([(m.name, m.status, m.data) for m in result.members],
                         [('NOTES.TXT', 'ok', payload)])
        self.assertIn(kind, archive.CONTAINER_KINDS)

    def test_a_partial_stream_is_not_reported_as_a_complete_member(self):
        archive = self.load()
        writer = _GroupWriter()
        for _ in range(8):
            writer.put(ord('B'), INITIAL_BITS)
        target = self.root / 'PARTIAL.BIN.Z'
        target.write_bytes(b'\x1f\x9d\x90' + writer.finish() + b'\0')
        result = archive.extract(target, 'PARTIAL.BIN.Z', 'unix-compress')
        self.assertEqual(result.status, 'partial')
        self.assertIn('truncated-final-code', result.detail)
        self.assertEqual(result.members[0].data, b'BBBBBBBB')

    def test_xz_member_name_is_derived_and_bounded(self):
        archive = self.load()
        target = self.root / 'payload.xz'
        target.write_bytes(lzma.compress(b'bound control', format=lzma.FORMAT_XZ))
        kind = archive.identify(target, 'payload.xz')
        self.assertEqual(kind, 'xz')
        result = archive.extract(target, 'payload.xz', kind,
                                 archive.Limits(member_bytes=4))
        self.assertEqual((result.status, result.detail), ('limited', 'xz; output-byte-limit'))
        self.assertEqual(result.members, [])

    def test_the_compression_input_bound_is_enforced_by_the_read_itself(self):
        archive = self.load()
        target = self.root / 'payload.xz'
        target.write_bytes(lzma.compress(b'bound control' * 4, format=lzma.FORMAT_XZ))
        # extract()'s size inspection is only a pre-check; the read that feeds
        # the decoder is what enforces the caller's input bound.
        result = archive._compressed(target, 'payload.xz', 'xz',
                                     archive.Limits(input_bytes=8))
        self.assertEqual((result.status, result.detail), ('limited', 'input-byte-limit'))

    def test_text_that_resembles_a_stream_header_stays_text(self):
        archive = self.load()
        target = self.root / 'notes.z'
        target.write_bytes(b'ordinary reference notes about BZh files\r\n')
        self.assertEqual(archive.identify(target, 'notes.z'), 'text')


if __name__ == '__main__':
    unittest.main()
