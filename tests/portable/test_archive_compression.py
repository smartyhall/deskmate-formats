"""Qualify standalone compression decoding against hand-authored streams."""

from io import BytesIO
from pathlib import Path
import bz2
import lzma
import sys
import unittest
from unittest.mock import patch


TOOLS = Path(__file__).resolve().parents[2] / 'tools' / 'archive'
with patch.object(sys, 'path', [str(TOOLS), *sys.path]):
    import compression


class _BitWriter:
    """LSB-first packer, authored from the compress(1) description."""

    def __init__(self, out):
        self.out = out
        self.buffer = 0
        self.count = 0

    def write(self, code, width):
        self.buffer |= code << self.count
        self.count += width
        while self.count >= 8:
            self.out.append(self.buffer & 0xFF)
            self.buffer >>= 8
            self.count -= 8

    def flush(self):
        while self.count > 0:
            self.out.append(self.buffer & 0xFF)
            self.buffer >>= 8
            self.count -= 8


def compress_stream(payload, maxbits=16, block_mode=True):
    """Encode a compress(1) LZW stream.

    This encoder exists so the decoder can be tested against bytes it did not
    produce. Width growth is applied before a code is written, matching the
    decoder's read-side behaviour.
    """
    out = bytearray(b'\x1f\x9d')
    out.append(maxbits | (0x80 if block_mode else 0))
    writer = _BitWriter(out)
    maxmaxcode = 1 << maxbits
    n_bits = 9
    maxcode = 511
    free_ent = 257 if block_mode else 256
    table = {}

    def emit(code, fixed_width=None):
        nonlocal n_bits, maxcode
        writer.write(code, fixed_width or n_bits)
        # compress(1) widens the code width only after the current code has
        # been written, because the reader cannot observe the increase until
        # it has consumed that code.
        if fixed_width is None and free_ent > maxcode and n_bits < maxbits:
            n_bits += 1
            maxcode = maxmaxcode if n_bits == maxbits else (1 << n_bits) - 1

    if not payload:
        writer.flush()
        return bytes(out)
    ent = payload[0]
    for value in payload[1:]:
        key = (ent, value)
        if key in table:
            ent = table[key]
            continue
        emit(ent)
        if free_ent < maxmaxcode:
            table[key] = free_ent
            free_ent += 1
        else:
            emit(256, fixed_width=n_bits)
            table = {}
            free_ent = 257
            n_bits = 9
            maxcode = 511
        ent = value
    emit(ent)
    writer.flush()
    return bytes(out)


