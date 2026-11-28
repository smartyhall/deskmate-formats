"""Inspect the small ASCII dBASE III character-table profile used by the Fil2dbf trial."""

import argparse
import json
from pathlib import Path
from struct import unpack_from


MAX_BYTES = 1024 * 1024


def inspect_dbf(data):
    """Report physical framing and raw values without using a DeskMate reader."""
    if not 65 <= len(data) <= MAX_BYTES or data[0] != 3:
        raise ValueError("expected a bounded dBASE III table without memo fields")
    count, header, record = unpack_from("<IHH", data, 4)
    if not 65 <= header <= len(data) or (header - 33) % 32 or data[header - 1] != 0x0D:
        raise ValueError("invalid field descriptor framing")
    fields = []
    for offset in range(32, header - 1, 32):
        desc = data[offset:offset + 32]
        name = desc[:11].partition(b"\0")[0].decode("ascii")
        if not name or desc[11] != ord("C") or not desc[16] or desc[17]:
            raise ValueError("expected a nonempty character field")
        fields.append({"name": name, "type": "C", "width": desc[16], "decimals": desc[17],
                       "descriptor_hex": desc.hex()})
    if record != 1 + sum(field["width"] for field in fields):
        raise ValueError("record size disagrees with field widths")
    end = header + count * record
    if end > len(data) or data[end:] not in (b"", b"\x1a"):
        raise ValueError("record count or end-of-file framing disagrees")
    records = []
    for offset in range(header, end, record):
        row = data[offset:offset + record]
        if row[0] not in (0x20, 0x2A):
            raise ValueError("invalid record deletion flag")
        cursor = 1
        values = []
        for field in fields:
            width = field["width"]
            values.append(row[cursor:cursor + width].rstrip(b" ").decode("ascii"))
            cursor += width
        records.append({"deleted": row[0] == 0x2A, "values": values, "raw_hex": row.hex()})
    return {"version": data[0], "date_hex": data[1:4].hex(), "header_hex": data[:32].hex(),
            "record_count": count, "header_length": header, "record_length": record,
            "fields": fields, "records": records, "header_terminator": data[header - 1],
            "eof_hex": data[end:].hex()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        with args.file.open("rb") as source:
            result = inspect_dbf(source.read(MAX_BYTES + 1))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
