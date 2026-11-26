"""Decode PC sector-image containers into explicit, provenance-bearing sectors.

This module keeps four layers apart on purpose:

* the *container* (IMD, TeleDisk, CopyQM) and its encoding of sector data;
* the *recording* attributes a container may describe (data rate, encoding);
* the *geometry* implied by the container or by a filesystem boot sector;
* the *filesystem*, which is never interpreted here.

Decoding produces ``Sector`` records and an optional normalised logical-block
view. A normalised image is a derivative: ``LbaImage.missing`` names every
logical sector that no input supplied, so a caller can never mistake a
zero-filled gap for verified data.

Teledisk's "advanced" variant compresses the whole post-header stream with an
LZSS/Huffman coder. It is recognised and its header metadata is reported, but
its payload is not decoded here; the record stays explicitly unsupported.

Disk Copy Fast (``.DCF``) has no published byte-level specification. It is
deliberately absent rather than guessed from file size or extension.
"""

from dataclasses import dataclass, field
from pathlib import Path
from struct import unpack_from


IMD_MAGIC = b'IMD '
TD0_SIGNATURES = (b'TD', b'td')
COPYQM_SIGNATURE = b'CQ\x14'
COPYQM_HEADER_BYTES = 133
SECTOR_SIZES = (128, 256, 512, 1024, 2048, 4096, 8192)

# IMD sector-data status bytes: 0 = absent, odd = raw, even = fill byte.
IMD_STATUS = {
    0x00: 'missing',
    0x01: 'ok', 0x02: 'ok-fill',
    0x03: 'deleted-data', 0x04: 'deleted-data-fill',
    0x05: 'read-error', 0x06: 'read-error-fill',
    0x07: 'deleted-read-error', 0x08: 'deleted-read-error-fill',
}
IMD_RAW_STATUS = frozenset({0x01, 0x03, 0x05, 0x07})

# TeleDisk drive types as documented for the image header.
TD0_DRIVE_GEOMETRY = {
    1: (40, 2, 9), 2: (80, 2, 15), 3: (80, 2, 9), 4: (80, 2, 18),
}
TD0_DATA_RATES = {0: '250 kbps', 1: '300 kbps', 2: '500 kbps'}

# Standard floppy geometries, used only when no boot sector describes the media.
STANDARD_GEOMETRY = {
    160 * 1024: (40, 1, 8), 180 * 1024: (40, 1, 9),
    320 * 1024: (40, 2, 8), 360 * 1024: (40, 2, 9),
    640 * 1024: (80, 2, 8), 720 * 1024: (80, 2, 9),
    1200 * 1024: (80, 2, 15), 1440 * 1024: (80, 2, 18),
    2880 * 1024: (80, 2, 36),
}


@dataclass(frozen=True)
class Bounds:
    """Input and member limits applied while decoding a container."""

    input_bytes: int = 512 * 1024 * 1024
    sectors: int = 200_000
    sector_bytes: int = 8192

    def __post_init__(self):
        if min(self.input_bytes, self.sectors, self.sector_bytes) <= 0:
            raise ValueError('sector-image bounds must be positive')


@dataclass(frozen=True)
class Geometry:
    """Declared or observed media geometry. Any field may be unknown (None)."""

    cylinders: int | None
    heads: int | None
    sectors_per_track: int | None
    sector_size: int | None

    @property
    def total_sectors(self):
        values = (self.cylinders, self.heads, self.sectors_per_track)
        return None if any(value is None for value in values) else (
            self.cylinders * self.heads * self.sectors_per_track)


@dataclass(frozen=True)
class Sector:
    """One sector exactly as the container presented it."""

    cylinder: int
    head: int
    number: int
    size: int
    data: bytes | None
    status: str


@dataclass
class Volume:
    """A decoded container: geometry, sectors and honest status."""

    container: str
    geometry: Geometry
    sectors: list[Sector] = field(default_factory=list)
    status: str = 'ok'
    detail: str | None = None
    warnings: tuple[str, ...] = ()
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class LbaImage:
    """A normalised logical-block derivative with its gaps named explicitly."""

    data: bytes
    sector_size: int
    total_sectors: int
    written: int
    missing: tuple[int, ...]
    conflicts: tuple[int, ...]
    status: str


class _Truncated(Exception):
    """Raised when a container ends before a declared structure is complete."""


