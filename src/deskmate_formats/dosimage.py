"""DOS executable structure and address mapping.

Standard-library only. This module reads DOS COM and MZ images and converts
between the coordinate systems that historical 16-bit analysis keeps
conflating:

``file``
    Byte position in the stored file, including any MZ header. This is the
    only coordinate that survives on disk without assumptions.
``image``
    Byte position relative to the first byte of the load image
    (``file - header_bytes``). For a COM image ``image == file``.
``linear``
    ``16 * segment + offset``. A synthetic analysis address adds an explicit
    load paragraph: ``16 * load_paragraph + image_offset``.
``segment:offset``
    A 16-bit real-mode pair. The pair that labels a byte in a disassembly is
    not unique: any segment whose 64 KiB window covers the linear address
    labels it too. Only an observed loader establishes the *runtime* pair.

Nothing here infers a runtime load segment, an initial DS (MZ has no DS
field), a function boundary, or the semantics of an indirect call. Those
require execution observation or reviewed instruction evidence.

Both historical executable signatures are accepted: ``MZ`` and its mirror
image ``ZM`` (some linkers emitted the two bytes reversed). The signature is
reported so a reader can see which one the stored bytes carry; it does not
change any arithmetic.

A COM reading loads at ``segment:0100h``, so at most ``0xFF00`` bytes are
representable at 16-bit offsets. That bound is enforced for an explicit COM
interpretation instead of silently accepting an image it cannot address.
"""
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field

__all__ = [
    "DEFAULT_LOAD_PARAGRAPH",
    "MAX_COM_BYTES",
    "MZ_SIGNATURES",
    "ComImage",
    "DosImageError",
    "FarPointer",
    "MzImage",
    "Relocation",
    "identify",
    "linear_to_segment_offset",
    "segment_offset_to_linear",
]


class DosImageError(ValueError):
    """Raised when the stored bytes contradict the claimed DOS image format."""


#: Synthetic analysis base used by this project's Ghidra imports. It is an
#: analysis convention, never a guest address.
DEFAULT_LOAD_PARAGRAPH = 0x1000

_MZ_HEADER_MIN = 28

#: Executable signatures that begin a standard DOS relocatable image. ``ZM``
#: is the same 14-word header with the two signature bytes reversed.
MZ_SIGNATURES = (b"MZ", b"ZM")

#: Largest load image a COM program can address: offsets 0100h-FFFFh.
MAX_COM_BYTES = 0x10000 - 0x100


def segment_offset_to_linear(segment: int, offset: int) -> int:
    """Return ``16 * segment + offset`` for a real-mode pair."""
    if not 0 <= segment <= 0xFFFF or not 0 <= offset <= 0xFFFF:
        raise DosImageError("segment and offset must be 16-bit values")
    return (segment << 4) + offset


def linear_to_segment_offset(linear: int, segment: int) -> tuple[int, int]:
    """Label a linear address with an explicit segment, if it is in range.

    The result is one valid labelling, not the original one. A caller asking
    for the runtime pair must supply an observed segment.
    """
    base = segment << 4
    if not base <= linear < base + 0x10000:
        raise DosImageError(
            f"linear {linear:#07x} is outside segment {segment:04x}'s 64 KiB window"
        )
    return segment, linear - base


@dataclass(frozen=True)
class Relocation:
    """One standard MZ relocation-table entry."""

    index: int
    table_offset: int
    segment: int
    offset: int
    file_offset: int
    image_offset: int
    original_word: int

    @property
    def image_relative_offset(self) -> int:
        """Offset of the stored word from the start of the *load image*.

        Deliberately not called a linear address: this is an image offset, and
        it becomes a linear address only after a load paragraph is chosen.
        """
        return self.image_offset


@dataclass(frozen=True)
class FarPointer:
    """A 16-bit ``offset:segment`` word pair read from the image.

    ``resolved_file_offset`` is set only when the segment word carries an MZ
    relocation, which is the only case where this image's loader is known to
    contribute the load paragraph. An unrelocated pair may name another
    segment, another module, or unresolved data.
    """

    file_offset: int
    offset_word: int
    segment_word: int
    segment_relocated: bool
    resolved_image_offset: int | None
    resolution: str


