"""Read-only DOS executable inspection and address mapping.

Every command prints JSON, including the input size and SHA-256. Output can
contain proprietary bytes: store it privately. Inputs are opened for reading
only; there is no write operation and no emulator, loader or GUI use.

Coordinate names follow ``deskmate_formats.dosimage``: *file* offsets index
the stored file, *image* offsets index the load image, and *linear* addresses
are ``16 * segment + offset``. A synthetic load paragraph turns an image
offset into an analysis address; it is never a guest address.

A file without an MZ signature carries no header at all, so no structural
evidence can identify it as a COM program. The ``identify`` command reports
such a file as an unqualified candidate unless the caller adopts the COM
convention explicitly with ``--interpretation com``; applying the COM
convention to a non-MZ input therefore always requires that explicit claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from deskmate_formats.dosimage import (
    DEFAULT_LOAD_PARAGRAPH,
    MAX_COM_BYTES,
    MZ_SIGNATURES,
    ComImage,
    DosImageError,
    MzImage,
    identify,
    linear_to_segment_offset,
    segment_offset_to_linear,
)

MAX_SPAN = 1 << 20
MAX_SEGMENT = 0xFFFF


def _load(args) -> bytes:
    data = Path(args.path).read_bytes()
    expected = getattr(args, "expect_sha256", None)
    if expected:
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected.lower():
            raise DosImageError(
                f"input SHA-256 {actual} does not match --expect-sha256 {expected.lower()}"
            )
    return data


def _segment(value: int, label: str, allow_none: bool = False) -> int | None:
    if value is None and allow_none:
        return None
    if not 0 <= value <= MAX_SEGMENT:
        raise DosImageError(f"{label} must be within 0000h-FFFFh")
    return value


def _image(data: bytes, args):
    """Return a parsed image, requiring an explicit claim for a headerless file."""
    if len(data) >= 2 and data[:2] in MZ_SIGNATURES:
        return MzImage.parse(data)
    interpretation = getattr(args, "interpretation", None)
    if interpretation != "com":
        raise DosImageError(
            "input has no MZ signature and therefore no header evidence. A COM "
            "load image has no magic number, so this is an interpretation, not a "
            "finding; re-run with --interpretation com to adopt IP=0100h"
        )
    return ComImage.parse(data)


def _label_segment(args) -> int:
    """Segment to label a linear address with.

    ``--segment 0`` is a real choice: segment 0000h is a valid real-mode
    segment. A truthiness test would silently replace it with the load
    paragraph, so only an absent value falls back.
    """
    segment = getattr(args, "segment", None)
    return args.load_paragraph if segment is None else segment


def _input_record(args, data: bytes) -> dict:
    return {
        "path": args.path,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def command_identify(args) -> dict:
    data = _load(args)
    return identify(data, args.interpretation)


def command_blocks(args) -> dict:
    data = _load(args)
    image = _image(data, args)
    blocks = image.loader_blocks(data, args.load_paragraph)
    return {
        "input": _input_record(args, data),
        "format": image.describe()["format"],
        "interpretation": getattr(args, "interpretation", None) or "structural",
        "load_paragraph": args.load_paragraph,
        "image_bytes": image.image_bytes,
        "block_total": sum(b["size"] for b in blocks),
        "blocks": blocks,
        "scope": (
            "model of the block split produced by Ghidra's 16-bit MZ loader, "
            "reproduced from relocation-table arithmetic; block boundaries are "
            "loader artifacts and not original program structure"
        ),
    }


def command_map(args) -> dict:
    data = _load(args)
    image = _image(data, args)
    result = {
        "input": _input_record(args, data),
        "format": image.describe()["format"],
        "interpretation": getattr(args, "interpretation", None) or "structural",
        "load_paragraph": args.load_paragraph,
        "coordinates": [],
        "scope": (
            "explicit loader-arithmetic conversions; a segment:offset label is one "
            "valid labelling, not necessarily the runtime one"
        ),
    }

    if args.file_offset is not None:
        f = args.file_offset
        if f < 0:
            raise DosImageError("--file-offset must not be negative")
        linear = image.file_to_linear(f, args.load_paragraph)
        segment, offset = linear_to_segment_offset(linear, _label_segment(args))
        result["coordinates"].append(
            {
                "kind": "file_offset",
                "value": f,
                "image_offset": f - getattr(image, "header_bytes", 0),
                "linear": linear,
                "segment": segment,
                "offset": offset,
                "runtime_note": (
                    "linear here is synthetic (load paragraph "
                    f"{args.load_paragraph:#06x}); the runtime address requires an "
                    "observed load segment"
                ),
            }
        )

    if args.linear is not None:
        f = image.linear_to_file(args.linear, args.load_paragraph)
        segment, offset = linear_to_segment_offset(args.linear, _label_segment(args))
        result["coordinates"].append(
            {
                "kind": "linear",
                "value": args.linear,
                "file_offset": f,
                "image_offset": f - getattr(image, "header_bytes", 0),
                "segment": segment,
                "offset": offset,
            }
        )

    if args.segment_offset is not None:
        segment, offset = args.segment_offset
        _segment(segment, "--segment-offset SEGMENT")
        if not 0 <= offset <= MAX_SEGMENT:
            raise DosImageError("--segment-offset OFFSET must be within 0000h-FFFFh")
        linear = segment_offset_to_linear(segment, offset)
        entry = {"kind": "segment_offset", "segment": segment, "offset": offset,
                 "linear": linear}
        try:
            f = image.linear_to_file(linear, args.load_paragraph)
            entry["file_offset"] = f
            entry["image_offset"] = f - getattr(image, "header_bytes", 0)
        except DosImageError as exc:
            entry["file_offset"] = None
            entry["note"] = str(exc)
        result["coordinates"].append(entry)

    if not result["coordinates"]:
        raise DosImageError("supply --file-offset, --linear or --segment-offset")

    return result


def command_far(args) -> dict:
    data = _load(args)
    image = _image(data, args)
    if not isinstance(image, MzImage):
        raise DosImageError("far-pointer candidates require an MZ image")
    if not 0 <= args.offset <= len(data) - 4:
        raise DosImageError("--offset must address four bytes inside the input")
    pointer = image.far_pointer_at(data, args.offset)
    resolved_file_offset = image.far_pointer_file_offset(pointer)
    inside_image = (
        pointer.resolved_image_offset is not None
        and 0 <= pointer.resolved_image_offset < image.image_bytes
    )
    payload = {
        "file_offset": pointer.file_offset,
        "offset_word": pointer.offset_word,
        "segment_word": pointer.segment_word,
        "segment_has_mz_relocation": pointer.segment_relocated,
        "resolved_image_offset": pointer.resolved_image_offset,
        "resolved_inside_image": inside_image,
        "resolved_file_offset": resolved_file_offset,
        "resolution": pointer.resolution,
        "scope": (
            "candidate pointer arithmetic; the caller still has to establish that "
            "the bytes are a pointer and what its target is"
        ),
    }
    if pointer.resolved_image_offset is not None and not inside_image:
        payload["note"] = (
            "the pair resolves outside the stored image, so it has no file "
            "offset. Do not map it to one: the target is in another segment, an "
            "overlay or unrelated data"
        )
    return payload


def _disassembler():
    """Return a bounded decoder description, or None when Capstone is absent."""
    try:
        import capstone  # noqa: PLC0415
    except ImportError:
        return None
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_16)
    md.detail = False
    return md


def command_disasm(args) -> dict:
    data = _load(args)
    image = _image(data, args)
    if args.file_offset is not None:
        first = args.file_offset
    elif args.image_offset is not None:
        first = getattr(image, "header_bytes", 0) + args.image_offset
    else:
        raise DosImageError("supply --file-offset or --image-offset")

    if args.length <= 0:
        raise DosImageError("--length must be positive")
    if args.length > MAX_SPAN:
        raise DosImageError(f"--length must not exceed {MAX_SPAN}")
    if args.max_instructions <= 0:
        raise DosImageError("--max-instructions must be positive")
    if first < 0 or first + args.length > len(data):
        raise DosImageError("requested span is outside the input")

    md = _disassembler()
    instructions = []
    if md is None:
        return {
            "input": _input_record(args, data),
            "decoder": None,
            "instructions": [],
            "warning": (
                "no independent decoder is installed; install capstone to enable "
                "byte-level corroboration. Ghidra listing output is not a substitute"
            ),
        }

    for ins in md.disasm(data[first:first + args.length], first):
        linear = image.file_to_linear(ins.address, args.load_paragraph)
        segment, offset = linear_to_segment_offset(linear, _label_segment(args))
        instructions.append(
            {
                "file_offset": ins.address,
                "image_offset": ins.address - getattr(image, "header_bytes", 0),
                "linear": linear,
                "segment": segment,
                "offset": offset,
                "bytes": ins.bytes.hex(),
                "size": ins.size,
                "text": f"{ins.mnemonic} {ins.op_str}".strip(),
            }
        )
        if len(instructions) >= args.max_instructions:
            break

    return {
        "input": _input_record(args, data),
        "decoder": {
            "name": "capstone",
            "version": _capstone_version(),
            "arch": "x86",
            "mode": "16",
            "note": "independent of Ghidra's x86 language definitions",
        },
        "load_paragraph": args.load_paragraph,
        "instructions": instructions,
        "scope": (
            "bounded straight-line decode with no branch following, symbol "
            "assignment or program mutation; a decode is not evidence that the "
            "bytes are executable at runtime"
        ),
    }


def _capstone_version() -> str:
    import capstone  # noqa: PLC0415

    return getattr(capstone, "__version__", "unknown")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    number = lambda s: int(s, 0)  # noqa: E731

    def shared(p, *, interpretation: bool = False) -> None:
        p.add_argument(
            "--expect-sha256",
            help="refuse the input unless it has this digest",
        )
        if interpretation:
            p.add_argument(
                "--interpretation",
                choices=("com",),
                help="adopt the COM load convention for a headerless input",
            )

    identify_parser = sub.add_parser(
        "identify", help="classify COM or MZ/ZM by header evidence"
    )
    identify_parser.add_argument("path")
    shared(identify_parser, interpretation=True)
    identify_parser.set_defaults(handler=command_identify)

    blocks_parser = sub.add_parser(
        "blocks", help="reproduce the Ghidra 16-bit MZ loader block model"
    )
    blocks_parser.add_argument("path")
    blocks_parser.add_argument("--load-paragraph", type=number, default=DEFAULT_LOAD_PARAGRAPH)
    shared(blocks_parser, interpretation=True)
    blocks_parser.set_defaults(handler=command_blocks)

    map_parser = sub.add_parser("map", help="convert between file, image, linear and segment:offset")
    map_parser.add_argument("path")
    map_parser.add_argument("--file-offset", type=number)
    map_parser.add_argument("--linear", type=number)
    map_parser.add_argument(
        "--segment-offset",
        type=number,
        nargs=2,
        metavar=("SEGMENT", "OFFSET"),
    )
    map_parser.add_argument(
        "--segment",
        type=number,
        help="segment label to apply (0000h is a real choice, not a default)",
    )
    map_parser.add_argument("--load-paragraph", type=number, default=DEFAULT_LOAD_PARAGRAPH)
    shared(map_parser, interpretation=True)
    map_parser.set_defaults(handler=command_map)

    far_parser = sub.add_parser("far", help="classify a 4-byte off16:seg16 candidate")
    far_parser.add_argument("path")
    far_parser.add_argument("--offset", type=number, required=True)
    shared(far_parser)
    far_parser.set_defaults(handler=command_far)

    disasm_parser = sub.add_parser("disasm", help="bounded decode with an independent decoder")
    disasm_parser.add_argument("path")
    disasm_parser.add_argument("--file-offset", type=number)
    disasm_parser.add_argument("--image-offset", type=number)
    disasm_parser.add_argument("--length", type=number, required=True)
    disasm_parser.add_argument("--segment", type=number)
    disasm_parser.add_argument("--load-paragraph", type=number, default=DEFAULT_LOAD_PARAGRAPH)
    disasm_parser.add_argument("--max-instructions", type=number, default=256)
    shared(disasm_parser, interpretation=True)
    disasm_parser.set_defaults(handler=command_disasm)

    args = parser.parse_args(argv)
    if getattr(args, "load_paragraph", None) is not None:
        try:
            _segment(args.load_paragraph, "--load-paragraph")
            _segment(getattr(args, "segment", None), "--segment", allow_none=True)
        except DosImageError as exc:
            json.dump({"error": str(exc)}, sys.stderr)
            sys.stderr.write("\n")
            return 2
    try:
        result = args.handler(args)
    except (DosImageError, OSError) as exc:
        json.dump({"error": str(exc)}, sys.stderr)
        sys.stderr.write("\n")
        return 2
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
