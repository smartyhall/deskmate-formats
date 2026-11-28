"""Build a disposable FAT12 floppy from verified application disk file sets.

Application packages in the private TVDog mirror arrive either as original
disk images (preserve those unchanged) or as flat ZIP file sets that were
distributed as loose files for a labelled disk. This tool turns one such set
into a working 360 KiB or 720 KiB image without executing any packaged
program, so an original installer can be run in a disposable guest.

The FAT12 writer is shared with :mod:`deskmate_install_media`; this module adds
directory sources, explicit geometry and an inventory receipt.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deskmate_install_media import GEOMETRIES, floppy  # noqa: E402


def read_set(source):
    """Return (filename, date_time, bytes) records from a ZIP or directory."""
    source = Path(source)
    if source.is_dir():
        members = []
        for path in sorted(source.rglob('*')):
            if path.is_file():
                relative = path.relative_to(source).as_posix()
                members.append((relative, (1980, 1, 1, 0, 0, 0), path.read_bytes()))
        return members
    with ZipFile(source) as archive:
        return [(info.filename, info.date_time, archive.read(info))
                for info in archive.infolist() if not info.is_dir()]


class _Member:
    __slots__ = ('filename', 'date_time')

    def __init__(self, filename, date_time):
        self.filename = filename
        self.date_time = date_time


def build(sources, label, geometry, output):
    encoded = label.encode('ascii')
    if not 1 <= len(encoded) <= 11:
        raise ValueError('floppy label must be 1..11 ASCII bytes')
    label = label.ljust(11)
    if geometry not in GEOMETRIES:
        raise ValueError(f'unknown geometry {geometry}')
    members = []
    seen = set()
    for source in sources:
        for filename, date_time, data in read_set(source):
            name = Path(filename.replace('\\', '/')).as_posix().lstrip('/')
            if not name:
                continue
            if name.upper() in seen:
                raise ValueError(f'duplicate member across sources: {name}')
            seen.add(name.upper())
            members.append((_Member(name, date_time), data))
    image = floppy(members, label.encode('ascii'), geometry)
    output = Path(output)
    with output.open('xb') as destination:
        destination.write(image)
    return {'output': str(output), 'bytes': len(image),
            'sha256': sha256(image).hexdigest(),
            'members': [{'name': member.filename, 'bytes': len(data),
                         'sha256': sha256(data).hexdigest()} for member, data in members]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', action='append', required=True, type=Path,
                        help='ZIP file set or directory; repeat for one disk')
    parser.add_argument('--label', required=True,
                        help='eleven-character FAT volume label')
    parser.add_argument('--geometry', choices=sorted(GEOMETRIES), default='720k')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    result = build(args.source, args.label, args.geometry, args.output)
    if args.receipt:
        args.receipt.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'members'}, indent=2))


if __name__ == '__main__':
    main()
