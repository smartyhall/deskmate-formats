"""Compare three offline six-byte DMCSR window-context samples."""

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from struct import unpack


WINDOW_START = 0x079C
CONTEXT_END = 0x0F9C
WINDOW_RECORD_SIZE = 0x3C
SMALL_RECORD_SIZE = 0x10
SAMPLE_SIZE = 6


@dataclass(frozen=True)
class WindowContext:
    window_record_top: int
    small_record_floor: int
    selected_window_id: int


def decode_sample(sample: bytes) -> WindowContext:
    if len(sample) != SAMPLE_SIZE:
        raise ValueError('expected exactly six bytes')
    window_top, small_floor, selected_id = unpack('<3H', sample)
    if not WINDOW_START <= window_top <= small_floor <= CONTEXT_END:
        raise ValueError('window records outside the context or overlapping')
    if (window_top - WINDOW_START) % WINDOW_RECORD_SIZE or (CONTEXT_END - small_floor) % SMALL_RECORD_SIZE:
        raise ValueError('misaligned window records')
    if selected_id > 0x07FF and selected_id != 0xFFFF:
        raise ValueError('selected window identifier outside the observed code bounds')
    return WindowContext(window_top, small_floor, selected_id)


def compare_triplet(before: bytes, during: bytes, after: bytes) -> dict:
    a, b, c = (decode_sample(sample) for sample in (before, during, after))
    return {
        'checkpoints': {label: asdict(sample) for label, sample in zip('ABC', (a, b, c))},
        'a_to_b_window_records': (b.window_record_top - a.window_record_top) // WINDOW_RECORD_SIZE,
        'a_to_b_small_records': (a.small_record_floor - b.small_record_floor) // SMALL_RECORD_SIZE,
        'a_to_b_selected_id_changed': a.selected_window_id != b.selected_window_id,
        'a_equals_c': a == c,
    }


def read_sample(path: Path) -> bytes:
    with path.open('rb') as stream:
        return stream.read(SAMPLE_SIZE + 1)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for checkpoint in 'ABC':
        parser.add_argument(checkpoint, type=Path)
    args = parser.parse_args(argv)
    try:
        result = compare_triplet(*(read_sample(getattr(args, label)) for label in 'ABC'))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
