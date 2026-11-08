"""Read Address Book diagnostics or create a NEW one-contact experimental file."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from .personal import Contact, parse_file
from .writer import create_contact, write_new


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args(argv)
    try:
        result = parse_file(args.source).to_dict()
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


def create_main(argv=None):
    parser = argparse.ArgumentParser(description='Create one contact from an empty ADR into a NEW file.')
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--contact', type=Path, required=True,
                        help='JSON object: first_name,last_name,city,work_phone')
    args = parser.parse_args(argv)
    try:
        item = json.loads(args.contact.read_text(encoding='utf-8'))
        if not isinstance(item, dict) or set(item) != set(asdict(Contact('Test', 'Example'))):
            raise ValueError('expected exactly first_name,last_name,city,work_phone')
        contact = Contact(**item)
        with args.source.open('rb') as handle:
            data = create_contact(handle.read(10241), contact)
        write_new(args.output, data)
    except (OSError, ValueError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0
