"""Self-authored synthetic specimen for x86 segment-register instruction forms.

The specimen is a raw 16-bit code payload, not a DOS image: it exists only to
make every ``MOV`` form that touches a segment register decodable at a known
offset. Nothing here comes from a commercial binary.

Encodings follow the Intel instruction set reference:

* ``8E /r``  ``MOV Sreg, r/m16``   (reg field selects the segment register)
* ``8C /r``  ``MOV r/m16, Sreg``

Segment-register codes are ``0=ES 1=CS 2=SS 3=DS 4=FS 5=GS``; 6 and 7 are
reserved. ``MOD=11`` selects the register form. The ``66`` prefix changes the
operand size of the general register to 32 bits while the move itself is still
16 bits wide.

``FORMS`` is the truth table used by the portable test: the offset, the bytes,
the architectural meaning, and the general and segment registers involved.
"""
from __future__ import annotations

SEGMENTS = {0: "ES", 1: "CS", 2: "SS", 3: "DS", 4: "FS", 5: "GS"}

# (offset, name, bytes, general register, segment register, direction, note)
# direction "to_segment" means the segment register is written.
FORMS = (
    (0, "mov_ds_ax", bytes([0x8E, 0xD8]), "AX", "DS", "to_segment", ""),
    (2, "mov_es_ax", bytes([0x8E, 0xC0]), "AX", "ES", "to_segment", ""),
    (4, "mov_ss_ax", bytes([0x8E, 0xD0]), "AX", "SS", "to_segment", ""),
    (6, "mov_fs_ax", bytes([0x8E, 0xE0]), "AX", "FS", "to_segment", ""),
    (8, "mov_gs_ax", bytes([0x8E, 0xE8]), "AX", "GS", "to_segment", ""),
    (10, "mov_ax_ds", bytes([0x8C, 0xD8]), "AX", "DS", "from_segment", ""),
    (12, "mov_ax_es", bytes([0x8C, 0xC0]), "AX", "ES", "from_segment", ""),
    (14, "mov_bx_ds", bytes([0x8C, 0xDB]), "BX", "DS", "from_segment", ""),
    (16, "mov_ds_mem", bytes([0x8E, 0x1E, 0x34, 0x12]), None, "DS",
     "to_segment", "memory form: DS <- [1234h]"),
    (20, "mov_mem_ds", bytes([0x8C, 0x1E, 0x34, 0x12]), None, "DS",
     "from_segment", "memory form: [1234h] <- DS"),
    (24, "mov_ds_eax", bytes([0x66, 0x8E, 0xD8]), "EAX", "DS",
     "to_segment", "operand-size prefix: 32-bit source, 16-bit move"),
    (27, "mov_eax_ds", bytes([0x66, 0x8C, 0xD8]), "EAX", "DS",
     "from_segment", "operand-size prefix: zero-extended to 32 bits"),
    (30, "mov_cs_ax", bytes([0x8E, 0xC8]), "AX", "CS", "to_segment",
     "reserved encoding: loading CS with MOV is invalid on hardware"),
    (32, "mov_ax_cs", bytes([0x8C, 0xC8]), "AX", "CS", "from_segment",
     "reading CS is valid"),
)


# Long-mode forms. REX.W makes the general operand 64 bits while the move to
# or from the segment register still transfers 16 bits; REX.R/REX.B extend the
# segment-register and general-register fields.
LONG_FORMS = (
    (0, "mov_ds_rax", bytes([0x48, 0x8E, 0xD8]), "RAX", "DS", "to_segment",
     "REX.W: MOV Sreg, r/m64"),
    (3, "mov_rax_ds", bytes([0x48, 0x8C, 0xD8]), "RAX", "DS", "from_segment",
     "REX.W: MOV r/m64, Sreg, zero-extended"),
    (6, "mov_ds_eax_norex", bytes([0x8E, 0xD8]), "EAX", "DS", "to_segment",
     "no prefix in long mode: default 32-bit source, lower 16 bits moved"),
    (8, "mov_es_r8", bytes([0x4D, 0x8E, 0xC0]), "R8", "ES", "to_segment",
     "REX.R/B: extended general register"),
    (11, "mov_r8_ds", bytes([0x49, 0x8C, 0xD8]), "R8", "DS", "from_segment",
     "REX.B: extended destination register (rm=0 + 8)"),
)


def build_payload() -> bytes:
    payload = bytearray(64)
    for offset, _name, encoded, _general, _segment, _direction, _note in FORMS:
        payload[offset:offset + len(encoded)] = encoded
    return bytes(payload)


def build_long_mode_payload() -> bytes:
    payload = bytearray(32)
    for offset, _name, encoded, _general, _segment, _direction, _note in LONG_FORMS:
        payload[offset:offset + len(encoded)] = encoded
    return bytes(payload)


def long_truth_table() -> list[dict]:
    return [
        {
            "offset": offset,
            "name": name,
            "bytes": encoded.hex(),
            "general_register": general,
            "segment_register": segment,
            "writes": segment if direction == "to_segment" else general,
            "reads": general if direction == "to_segment" else segment,
            "note": note,
        }
        for offset, name, encoded, general, segment, direction, note in LONG_FORMS
    ]


def truth_table() -> list[dict]:
    return [
        {
            "offset": offset,
            "name": name,
            "bytes": encoded.hex(),
            "general_register": general,
            "segment_register": segment,
            "writes": segment if direction == "to_segment" else general,
            "reads": general if direction == "to_segment" else segment,
            "note": note,
        }
        for offset, name, encoded, general, segment, direction, note in FORMS
    ]


def describe() -> dict:
    return {
        "kind": "raw-16-bit-x86-payload",
        "size": 64,
        "forms": truth_table(),
        "scope": (
            "encodings taken from the Intel instruction set reference; the "
            "specimen is authored here, so any mismatch is a decoder or "
            "display finding, not a property of a commercial binary"
        ),
    }
