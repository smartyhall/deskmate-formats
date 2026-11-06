"""Generate independent, programmatic six-page Calendar specimens."""
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from itertools import combinations

from synthetic import INTERNAL, assemble, event

DEFAULT_SEED = 20261105
NORMAL_COUNT = 256
STRESS_COUNT = 1024
DATES = (
    (date(2026, 10, 23), 'Friday', b'\x8fkx', b'g'),
    (date(2026, 10, 24), 'Saturday', b'\x8fky', b'h'),
    (date(2026, 11, 1), 'Sunday', b'\x8flb', b'b'),
    (date(2027, 11, 1), 'Monday', b'\x90lb', b'c'),
)
TIMES = (540, 555, 600, 615, 660, 720)
PAIRS = tuple(combinations(range(len(TIMES)), 2))
KEYS = tuple((day, start) for day in range(len(DATES)) for start in range(len(TIMES) - 1))
LENGTHS = (1, 7, 10, 60, 119, 120)


@dataclass(frozen=True)
class Event:
    day: int
    start: int
    end: int
    description: str

    @property
    def key(self):
        return self.day, self.start

    def row(self, ident):
        _, _, raw_date, weekday = DATES[self.day]
        return event(ident, self.description, raw_date, weekday,
                     bytes((0x80 + TIMES[self.start] // 15,)),
                     bytes((0x80 + TIMES[self.end] // 15,)))


@dataclass(frozen=True)
class Case:
    name: str
    events: tuple[Event, ...]
    category: str

    @property
    def index_order(self):
        return sorted(range(len(self.events)), key=lambda i: self.events[i].key)

    def build(self):
        rows = [(16, INTERNAL)] + [(17 + i, item.row(17 + i))
                                    for i, item in enumerate(self.events)]
        return assemble(rows, [16] + [17 + i for i in self.index_order])


def specimen_cases(seed=DEFAULT_SEED, count=NORMAL_COUNT):
    """Yield count valid specimens, including fixed structural boundaries."""
    if not 64 <= count <= STRESS_COUNT:
        raise ValueError(f'count must be in 64..{STRESS_COUNT}')
    yield Case('empty', (), 'empty')
    # 39-byte internal row + seven 137-byte rows + a 25-byte row + marker.
    full = tuple(Event(day, start, start + 1, '~' * length)
                 for (day, start), length in zip(reversed(KEYS[:8]), (120,) * 7 + (8,)))
    yield Case('exact-fit', full, 'exact-fit')
    yield Case('printable-ascii', (Event(0, 0, 1, ''.join(map(chr, range(32, 127)))),),
               'printable-ascii')
    all_keys = tuple(Event(day, start, start + 1, 'KEY')
                     for day, start in reversed(KEYS))
    yield Case('all-start-keys', all_keys, 'all-start-keys')
    # Single appointments exhaust the observed date x increasing time-pair matrix.
    for number in range(count - 4):
        token = sha256(f'{seed}:{number}'.encode('ascii')).hexdigest()
        day = number % len(DATES)
        start, end = PAIRS[number // len(DATES) % len(PAIRS)]
        length = LENGTHS[number % len(LENGTHS)]
        # Use one-byte extremes, then embed a per-case serial in longer descriptions.
        text = ' ~'[number // len(LENGTHS) % 2] if length == 1 else (
            f'{number:04x}' + token * 2)[:length]
        items = [Event(day, start, end, text)]
        if number >= len(DATES) * len(PAIRS):
            first_key = items[0].key
            others = [key for key in KEYS if key != first_key]
            offset = int(token[:4], 16) % len(others)
            for j in range(1 + number % 5):
                other_day, other_start = others[(offset + j) % len(others)]
                other_end = other_start + 1 + int(token[4 + j], 16) % (5 - other_start)
                size = LENGTHS[(number + j + 1) % len(LENGTHS)]
                desc = (token + ' AZaz09~' + token)[:size]
                items.append(Event(other_day, other_start, other_end, desc))
        yield Case(f'matrix-{number:04d}', tuple(items), 'single' if len(items) == 1 else 'multi')

@dataclass(frozen=True)
class Probe:
    name: str
    data: bytes
    error: str | None


def probes():
    single = Case('probe-base', (Event(0, 0, 1, 'X'),), 'single').build()
    yield Probe('truncated', single[:-1], 'truncated_file')
    yield Probe('extra-page', single + bytes(1024), 'unsupported_layout')
    yield Probe('bad-magic', b'BAD!' + single[4:], 'invalid_header')
    yield Probe('duplicate-index', single[:5166] + single[5160:5166] + single[5172:],
                'invalid_index')
    overlong = Case('overlong', (Event(0, 0, 1, 'X' * 121),), 'malformed').build()
    yield Probe('overlong', overlong, 'unsupported_record')
    reversed_time = Case('reversed', (Event(0, 1, 0, 'X'),), 'unsupported').build()
    yield Probe('reversed-time', reversed_time, 'unsupported_time_order')
    # Replace one description byte without changing widths or record framing.
    description = single.index(b'X', 4096, 5120)
    yield Probe('opaque-description', single[:description] + b'\x82' + single[description + 1:],
                None)



def manifest_bytes(hashes):
    """Serialize specimen names and hex SHA-256 hashes in stable order."""
    return ''.join(f'{name} {digest}\n' for name, digest in sorted(hashes.items())).encode('ascii')