@dataclass(frozen=True)
class MzImage:
    """A parsed standard DOS MZ executable image."""

    size: int
    sha256: str
    header_bytes: int
    declared_file_bytes: int
    pages: int
    last_page_bytes: int
    min_alloc_paragraphs: int
    max_alloc_paragraphs: int
    initial_ss: int
    initial_sp: int
    checksum: int
    entry_cs: int
    entry_ip: int
    relocation_table_offset: int
    signature: bytes = b"MZ"
    relocations: tuple[Relocation, ...] = field(default_factory=tuple)

    # -- construction ----------------------------------------------------
    @classmethod
    def parse(cls, data: bytes) -> "MzImage":
        if len(data) < _MZ_HEADER_MIN:
            raise DosImageError("input is shorter than a DOS MZ header")
        if data[:2] not in MZ_SIGNATURES:
            raise DosImageError(
                "expected an MZ or ZM signature; neither is present, so the "
                "input carries no DOS executable header"
            )
        signature = data[:2]
        (
            _sig,
            last_page,
            pages,
            reloc_count,
            header_paragraphs,
            min_alloc,
            max_alloc,
            initial_ss,
            initial_sp,
            checksum,
            entry_ip,
            entry_cs,
            reloc_table,
            _overlay,
        ) = struct.unpack_from("<2s13H", data)
        if pages == 0:
            raise DosImageError("MZ page count is zero")
        if last_page > 511:
            raise DosImageError("MZ last-page byte count exceeds 511")
        declared = (pages - 1) * 512 + (last_page or 512)
        header = header_paragraphs * 16
        if header < _MZ_HEADER_MIN:
            raise DosImageError("MZ header paragraph count is too small")
        if declared < header:
            raise DosImageError("MZ declared size is smaller than its header")
        if declared > len(data):
            raise DosImageError(
                f"MZ declares {declared} bytes but the file holds {len(data)}"
            )
        if reloc_table < _MZ_HEADER_MIN or reloc_table > header:
            raise DosImageError("MZ relocation table starts outside the header")
        if reloc_table + reloc_count * 4 > header:
            raise DosImageError("MZ relocation table extends outside the header")

        relocations = []
        seen_sites: set[int] = set()
        for index in range(reloc_count):
            table_offset = reloc_table + index * 4
            within, segment = struct.unpack_from("<HH", data, table_offset)
            image_offset = (segment << 4) + within
            if image_offset < 0 or image_offset + 2 > declared - header:
                raise DosImageError(
                    f"MZ relocation {index} targets a word outside the image"
                )
            if image_offset in seen_sites:
                raise DosImageError(
                    f"MZ relocation {index} duplicates relocation site {image_offset:#x}"
                )
            seen_sites.add(image_offset)
            relocations.append(
                Relocation(
                    index=index,
                    table_offset=table_offset,
                    segment=segment,
                    offset=within,
                    file_offset=header + image_offset,
                    image_offset=image_offset,
                    original_word=struct.unpack_from("<H", data, header + image_offset)[0],
                )
            )

        return cls(
            size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            header_bytes=header,
            declared_file_bytes=declared,
            pages=pages,
            last_page_bytes=last_page,
            min_alloc_paragraphs=min_alloc,
            max_alloc_paragraphs=max_alloc,
            initial_ss=initial_ss,
            initial_sp=initial_sp,
            checksum=checksum,
            entry_cs=entry_cs,
            entry_ip=entry_ip,
            relocation_table_offset=reloc_table,
            signature=signature,
            relocations=tuple(relocations),
        )

    # -- structural facts ------------------------------------------------
    @property
    def image_bytes(self) -> int:
        return self.declared_file_bytes - self.header_bytes

    @property
    def trailing_bytes(self) -> int:
        """Bytes after the declared load image; an overlay is plausible, not proved."""
        return self.size - self.declared_file_bytes

    @property
    def overlay(self) -> dict:
        """Classify the bytes past the declared load image without naming them.

        Header arithmetic alone cannot distinguish an appended overlay, an
        embedded archive, alignment padding or a truncated/garbage tail. This
        reports the count and the uncertainty rather than a verdict.
        """
        if self.trailing_bytes == 0:
            return {
                "status": "none",
                "trailing_bytes": 0,
                "note": "the stored file ends at the declared load image",
            }
        return {
            "status": "possible",
            "trailing_bytes": self.trailing_bytes,
            "note": (
                "bytes follow the declared load image. An appended overlay, an "
                "embedded archive, linker padding and a corrupt tail all look "
                "identical here; identifying one requires separate evidence"
            ),
        }

    def header_warnings(self) -> list[str]:
        """Report internally contradictory or unusual header values.

        These are observations about the header words, not loader verdicts.
        A warning marks a value a reader should look at; it does not mean DOS
        refuses the image, and several historical linkers emitted them.
        """
        warnings: list[str] = []
        if self.image_bytes <= 0:
            warnings.append("the declared load image is empty")
        if self.entry_image_offset >= max(self.image_bytes, 1):
            warnings.append(
                "the declared entry point lies outside the declared load image"
            )
        if self.min_alloc_paragraphs > self.max_alloc_paragraphs:
            warnings.append(
                "declared minimum allocation exceeds declared maximum allocation"
            )
        if self.max_alloc_paragraphs == 0:
            warnings.append(
                "declared maximum allocation is zero, which contradicts a "
                "loadable image"
            )
        sites = sorted(r.image_offset for r in self.relocations)
        for earlier, later in zip(sites, sites[1:]):
            if later - earlier < 2:
                warnings.append(
                    "relocation sites "
                    f"{earlier:#06x} and {later:#06x} name overlapping words"
                )
                break
        stack_top = (self.initial_ss << 4) + self.initial_sp
        if self.initial_ss and stack_top > self.image_bytes:
            warnings.append(
                "initial SS:SP lies beyond the initialized image, so the stack "
                "is expected in uninitialized memory allocated at load time "
                "(common; not a contradiction)"
            )
        return warnings

    @property
    def entry_image_offset(self) -> int:
        return (self.entry_cs << 4) + self.entry_ip

    @property
    def entry_file_offset(self) -> int:
        return self.header_bytes + self.entry_image_offset

    @property
    def relocation_site_segments(self) -> tuple[int, ...]:
        """Segments that contain relocation sites (where words are stored)."""
        return tuple(sorted({r.segment for r in self.relocations}))

    @property
    def relocated_segments(self) -> tuple[int, ...]:
        """Segment values that the relocated words actually name."""
        return tuple(sorted({r.original_word for r in self.relocations}))


    # -- coordinate conversion -------------------------------------------
    def file_to_image(self, file_offset: int) -> int:
        if not self.header_bytes <= file_offset < self.declared_file_bytes:
            if 0 <= file_offset < self.header_bytes:
                raise DosImageError(
                    f"file offset {file_offset:#x} is inside the MZ header "
                    f"(0..{self.header_bytes - 1:#x}), not the load image. Image "
                    "offsets start at 0, which is file offset "
                    f"{self.header_bytes:#x}"
                )
            raise DosImageError(
                f"file offset {file_offset:#x} is outside the declared image "
                f"(file offsets {self.header_bytes:#x}.."
                f"{self.declared_file_bytes - 1:#x})"
            )
        return file_offset - self.header_bytes

    def image_to_file(self, image_offset: int) -> int:
        if not 0 <= image_offset < self.image_bytes:
            raise DosImageError(
                f"image offset {image_offset:#x} is outside the stored image"
            )
        return self.header_bytes + image_offset

    def file_to_linear(
        self, file_offset: int, load_paragraph: int = DEFAULT_LOAD_PARAGRAPH
    ) -> int:
        return (load_paragraph << 4) + self.file_to_image(file_offset)

    def linear_to_file(
        self, linear: int, load_paragraph: int = DEFAULT_LOAD_PARAGRAPH
    ) -> int:
        image = linear - (load_paragraph << 4)
        if not 0 <= image < self.image_bytes:
            raise DosImageError(
                f"linear {linear:#07x} is outside the image at load {load_paragraph:04x}"
            )
        return self.header_bytes + image

    def entry_linear(self, load_paragraph: int = DEFAULT_LOAD_PARAGRAPH) -> int:
        return (load_paragraph << 4) + self.entry_image_offset

    def runtime_linear(
        self, file_offset: int, observed_load_segment: int
    ) -> int:
        """Guest linear address under an *observed* loader load segment."""
        return (observed_load_segment << 4) + self.file_to_image(file_offset)

    # -- loader-block model ----------------------------------------------
    def loader_segments(self, load_paragraph: int = DEFAULT_LOAD_PARAGRAPH) -> list[int]:
        """Segments a 16-bit DOS loader must establish for this image.

        A relocation-table entry names where a segment word *lives*; the word
        itself holds the image-relative segment the loader must adjust. The
        adjusted values, the load segment and the entry segment form the set a
        loader creates memory blocks for. This is the loader's view, not the
        program's own segmentation.
        """
        segments = {load_paragraph + r.original_word for r in self.relocations}
        segments.add(load_paragraph)
        if self.entry_cs:
            segments.add(load_paragraph + self.entry_cs)
        return sorted(segments)

    def loader_blocks(
        self,
        data: bytes,
        load_paragraph: int = DEFAULT_LOAD_PARAGRAPH,
    ) -> list[dict]:
        """Reproduce the memory blocks Ghidra 12.1.4 and 12.2 MZ loaders create.

        Modelled from ``MzLoader.processMemoryBlocks`` and
        ``adjustSegmentStarts``: one initialized block per loader segment,
        starting at ``segment:0000`` and running to the next segment, then a
        backward scan of the block's first 16 bytes for a far return (``CB``)
        that moves the split point forward and joins the head to the previous
        block. ``CODE_<n>u`` and ``DATA`` are uninitialized and hold no file
        bytes.

        The block origins are loader artifacts. A segment:offset label in a
        Ghidra listing therefore reflects the relocation table and this
        adjustment, not the program's own segmentation.
        """
        starts = []
        for segment in self.loader_segments(load_paragraph):
            offset = (segment - load_paragraph) << 4
            if 0 <= offset < self.image_bytes:
                starts.append((segment, offset))
        starts.sort(key=lambda item: item[1])

        blocks = []
        for index, (segment, start) in enumerate(starts):
            if index + 1 < len(starts):
                size = starts[index + 1][1] - start
            else:
                size = self.image_bytes - start
            if size <= 0:
                continue
            file_start = self.header_bytes + start
            available = max(0, min(size, self.declared_file_bytes - file_start))
            blocks.append(
                {
                    "name": f"CODE_{index}",
                    "segment": segment,
                    "image_offset": start,
                    "file_offset": file_start,
                    "size": size,
                    "initialized_size": available,
                    "initialized": available > 0,
                    "uninitialized_size": size - available,
                }
            )

        # adjustSegmentStarts: highest far return within the first 16 bytes.
        # Bytes move from the head of one block to the tail of the previous
        # block, so the previous block's uninitialized tail is unchanged and
        # can never be driven negative.
        for index in range(1, len(blocks)):
            block = blocks[index]
            if block["initialized_size"] <= 0:
                continue
            limit = 15 if block["initialized_size"] > 16 else block["initialized_size"] - 2
            for probe in range(limit, -1, -1):
                byte_index = block["file_offset"] + probe
                if byte_index >= len(data):
                    continue
                if data[byte_index] == 0xCB:
                    moved = probe + 1
                    previous = blocks[index - 1]
                    previous["size"] += moved
                    previous["initialized_size"] += moved
                    block["image_offset"] += moved
                    block["file_offset"] += moved
                    block["size"] -= moved
                    block["initialized_size"] -= moved
                    break

        for block in blocks:
            block["uninitialized_size"] = block["size"] - block["initialized_size"]
            if block["uninitialized_size"] < 0 or block["initialized_size"] < 0:
                raise DosImageError(
                    "loader block sizes are inconsistent at image offset "
                    f"{block['image_offset']:#x}"
                )
            base = (load_paragraph << 4) + block["image_offset"]
            segment, offset = divmod(base, 16)
            block["start"] = f"{segment:04x}:{offset:04x}"
            block["linear_start"] = base
            block["linear_end"] = base + block["size"] - 1
            block.pop("segment", None)
        return blocks

    # -- data helpers ----------------------------------------------------
    def far_pointer_file_offset(self, pointer: FarPointer) -> int | None:
        """Map a resolved far pointer into this file, or None.

        A pair can resolve outside the stored image (another segment, an
        overlay, or unrelated data). Such a pointer is still reported, but it
        has no file offset and must not be given one.
        """
        if pointer.resolved_image_offset is None:
            return None
        if not 0 <= pointer.resolved_image_offset < self.image_bytes:
            return None
        return self.header_bytes + pointer.resolved_image_offset

    def far_pointer_at(self, data: bytes, file_offset: int) -> FarPointer:
        """Read an explicit 4-byte off16:seg16 candidate and classify it."""
        if file_offset < 0 or file_offset + 4 > len(data):
            raise DosImageError("far-pointer candidate extends past the input")
        within, segment = struct.unpack_from("<HH", data, file_offset)
        relocated = any(r.file_offset == file_offset + 2 for r in self.relocations)
        target = (segment << 4) + within if relocated else None
        if not relocated:
            resolution = (
                "segment word has no MZ relocation; the loader does not adjust it, "
                "so this image's base cannot be applied"
            )
        elif not 0 <= target < self.image_bytes:
            resolution = (
                "relocated pair resolves outside the stored image "
                "(possible overlay or cross-module reference)"
            )
        else:
            resolution = "relocated pair resolves inside the stored image"

        return FarPointer(
            file_offset=file_offset,
            offset_word=within,
            segment_word=segment,
            segment_relocated=relocated,
            resolved_image_offset=target,
            resolution=resolution,
        )

    def describe(self) -> dict:
        return {
            "format": "mz",
            "signature": self.signature.decode("ascii", "replace"),
            "size": self.size,
            "sha256": self.sha256,
            "header_bytes": self.header_bytes,
            "declared_file_bytes": self.declared_file_bytes,
            "trailing_bytes": self.trailing_bytes,
            "image_bytes": self.image_bytes,
            "pages": self.pages,
            "last_page_bytes": self.last_page_bytes,
            "min_alloc_paragraphs": self.min_alloc_paragraphs,
            "max_alloc_paragraphs": self.max_alloc_paragraphs,
            "entry_cs": self.entry_cs,
            "entry_ip": self.entry_ip,
            "entry_image_offset": self.entry_image_offset,
            "entry_file_offset": self.entry_file_offset,
            "initial_ss": self.initial_ss,
            "initial_sp": self.initial_sp,
            "checksum": self.checksum,
            "relocation_table_offset": self.relocation_table_offset,
            "relocation_count": len(self.relocations),
            "relocation_site_segments": list(self.relocation_site_segments),
            "relocated_segments": list(self.relocated_segments),
            "overlay": self.overlay,
            "header_warnings": self.header_warnings(),
            "relocations": [
                {
                    "index": r.index,
                    "segment": r.segment,
                    "offset": r.offset,
                    "file_offset": r.file_offset,
                    "image_offset": r.image_offset,
                    "original_word": r.original_word,
                }
                for r in self.relocations
            ],
            "scope": (
                "standard DOS MZ/ZM arithmetic and declared sizes only; no runtime "
                "load segment, initial DS, overlay identity, function boundary or "
                "API semantics are implied. A relocation site is where a word is "
                "stored; the relocated value is the segment that word names, and "
                "those are different facts"
            ),
        }