class _Cursor:
    __slots__ = ('data', 'position')

    def __init__(self, data, position=0):
        self.data = data
        self.position = position

    def take(self, count):
        end = self.position + count
        if count < 0 or end > len(self.data):
            raise _Truncated(f'need {count} bytes at {self.position}')
        chunk = self.data[self.position:end]
        self.position = end
        return chunk

    def byte(self):
        return self.take(1)[0]

    def remaining(self):
        return len(self.data) - self.position


def identify(data: bytes) -> str | None:
    """Classify a sector-image container from its header, without an extension.

    Each test requires a structural invariant, not just a magic string, so an
    ordinary text file cannot be mistaken for a disk image.
    """
    if data.startswith(IMD_MAGIC):
        # The preamble is "IMD <version>: <timestamp>" followed by free-form
        # comment text, so require the identifying line rather than only the tag.
        line_end = data.find(b'\r\n')
        if 0 < line_end <= 64 and b':' in data[:line_end]:
            return 'imd'
    if (len(data) >= 12 and data[:1] in (b'T', b't') and data[1:2] in (b'D', b'd')
            and 0x10 <= data[4] <= 0x2F):
        # 'TD' is the ordinary image and 'td' the advanced-compression variant.
        # Byte 3 is a *volume set* identifier, not a checksum: three genuine
        # TeleDisk images carry 0x42, 0x43 and 0x2E there, so a sum test would
        # reject every real file. The header CRC at offset 10 is the actual
        # integrity field and is verified by the reader instead.
        return 'td0-advanced' if data[:1] == b't' else 'td0'
    if (len(data) >= COPYQM_HEADER_BYTES and data[:3] == COPYQM_SIGNATURE
            and sum(data[:COPYQM_HEADER_BYTES]) & 0xFF == 0):
        return 'copyqm'
    return None


def _geometry_from_bpb(boot: bytes):
    """Read a plausible BIOS parameter block. Returns Geometry or None."""
    if len(boot) < 32 or boot[0] not in (0xE9, 0xEB):
        return None
    sector_size, sectors_per_cluster, _, _, _, total16, media, _, spt, heads = \
        unpack_from('<HBHBHHBHHH', boot, 11)
    if sector_size not in SECTOR_SIZES or sectors_per_cluster not in (1, 2, 4, 8, 16, 32, 64, 128):
        return None
    if not spt or not heads:
        return None
    total = total16 or unpack_from('<I', boot, 32)[0]
    if not total:
        return None
    cylinders = total // (spt * heads)
    if not 1 <= cylinders <= 1024:
        return None
    return Geometry(cylinders, heads, spt, sector_size)


def raw_geometry(size: int, boot: bytes | None = None):
    """Describe a raw (``.img``/``.ima``) image.

    A boot sector is authoritative when present. Otherwise only the classic
    floppy capacities are named; any other length returns an empty geometry
    rather than an invented one.
    """
    if boot:
        declared = _geometry_from_bpb(boot)
        if declared is not None:
            return declared, 'bpb'
    standard = STANDARD_GEOMETRY.get(size)
    if standard:
        return Geometry(*standard, 512), 'standard-capacity'
    return Geometry(None, None, None, None), 'unknown'


