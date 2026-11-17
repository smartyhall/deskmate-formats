"""Create a new bounded month Calendar with one same-length description edit."""
import argparse
from pathlib import Path

from deskmate_formats.calendar.maintenance import write_description


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('source', type=Path)
    cli.add_argument('output', type=Path)
    cli.add_argument('record_id', type=int)
    cli.add_argument('description')
    cli.add_argument('--normalize-index', action='store_true')
    cli.add_argument('--experimental', action='store_true')
    args = cli.parse_args(argv)
    try:
        with args.source.open('rb') as handle:
            source = handle.read(8193)
        write_description(args.output, source, args.record_id, args.description,
                          normalize=args.normalize_index, experimental=args.experimental)
    except (OSError, ValueError, TypeError) as exc:
        cli.exit(2, str(exc) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
