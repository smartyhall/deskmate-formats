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
"""
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field

__all__ = [
    "DEFAULT_LOAD_PARAGRAPH",
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
    def linear_offset(self) -> int:
        """Linear offset from the start of the load image of the adjusted word."""
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
    relocations: tuple[Relocation, ...] = field(default_factory=tuple)

    # -- construction ----------------------------------------------------
    @classmethod
    def parse(cls, data: bytes) -> "MzImage":
        if len(data) < _MZ_HEADER_MIN:
            raise DosImageError("input is shorter than a DOS MZ header")
        if data[:2] != b"MZ":
            raise DosImageError("expected an MZ signature")
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
            raise DosImageError(
                f"file offset {file_offset:#x} is outside the stored image"
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
        """Reproduce the memory blocks Ghidra 12.1.4's MZ loader creates.

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
                    previous["uninitialized_size"] -= moved
                    block["image_offset"] += moved
                    block["file_offset"] += moved
                    block["size"] -= moved
                    block["initialized_size"] -= moved
                    break

        for block in blocks:
            base = (load_paragraph << 4) + block["image_offset"]
            segment, offset = divmod(base, 16)
            block["start"] = f"{segment:04x}:{offset:04x}"
            block["linear_start"] = base
            block["linear_end"] = base + block["size"] - 1
            block.pop("segment", None)
        return blocks

    # -- data helpers ----------------------------------------------------
    def far_pointer_at(self, data: bytes, file_offset: int) -> FarPointer:
        """Read an explicit 4-byte off16:seg16 candidate and classify it."""
        if not 0 <= file_offset or file_offset + 4 > len(data):
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
                "standard DOS MZ arithmetic and declared sizes only; no runtime "
                "load segment, initial DS, overlay identity, function boundary or "
                "API semantics are implied"
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
        if data[:2] in (b"MZ", b"ZM"):
            raise DosImageError("input carries an MZ signature")
        return cls(size=len(data), sha256=hashlib.sha256(data).hexdigest())

    @property
    def image_bytes(self) -> int:
        return self.size

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
                "to detect"
            ),
        }


def identify(data: bytes) -> dict:
    """Classify an image by standard header evidence only."""
    if len(data) >= 2 and data[:2] in (b"MZ", b"ZM"):
        return MzImage.parse(data).describe()
    if len(data) >= 2 and data[:2] == b"ZM":
        raise DosImageError("ZM-prefixed images are not standard DOS MZ images")
    return ComImage.parse(data).describe()
