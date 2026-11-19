"""Build a fresh 1.44 MB FAT12 data floppy for disposable Draw trials."""
import argparse
from pathlib import Path
import re
from struct import pack_into

from guest_canary import floppy


def data_floppy(files):
    if not 0 < len(files) < 224:
        raise ValueError('invalid floppy file count')
    image = bytearray(floppy(b'\0'))
    image[9760:16_896] = bytes(16_896 - 9760)
    fat = bytearray(9 * 512)
    fat[:3] = b'\xf0\xff\xff'
    next_cluster = 2
    for index, (name, data) in enumerate(sorted(files.items()), 1):
        if not re.fullmatch(r'[A-Z0-9]{1,8}\.FIG', name):
            raise ValueError('expected unique uppercase DOS FIG names')
        blocks = (len(data) + 511) // 512
        if blocks < 1 or next_cluster + blocks > 2849:
            raise ValueError('floppy capacity exceeded')
        entry = 9728 + index * 32
        image[entry:entry + 11] = (name[:-4].ljust(8) + 'FIG').encode('ascii')
        image[entry + 11] = 32
        pack_into('<HHI', image, entry + 24, (46 << 9) | (11 << 5) | 4, next_cluster, len(data))
        start = 16_896 + 512 * (next_cluster - 2)
        image[start:start + len(data)] = data
        end = next_cluster + blocks
        for cluster in range(next_cluster, end):
            link = 0xfff if cluster == end - 1 else cluster + 1
            offset = cluster + cluster // 2
            if cluster % 2:
                fat[offset] |= (link & 15) << 4
                fat[offset + 1] = link >> 4
            else:
                fat[offset] = link & 255
                fat[offset + 1] |= link >> 8
        next_cluster = end
    image[512:5120] = fat
    image[5120:9728] = fat
    return bytes(image)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('files', nargs='+', type=Path)
    args = parser.parse_args()
    files = {path.name.upper(): path.read_bytes() for path in args.files}
    if len(files) != len(args.files):
        parser.error('duplicate DOS filenames')
    with args.image.open('xb') as output:
        output.write(data_floppy(files))
