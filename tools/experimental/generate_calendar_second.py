"""Generate the bounded A→B first-SECOND candidate; never overwrite a file."""
import argparse
from datetime import date
import json
from pathlib import Path
import sys

from deskmate_formats.calendar.experimental_second import append_first_second
from deskmate_formats.calendar.writer import Appointment, _publish_new
from check_calendar_multicalendar import check_append, read


EXPECTED = {'date': '2026-10-24', 'start_minutes': 660, 'end_minutes': 720,
            'description': 'SECOND ONLY 001', 'alarm_enabled': False}


def generate(source):
    event = Appointment(date.fromisoformat(EXPECTED['date']), EXPECTED['start_minutes'],
                        EXPECTED['end_minutes'], EXPECTED['description'])
    candidate = append_first_second(source, event, experimental=True)
    return candidate, check_append(source, candidate, EXPECTED)


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('source', type=Path)
    cli.add_argument('output', type=Path)
    cli.add_argument('--experimental-first-second', action='store_true')
    args = cli.parse_args(argv)
    try:
        if not args.experimental_first_second:
            raise ValueError('explicit --experimental-first-second required')
        if args.source.resolve() == args.output.resolve():
            raise ValueError('source and output must differ')
        source = read(args.source, 10240)
        candidate, report = generate(source)
        _publish_new(args.output, candidate)
        print(json.dumps(report, indent=2))
    except (OSError, ValueError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
