"""Deterministic synthetic DOS executables for structural regression tests.

These builders are the project's own work. They let the DOS-image readers,
address mapping and loader-block model be checked against bytes whose layout
is known independently, without any commercial binary, emulator or Ghidra
installation.

Every specimen is generated from a description, so it is reproducible: the
test suite asserts the expected bytes as well as the derived structure.
"""
from __future__ import annotations

import struct

__all__ = [
    "FAR_RETURN",
    "build_com",
    "build_mz",
    "build_segmented_mz",
]

FAR_RETURN = 0xCB


def build_mz(
    *,
    image: bytes,
    entry_cs: int,
    entry_ip: int,
    initial_ss: int = 0,
    initial_sp: int = 0xFFFF,
    relocations: tuple[tuple[int, int, int], ...] = (),
    header_paragraphs: int = 4,
    min_alloc: int = 0x10,
    max_alloc: int = 0xFFFF,
    trailing: bytes = b"",
) -> bytes:
    """Build a standard DOS MZ image.

    ``image`` is the load image (what DOS places at the load segment).
    ``relocations`` holds ``(site_segment, site_offset, value)`` triples: the
    value is written into the image at ``16 * site_segment + site_offset`` and
    the site is entered in the relocation table, exactly as a linker does.
    """
    image = bytearray(image)
    header_bytes = header_paragraphs * 16
    table_offset = 0x1C
    if table_offset + 4 * len(relocations) > header_bytes:
        raise ValueError("header is too small for the relocation table")

    entries = bytearray()
    for site_segment, site_offset, value in relocations:
        position = (site_segment << 4) + site_offset
        if position + 2 > len(image):
            raise ValueError("relocation site is outside the image")
        struct.pack_into("<H", image, position, value)
        entries += struct.pack("<HH", site_offset, site_segment)

    # The declared size covers the header and load image only; trailing bytes
    # sit after the declared image and are how an overlay appears on disk.
    total = header_bytes + len(image)
    pages, last = divmod(total, 512)
    if last:
        pages += 1
    else:
        last = 512

    header = bytearray(header_bytes)
    struct.pack_into(
        "<2s13H",
        header,
        0,
        b"MZ",
        last,
        pages,
        len(relocations),
        header_paragraphs,
        min_alloc,
        max_alloc,
        initial_ss,
        initial_sp,
        0,
        entry_ip,
        entry_cs,
        table_offset,
        0,
    )
    header[table_offset:table_offset + len(entries)] = entries
    return bytes(header) + bytes(image) + bytes(trailing)


def build_segmented_mz() -> tuple[bytes, dict]:
    """A two-segment MZ image with a far return at the second segment start.

    Layout of the load image (segment values are image-relative):

    * segment 0000: origin code. ``MOV AX,0010h`` / ``MOV DS,AX`` at image
      offset 0. A far call to ``0010:C000``. Embedded string ``DMDB\\0``.
    * segment 0010: starts at image offset 0x100 with the single byte ``CB``
      (far return) followed by padding, so a loader's far-return adjustment
      moves the split point one byte forward.

    A third relocated word names segment 0020, which lies outside the stored
    image and must be dropped by a loader's block construction.
    """
    image = bytearray(0x200)
    code = bytes(
        [
            0xB8, 0x10, 0x00,        # MOV AX,0010h
            0x8E, 0xD8,              # MOV DS,AX   (8E /r register form)
            0xB8, 0x20, 0x00,        # MOV AX,0020h
            0x8E, 0xC0,              # MOV ES,AX
            0x9A, 0x00, 0xC0, 0x10, 0x00,  # CALL FAR 0010:C000
            0xCD, 0x21,              # INT 21h
            0xCB,                    # RETF
        ]
    )
    image[0:len(code)] = code
    image[0x40:0x40 + 5] = b"DMDB\x00"
    # Far pointer at image 0030: offset word C000, segment word 0010.
    image[0x30:0x34] = b"\x00\xc0\x10\x00"
    # A relocated word naming segment 0020, which is outside the image.
    image[0x34:0x36] = b"\x20\x00"
    image[0x100] = FAR_RETURN
    image[0x110:0x114] = b"\x90\x90\x90\xcb"

    relocations = (
        (0x0000, 0x32, 0x0010),  # segment word of the far pointer -> 0010
        (0x0000, 0x34, 0x0020),  # names segment 0020
    )
    data = build_mz(
        image=bytes(image),
        entry_cs=0x0000,
        entry_ip=0x0000,
        initial_ss=0x0000,
        initial_sp=0x0100,
        relocations=relocations,
        min_alloc=0x0100,
    )
    expected = {
        "header_bytes": 0x40,
        "image_bytes": 0x200,
        "entry_cs": 0x0000,
        "entry_ip": 0x0000,
        "entry_file_offset": 0x40,
        "relocation_count": 2,
        "relocation_sites": [(0x0000, 0x32), (0x0000, 0x34)],
        "relocated_values": [0x0010, 0x0020],
        "far_pointer_file_offset": 0x40 + 0x30,
        "far_return_file_offset": 0x40 + 0x100,
        "string_file_offset": 0x40 + 0x40,
    }
    return data, expected


def build_com(*, code: bytes, trailing: bytes = b"") -> bytes:
    """Build a DOS COM image (no header; the program loads at IP 0x100)."""
    return bytes(code) + bytes(trailing)
