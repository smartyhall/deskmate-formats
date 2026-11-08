"""Build a NEW 30-day candidate; requires --experimental-new-pages.

Tool-generated, not native accepted. Prints receipt with independent raw checks
and expected physical insertion order. Never overwrites a destination.
"""
import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import tempfile

from deskmate_formats.calendar.experimental_new import build_new
from deskmate_formats.calendar.samples import schedule
from check_calendar_multipage import check


def generate(source):
    events = tuple(replace(e, description=e.description + ' / allocator trial')
                   for e in reversed(schedule(days=30)))
    additions = [{'date': e.day.isoformat(), 'start_minutes': e.start_minutes,
                  'end_minutes': e.end_minutes, 'description': e.description,
                  'alarm_enabled': e.protected_raw == b'q'} for e in events]
    data = build_new(source, events, experimental=True)
    receipt = check(source, data, additions)
    receipt['additions'] = additions
    return data, receipt


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('source', type=Path)
    cli.add_argument('output', type=Path)
    cli.add_argument('--experimental-new-pages', action='store_true')
    args = cli.parse_args(argv)
    try:
        if not args.experimental_new_pages:
            raise ValueError('explicit --experimental-new-pages required')
        with args.source.open('rb') as handle:
            source = handle.read(6145)
        data, receipt = generate(source)
        # Checked before publication. Hard-link creation is atomic and fails
        # for an existing destination, including a symlink or the source path.
        fd, temp = tempfile.mkstemp(prefix='.calendar-month-', dir=args.output.parent)
        try:
            with os.fdopen(fd, 'wb') as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.link(temp, args.output)
        finally:
            os.unlink(temp)
    except (OSError, ValueError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
