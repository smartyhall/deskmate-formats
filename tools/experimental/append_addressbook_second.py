"""Create a new exact-A01/ALPHA two-contact candidate; never overwrite."""
import argparse
from pathlib import Path

from deskmate_formats.addressbook.personal import Contact
from deskmate_formats.addressbook.experimental_second import write_second_contact


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('source', type=Path)
    cli.add_argument('output', type=Path)
    cli.add_argument('--first', default='ZULU')
    cli.add_argument('--work-phone', default='555-0100')
    cli.add_argument('--experimental', action='store_true')
    args = cli.parse_args(argv)
    try:
        with args.source.open('rb') as handle:
            source = handle.read(10241)
        contact = Contact(args.first, 'ALPHA', work_phone=args.work_phone)
        write_second_contact(args.output, source, contact, experimental=args.experimental)
    except (OSError, ValueError, TypeError) as exc:
        cli.exit(2, str(exc) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
