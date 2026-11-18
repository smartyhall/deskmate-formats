"""Decode the measured Filer GRAPHICS record stream."""
from dataclasses import dataclass
from struct import unpack_from

from . import graphics


@dataclass(frozen=True)
class Section:
    """One complete encoded card or report form and its database row locators."""

    marker: str
    row_offsets: tuple[int, ...]
    encoded_chunks: tuple[bytes, ...]
    payload: bytes
    form: graphics.Form


def _section(marker, rows, payload, size):
    if len(payload) != size:
        raise graphics.GraphicsFormatError('incomplete GRAPHICS section')
    return Section(marker, tuple(row.offset for row in rows),
                   tuple(row.fields[1] for row in rows), payload, graphics.parse_bytes(payload))


def _unescape(chunk):
    output = bytearray()
    cursor = 0
    while cursor < len(chunk):
        byte = chunk[cursor]
        cursor += 1
        if byte == 7:
            if cursor >= len(chunk) or not 0x40 <= chunk[cursor] <= 0x47:
                raise graphics.GraphicsFormatError('invalid or truncated GRAPHICS escape')
            byte = chunk[cursor] - 0x40
            cursor += 1
        elif byte < 7:
            raise graphics.GraphicsFormatError('unescaped low byte in GRAPHICS')
        output.append(byte)
    return bytes(output)


def decode(snapshot):
    """Decode indexed GRAPHICS chunks in native record order.

    F and R start record/card and report forms. Ampersand continues the
    current form. Other record dialects are outside the measured profile.
    """
    if not any(table.name == 'GRAPHICS' for table in snapshot.tables):
        return ()
    table = snapshot.table('GRAPHICS')
    schema = tuple((col.name, col.width, col.kind) for col in table.columns)
    if schema != (('RECORD', 1, 'C'), ('BITS', 1018, 'C')):
        raise graphics.GraphicsFormatError('unsupported Filer GRAPHICS schema')
    sections = []
    marker = None
    rows = []
    payload = b''
    size = 0
    for row in table.rows:
        record, encoded = row.fields
        if not 1 <= len(encoded) <= 1016:
            raise graphics.GraphicsFormatError('invalid GRAPHICS field size')
        chunk = _unescape(encoded)
        if record in (b'F', b'R'):
            if marker is not None:
                sections.append(_section(marker, rows, payload, size))
            marker = record.decode('ascii')
            if any(section.marker == marker for section in sections):
                raise graphics.GraphicsFormatError('duplicate GRAPHICS section')
            if len(chunk) < graphics.PREFIX_SIZE:
                raise graphics.GraphicsFormatError('truncated GRAPHICS form header')
            size = graphics.PREFIX_SIZE + sum(unpack_from('<HH', chunk, graphics.HEADER_SIZE))
            rows = [row]
            payload = chunk
        elif record == b'&' and marker is not None:
            rows.append(row)
            payload += chunk
        else:
            raise graphics.GraphicsFormatError('unexpected GRAPHICS record marker')
        if len(payload) > size:
            raise graphics.GraphicsFormatError('GRAPHICS section exceeds declared size')
    if marker is not None:
        sections.append(_section(marker, rows, payload, size))
    return tuple(sections)
