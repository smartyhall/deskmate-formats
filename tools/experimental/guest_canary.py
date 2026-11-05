"""Original 386 DOS canary: deterministic COM encoding and FAT12 data floppy.

No assembler, DOS files or ROMs are embedded. Output is exclusively created
outside the repository. See experiments/guest-canary/canary.asm for matching
assembly and docs/research/86box-guest-canary.md for the measured experiment.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

ORIGIN = 0x100
CHECKPOINT = 0x160
BANNER_OFFSET = 0x180
DATA_OFFSET = 0x200
DATA = b'DMF-CANARY-v1\x00' + bytes(range(16)) + b'\xa5\x5a'
LINES = ['DMF CANARY v1', 'SOURCE / REGISTERS / RAM',
         '┌──────────────┐', '│ CANARY READY │', '└──────────────┘']
BANNER = ('\r\n'.join(LINES) + '\r\n$').encode('cp437')
# x86 MOV r32, imm32 uses register order AX,CX,DX,BX,SP,BP,SI,DI.
REGISTERS = dict(eax=0x13579bdf, ecx=0x0badf00d, edx=0x55aa33cc,
                 ebx=0x2468ace0, esp=0x0000ff00, ebp=0x10203040,
                 esi=0x11223344, edi=0x55667788)
ROOT = Path(__file__).resolve().parents[2]


def program():
    # push cs/pop ds; mov ax,3/int10; mov dx,0180/mov ah,09/int21.
    code = bytearray.fromhex('0e 1f b8 03 00 cd 10 ba 80 01 b4 09 cd 21')
    # All interrupts precede the checkpoint register values.
    # cli; mov ax,cs; mov ds,ax; mov es,ax; mov ss,ax.
    code += bytes.fromhex('fa 8c c8 8e d8 8e c0 8e d0')
    for reg, value in enumerate(REGISTERS.values()):
        code += bytes((0x66, 0xb8 + reg)) + struct.pack('<I', value)
    assert len(code) + ORIGIN <= CHECKPOINT
    code += b'\x90' * (CHECKPOINT - ORIGIN - len(code))
    code += b'\xeb\xfe'  # JMP short 0160: target = 0162 + sign_extend(FE).
    code += bytes(BANNER_OFFSET - ORIGIN - len(code))
    code += BANNER
    assert len(code) + ORIGIN <= DATA_OFFSET
    code += bytes(DATA_OFFSET - ORIGIN - len(code))
    code += DATA
    return bytes(code)


def floppy(payload):
    """One-file 1.44 MB FAT12 data image; never uses a host disk API.

    A single <=512-byte file occupies cluster 2. Dates are fixed at 2026-11-04
    00:00. Bootstrap halts if mistakenly booted: mount only AFTER DOS boots.
    """
    if not isinstance(payload, bytes) or not 1 <= len(payload) <= 512:
        raise ValueError('one-cluster payload must contain 1..512 bytes')
    image = bytearray(1474560)
    image[:11] = b'\xeb\x3c\x90DMFTEST '
    struct.pack_into('<HBHBHHBHHHII', image, 11,
                     512, 1, 1, 2, 224, 2880, 0xf0, 9, 18, 2, 0, 0)
    image[36:39] = b'\x00\x00\x29'
    struct.pack_into('<I', image, 39, 0x43414e31)
    image[43:54] = b'DMFCANARY  '
    image[54:62] = b'FAT12   '
    image[62:66] = b'\xfa\xf4\xeb\xfd'
    image[510:512] = b'\x55\xaa'
    fat = bytearray(9 * 512)
    fat[:5] = b'\xf0\xff\xff\xff\x0f'  # entry 2 = FFF (end of chain).
    image[512:5120] = fat
    image[5120:9728] = fat
    image[9728:9739] = b'DMFCANARY  '
    image[9739] = 8  # Volume label; next entry is the only file.
    entry = 9760
    image[entry:entry + 11] = b'CANARY  COM'
    image[entry + 11] = 0x20
    struct.pack_into('<H', image, entry + 24, (46 << 9) | (11 << 5) | 4)
    struct.pack_into('<HI', image, entry + 26, 2, len(payload))
    image[16896:16896 + len(payload)] = payload
    return bytes(image)


def locations(registers):
    """Validate the checkpoint BEFORE calculating bounded ordinary RAM reads."""
    if any(registers.get(k) != v for k, v in REGISTERS.items()):
        raise ValueError('not the canary register checkpoint')
    segment = registers.get('cs')
    if type(segment) is not int or not 0x50 <= segment <= 0x9000:
        raise ValueError('unexpected ordinary-RAM program segment')
    if registers.get('eip') != CHECKPOINT or registers.get('cr0', 1) & 1:
        raise ValueError('not the intended real-mode CS:IP')
    if registers.get('eflags', 0x200) & 0x200:
        raise ValueError('checkpoint requires interrupts disabled')
    for name in ('cs', 'ds', 'es', 'ss'):
        if registers.get(name) != segment or registers.get(name + '_base') != segment * 16:
            raise ValueError('segment/base correspondence failed')
    return {'segment': segment, 'code': segment * 16 + ORIGIN,
            'checkpoint': segment * 16 + CHECKPOINT,
            'data': segment * 16 + DATA_OFFSET}


def validate(observation):
    """Export only verified original-canary content, never raw DOS RAM/paths."""
    regs, status, identity = (observation[k] for k in ('registers', 'status', 'info'))
    where = locations(regs)
    if status.get('held') is not True or status.get('paused') is not False:
        raise ValueError('observation must be held and unpaused')
    reads = {item['address']: bytes.fromhex(item['data']) for item in observation['memory']}
    code = program()[:CHECKPOINT - ORIGIN + 2]
    if reads.get(where['code']) != code or reads.get(where['data']) != DATA:
        raise ValueError('guest code/data differs from original source')
    lines = [s.rstrip() for s in observation['text']['lines']]
    if lines[:len(LINES)] != LINES:
        raise ValueError('CP437 screen does not match source banner/pattern')
    return {'locations': where, 'registers': dict(REGISTERS), 'ip': regs['eip'],
            'code_bytes_verified': len(code), 'data_bytes_verified': len(DATA),
            'data_hex': DATA.hex(), 'screen_lines': LINES,
            'status': {k:status[k] for k in ('ms', 'frames', 'held', 'paused', 'bios_mode', 'w', 'h')},
            'identity': {k:identity[k] for k in ('version', 'machine', 'hard_resets', 'soft_resets', 'last_reset_ms')}}


def generate(destination):
    destination = Path(destination).resolve()
    if destination.is_relative_to(ROOT):
        raise ValueError('generated binary artifacts must stay outside the repository')
    destination.mkdir(parents=True, exist_ok=False)
    outputs = {'CANARY.COM': program(), 'canary-data.img': floppy(program())}
    inventory = {}
    for name, data in outputs.items():
        with (destination / name).open('xb') as out:
            out.write(data)
        inventory[name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    with (destination / 'generated.json').open('x', encoding='utf-8') as out:
        json.dump(inventory, out, indent=2)
    return inventory


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('new_private_output_directory', type=Path)
    print(json.dumps(generate(parser.parse_args().new_private_output_directory), indent=2))