class UnixCompressTests(unittest.TestCase):
    def test_round_trips_short_streams_across_dictionary_widths(self):
        payloads = [
            b'a',
            b'TOPSPEED',
            b'ABABABABABABABABAB',
            bytes(range(256)) * 3,
            (b'synthetic control line\r\n' * 40),
        ]
        for maxbits in (9, 10, 12, 16):
            for payload in payloads:
                with self.subTest(maxbits=maxbits, size=len(payload)):
                    stream = compress_stream(payload, maxbits=maxbits)
                    self.assertEqual(stream[:2], b'\x1f\x9d')
                    result = compression.decode_unix_compress(stream)
                    self.assertEqual(result.status, 'ok')
                    self.assertEqual(result.data, payload)

    def test_clear_code_resets_a_full_dictionary(self):
        # maxbits=9 saturates the dictionary quickly, forcing block-mode clears
        # while keeping every code nine bits wide.
        payload = (b'0123456789abcdef' * 200)
        stream = compress_stream(payload, maxbits=9)
        self.assertGreater(len(stream), 3)
        result = compression.decode_unix_compress(stream)
        self.assertEqual(result.status, 'ok')
        self.assertEqual(result.data, payload)

    def test_unblocked_stream_never_emits_a_clear_code(self):
        payload = b'ABCDABCDABCDABCDABCD'
        stream = compress_stream(payload, maxbits=9, block_mode=False)
        result = compression.decode_unix_compress(stream)
        self.assertEqual(result.data, payload)

    def test_rejects_malformed_headers_and_invalid_codes(self):
        self.assertEqual(compression.decode_unix_compress(b'\x1f\x9d').status, 'failed')
        unsupported = b'\x1f\x9d' + bytes([0x88])
        self.assertEqual(compression.decode_unix_compress(unsupported).detail,
                         'unsupported compress maxbits')
        # A block-mode stream whose first code is 257 rather than a literal is invalid.
        invalid = b'\x1f\x9d' + bytes([0x90]) + bytes([0x01, 0x01])
        self.assertEqual(compression.decode_unix_compress(invalid).detail,
                         'invalid-initial-code')

    def test_bounds_truncated_input_and_output_expansion(self):
        payload = b'repeat ' * 400
        stream = compress_stream(payload)
        bounds = compression.Bounds(output_bytes=64)
        limited = compression.decode_unix_compress(stream, bounds)
        self.assertEqual((limited.status, limited.detail), ('limited', 'output-byte-limit'))
        self.assertIsNone(limited.data)
        truncated = compression.decode_unix_compress(stream[:12])
        self.assertEqual(truncated.status, 'ok')
        self.assertNotEqual(truncated.data, payload)
        self.assertEqual(compression.decode_unix_compress(b'').status, 'failed')

    def test_identification_requires_the_magic_pair(self):
        self.assertEqual(compression.identify_stream(b'\x1f\x9d\x90'), 'unix-compress')
        self.assertIsNone(compression.identify_stream(b'\x1f\x8b\x08'))
        self.assertIsNone(compression.identify_stream(b''))


class StandardLibraryStreamTests(unittest.TestCase):
    def test_bzip2_round_trip_and_identification(self):
        payload = b'synthetic bzip2 control\r\n' * 50
        stream = bz2.compress(payload)
        self.assertEqual(compression.identify_stream(stream), 'bzip2')
        result = compression.decode_bzip2(stream)
        self.assertEqual((result.status, result.data), ('ok', payload))

    def test_xz_round_trip_and_identification(self):
        payload = b'synthetic xz control\r\n' * 50
        stream = lzma.compress(payload, format=lzma.FORMAT_XZ)
        self.assertEqual(compression.identify_stream(stream), 'xz')
        result = compression.decode_xz(stream)
        self.assertEqual((result.status, result.data), ('ok', payload))

    def test_truncated_corrupt_and_trailing_data(self):
        payload = b'truncation control' * 20
        stream = bz2.compress(payload)
        self.assertEqual(compression.decode_bzip2(stream[:-4]).status, 'failed')
        self.assertEqual(compression.decode_bzip2(stream[:-4]).detail, 'truncated-stream')
        corrupt = bytearray(stream)
        corrupt[10] ^= 0xFF
        self.assertEqual(compression.decode_bzip2(bytes(corrupt)).status, 'failed')
        trailing = bz2.compress(payload) + b'leavings'
        result = compression.decode_bzip2(trailing)
        self.assertEqual(result.status, 'ok')
        self.assertIn('trailing-data', result.warnings)

    def test_output_bound_applies_before_full_expansion(self):
        payload = bytes(1 << 20)
        stream = lzma.compress(payload, format=lzma.FORMAT_XZ)
        result = compression.decode_xz(stream, compression.Bounds(output_bytes=1024))
        self.assertEqual((result.status, result.detail), ('limited', 'output-byte-limit'))

    def test_unknown_family_is_unsupported(self):
        self.assertEqual(compression.decode(b'x', 'lzo').status, 'unsupported')


class ExtractorIntegrationTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

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

    def test_text_that_resembles_a_stream_header_stays_text(self):
        archive = self.load()
        target = self.root / 'notes.z'
        target.write_bytes(b'ordinary reference notes about BZh files\r\n')
        self.assertEqual(archive.identify(target, 'notes.z'), 'text')


if __name__ == '__main__':
    unittest.main()
