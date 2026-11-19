"""Inspect, export and verify DeskMate Preservation Workbench bundles."""
import argparse
from pathlib import Path
import sys

from .. import font_resources, sampled_music
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
        action.add_argument('--instruments', type=Path, help='SND directory for Music sampled playback')
        action.add_argument('--ff1', action='append', type=Path, default=[],
                            help='use this local outline font for Draw, Text or Filer graphics (repeatable)')
        action.add_argument('--sample-policy', choices=sampled_music.SAMPLE_POLICIES,
                            help='Music sample range resolution (default rsx-ranges)')
    convert.add_argument('--output-dir', required=True, help='new directory for the bundle or collection')
    check = actions.add_parser('verify', help='check manifests, inventory, lengths and SHA-256 hashes')
    check.add_argument('output')
    return parser


def main(argv=None):
    parser = _parser()
    args = parser.parse_args(argv)
    status = 0
    try:
        options = {}
        if args.command in ('inspect', 'export'):
            if args.sample_policy and args.instruments is None:
                parser.error('--sample-policy requires --instruments')
            options = {
                'application': args.application,
                'instruments': None if args.instruments is None else sampled_music.load_instruments(args.instruments),
                'sample_policy': args.sample_policy or 'rsx-ranges',
                'outline_faces': font_resources.load_outline_faces(args.ff1),
            }
        if args.command == 'inspect':
            result = prepare(args.input, **options).manifest
            result['planned_artifacts'] = result.pop('artifacts')
            result['format'] = 'deskmate-preservation-inspection'
        elif args.command == 'export':
            if Path(args.input).is_dir():
                result = collection.export(args.input, args.output_dir, **options)
                status = int(any(item['status'] == 'failed' for item in result['entries']))
            else:
                result = export(args.input, args.output_dir, **options)
        elif (Path(args.output) / collection.MANIFEST).exists():
            result = collection.verify(args.output)
        else:
            manifest = verify(args.output)
            result = {'verified': True, 'source': manifest['source'],
                      'artifact_count': len(manifest['artifacts'])}
    except sampled_music.PlaybackError as exc:
        error = PreservationError('instrument_collection_error', str(exc))
        sys.stderr.write(json_bytes(error_report(error)).decode('ascii'))
        return 2
    except font_resources.FontResourceError as exc:
        error = PreservationError('outline_resource_error', str(exc))
        sys.stderr.write(json_bytes(error_report(error)).decode('ascii'))
        return 2
    except (PreservationError, OSError) as exc:
        sys.stderr.write(json_bytes(error_report(exc)).decode('ascii'))
        return 2
    sys.stdout.write(json_bytes(result).decode('ascii'))
    return status


if __name__ == '__main__':
    raise SystemExit(main())
