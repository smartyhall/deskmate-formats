"""Qualify the native ARC methods 8 and 9 decoder against an independent encoder.

The encoder here is written from the same bit-level description as the
decoder, so it can only show that both agree. The conventions it encodes were
established separately: all four method-8 members in the historical corpus
reproduce their stored CRC, and each consumes its packed bytes exactly.
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


class _CrunchWriter:
    """LSB-first bit packer that keeps the group-of-eight code count."""

    def __init__(self, prefix=b''):
        self.out = bytearray(prefix)
        self.box = 0
        self.count = 0
        self.codes = 0

    def write(self, code, width):
        self.box |= code << self.count
        self.count += width
        while self.count >= 8:
            self.out.append(self.box & 0xFF)
            self.box >>= 8
            self.count -= 8
        self.codes = (self.codes + 1) & 7

    def pad(self, width):
        # ARC padded a group of eight before changing the code width.
        while self.codes:
            self.write(0, width)

    def flush(self):
        while self.count > 0:
            self.out.append(self.box & 0xFF)
            self.box >>= 8
            self.count -= 8
        self.count = 0
        return bytes(self.out)


def rle90(payload):
    """Encode the RLE90 stage that method 8 applies after LZW."""
    out = bytearray()
    position = 0
    while position < len(payload):
        byte = payload[position]
        if byte == 0x90:
            out += b'\x90\x00'
            position += 1
            continue
        run = 1
        while (position + run < len(payload) and payload[position + run] == byte
               and run < 255):
            run += 1
        if run >= 3:
            out += bytes([byte, 0x90, run])
        else:
            out += payload[position:position + run]
        position += run
    return bytes(out)


def crunch(payload, max_bits=12, rle=True):
    """Encode one ARC method 8 (max_bits 12) or method 9 (13) member.

    The table bookkeeping mirrors the decoder's: slot 256 is always the
    width-shrink code, so the decoder's entry at 256 is an artefact and the
    encoder never assigns a string to it.
    """
    source = rle90(payload) if rle else payload
    limit = 1 << max_bits
    writer = _CrunchWriter(b'\x0c' if max_bits == 12 else b'')
    width = 9
    last = 255
    table = {}
    if not source:
        return writer.flush()
    entry = source[0]
    for byte in source[1:]:
        key = (entry, byte)
        if key in table:
            entry = table[key]
            continue
        writer.write(entry, width)
        # The decoder adds its entry one code after the encoder matches the
        # string, so the decoder cursor trails the encoder index by one.
        last += 1
        if last != limit - 1:
            table[key] = last + 1
            if last == (1 << width) - 1 and width < max_bits:
                writer.pad(width)
                width += 1
        else:
            # The table is full: 256 shrinks the width and lets entries above
            # 255 be overwritten.
            writer.write(256, width)
            writer.pad(width)
            width = 9
            last = 255
            table = {}
        entry = byte
    writer.write(entry, width)
    return writer.flush()


def crc16(payload):
    crc = 0
    for byte in payload:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc & 0xFFFF


def archive(method, name, payload, original):
    header = (b'\x1a' + bytes([method]) + name.encode('cp437').ljust(13, b'\0')
              + struct.pack('<IHHH', len(payload), 0x0f10, 0x0a5c, crc16(original))
              + struct.pack('<I', len(original)))
    return header + payload + b'\x1a\0'


class CrunchDecoderTests(unittest.TestCase):
    def round_trip(self, payload, max_bits=12, rle=True):
        packed = crunch(payload, max_bits=max_bits, rle=rle)
        decoded = extractor._arc_crunch(packed, max_bits, rle, len(payload))
        self.assertEqual(decoded, payload)
        return packed

    def test_literals_and_repeated_strings(self):
        for payload in (b'A', b'TOPSPEED', b'ABCABCABCABCABC', bytes(range(256))):
            with self.subTest(payload=payload[:12]):
                self.round_trip(payload)

    def test_rle_stage_runs_and_literal_escape(self):
        self.assertEqual(rle90(b'AAAAAA'), b'A\x90\x06')
        self.assertEqual(rle90(b'\x90'), b'\x90\x00')
        payload = b'AAAAAA' + b'\x90' + b'BBBB' + b'\x90\x90' + b'CC'
        self.round_trip(payload)
        # Method 9 has no RLE stage, so the same bytes must also survive there.
        self.round_trip(payload, max_bits=13, rle=False)

    def test_code_width_grows_through_ten_and_eleven_bits(self):
        payload = b''.join(b'line %04d of a synthetic control file\r\n' % index
                           for index in range(400))
        packed = self.round_trip(payload)
        self.assertGreater(len(packed), 512)

    def test_code_256_shrinks_the_width_without_clearing_the_table(self):
        # Enough distinct strings to fill the 12-bit table and force a 256.
        payload = b''.join(b'%05d:%s;' % (index, bytes([65 + index % 26]) * (index % 7))
                           for index in range(9000))
        packed = self.round_trip(payload)
        self.assertGreater(len(packed), 4096)

    def test_method_9_uses_thirteen_bits_and_no_rle(self):
        payload = (b'\x90\x90\x90' + b'method nine control line\r\n') * 300
        packed = self.round_trip(payload, max_bits=13, rle=False)
        # Method 9 has no leading max-width byte and no RLE stage.
        self.assertNotEqual(packed[0], 0x0C)

    def test_output_budget_is_enforced(self):
        payload = b'budget control ' * 400
        packed = crunch(payload)
        with self.assertRaises(ValueError):
            extractor._arc_crunch(packed, 12, True, 64)


class ArchiveReaderTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def extract(self, data, name='member.arc'):
        target = self.root / name
        target.write_bytes(data)
        return extractor.extract(target, name, extractor.identify(target, name))

    def test_method_8_member_is_extracted_without_an_external_decoder(self):
        original = b'method eight control\r\n' * 40 + b'RRRRRRRR' + b'\x90'
        packed = crunch(original)
        result = self.extract(archive(8, 'CONTROL.DOC', packed, original))
        self.assertEqual(result.status, 'ok')
        self.assertEqual([(m.name, m.status, m.data) for m in result.members],
                         [('CONTROL.DOC', 'ok', original)])

    def test_method_9_member_is_extracted_without_an_external_decoder(self):
        original = (b'\x90' * 5 + b'method nine control\r\n') * 60
        packed = crunch(original, max_bits=13, rle=False)
        result = self.extract(archive(9, 'NINE.TXT', packed, original))
        self.assertEqual([(m.name, m.status, m.data) for m in result.members],
                         [('NINE.TXT', 'ok', original)])

    def test_corrupted_member_fails_its_crc(self):
        original = b'crc control\r\n' * 10
        packed = bytearray(crunch(original))
        packed[3] ^= 0x40
        result = self.extract(archive(8, 'BROKEN.TXT', bytes(packed), original))
        self.assertEqual(result.status, 'partial')
        self.assertEqual(result.members[0].status, 'read-error')

    def test_truncated_member_is_reported_rather_than_repaired(self):
        original = b'truncation control\r\n' * 40
        packed = crunch(original)
        result = self.extract(archive(8, 'SHORT.TXT', packed[:-6], original))
        self.assertEqual(result.status, 'partial')
        self.assertIn(result.members[0].status, ('read-error', 'size-mismatch'))
        self.assertIsNone(result.members[0].data)

    def test_stored_method_with_a_size_mismatch_is_reported(self):
        original = b'stored control'
        result = self.extract(archive(2, 'STORED.TXT', original, original + b'!'))
        self.assertEqual(result.members[0].status, 'size-mismatch')

    def test_unsupported_method_still_needs_the_external_decoder(self):
        original = b'packed control'
        result = self.extract(archive(5, 'OLD.TXT', b'\x00\x01', original))
        self.assertEqual(result.status, 'partial')
        self.assertEqual(result.members[0].status, 'unsupported-arc-method-5')


if __name__ == '__main__':
    unittest.main()
