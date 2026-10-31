"""Read an explicitly selected ASCII span from a private RAM capture, never a guest."""
import argparse
import json
from pathlib import Path


def extract(data, offset, length):
    """No scanning, field interpretation, focus inference or implicit addresses."""
    if offset < 0 or not 1 <= length <= 256 or offset + length > len(data):
        raise ValueError("Selected span is outside capture or exceeds 256 bytes")
    raw = data[offset:offset + length]
    if any(c < 32 or c > 126 for c in raw):
        raise ValueError("Selected span is not entirely printable ASCII")
    return {"capture_offset": offset, "byte_length": length,
            "text": raw.decode("ascii"), "interpretation": "unclassified RAM text",
            "screen_coordinates": None, "focus": None,
            "live_screen_verified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("offset", type=lambda s: int(s, 0))
    parser.add_argument("length", type=lambda s: int(s, 0))
    args = parser.parse_args()
    try:
        result = extract(args.capture.read_bytes(), args.offset, args.length)
    except (OSError, ValueError) as exc:
        parser.exit(1, str(exc) + "\n")
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
