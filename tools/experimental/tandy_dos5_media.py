"""Verify original DOS images and derive new working copies, never edit originals.

The supplied Disk 2 lacks the label required by SETUP.INI. This tool adds
only a FAT12 root volume-label entry to a separately named working image.
No proprietary file bytes are embedded in this source.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

EXPECTED = {
    'MSDOS1.img': 'ad566ffef55afab65e73b7bfd4edd94ff22c062bfdfab92bd70bb0c2884594fe',
    'MSDOS2.img': 'c187413ce6d40c715e49b94001f976d1bb35f7fd6a96aa06745dd620aad2f393',
}


def add_label(data, label=b'DISK      2'):
    """Return an independent FAT12 floppy copy plus exact derivation metadata."""
    if len(label) != 11 or any(c < 32 or c > 126 for c in label):
        raise ValueError('label must be eleven printable ASCII bytes')
    if len(data) != 1474560:
        raise ValueError('expected 1.44 MB floppy length')
    geometry = (struct.unpack_from('<H', data, 11)[0],
                struct.unpack_from('<H', data, 14)[0], data[16],
                struct.unpack_from('<H', data, 17)[0],
                struct.unpack_from('<H', data, 22)[0])
    if geometry != (512, 1, 2, 224, 9):
        raise ValueError('unexpected FAT12 BPB geometry')
    start, end = 19 * 512, 33 * 512
    offsets = range(start, end, 32)
    if any(data[i] not in (0, 0xe5) and data[i + 11] == 8 for i in offsets):
        raise ValueError('volume label already exists')
    offset = next((i for i in offsets if data[i] == 0), None)
    if offset is None or offset + 64 > end or any(data[offset:offset + 64]):
        raise ValueError('no empty root-directory slot and terminator available')
    derived = bytearray(data)
    derived[offset:offset + 32] = label + b'\x08' + bytes(20)
    derived = bytes(derived)
    return derived, {
        'source_sha256': hashlib.sha256(data).hexdigest(),
        'derived_sha256': hashlib.sha256(derived).hexdigest(),
        'directory_entry_offset': offset,
        'before_entry_hex': data[offset:offset + 32].hex(),
        'after_entry_hex': derived[offset:offset + 32].hex(),
        'changed_offsets': [i for i in range(offset, offset + 32) if data[i] != derived[i]],
    }


def stage(source, destination):
    source, destination = Path(source), Path(destination)
    images = {}
    for name, expected in EXPECTED.items():
        data = (source / name).read_bytes()
        if len(data) != 1474560 or hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('original media verification failed: ' + name)
        images[name] = data
    derived, manifest = add_label(images['MSDOS2.img'])
    # A dedicated NEW directory prevents replacing an existing research artifact.
    destination.mkdir(parents=True, exist_ok=False)
    images['MSDOS2-labeled.img'] = derived
    for name, data in images.items():
        with (destination / name).open('xb') as out:
            out.write(data)
    with (destination / 'disk2-label-derivation.json').open('x', encoding='utf-8') as out:
        json.dump(manifest, out, indent=2)
        out.write('\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original_directory', type=Path)
    parser.add_argument('new_working_directory', type=Path)
    args = parser.parse_args()
    print(json.dumps(stage(args.original_directory, args.new_working_directory), indent=2))


if __name__ == '__main__':
    main()
