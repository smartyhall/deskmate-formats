"""Read the measured fixed-size DOS DeskMate DMCORKBD note buffer.

The text area is treated as CP437 bytes, not ASCII: the RSX editor renders
CP437 glyphs and stores the bytes unchanged (Alt+130 stored 0x82, Alt+225
stored 0xE1). Printable ASCII, CR and the high half are accepted; the control
range other than CR, and DEL, stay rejected because no native specimen has
exercised them.
"""

from dataclasses import dataclass
from pathlib import Path
from struct import unpack_from

SIZE = 2864
TEXT_OFFSET = 4
TEXT_SIZE = 2860
TERMINATOR = b'\x0D'
ENCODING = 'cp437'


@dataclass(frozen=True)
class Corkboard:
    """Keep the original bytes, including any text left behind by Clear."""

    data: bytes
    header_words: tuple[int, int]
    text: bytes

    @property
    def decoded(self):
        """The visible text as CP437, which is what the native editor draws."""
        return self.text.decode(ENCODING)

    @property
    def rows(self):
        """CR-delimited rows as CP437 text, without a trailing empty row for a final CR."""
        rows = self.text.split(TERMINATOR)
        if self.text.endswith(TERMINATOR):
            rows.pop()
        return [row.decode(ENCODING) for row in rows]


def _supported(byte):
    # Measured: 0x0D delimiters, printable ASCII, and the CP437 high half.
    # Unmeasured: 0x00-0x1F other than CR, and 0x7F.
    return byte == 0x0D or 0x20 <= byte <= 0xFF and byte != 0x7F


def parse_bytes(source):
    """Inspect a known DMCORKBD file with CP437 text and CR line breaks."""
    if not isinstance(source, (bytes, bytearray, memoryview)):
        raise ValueError('expected byte snapshot')
    size = source.nbytes if isinstance(source, memoryview) else len(source)
    if size != SIZE:
        raise ValueError('expected a 2864-byte DMCORKBD buffer')
    data = bytes(source)
    end = data.find(b'\0', TEXT_OFFSET)
    if end < 0:
        raise ValueError('unterminated DMCORKBD text')
    note = data[TEXT_OFFSET:end]
    if any(not _supported(byte) for byte in note):
        raise ValueError('unsupported DMCORKBD text byte')
    return Corkboard(data, unpack_from('<HH', data), note)


def parse_file(path):
    with Path(path).open('rb') as handle:
        return parse_bytes(handle.read(SIZE + 1))