def _imd(data, bounds):
    terminator = data.find(b'\x1a')
    if terminator < 0:
        return Volume('imd', Geometry(None, None, None, None), status='failed',
                      detail='missing-preamble-terminator')
    preamble = data[:terminator].decode('cp437', 'replace').split('\r\n')
    cursor = _Cursor(data, terminator + 1)
    sectors = []
    warnings = []
    max_cylinder = max_head = None
    spt = None
    size_seen = None
    status, detail = 'ok', None
    while cursor.remaining():
        if len(sectors) >= bounds.sectors:
            status, detail = 'limited', 'sector-limit'
            break
        try:
            mode, cylinder, head, count, size_code = (
                cursor.byte(), cursor.byte(), cursor.byte(), cursor.byte(), cursor.byte())
        except _Truncated:
            status, detail = 'partial', 'truncated-track-header'
            break
        if mode > 5:
            status, detail = 'failed', f'unknown-imd-mode-{mode}'
            break
        if not count:
            status, detail = 'failed', 'empty-track'
            break
        cylinder_map_present = bool(head & 0x80)
        head_map_present = bool(head & 0x40)
        physical_head = head & 0x01
        if head & 0x3C:
            warnings.append('undefined-head-bits-set')
        try:
            numbers = list(cursor.take(count))
            cylinder_map = list(cursor.take(count)) if cylinder_map_present else None
            head_map = list(cursor.take(count)) if head_map_present else None
            if size_code == 0xFF:
                raw_sizes = cursor.take(count * 2)
                sizes = [unpack_from('<H', raw_sizes, index * 2)[0] for index in range(count)]
            elif size_code < len(SECTOR_SIZES):
                sizes = [SECTOR_SIZES[size_code]] * count
            else:
                status, detail = 'failed', f'unknown-sector-size-code-{size_code}'
                break
        except _Truncated:
            status, detail = 'partial', 'truncated-track-map'
            break
        if any(size <= 0 or size > bounds.sector_bytes for size in sizes):
            status, detail = 'failed', 'sector-size-out-of-range'
            break
        truncated = False
        for index in range(count):
            try:
                marker = cursor.byte()
            except _Truncated:
                status, detail = 'partial', 'truncated-sector-data'
                truncated = True
                break
            if marker not in IMD_STATUS:
                status, detail = 'failed', f'unknown-imd-sector-status-{marker}'
                truncated = True
                break
            size = sizes[index]
            payload = None
            sector_status = IMD_STATUS[marker]
            try:
                if marker == 0x00:
                    pass
                elif marker in IMD_RAW_STATUS:
                    payload = cursor.take(size)
                else:
                    payload = cursor.take(1) * size
            except _Truncated:
                status, detail = 'partial', 'truncated-sector-data'
                truncated = True
                break
            sectors.append(Sector(
                cylinder_map[index] if cylinder_map else cylinder,
                head_map[index] if head_map else physical_head,
                numbers[index], size, payload, sector_status))
        if truncated:
            break
        max_cylinder = cylinder if max_cylinder is None else max(max_cylinder, cylinder)
        max_head = physical_head if max_head is None else max(max_head, physical_head)
        spt = count if spt is None else max(spt, count)
        size_seen = sizes[0] if size_seen is None else max(size_seen, max(sizes))
    geometry = Geometry(
        None if max_cylinder is None else max_cylinder + 1,
        None if max_head is None else max_head + 1, spt, size_seen)
    return Volume('imd', geometry, sectors, status, detail, tuple(dict.fromkeys(warnings)),
                  {'preamble': preamble[0] if preamble else '', 'comment_lines': len(preamble) - 1})


def _td0_crc16(data, crc=0):
    """CRC-16 with polynomial 0xA097 and preset 0, as documented for TeleDisk.

    Confirmed against three genuine images with distinct stored values, which
    is what distinguishes this from the four alternative CRC conventions that
    all fail on the same files.
    """
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0xA097) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def _td0_repeat_pattern(payload, size):
    """Method 1: repeated 16-bit pattern, 4-byte (count, pattern) entries."""
    out = bytearray()
    cursor = _Cursor(payload)
    while len(out) < size:
        if cursor.remaining() < 4:
            raise _Truncated('truncated repeat-pattern entry')
        count, pattern = unpack_from('<HH', cursor.take(4))
        if not count:
            raise _Truncated('zero repeat-pattern count')
        out.extend(pattern.to_bytes(2, 'little') * count)
    return bytes(out[:size]) if len(out) == size else None


def _td0_rle(payload, size):
    """Method 2: literal blocks and repeat blocks, as documented by Dunfield."""
    out = bytearray()
    cursor = _Cursor(payload)
    while len(out) < size:
        flag = cursor.byte()
        if flag == 0:
            length = cursor.byte()
            if not length:
                raise _Truncated('zero-length literal block')
            out.extend(cursor.take(length))
        else:
            length = flag * 2
            repeat = cursor.byte()
            block = cursor.take(length)
            if not repeat:
                raise _Truncated('zero repeat count')
            out.extend(block * repeat)
        if len(out) > size:
            raise _Truncated('run exceeds sector extent')
    return bytes(out)


