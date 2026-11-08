"""Invented two-calendar scaffolding, never a reconstruction of native B.

Uses a different year, times, description and header. No output is archived as
a native specimen or writer candidate; only parser isolation is exercised.
"""
import struct

from synthetic import PERSONAL, INTERNAL, allocation, build, event, row


def two_calendars():
    data = bytearray(build('one'))
    data.extend(bytes(4096))
    data[0x15] = 2
    allocation(data)
    # Add seven schema records from the documented schema, not copied native bytes.
    at = data.index(3, 2048, 3072)
    for n, (name, width, kind) in enumerate(PERSONAL, 1):
        raw = row(28 + n, [name.encode(), b'SECOND', f'{n:03d}'.encode(),
                          str(width).encode(), kind.encode(), b'0'])
        data[at:at + len(raw)] = raw
        struct.pack_into('<HHH', data, 3112 + (12 + n) * 6, 2, at - 2048, 28 + n)
        at += len(raw)
    data[at] = 3
    data[0x40E:0x413] = b'00020'
    data[0x418:0x41D] = b'00036'
    at = data.index(3, 1024, 2048)
    descriptor = b'T\x01SECOND\x018\x0107\x0100002\x01000\x0100018\x019\x011\x012\x014\x015\x017\x01\x02'
    data[at:at + len(descriptor)] = descriptor
    data[at + len(descriptor)] = 3
    # Wednesday 2030-01-02, 13:00..14:00, alarm enabled. This is not B's event.
    payload = INTERNAL + event(17, 'SYNTHETIC SECOND / SCOPED ID', b'\x93bc', b'e', b'\xb4', b'\xb8', protected=b'q')
    data[8192:8192 + len(payload)] = payload
    data[8192 + len(payload)] = 3
    data[9216:9256] = (b'\xff' * 9 + b'\0') * 4
    for n, (offset, rid) in enumerate(((0, 16), (len(INTERNAL), 17))):
        struct.pack_into('<HHH', data, 9256 + 6 * n, 8, offset, rid)
    return bytes(data)
