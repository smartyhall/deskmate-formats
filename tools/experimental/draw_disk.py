"""Read a native document directly from a stopped RSX FAT16 clone for verification."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
from struct import unpack_from


def extract(image, names):
    def word(offset):
        return unpack_from('<H', image, offset)[0]

    def dword(offset):
        return unpack_from('<I', image, offset)[0]

    if image[510:512] != b'\x55\xaa' or image[450] != 6:
        raise ValueError('unexpected RSX partition table')
    bpb = dword(454) * 512
    if word(bpb + 11) != 512 or image[bpb + 54:bpb + 62] != b'FAT16   ' or image[bpb + 16] != 2:
        raise ValueError('unexpected RSX FAT16 BPB')
    cluster_size = image[bpb + 13] * 512
    fat = bpb + word(bpb + 14) * 512
    fat_size = word(bpb + 22) * 512
    root_start = fat + 2 * fat_size
    root_size = word(bpb + 17) * 32
    first_data = root_start + root_size
    if (cluster_size != 2048 or root_size % 512 or
            not 0 < fat < root_start < first_data < len(image) or
            image[fat:fat + fat_size] != image[fat + fat_size:root_start]):
        raise ValueError('unexpected or inconsistent FAT16 layout')
    limit = min(2 + (len(image) - first_data) // cluster_size, fat_size // 2, 0xfff0)

    def chain(cluster):
        result = []
        seen = set()
        while cluster < 0xfff8:
            if not 2 <= cluster < limit or cluster in seen:
                raise ValueError('invalid FAT16 chain')
            seen.add(cluster)
            result.append(first_data + (cluster - 2) * cluster_size)
            cluster = word(fat + 2 * cluster)
        return result

    def directory(blocks, size):
        for start in blocks:
            for offset in range(start, start + size, 32):
                if image[offset] == 0:
                    return
                if image[offset] != 0xe5 and image[offset + 11] & 8 == 0:
                    yield image[offset:offset + 11], offset

    root = dict(directory([root_start], root_size))
    desk = root[b'DESKMATE   ']
    if not image[desk + 11] & 16:
        raise ValueError('missing DESKMATE directory')
    entries = dict(directory(chain(word(desk + 26)), cluster_size))
    result = {}
    for name in names:
        if not re.fullmatch(r'[A-Z0-9]{1,8}\.(?:FIG|DOC|FIL|FF1|PRN)', name):
            raise ValueError('expected an uppercase DOS research filename')
        entry = entries[(name[:-4].ljust(8) + name[-3:]).encode('ascii')]
        size = dword(entry + 28)
        blocks = chain(word(entry + 26))
        if image[entry + 11] & 16 or not blocks or not (len(blocks) - 1) * cluster_size < size <= len(blocks) * cluster_size:
            raise ValueError(f'Document length or allocation disagrees for {name}')
        result[name] = b''.join(image[p:p + cluster_size] for p in blocks)[:size]
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('disk', type=Path)
    parser.add_argument('independent_extraction', type=Path, help='7-Zip extracted DESKMATE directory')
    parser.add_argument('names', nargs='+')
    args = parser.parse_args()
    if args.disk.stat().st_size > 128 * 1024 * 1024:
        parser.error('disk exceeds supported RSX size')
    image = args.disk.read_bytes()
    files = extract(image, args.names)
    for name, data in files.items():
        if data != (args.independent_extraction / name).read_bytes():
            raise ValueError(f'independent extraction disagrees for {name}')
    print(json.dumps({'disk_sha256': sha256(image).hexdigest(),
                      'files': {name: {'size': len(data), 'sha256': sha256(data).hexdigest()}
                                for name, data in files.items()}}, indent=2))
