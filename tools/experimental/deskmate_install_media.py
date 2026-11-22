"""Reconstruct disposable FAT12 floppies from verified TVDog file sets."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
from struct import pack_into
from zipfile import ZipFile


INVENTORY = Path(__file__).resolve().parents[2] / 'docs/ecosystem/deskmate-installation-media.json'
DISK_COUNTS = {'300': 5, '302': 3, '303': 4}
SECTOR_SIZE = 512
# Total sectors, sectors per FAT, sectors per track, sectors per cluster,
# root directory entries, and media descriptor.
GEOMETRIES = {
    '360k': (720, 2, 9, 2, 112, 0xfd),
    '720k': (1440, 3, 9, 2, 112, 0xf9),
    '1440k': (2880, 9, 18, 1, 224, 0xf0),
}


def floppy(members, label, geometry='720k'):
    sectors, fat_sectors, track_sectors, cluster_sectors, root_entries, media = GEOMETRIES[geometry]
    directories = {(): []}
    seen = set()
    for member, data in members:
        parts = tuple(member.filename.upper().split('/'))
        if (len(parts) > 3 or any(not re.fullmatch(r'[-A-Z0-9_]{1,8}(?:\.[-A-Z0-9_]{1,3})?', p)
                                 for p in parts) or parts in seen):
            raise ValueError(f'expected a unique DOS 8.3 path with at most two directories: {member.filename}')
        seen.add(parts)
        for depth in range(1, len(parts)):
            directory = parts[:depth]
            if directory not in directories:
                directories[directory] = []
                directories[directory[:-1]].append((directory[-1], member.date_time, None))
        directories[parts[:-1]].append((parts[-1], member.date_time, data))
    if len(label) != 11 or len(directories[()]) >= root_entries:
        raise ValueError(f'expected an eleven-byte FAT label and at most {root_entries - 1} root entries')
    if seen.intersection(directories):
        raise ValueError('file and directory names collide')
    fat_size = fat_sectors * SECTOR_SIZE
    cluster_size = cluster_sectors * SECTOR_SIZE
    root_offset = SECTOR_SIZE + 2 * fat_size
    data_offset = root_offset + root_entries * 32
    image = bytearray(sectors * SECTOR_SIZE)
    image[:11] = b'\xeb\x3c\x90MSDOS5.0'
    pack_into('<HBHBHHBHHHII', image, 11, SECTOR_SIZE, cluster_sectors, 1, 2,
              root_entries, sectors, media, fat_sectors, track_sectors, 2, 0, 0)
    image[38] = 0x29
    image[43:62] = label + b'FAT12   '
    image[510:512] = b'\x55\xaa'
    image[root_offset:root_offset + 12] = label + b'\x08'
    fat = bytearray(fat_size)
    fat[:3] = bytes((media, 0xff, 0xff))
    cluster = 2

    def allocate(length):
        nonlocal cluster
        count = (length + cluster_size - 1) // cluster_size
        begin = data_offset + (cluster - 2) * cluster_size
        if begin + count * cluster_size > len(image):
            raise ValueError('disk capacity exceeded')
        first = cluster if count else 0
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
        return first, begin

    def directory_entry(offset, name, date_time, attr, first, length):
        stem, _, extension = name.partition('.') if name not in ('.', '..') else (name, '', '')
        image[offset:offset + 11] = (stem.ljust(8) + extension.ljust(3)).encode('ascii')
        image[offset + 11] = attr
        year, month, day, hour, minute, second = date_time
        dos_time = (hour << 11) | (minute << 5) | (second // 2)
        dos_date = ((year - 1980) << 9) | (month << 5) | day
        pack_into('<HHHI', image, offset + 22, dos_time, dos_date, first, length)

    def write_entries(path, offset, parent_cluster):
        for index, (name, date_time, data) in enumerate(directories[path]):
            entry_offset = offset + index * 32
            if data is not None:
                first, begin = allocate(len(data))
                image[begin:begin + len(data)] = data
                directory_entry(entry_offset, name, date_time, 0x20, first, len(data))
                continue
            child = (*path, name)
            first, begin = allocate((len(directories[child]) + 2) * 32)
            directory_entry(entry_offset, name, date_time, 0x10, first, 0)
            directory_entry(begin, '.', date_time, 0x10, first, 0)
            directory_entry(begin + 32, '..', date_time, 0x10, parent_cluster, 0)
            write_entries(child, begin + 64, first)

    write_entries((), root_offset + 32, 0)
    image[SECTOR_SIZE:SECTOR_SIZE + fat_size] = fat
    image[SECTOR_SIZE + fat_size:root_offset] = fat
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
