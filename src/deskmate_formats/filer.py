"""Inspect measured DeskMate 3.05 Filer databases without modifying the source."""
import argparse
from dataclasses import asdict
import json
import sys

from . import database


def parse_bytes(source):
    """Return the common database snapshot, including any retained 0x44 rows."""
    return _filer(database.parse_bytes(source, allow_retired=True))


def parse_file(path):
    """Read a bounded Filer snapshot from disk."""
    return _filer(database.parse_file(path, allow_retired=True))


def _filer(snapshot):
    names = {table.name for table in snapshot.tables}
    required = {'DBCOLS', 'LAYOUTS', 'DATA'}
    database.require(snapshot.data[:4] == b'\x03FIL' and required <= names <= required | {'GRAPHICS'},
                     'unsupported_schema', 'expected Filer DBCOLS, LAYOUTS and DATA')
    return snapshot


def _display_row(row):
    return {
        'offset': row.offset,
        'record_id': row.record_id,
        'index_offset': row.index_offset,
        'fields': [value.decode('ascii') if all(32 <= byte <= 126 for byte in value)
                   else None for value in row.fields],
        'fields_hex': [value.hex() for value in row.fields],
    }


def inspect_file(path):
    """Return JSON-compatible table definitions and Filer DATA in index order."""
    snapshot = parse_file(path)
    data = snapshot.table('DATA')
    return {
        'sha256': snapshot.sha256,
        'size': len(snapshot.data),
        'tables': [
            {
                'name': table.name,
                'record_count': table.record_count,
                'data_pages': table.data_pages,
                'index_page': table.index_page,
                'next_id_candidate': table.next_id_candidate,
                'columns': [
                    {'name': col.name, 'width': col.width, 'kind': col.kind}
                    for col in table.columns
                ],
            }
            for table in snapshot.tables
        ],
        'data_index': [asdict(entry) for entry in data.entries],
        'data_rows': [_display_row(row) for row in data.rows],
        'retired_data_rows': [_display_row(row) for row in data.retired_rows],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    args = parser.parse_args(argv)
    try:
        result = inspect_file(args.source)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
