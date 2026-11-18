"""Inspect DeskMate 3.05 Worksheet WKS files without evaluating formulas."""
import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from struct import unpack_from
import sys


PAGE_SETUP_SIZE = 22
TOPLIST_START = 126
TOPLIST_SIZE = 10
CELL_SIZES = (('label', 6), ('number', 14), ('formula', 14), ('input', 14), ('text_block', 8))
CELL_START = TOPLIST_START + len(CELL_SIZES) * TOPLIST_SIZE
MIN_BYTES = CELL_START + sum(size for _, size in CELL_SIZES)
MAX_BYTES = PAGE_SETUP_SIZE + 0xFFFF
DUMMY_COORDINATE = 100


class WorksheetFormatError(ValueError):
    """Invalid boundaries or a layout outside the measured Worksheet profile."""


@dataclass(frozen=True)
class TopList:
    category: str
    offset: int
    start_pointer: int
    end_pointer: int
    cell_size: int
    status: int
    count: int
    cells_start: int
    cells_end: int


@dataclass(frozen=True)
class Cell:
    category: str
    offset: int
    row: int
    column: int
    status: int
    string_offset: int
    raw: bytes
    dummy: bool
    text: str | None = None
    raw_string: bytes | None = None
    numeric_value: float | None = None
    result_flag: bool | None = None
    error_flag: bool | None = None
    row_span: int | None = None
    column_span: int | None = None


@dataclass(frozen=True)
class Worksheet:
    size: int
    sha256: str
    page_setup: bytes
    column_widths: tuple[int, ...]
    extreme_row: int
    extreme_column: int
    pad_size: int
    string_pool_offset: int
    toplists: tuple[TopList, ...]
    cells: tuple[Cell, ...]


def _require(condition, message):
    if not condition:
        raise WorksheetFormatError(message)


def _toplists(data):
    lists = []
    cursor = CELL_START
    for index, (category, expected_size) in enumerate(CELL_SIZES):
        offset = TOPLIST_START + index * TOPLIST_SIZE
        start, end, size, status, count = unpack_from('<5H', data, offset)
        _require(size == expected_size and count >= 1, f'invalid {category} descriptor')
        limit = cursor + size * count
        _require(limit <= len(data), f'{category} list exceeds file')
        lists.append(TopList(category, offset, start, end, size, status, count, cursor, limit))
        cursor = limit
    return tuple(lists)


def _string_pool(data, start):
    strings = {}
    while start < len(data):
        limit = data.find(b'\x00', start)
        _require(limit >= 0, f'unterminated string at {start}')
        strings[start - TOPLIST_START] = data[start:limit]
        start = limit + 1
    return strings


def _cell(raw, category, offset, dummy, strings, extreme, seen):
    row, col, status, ref = unpack_from('<BBHH', raw)
    if dummy:
        _require((row, col) == (DUMMY_COORDINATE, DUMMY_COORDINATE), f'missing {category} dummy')
        return Cell(category, offset, row, col, status, ref, raw, True)
    max_row, max_col = extreme
    _require(1 <= row <= max_row and 1 <= col <= max_col, f'cell outside used grid at {offset}')
    _require((row, col) not in seen, f'duplicate cell at row {row} column {col}')
    seen.add((row, col))
    _require(ref in strings, f'invalid string offset {ref} in cell at {offset}')
    value = strings.pop(ref)
    text = value.decode('cp437')
    number = result_flag = error_flag = rows = columns = None
    if category == 'text_block':
        rows, columns = raw[6] + 1, raw[7] + 1
        _require(row + rows - 1 <= max_row and col + columns - 1 <= max_col,
                 f'text block outside used grid at {offset}')
        _require(value.endswith(b'\x02'), f'unterminated text block at {offset}')
        visible = value[:-1].rstrip(b'\x01')
        _require(all(c >= 32 or c in (10, 13) for c in visible),
                 f'unsupported text block control at {offset}')
        text = visible.decode('cp437').replace('\r\n', '\n').replace('\r', '\n')
    elif category in ('number', 'formula', 'input'):
        stored, = unpack_from('<d', raw, 6)
        number = stored if isfinite(stored) else None
        if category != 'number':
            result_flag = bool(status & 0x80)
        if category == 'formula':
            error_flag = bool(status & 0x0120)
    return Cell(category, offset, row, col, status, ref, raw, False,
                text, value, number, result_flag, error_flag, rows, columns)


def parse_bytes(source):
    """Read the measured packed-list profile and preserve raw cell bytes.

    Grid coordinates are one based. File offsets are absolute and ends
    exclusive. A cell's string offset is relative to TOPLIST_START. The
    result flag records bit 0x80 on formulas and inputs. The formula error
    flag interprets the measured out-of-bounds and arithmetic error bits.
    Numeric caches come from the file and may be stale or uncalculated.
    """
    _require(isinstance(source, (bytes, bytearray, memoryview)), 'expected worksheet bytes')
    _require(MIN_BYTES <= memoryview(source).nbytes <= MAX_BYTES, 'invalid worksheet size')
    data = bytes(source)
    _require(data[:4] == b'\x0eWKS', 'unsupported worksheet signature')
    widths = tuple(data[22:122])
    _require(all(4 <= n <= 77 for n in widths), 'column width outside measured profile')
    row, col, pad_size = unpack_from('<BBH', data, 122)
    _require(row < DUMMY_COORDINATE and col < DUMMY_COORDINATE, 'invalid extreme coordinates')
    _require(pad_size == len(data) - PAGE_SETUP_SIZE, 'pad size disagrees with file length')
    toplists = _toplists(data)
    pool_start = toplists[-1].cells_end
    strings = _string_pool(data, pool_start)
    cells, seen = [], set()
    for item in toplists:
        last_key = (0, 0)
        for offset in range(item.cells_start, item.cells_end, item.cell_size):
            stop = offset + item.cell_size
            cell = _cell(data[offset:stop], item.category, offset, stop == item.cells_end,
                         strings, (row, col), seen)
            key = (cell.column, cell.row)
            _require(key > last_key, f'{item.category} cells outside measured order')
            last_key = key
            cells.append(cell)
    _require(not strings, 'unreferenced data in string pool')
    return Worksheet(len(data), sha256(data).hexdigest(), data[:22], widths, row, col, pad_size,
                     pool_start, toplists, tuple(cells))


def parse_file(path):
    """Read a bounded Worksheet snapshot from disk."""
    with Path(path).open('rb') as handle:
        return parse_bytes(handle.read(MAX_BYTES + 1))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('--list', action='store_true', help='print a compact listing of populated cells')
    args = parser.parse_args(argv)
    try:
        sheet = parse_file(args.source)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.list:
        for cell in sorted((c for c in sheet.cells if not c.dummy), key=lambda c: (c.row, c.column)):
            number = f'  stored={cell.numeric_value!r}' if cell.numeric_value is not None else ''
            status = f'  status=0x{cell.status:04X}' if cell.result_flag is not None else ''
            if cell.error_flag:
                status += ' (error)'
            print(f'R{cell.row}C{cell.column}  {cell.category:<10} {cell.text!r}{number}{status}')
    else:
        print(json.dumps(asdict(sheet), default=bytes.hex, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
