"""Command-line presentation kept separate from calendar_personal parsing."""
import argparse
import json
import sys
from .personal import CalendarParseError, parse_file


def format_listing(database):
    lines = [f'PERSONAL.CLN: {len(database.appointments)} user appointment(s), '
             f'{len(database.internal_records)} internal/control record(s)',
             f'Source: {database.source or "<bytes>"}', f'SHA-256: {database.sha256}', '']
    for record in database.appointments:
        value = lambda v: '<undecoded>' if v is None else v
        lines.append(f'ID 0x{record.record_id:02X} | {value(record.date)} '
                     f'{value(record.day_of_week)} | {value(record.start_time)} - '
                     f'{value(record.end_time)} | {value(record.description)}')
        lines.append(f'  Record 0x{record.offset:04X}, {record.length} bytes; '
                     f'index 0x{record.index_offset:04X}')
        for name, raw in record.undecoded_fields.items():
            lines.append(f'  Undecoded {name}: {raw or "<empty>"}')
        for warning in record.warnings:
            lines.append(f'  Note: {warning}')
    for record in database.internal_records:
        lines.append(f'Internal/control ID 0x{record.record_id:02X}: '
                     f'0x{record.offset:04X}, {record.length} bytes; opaque, excluded from appointments.')
        lines.append(f'  Raw: {record.raw_hex}')
    lines.extend(f'Note: {warning}' for warning in database.warnings)
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Read the observed DeskMate 3.05 PERSONAL.CLN subset.')
    parser.add_argument('database', help='Read-only path to PERSONAL.CLN')
    parser.add_argument('--json', action='store_true', help='JSON with raw fields and undecoded records')
    args = parser.parse_args(argv)
    try:
        database = parse_file(args.database)
    except (CalendarParseError, OSError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(database.to_dict(), indent=2, ensure_ascii=True) if args.json else format_listing(database))
    return 0


if __name__ == '__main__':
    sys.exit(main())