@dataclass(frozen=True)
class ComImage:
    """A DOS COM image: a raw load image with no header and IP starting at 0x100."""

    size: int
    sha256: str

    @classmethod
    def parse(cls, data: bytes) -> "ComImage":
        if not data:
            raise DosImageError("empty input")
        if data[:2] in MZ_SIGNATURES:
            raise DosImageError(
                "input carries an MZ/ZM signature, so the COM reading is not "
                "available; parse it as a relocatable image instead"
            )
        if len(data) > MAX_COM_BYTES:
            raise DosImageError(
                f"a COM image loads at offset 0100h, so at most "
                f"{MAX_COM_BYTES} bytes ({MAX_COM_BYTES:#06x}) are addressable "
                f"at 16-bit offsets; this input holds {len(data)}"
            )
        return cls(size=len(data), sha256=hashlib.sha256(data).hexdigest())

    @property
    def image_bytes(self) -> int:
        return self.size

    @property
    def max_representable_bytes(self) -> int:
        """Addressable extent of a COM load image: 0100h..FFFFh."""
        return MAX_COM_BYTES

    @property
    def entry_ip(self) -> int:
        return 0x100

    @property
    def entry_image_offset(self) -> int:
        return self.entry_ip

    def file_to_linear(
        self, file_offset: int, load_paragraph: int = DEFAULT_LOAD_PARAGRAPH
    ) -> int:
        if not 0 <= file_offset < self.size:
            raise DosImageError(f"file offset {file_offset:#x} is outside the image")
        return (load_paragraph << 4) + self.entry_ip + file_offset

    def linear_to_file(
        self, linear: int, load_paragraph: int = DEFAULT_LOAD_PARAGRAPH
    ) -> int:
        image = linear - (load_paragraph << 4) - self.entry_ip
        if not 0 <= image < self.size:
            raise DosImageError(
                f"linear {linear:#07x} is outside the image at load {load_paragraph:04x}"
            )
        return image

    def loader_blocks(
        self,
        data: bytes,
        load_paragraph: int = DEFAULT_LOAD_PARAGRAPH,
    ) -> list[dict]:
        """A COM image is one initialized block with IP starting at 0x100."""
        segment = load_paragraph + (self.entry_ip >> 4)
        absolute = (load_paragraph << 4) + self.entry_ip
        return [
            {
                "name": "CODE_0",
                "start": f"{segment:04x}:{absolute - (segment << 4):04x}",
                "image_offset": 0,
                "file_offset": 0,
                "size": self.size,
                "initialized_size": self.size,
                "initialized": True,
                "uninitialized_size": 0,
                "linear_start": absolute,
                "linear_end": absolute + self.size - 1,
            }
        ]

    def describe(self) -> dict:
        return {
            "format": "com",
            "size": self.size,
            "sha256": self.sha256,
            "header_bytes": 0,
            "declared_file_bytes": self.size,
            "trailing_bytes": 0,
            "image_bytes": self.size,
            "max_representable_bytes": self.max_representable_bytes,
            "entry_ip": self.entry_ip,
            "entry_image_offset": self.entry_image_offset,
            "initial_ss": None,
            "initial_sp": None,
            "relocation_count": 0,
            "relocations": [],
            "relocation_site_segments": [],
            "relocated_segments": [],
            "scope": (
                "COM images have no header or relocation table; a COM program may "
                "still be a DOS 3 EXE-format carrier, which this parser does not claim "
                "to detect. The load extent is the representable 16-bit one, not a "
                "statement about the stack or about free memory at run time"
            ),
        }


