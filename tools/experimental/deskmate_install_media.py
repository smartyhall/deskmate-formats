"""Reconstruct disposable 720 KiB floppies from the verified TVDog ZIP sets."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
from struct import pack_into
from zipfile import ZipFile


INVENTORY = Path(__file__).resolve().parents[2] / 'docs/ecosystem/deskmate-installation-media.json'
ROOT_OFFSET = 3584
DATA_OFFSET = 7168
CLUSTER_SIZE = 1024
DISK_COUNTS = {'300': 5, '302': 3, '303': 4}


def floppy(members, label):
    if len(label) != 11 or len(members) >= 112:
        raise ValueError('expected an eleven-byte FAT label and at most 111 files')
    image = bytearray(737_280)
    image[:11] = b'\xeb\x3c\x90MSDOS5.0'
    pack_into('<HBHBHHBHHHII', image, 11, 512, 2, 1, 2, 112, 1440, 0xf9, 3, 9, 2, 0, 0)
    image[38] = 0x29
    image[43:62] = label + b'FAT12   '
    image[510:512] = b'\x55\xaa'
    image[ROOT_OFFSET:ROOT_OFFSET + 12] = label + b'\x08'
    fat = bytearray(1536)
    fat[:3] = b'\xf9\xff\xff'
    cluster = 2
    seen = set()
    for index, (member, data) in enumerate(members, 1):
        name = member.filename.upper()
        if not re.fullmatch(r'[A-Z0-9_]{1,8}(?:\.[A-Z0-9_]{1,3})?', name) or name in seen:
            raise ValueError(f'expected a unique flat DOS 8.3 filename: {name}')
        seen.add(name)
        stem, _, extension = name.partition('.')
        count = (len(data) + CLUSTER_SIZE - 1) // CLUSTER_SIZE
        begin = DATA_OFFSET + (cluster - 2) * CLUSTER_SIZE
        if begin + count * CLUSTER_SIZE > len(image):
            raise ValueError('disk capacity exceeded')
        entry = ROOT_OFFSET + index * 32
        image[entry:entry + 12] = (stem.ljust(8) + extension.ljust(3)).encode('ascii') + b'\x20'
        year, month, day, hour, minute, second = member.date_time
        dos_time = (hour << 11) | (minute << 5) | (second // 2)
        dos_date = ((year - 1980) << 9) | (month << 5) | day
        pack_into('<HHHI', image, entry + 22, dos_time, dos_date, cluster if count else 0, len(data))
        image[begin:begin + len(data)] = data
        for current in range(cluster, cluster + count):
            value = 0xfff if current == cluster + count - 1 else current + 1
            offset = current + current // 2
            if current % 2:
                fat[offset] |= (value & 15) << 4
                fat[offset + 1] = value >> 4
            else:
                fat[offset] = value & 255
                fat[offset + 1] |= value >> 8
        cluster += count
    image[512:2048] = image[2048:3584] = fat
    return image


def build(version, originals, output, separator):
    manifest = json.loads(INVENTORY.read_text(encoding='utf-8'))
    records = {record['path']: record for record in manifest['archives']}
    for number in range(1, DISK_COUNTS[version] + 1):
        archive_name = f'dm{version}dk{number}.zip'
        relative = f'tandy1000/deskmate/{archive_name}'
        archive = originals / relative
        record = records[relative]
        if archive.stat().st_size != record['bytes'] or sha256(archive.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError(f'archive differs from inventory: {archive_name}')
        with ZipFile(archive) as source:
            members = [(member, source.read(member)) for member in source.infolist() if not member.is_dir()]
        if len(members) != record['file_count'] or sum(len(data) for _, data in members) != record['unpacked_bytes']:
            raise ValueError(f'archive member inventory differs: {archive_name}')
        image = floppy(members, f'DESKMATE{separator}{number} '.encode('ascii'))
        name = f'dm{version}dk{number}.img'
        with (output / name).open('xb') as destination:
            destination.write(image)
        print(f'{name} {len(image)} {sha256(image).hexdigest()}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version', choices=DISK_COUNTS)
    parser.add_argument('originals', type=Path, help='private TVDog mirror originals directory')
    parser.add_argument('output', type=Path, help='existing private output directory')
    parser.add_argument('--space-label', action='store_true', help='reconstruct the rejected 3.03 label control')
    args = parser.parse_args()
    build(args.version, args.originals, args.output, ' ' if args.space_label else '_')


if __name__ == '__main__':
    main()
