"""Inspect, build and interchange measured DeskMate FF1 outlines."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from

from .ff1 import parse_resource, serialize_resource
from .ff1_geometric import geometric_face
from .font_resources import MAX_SIZE, FontResourceError, parse_bytes


def read_resource(path):
    with path.open('rb') as handle:
        return handle.read(MAX_SIZE + 1)


def inspect(data):
    resource = parse_resource(data)
    directory = parse_bytes(data)
    return {
        'sha256': directory.sha256, 'size': directory.size, 'family': resource.family,
        'variants': [{'name': v.name, 'attributes_hex': v.attributes.hex()} for v in directory.variants],
        'first_code': resource.first_code, 'glyph_count': len(resource.glyphs),
        'units_per_em': resource.units_per_em,
        'contour_count': sum(len(g.outline.contours) for g in resource.glyphs),
        'glyphs_with_auxiliary_data': sum(bool(g.outline.auxiliary) for g in resource.glyphs),
        'trailing_bytes': len(resource.trailing), 'section_pointer_38': unpack_from('<I', data, 38)[0],
        'native_acceptance': 'requires a native trial with this exact resource',
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest='command', required=True)
    for command in ('inspect', 'validate', 'roundtrip', 'create', 'import', 'export'):
        sub = subcommands.add_parser(command)
        if command != 'create':
            sub.add_argument('source', type=Path)
        if command not in ('inspect', 'validate'):
            sub.add_argument('--output', required=True, type=Path)
        if command in ('create', 'import'):
            sub.add_argument('--family', required=command == 'import', default='Lab Grid')
            sub.add_argument('--face-id', type=int, default=50)
            sub.add_argument('--family-id', type=int, default=2)
    args = parser.parse_args(argv)
    try:
        if args.command in ('inspect', 'validate', 'roundtrip', 'export'):
            source = read_resource(args.source)
            resource = parse_resource(source)
        if args.command in ('inspect', 'validate'):
            result = inspect(source)
            if args.command == 'validate':
                result['exact_roundtrip'] = serialize_resource(resource) == source
                if not result['exact_roundtrip']:
                    raise FontResourceError('reconstruction differs from source bytes')
        else:
            if args.command == 'create':
                output = serialize_resource(geometric_face(args.family, face_id=args.face_id,
                                                            family_id=args.family_id))
            elif args.command == 'import':
                from .ff1_interchange import import_outline
                with args.source.open('rb') as handle:
                    source = handle.read(32 * 1024 * 1024 + 1)
                if len(source) > 32 * 1024 * 1024:
                    raise FontResourceError('modern font exceeds the 32 MiB input limit')
                resource, report = import_outline(source, args.family, face_id=args.face_id,
                                                  family_id=args.family_id)
                output = serialize_resource(resource)
            elif args.command == 'export':
                from .ff1_interchange import export_cff
                output = export_cff(resource)
            else:
                output = serialize_resource(resource)
                if output != source:
                    raise FontResourceError('reconstruction differs from source bytes')
            with args.output.open('xb') as target:
                target.write(output)
            result = {'size': len(output), 'sha256': sha256(output).hexdigest()}
            if args.command == 'import':
                result.update(report)
            if args.command == 'export':
                result['limits'] = ['base outlines and nominal advances only', 'bounds-derived vertical metrics',
                                    'provisional CP437 mapping', 'native metadata and auxiliary data omitted']
    except ImportError:
        parser.exit(2, 'outline interchange requires deskmate-formats[fonts]\n')
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
