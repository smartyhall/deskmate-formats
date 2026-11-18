"""Inspect, export and verify DeskMate Preservation Workbench bundles."""
import argparse
import sys

from .bundle import export, prepare, verify
from .model import PreservationError
from .native import APPLICATIONS
from .render import json_bytes


def _parser():
    parser = argparse.ArgumentParser(prog='deskmate-preserve', description=__doc__)
    actions = parser.add_subparsers(dest='command', required=True)
    inspect = actions.add_parser('inspect', help='report source identity, profile and planned artifacts')
    convert = actions.add_parser('export', help='create a new preservation bundle')
    for action in (inspect, convert):
        action.add_argument('input')
        action.add_argument('--application', choices=APPLICATIONS, help='select the native reader explicitly')
    convert.add_argument('--output-dir', required=True, help='new directory for the preservation bundle')
    check = actions.add_parser('verify', help='check the manifest, inventory, lengths and SHA-256 hashes')
    check.add_argument('output')
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        if args.command == 'inspect':
            result = prepare(args.input, application=args.application).manifest
            result['planned_artifacts'] = result.pop('artifacts')
            result['format'] = 'deskmate-preservation-inspection'
        elif args.command == 'export':
            result = export(args.input, args.output_dir, application=args.application)
        else:
            manifest = verify(args.output)
            result = {'verified': True, 'source': manifest['source'],
                      'artifact_count': len(manifest['artifacts'])}
    except (PreservationError, OSError) as exc:
        code = getattr(exc, 'code', 'output_exists' if isinstance(exc, FileExistsError) else 'io_error')
        sys.stderr.write(json_bytes({'error': code, 'message': str(exc)}).decode('ascii'))
        return 2
    sys.stdout.write(json_bytes(result).decode('ascii'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
