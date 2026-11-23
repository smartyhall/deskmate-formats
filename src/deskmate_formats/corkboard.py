"""Read the measured fixed-size DOS DeskMate DMCORKBD note buffer."""

from dataclasses import dataclass
from pathlib import Path
from struct import unpack_from

SIZE = 2864


@dataclass(frozen=True)
class Corkboard:
    """Keep the original bytes, including any text left behind by Clear."""

    data: bytes
    header_words: tuple[int, int]
    text: bytes


def parse_bytes(source):
    """Inspect a known DMCORKBD file with ASCII text and CR line breaks."""
    if not isinstance(source, (bytes, bytearray, memoryview)):
        raise ValueError('expected byte snapshot')
    size = source.nbytes if isinstance(source, memoryview) else len(source)
    if size != SIZE:
        raise ValueError('expected a 2864-byte DMCORKBD buffer')
    data = bytes(source)
    end = data.find(b'\0', 4)
    if end < 0:
        raise ValueError('unterminated DMCORKBD text')
    note = data[4:end]
    if any(byte != 0x0D and not 0x20 <= byte <= 0x7E for byte in note):
        raise ValueError('unsupported DMCORKBD text byte')
    return Corkboard(data, unpack_from('<HH', data), note)


def parse_file(path):
    with Path(path).open('rb') as handle:
        return parse_bytes(handle.read(SIZE + 1))