def _td0(data, bounds):
    advanced = data[:1] == b't'
    header = data[:12]
    (sequence, check, version, rate, drive, stepping, dos_flag, sides,
     stored_crc) = unpack_from('<BBBBBBBBH', header, 2)
    header_crc_verified = _td0_crc16(header[:10]) == stored_crc
    metadata = {
        'advanced_compression': advanced,
        'volume_sequence': sequence,
        'volume_set': check,
        'header_crc_verified': header_crc_verified,
        'teledisk_version': f'{version >> 4}.{version & 0x0F}',
        'data_rate': TD0_DATA_RATES.get(rate & 0x03, f'unknown-{rate & 0x03}'),
        'single_density': bool(rate & 0x80),
        'drive_type': drive,
        'stepping': stepping & 0x03,
        'dos_allocation_only': bool(dos_flag),
        'sides': 1 if sides == 1 else 2,
        'stored_header_crc': stored_crc,
        'computed_header_crc': _td0_crc16(header[:10]),
    }
    warnings = []
    # CRC-16 with polynomial 0xA097, preset 0, most-significant bit first, was
    # confirmed against three genuine TeleDisk images (see the campaign report),
    # so a mismatch now reports real damage rather than an unconfirmed guess.
    if not header_crc_verified:
        warnings.append('header-crc-mismatch')
    geometry_hint = TD0_DRIVE_GEOMETRY.get(drive)
    geometry = Geometry(*(geometry_hint + (512,)) if geometry_hint else (None, None, None, None))
    if advanced:
        return Volume('td0', geometry, status='unsupported',
                      detail='teledisk-advanced-lzss-huffman',
                      warnings=tuple(warnings), metadata=metadata)
    cursor = _Cursor(data, 12)
    comment = None
    try:
        if stepping & 0x80:
            comment_header = cursor.take(10)
            comment_crc, comment_length = unpack_from('<HH', comment_header)
            raw = cursor.take(comment_length)
            comment = raw.replace(b'\x00', b'\n').decode('cp437', 'replace')
            metadata['comment_bytes'] = comment_length
            metadata['stored_comment_crc'] = comment_crc
    except _Truncated:
        return Volume('td0', geometry, status='partial', detail='truncated-comment',
                      warnings=tuple(warnings), metadata=metadata)
    sectors = []
    status, detail = 'ok', None
    max_cylinder = max_head = spt = None
    sector_size = None
    while True:
        if len(sectors) >= bounds.sectors:
            status, detail = 'limited', 'sector-limit'
            break
        try:
            count = cursor.byte()
        except _Truncated:
            status, detail = 'partial', 'missing-end-marker'
            break
        if count == 0xFF:
            break
        try:
            cylinder = cursor.byte()
            head_byte = cursor.byte()
            cursor.byte()  # Low byte of the track-header CRC.
        except _Truncated:
            status, detail = 'partial', 'truncated-track-header'
            break
        physical_head = head_byte & 0x01
        if not count:
            status, detail = 'failed', 'empty-track'
            break
        truncated = False
        for _ in range(count):
            try:
                sector_cylinder = cursor.byte()
                sector_head = cursor.byte()
                number = cursor.byte()
                size_code = cursor.byte()
                flags = cursor.byte()
                cursor.byte()  # Low byte of the sector-header CRC.
            except _Truncated:
                status, detail = 'partial', 'truncated-sector-header'
                truncated = True
                break
            if size_code >= len(SECTOR_SIZES):
                status, detail = 'failed', f'unknown-sector-size-code-{size_code}'
                truncated = True
                break
            size = SECTOR_SIZES[size_code]
            if size > bounds.sector_bytes:
                status, detail = 'failed', 'sector-size-out-of-range'
                truncated = True
                break
            if flags & 0x10:
                sectors.append(Sector(sector_cylinder, sector_head, number, size, None, 'skipped'))
                continue
            if flags & 0x20:
                sectors.append(Sector(sector_cylinder, sector_head, number, size, None, 'id-only'))
                continue
            if flags & 0x40:
                warnings.append('bogus-id-header')
            try:
                block_size, encoding = unpack_from('<HB', cursor.take(3))
            except _Truncated:
                status, detail = 'partial', 'truncated-data-header'
                truncated = True
                break
            if block_size < 1 or block_size - 1 > size * 2 + 16:
                status, detail = 'failed', 'implausible-data-block-size'
                truncated = True
                break
            try:
                payload = cursor.take(block_size - 1)
            except _Truncated:
                status, detail = 'partial', 'truncated-data-block'
                truncated = True
                break
            sector_status = 'ok'
            if flags & 0x04:
                sector_status = 'deleted-data'
            elif flags & 0x02:
                sector_status = 'read-error'
            decoded = None
            try:
                if encoding == 0:
                    decoded = payload if len(payload) == size else None
                    if decoded is None:
                        status = 'partial'
                        sector_status = 'size-mismatch'
                elif encoding == 1:
                    decoded = _td0_repeat_pattern(payload, size)
                elif encoding == 2:
                    decoded = _td0_rle(payload, size)
                else:
                    status = 'partial'
                    sector_status = f'unsupported-encoding-{encoding}'
            except _Truncated:
                status = 'partial'
                sector_status = 'malformed-encoding'
            if decoded is None and sector_status == 'ok':
                sector_status = 'malformed-encoding'
                status = 'partial'
            sectors.append(Sector(sector_cylinder, sector_head, number, size, decoded, sector_status))
            sector_size = size if sector_size is None else max(sector_size, size)
        if truncated:
            break
        max_cylinder = cylinder if max_cylinder is None else max(max_cylinder, cylinder)
        max_head = physical_head if max_head is None else max(max_head, physical_head)
        spt = count if spt is None else max(spt, count)
    observed = Geometry(
        None if max_cylinder is None else max_cylinder + 1,
        None if max_head is None else max_head + 1, spt, sector_size)
    # Observed track structure is stronger evidence than the drive-type hint.
    geometry = Geometry(
        observed.cylinders if observed.cylinders is not None else geometry.cylinders,
        observed.heads if observed.heads is not None else geometry.heads,
        observed.sectors_per_track if observed.sectors_per_track is not None else geometry.sectors_per_track,
        observed.sector_size if observed.sector_size is not None else geometry.sector_size)
    if comment:
        metadata['comment'] = comment
    return Volume('td0', geometry, sectors, status, detail,
                  tuple(dict.fromkeys(warnings)), metadata)


