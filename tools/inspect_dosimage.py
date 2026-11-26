"""Read-only DOS executable inspection and address mapping.

Every command prints JSON, including the input size and SHA-256. Output can
contain proprietary bytes: store it privately. Inputs are opened for reading
only; there is no write operation and no emulator, loader or GUI use.

Coordinate names follow ``deskmate_formats.dosimage``: *file* offsets index
the stored file, *image* offsets index the load image, and *linear* addresses
are ``16 * segment + offset``. A synthetic load paragraph turns an image
offset into an analysis address; it is never a guest address.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from deskmate_formats.dosimage import (
    DEFAULT_LOAD_PARAGRAPH,
    ComImage,
    DosImageError,
    MzImage,
    identify,
    linear_to_segment_offset,
    segment_offset_to_linear,
)


def _load(path: str) -> bytes:
    return Path(path).read_bytes()


def _image(data: bytes):
    if len(data) >= 2 and data[:2] == b"MZ":
        return MzImage.parse(data)
    return ComImage.parse(data)


def command_identify(args) -> dict:
    data = _load(args.path)
    result = identify(data)
    return result


def command_blocks(args) -> dict:
    data = _load(args.path)
    image = _image(data)
    blocks = image.loader_blocks(data, args.load_paragraph)
    return {
        "input": {
            "path": args.path,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        },
        "format": image.describe()["format"],
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
    data = _load(args.path)
    image = _image(data)
    result = {
        "input": {
            "path": args.path,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        },
        "format": image.describe()["format"],
        "load_paragraph": args.load_paragraph,
        "coordinates": [],
        "scope": (
            "explicit loader-arithmetic conversions; a segment:offset label is one "
            "valid labelling, not necessarily the runtime one"
        ),
    }

    if args.file_offset is not None:
        f = args.file_offset
        linear = image.file_to_linear(f, args.load_paragraph)
        segment, offset = linear_to_segment_offset(linear, args.segment or args.load_paragraph)
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
        segment, offset = linear_to_segment_offset(args.linear, args.segment or args.load_paragraph)
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
        pair = args.segment_offset
        segment, offset = pair
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
    data = _load(args.path)
    image = _image(data)
    if not isinstance(image, MzImage):
        raise DosImageError("far-pointer candidates require an MZ image")
    pointer = image.far_pointer_at(data, args.offset)
    payload = {
        "file_offset": pointer.file_offset,
        "offset_word": pointer.offset_word,
        "segment_word": pointer.segment_word,
        "segment_has_mz_relocation": pointer.segment_relocated,
        "resolved_image_offset": pointer.resolved_image_offset,
        "resolved_file_offset": None,
        "resolution": pointer.resolution,
        "scope": (
            "candidate pointer arithmetic; the caller still has to establish that "
            "the bytes are a pointer and what its target is"
        ),
    }
    if pointer.resolved_image_offset is not None:
        payload["resolved_file_offset"] = image.image_to_file(pointer.resolved_image_offset)
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
    data = _load(args.path)
    image = _image(data)
    starts = []

    if args.file_offset is not None:
        prefix = 0
        first = args.file_offset
    elif args.image_offset is not None:
        prefix = 0
        first = getattr(image, "header_bytes", 0) + args.image_offset
    else:
        raise DosImageError("supply --file-offset or --image-offset")

    if args.length <= 0:
        raise DosImageError("--length must be positive")
    if first < 0 or first + args.length > len(data):
        raise DosImageError("requested span is outside the input")

    md = _disassembler()
    instructions = []
    if md is None:
        return {
            "input": {
                "path": args.path,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            },
            "decoder": None,
            "instructions": [],
            "warning": (
                "no independent decoder is installed; install capstone to enable "
                "byte-level corroboration. Ghidra listing output is not a substitute"
            ),
        }

    for ins in md.disasm(data[first:first + args.length], first):
        linear = image.file_to_linear(ins.address, args.load_paragraph)
        segment, offset = linear_to_segment_offset(
            linear, args.segment or args.load_paragraph
        )
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
        "input": {
            "path": args.path,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        },
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

    identify_parser = sub.add_parser("identify", help="classify COM or MZ by header evidence")
    identify_parser.add_argument("path")
    identify_parser.set_defaults(handler=command_identify)

    blocks_parser = sub.add_parser(
        "blocks", help="reproduce the Ghidra 16-bit MZ loader block model"
    )
    blocks_parser.add_argument("path")
    blocks_parser.add_argument("--load-paragraph", type=number, default=DEFAULT_LOAD_PARAGRAPH)
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
    map_parser.add_argument("--segment", type=number, help="segment label to apply")
    map_parser.add_argument("--load-paragraph", type=number, default=DEFAULT_LOAD_PARAGRAPH)
    map_parser.set_defaults(handler=command_map)

    far_parser = sub.add_parser("far", help="classify a 4-byte off16:seg16 candidate")
    far_parser.add_argument("path")
    far_parser.add_argument("--offset", type=number, required=True)
    far_parser.set_defaults(handler=command_far)

    disasm_parser = sub.add_parser("disasm", help="bounded decode with an independent decoder")
    disasm_parser.add_argument("path")
    disasm_parser.add_argument("--file-offset", type=number)
    disasm_parser.add_argument("--image-offset", type=number)
    disasm_parser.add_argument("--length", type=number, required=True)
    disasm_parser.add_argument("--segment", type=number)
    disasm_parser.add_argument("--load-paragraph", type=number, default=DEFAULT_LOAD_PARAGRAPH)
    disasm_parser.add_argument("--max-instructions", type=number, default=256)
    disasm_parser.set_defaults(handler=command_disasm)

    args = parser.parse_args(argv)
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
