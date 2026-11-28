"""Create the exact campaign 002 DBrepair inputs from the pinned native fixture."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

SOURCE_SHA256 = "5b878f77b43dc6517b4065477f0e15b9d42b02ad0b0b493bc029ec8f06125682"
CASES = (
    ("BADLOC", 0x1C2A, "25", "26",
     "ALPHA's locator points inside its physical row.",
     ["Rebuild from DATA and recover ALPHA", "Trust the index and lose ALPHA or reject the file"]),
    ("BADID", 0x1C2C, "11", "18",
     "ALPHA's index ID becomes 24 while its row still carries 17.",
     ["Rebuild the association from DATA", "Use the index ID, skip ALPHA, or reject the file"]),
    ("NOENTRY", 0x1C52, "060000001000", "000000000000",
     "The final indexed entry for ZULU is absent; the physical row and declared count remain.",
     ["Scan DATA and restore ZULU", "Recover only the seven indexed rows or reject the count mismatch"]),
    ("BADLINK", 0x29, "00", "ff",
     "DATA page 6 becomes terminal (008 to FF8), leaving page 8 disconnected from its chain.",
     ["Find the disconnected page and recover all eight rows", "Follow the shortened chain and lose DELTA, ECHO and FOXTROT, or reject"]),
    ("BADFRAME", 0x2375, "02", "03",
     "FOXTROT's end-of-row marker becomes an end-of-list marker.",
     ["Recognize the final record from its field framing or index", "Skip FOXTROT or reject"]),
    ("BADCOUNT", 0x45B, "38", "39",
     "The declared DATA row count rises from eight to nine.",
     ["Count the eight intact rows during rebuild", "Trust the directory count or reject the mismatch"]),
)


def generate(source, destination):
    data = source.read_bytes()
    if sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError("unexpected original Filer specimen")
    destination.mkdir()
    receipts = {}
    for name, offset, old_hex, new_hex, defect, predictions in CASES:
        old = bytes.fromhex(old_hex)
        new = bytes.fromhex(new_hex)
        if len(old) != len(new) or data[offset:offset + len(old)] != old:
            raise ValueError(f"preimage mismatch for {name}")
        damaged = data[:offset] + new + data[offset + len(old):]
        filename = f"{name}.FIL"
        (destination / filename).write_bytes(damaged)
        receipts[filename] = {
            "offset": offset, "before_hex": old_hex, "after_hex": new_hex,
            "bytes": len(damaged), "sha256": sha256(damaged).hexdigest(),
            "defect": defect, "predictions": predictions,
        }
    return {"source_sha256": SOURCE_SHA256, "cases": receipts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(generate(args.source, args.destination), indent=2))


if __name__ == "__main__":
    main()
