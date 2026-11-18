"""Inspect, export and verify DeskMate Preservation Workbench bundles."""
import argparse
from pathlib import Path
import sys

from . import collection
from .bundle import export, prepare, verify
from .model import PreservationError, error_report
from .native import APPLICATIONS
from .render import json_bytes


def _parser():
    parser = argparse.ArgumentParser(prog='deskmate-preserve', description=__doc__)
    actions = parser.add_subparsers(dest='command', required=True)
    inspect = actions.add_parser('inspect', help='report source identity, profile and planned artifacts')
    convert = actions.add_parser('export', help='export a file or the direct files in a directory')
    for action in (inspect, convert):
        action.add_argument('input')
        action.add_argument('--application', choices=APPLICATIONS, help='select the native reader explicitly')
    convert.add_argument('--output-dir', required=True, help='new directory for the bundle or collection')
    check = actions.add_parser('verify', help='check manifests, inventory, lengths and SHA-256 hashes')
    check.add_argument('output')
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    status = 0
    try:
        if args.command == 'inspect':
            result = prepare(args.input, application=args.application).manifest
            result['planned_artifacts'] = result.pop('artifacts')
            result['format'] = 'deskmate-preservation-inspection'
        elif args.command == 'export':
            if Path(args.input).is_dir():
                result = collection.export(args.input, args.output_dir, application=args.application)
                status = int(any(item['status'] == 'failed' for item in result['entries']))
            else:
                result = export(args.input, args.output_dir, application=args.application)
        elif (Path(args.output) / collection.MANIFEST).exists():
            result = collection.verify(args.output)
        else:
            manifest = verify(args.output)
            result = {'verified': True, 'source': manifest['source'],
                      'artifact_count': len(manifest['artifacts'])}
    except (PreservationError, OSError) as exc:
        sys.stderr.write(json_bytes(error_report(exc)).decode('ascii'))
        return 2
    sys.stdout.write(json_bytes(result).decode('ascii'))
    return status


if __name__ == '__main__':
    raise SystemExit(main())
