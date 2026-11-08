"""Generate exact-source SECOND creation profile; independent check before publish."""
import argparse
import json
from pathlib import Path
import sys

from deskmate_formats.calendar.experimental_create import create_second
from deskmate_formats.calendar.writer import _publish_new
from check_calendar_multicalendar import check, read


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('source', type=Path)
    cli.add_argument('expected_personal', type=Path)
    cli.add_argument('output', type=Path)
    cli.add_argument('--experimental-create-second', action='store_true')
    args = cli.parse_args(argv)
    try:
        if not args.experimental_create_second:
            raise ValueError('explicit --experimental-create-second required')
        if args.output.resolve() in (args.source.resolve(), args.expected_personal.resolve()):
            raise ValueError('source/expected and output must differ')
        source = read(args.source, 8192)
        candidate = create_second(source, experimental=True)
        report = check(source, candidate, json.loads(read(args.expected_personal, 131072)))
        report['evidence_class'] = 'tool-generated, independently checked offline; not application-produced or native-accepted'
        report['native_opened'] = report['native_saved'] = False
        report['creation_profile'] = 'exact month source, exact SECOND, measured 41→20/21 split; no general balancer'
        _publish_new(args.output, candidate)
        print(json.dumps(report, indent=2))
    except (OSError, ValueError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
