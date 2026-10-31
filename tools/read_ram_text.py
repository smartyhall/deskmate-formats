"""Offline, bounded analysis of conventional guest RAM; never a live-screen API."""
import argparse
import hashlib
import json
from pathlib import Path
import re

CONVENTIONAL_LIMIT = 0xA0000
WINDOW_LIMIT = 256


def _capture(data, base_address):
    if not isinstance(data, (bytes, bytearray)) or not 1 <= len(data) <= CONVENTIONAL_LIMIT:
        raise ValueError("Capture must contain 1..655360 raw bytes")
    if type(base_address) is not int or base_address < 0 or base_address + len(data) > CONVENTIONAL_LIMIT:
        raise ValueError("Capture lies outside supported conventional RAM 0..0x9FFFF")
    return {"base_address": base_address, "byte_length": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def _window(data, offset, length):
    if type(offset) is not int or type(length) is not int or offset < 0 or not 1 <= length <= WINDOW_LIMIT or offset + length > len(data):
        raise ValueError("Selected span is outside capture or exceeds 256 bytes")
    return bytes(data[offset:offset + length])


def extract(data, offset, length, *, base_address=0, physical=False):
    """Select explicit bytes; preserve the original positional API and unknowns."""
    provenance = _capture(data, base_address)
    if type(offset) is not int or type(physical) is not bool:
        raise ValueError("Offset must be an integer; physical must be boolean")
    relative = offset - base_address if physical else offset
    raw = _window(data, relative, length)
    if any(c < 32 or c > 126 for c in raw):
        raise ValueError("Selected span is not entirely printable ASCII")
    return {"capture_offset": relative, "byte_length": length,
            "physical_address": base_address + relative, "capture": provenance,
            "raw_hex": raw.hex(), "text": raw.decode("ascii"),
            "interpretation": "unclassified RAM text", "screen_coordinates": None,
            "focus": None, "live_screen_verified": False}


def _candidates(raw, relative, physical):
    return [{"capture_offset": relative + m.start(),
             "physical_address": physical + m.start(),
             "byte_length": len(m.group()), "text": m.group().decode("ascii")}
            for m in re.finditer(rb"[ -~]{4,}", raw)]


def compare_regions(before, after, physical_address, length, *, before_base=0, after_base=0):
    """Compare one physical interval, keeping complete raw context and every delta."""
    first = _capture(before, before_base)
    second = _capture(after, after_base)
    if type(physical_address) is not int:
        raise ValueError("Physical address must be an integer")
    left = physical_address - before_base
    right = physical_address - after_base
    old = _window(before, left, length)
    new = _window(after, right, length)
    return {"physical_address": physical_address, "byte_length": length,
            "before_capture": first, "after_capture": second,
            "before_capture_offset": left, "after_capture_offset": right,
            "before_hex": old.hex(), "after_hex": new.hex(),
            "differences": [{"physical_address": physical_address + i,
                             "before_capture_offset": left + i,
                             "after_capture_offset": right + i,
                             "before": a, "after": b}
                            for i, (a, b) in enumerate(zip(old, new)) if a != b],
            "candidate_ascii": {"before": _candidates(old, left, physical_address),
                                "after": _candidates(new, right, physical_address)},
            "candidate_minimum_bytes": 4,
            "interpretation": "unclassified RAM bytes and candidate text",
            "screen_coordinates": None, "focus": None, "live_screen_verified": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    number = lambda s: int(s, 0)
    parser.add_argument("capture", type=Path)
    parser.add_argument("offset", type=number)
    parser.add_argument("length", type=number)
    parser.add_argument("--base-address", type=number, default=0)
    parser.add_argument("--physical", action="store_true", help="Interpret offset as a physical address")
    parser.add_argument("--compare", type=Path, help="Compare this second raw capture")
    parser.add_argument("--compare-base-address", type=number, default=None)
    args = parser.parse_args(argv)
    if args.compare_base_address is not None and args.compare is None:
        parser.error("--compare-base-address requires --compare")
    try:
        data = args.capture.read_bytes()
        if args.compare is None:
            result = extract(data, args.offset, args.length,
                             base_address=args.base_address, physical=args.physical)
        else:
            address = args.offset if args.physical else args.base_address + args.offset
            result = compare_regions(data, args.compare.read_bytes(), address, args.length,
                                     before_base=args.base_address,
                                     after_base=args.base_address if args.compare_base_address is None else args.compare_base_address)
    except (OSError, ValueError) as exc:
        parser.exit(1, str(exc) + "\n")
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
