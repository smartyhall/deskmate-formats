"""Native controls checked with raw offsets, independent of production codecs."""
from pathlib import Path
from hashlib import sha256
import struct
import unittest

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures/application-generated/calendar'


def expected_split(source):
    first = source[0x1428:0x151E]
    second = source[0x151E:0x1614]
    page, offset, ident = struct.unpack_from('<HHH', first, 19 * 6)
    at = page * 1024 + offset
    assert source[at:at + 2] == bytes((0x80, ident))
    end = source.index(b'\x01\x02', at + 2)
    fields = source[at + 2:end].split(b'\x01')
    # In these ordinary Calendar endpoints the first four sort fields exactly
    # fill ten bytes; no production index_prefix or Calendar value codec.
    prefix = b''.join(fields[n - 1] + b'\x01' for n in (1, 2, 4, 5))
    assert len(prefix) == 10
    output = bytearray(source)
    output[0x1400:0x140A] = prefix
    output[0x1428:0x1800] = (first[:120] + bytes(126) + first[120:]
                             + bytes(120) + second + bytes(246))
    return bytes(output)


class NativeIndexControlsTests(unittest.TestCase):
    def test_two_native_whole_files_match_independent_split(self):
        for source, native, digest, count in (
            ('sdk-30-days-allocator-tool-generated.cln', 'native-30-day-open-close-20261117.cln',
             '8ba8a9b45fe2da1f0c685a4b1b0e3a8ad0c1672bc8429390d2e456f5acc99b8d', 237),
            ('sdk-29-days-forward-tool-generated.cln', 'native-29-day-open-close-20261117.cln',
             '90fb11730967dc3957c6f8a33313073a20de0fc9916efd94164e661046ccf2e7', 226),
        ):
            with self.subTest(native=native):
                before, after = (FIXTURES / source).read_bytes(), (FIXTURES / native).read_bytes()
                self.assertEqual(len(after), 8192)
                self.assertEqual(sha256(after).hexdigest(), digest)
                self.assertEqual(after, expected_split(before))
                self.assertEqual(sum(a != b for a, b in zip(before, after)), count)

    def test_native_month_page_matches_earlier_independent_specimens(self):
        page = (FIXTURES / 'native-30-day-open-close-20261117.cln').read_bytes()[5120:6144]
        for name in ('native-second-empty-calendar-operator.cln',
                     'native-second-first-event-operator.cln',
                     'native-30-day-edit-save-20261117.cln'):
            self.assertEqual(page, (FIXTURES / name).read_bytes()[5120:6144])
