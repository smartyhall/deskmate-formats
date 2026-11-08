"""Generate a deterministic SDK-profile Calendar in a NEW disposable file.

Example: python tools/generate_calendar_sample.py source.cln new-output.cln
The JSON receipt is safe derived metadata; no application verification is implied.
"""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

from deskmate_formats.calendar.personal import parse_bytes
from deskmate_formats.calendar.samples import schedule
from deskmate_formats.calendar.writer import append_appointment, capacity, write_new


def generate(source, *, start=date(2026, 10, 23), days=14):
    data = bytes(source)
    events = schedule(start, days)
    for event in reversed(events):
        data = append_appointment(data, event, profile='sdk')
    db = parse_bytes(data, profile='sdk')
    receipt = {'receipt_version': 1, 'profile': 'sdk',
               'source_sha256': hashlib.sha256(source).hexdigest(),
               'output_sha256': db.sha256, 'size': db.size,
               'added_appointments': len(events), 'total_appointments': len(db.appointments),
               'distinct_dates': len({r.date for r in db.appointments}),
               'start': start.isoformat(), 'days': days,
               'capacity': capacity(data, profile='sdk'),
               'native_opened': False, 'native_save_tested': False}
    return data, receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--start', type=date.fromisoformat, default=date(2026, 10, 23))
    parser.add_argument('--days', type=int, choices=(14, 30), default=14)
    args = parser.parse_args(argv)
    try:
        with args.source.open('rb') as handle:
            source = handle.read(6145)
        data, receipt = generate(source, start=args.start, days=args.days)
        write_new(args.output, data, profile='sdk')
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