def _copyqm_track(cursor, track_bytes):
    """Decode one CopyQM track: signed 16-bit lengths, never crossing a track.

    Returns the bytes recovered so far and whether the track was complete, so a
    damaged payload still yields every sector it actually described.
    """
    out = bytearray()
    while len(out) < track_bytes:
        if cursor.remaining() < 2:
            return bytes(out), False
        length = unpack_from('<h', cursor.take(2))[0]
        if length < 0:
            repeat = -length
            if not repeat or cursor.remaining() < 1:
                return bytes(out), False
            out.extend(cursor.take(1) * repeat)
        elif length > 0:
            if cursor.remaining() < length:
                return bytes(out), False
            out.extend(cursor.take(length))
        else:
            return bytes(out), False
    return bytes(out[:track_bytes]), True


def _copyqm(data, bounds):
    header = data[:COPYQM_HEADER_BYTES]
    (sector_size, sectors_per_cluster, reserved, fats, root_entries, total16, media,
     sectors_per_fat, spt, heads) = unpack_from('<HBHBHHBHHH', header, 3)
    hidden, total32 = unpack_from('<II', header, 0x14)
    description = header[0x1C:0x58].split(b'\x00')[0].decode('cp437', 'replace').rstrip(' ')
    blind, density, cylinders_in_image, cylinders_on_disk = unpack_from('<4B', header, 0x58)
    stored_crc, = unpack_from('<I', header, 0x5C)
    label = header[0x60:0x6B].split(b'\x00')[0].decode('cp437', 'replace').rstrip(' ')
    comment_length, sector_base, _, interleave, skew = unpack_from('<HBBBB', header, 0x6F)
    metadata = {
        'description': description,
        'volume_label': label,
        'blind_mode': bool(blind),
        'density_code': density,
        'cylinders_in_image': cylinders_in_image,
        'cylinders_on_disk': cylinders_on_disk,
        'stored_data_crc': stored_crc,
        'comment_length': comment_length,
        'first_sector_number': sector_base + 1,
        'interleave': interleave,
        'skew': skew,
        'total_sectors_bpb': total16 or total32,
        'hidden_sectors': hidden,
        'sectors_per_fat': sectors_per_fat,
        'root_entries': root_entries,
        'reserved_sectors': reserved,
        'fat_copies': fats,
        'media_descriptor': media,
        'sectors_per_cluster': sectors_per_cluster,
    }
    if sector_size not in SECTOR_SIZES or not spt or not heads or not cylinders_in_image:
        return Volume('copyqm', Geometry(None, None, None, None), status='failed',
                      detail='implausible-copyqm-geometry', metadata=metadata)
    if sector_size > bounds.sector_bytes:
        return Volume('copyqm', Geometry(None, None, None, None), status='limited',
                      detail='sector-size-out-of-range', metadata=metadata)
    geometry = Geometry(cylinders_in_image, heads, spt, sector_size)
    cursor = _Cursor(data, COPYQM_HEADER_BYTES + comment_length)
    track_bytes = spt * sector_size
    sectors = []
    status, detail = 'ok', None
    first_number = sector_base + 1
    for cylinder in range(cylinders_in_image):
        for head in range(heads):
            if len(sectors) >= bounds.sectors:
                status, detail = 'limited', 'sector-limit'
                break
            try:
                track, complete = _copyqm_track(cursor, track_bytes)
            except _Truncated as exc:
                status, detail = 'partial', f'truncated-track-{cylinder}-{head}:{exc}'
                break
            for index in range(spt):
                start = index * sector_size
                chunk = track[start:start + sector_size]
                if len(chunk) == sector_size:
                    sectors.append(Sector(cylinder, head, first_number + index,
                                          sector_size, chunk, 'ok'))
                else:
                    sectors.append(Sector(cylinder, head, first_number + index,
                                          sector_size, None, 'missing'))
            if not complete:
                status, detail = 'partial', f'truncated-track-{cylinder}-{head}'
                break
        if status != 'ok':
            break
    if comment_length:
        comment = data[COPYQM_HEADER_BYTES:COPYQM_HEADER_BYTES + comment_length]
        text = comment.replace(b'\r\n', b'\n').split(b'\x00')[0].decode('cp437', 'replace')
        metadata['comment'] = text.rstrip('\n')
    return Volume('copyqm', geometry, sectors, status, detail, (), metadata)


