"""Build MDIAG.COM and a one-file FAT12 data floppy.

Deterministic: GNU as (.code16, origin 0x100) plus objcopy to a flat image, with
the 0x100-byte origin gap stripped. The assembler is a build tool only; the
result is our own code and no third-party object is committed.

    python build.py --out <dir> [--floppy <image>]

The floppy is a private transfer medium: one <=512-byte file in cluster 2,
never bootable, mounted only after DOS has booted.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ORIGIN = 0x100
TOOLCHAIN = Path('C:/msys64/ucrt64/bin')


def toolchain():
    names = {}
    for name in ('as', 'objcopy'):
        found = shutil.which(name) or (TOOLCHAIN / f'{name}.exe')
        if not found or not Path(found).exists():
            raise SystemExit(f'{name} not found; install GNU binutils or set PATH')
        names[name] = str(found)
    return names


def assemble(source, workdir):
    tools = toolchain()
    obj = workdir / 'mdiag.o'
    flat = workdir / 'mdiag.bin'
    subprocess.run([tools['as'], '--32', '-o', str(obj), str(source)], check=True)
    subprocess.run([tools['objcopy'], '-O', 'binary', str(obj), str(flat)], check=True)
    image = flat.read_bytes()
    if image[:ORIGIN] != bytes(ORIGIN):
        raise SystemExit('origin gap is not zero-filled; refusing to strip')
    return image[ORIGIN:]


def floppy(payload, name='MDIAG   COM'):
    """One-file 1.44 MB FAT12 image; never touches a host disk."""
    if not isinstance(payload, bytes) or not 1 <= len(payload) <= 512:
        raise ValueError('one-cluster payload must contain 1..512 bytes')
    encoded = name.encode('ascii')
    if len(encoded) != 11:
        raise ValueError('8.3 name must be 11 characters')
    name = encoded
    image = bytearray(1474560)
    image[:11] = b'\xeb\x3c\x90MDIAG001 '
    struct.pack_into('<HBHBHHBHHHII', image, 11,
                     512, 1, 1, 2, 224, 2880, 0xf0, 9, 18, 2, 0, 0)
    image[36:39] = b'\x00\x00\x29'
    struct.pack_into('<I', image, 39, 0x4d444941)
    image[43:54] = b'MDIAGFLOPPY'
    image[54:62] = b'FAT12   '
    image[62:66] = b'\xfa\xf4\xeb\xfd'
    image[510:512] = b'\x55\xaa'
    fat = bytearray(9 * 512)
    fat[:5] = b'\xf0\xff\xff\xff\x0f'
    image[512:5120] = fat
    image[5120:9728] = fat
    image[9728:9739] = b'MDIAGFLOPPY'
    image[9739] = 8
    entry = 9760
    image[entry:entry + 11] = name
    image[entry + 11] = 0x20
    struct.pack_into('<H', image, entry + 24, (46 << 9) | (11 << 5) | 4)
    struct.pack_into('<HI', image, entry + 26, 2, len(payload))
    image[16896:16896 + len(payload)] = payload
    return bytes(image)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--floppy', type=Path)
    parser.add_argument('--source', type=Path, default=HERE / 'mdiag.S')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        program = assemble(args.source, Path(temp))
    if b'MDIAG001' not in program:
        raise SystemExit('record signature missing from the built image')
    binary = args.out / 'MDIAG.COM'
    binary.write_bytes(program)
    receipt = {
        'source': str(args.source),
        'source_sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
        'program': str(binary),
        'program_bytes': len(program),
        'program_sha256': hashlib.sha256(program).hexdigest(),
        'assembler': 'GNU as --32 (.code16, .org 0x100) + objcopy -O binary, origin gap stripped',
        'record_layout': {'signature': b'MDIAG001'.decode(),
                          'fields': ['x', 'y', 'buttons', 'presses', 'releases', 'ticks', 'version', 'reserved'],
                          'bytes': 24},
    }
    if args.floppy:
        image = floppy(program)
        args.floppy.parent.mkdir(parents=True, exist_ok=True)
        args.floppy.write_bytes(image)
        receipt['floppy'] = str(args.floppy)
        receipt['floppy_sha256'] = hashlib.sha256(image).hexdigest()
    (args.out / 'build.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