def identify(data: bytes, interpretation: str | None = None) -> dict:
    """Classify an image from standard header evidence, or an explicit claim.

    An MZ image is identified by its signature. Anything else has no header
    and therefore **no structural signature at all**: every byte sequence is a
    valid COM load image, so a COM reading is a chosen interpretation, not an
    observation. Without ``interpretation="com"`` the result is an
    unqualified candidate and callers should not map addresses through it.
    """
    if len(data) >= 2 and data[:2] in MZ_SIGNATURES:
        return MzImage.parse(data).describe()
    if interpretation == "com":
        result = ComImage.parse(data).describe()
        result["interpretation"] = "explicit"
        return result
    if interpretation not in (None, "auto"):
        raise DosImageError(f"unsupported interpretation: {interpretation}")
    return {
        "format": "unknown",
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "com_candidate": True,
        "header_bytes": None,
        "trailing_bytes": None,
        "relocation_count": 0,
        "relocations": [],
        "relocation_site_segments": [],
        "relocated_segments": [],
        "interpretation": "none",
        "reason": (
            "no MZ signature and no other header evidence; a COM image has no "
            "header or magic number, so this classification cannot be made from "
            "structure alone"
        ),
        "scope": (
            "unqualified candidate only. Pass interpretation='com' to adopt the "
            "COM load convention (IP=0100h), which is an assumption about the "
            "file, not a finding"
        ),
    }