READERS = {'imd': _imd, 'td0': _td0, 'td0-advanced': _td0, 'copyqm': _copyqm}


def read(path: Path, kind: str | None = None, bounds: Bounds = Bounds()) -> Volume:
    """Decode one sector-image container. ``kind`` defaults to structural sniffing."""
    data = path.read_bytes() if path.stat().st_size <= bounds.input_bytes else None
    if data is None:
        return Volume(kind or 'unknown', Geometry(None, None, None, None),
                      status='limited', detail='input-byte-limit')
    resolved = kind or identify(data)
    if resolved is None:
        return Volume('unknown', Geometry(None, None, None, None),
                      status='unhandled', detail='no-sector-container-signature')
    reader = READERS.get(resolved)
    if reader is None:
        return Volume(resolved, Geometry(None, None, None, None),
                      status='unsupported', detail='no-sector-reader')
    try:
        return reader(data, bounds)
    except (ValueError, IndexError, KeyError, _Truncated) as exc:
        return Volume(resolved, Geometry(None, None, None, None),
                      status='failed', detail=type(exc).__name__)


def to_lba(volume: Volume, first_sector_number: int = 1) -> LbaImage:
    """Normalise a volume to a logical-block derivative.

    Logical block order is ``((cylinder * heads) + head) * spt + (number - first)``.
    Every unwritten block is listed in ``missing`` and every conflicting write
    in ``conflicts``; neither is silently replaced by another value.
    """
    geometry = volume.geometry
    total = geometry.total_sectors
    if total is None or not geometry.sector_size:
        return LbaImage(b'', 0, 0, 0, (), (), 'unknown-geometry')
    if len(volume.sectors) > total * 2:
        return LbaImage(b'', geometry.sector_size, total, 0, (), (), 'implausible-sector-count')
    image = bytearray(total * geometry.sector_size)
    written = set()
    conflicts = []
    heads = geometry.heads
    spt = geometry.sectors_per_track
    size = geometry.sector_size
    for sector in volume.sectors:
        if sector.data is None or sector.size != size:
            continue
        index = sector.number - first_sector_number
        if not 0 <= index < spt:
            continue
        block = (sector.cylinder * heads + sector.head) * spt + index
        if not 0 <= block < total:
            continue
        start = block * size
        if block in written:
            if image[start:start + size] != sector.data:
                conflicts.append(block)
            continue
        image[start:start + size] = sector.data
        written.add(block)
    missing = tuple(index for index in range(total) if index not in written)
    status = 'complete' if not missing and not conflicts else 'incomplete'
    return LbaImage(bytes(image), size, total, len(written), missing, tuple(conflicts), status)
