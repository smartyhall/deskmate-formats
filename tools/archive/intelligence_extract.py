"""Identify and read bounded archive members without creating member paths."""

from collections import Counter
from dataclasses import dataclass, field
import gzip
from html.parser import HTMLParser
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from struct import unpack_from
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
from threading import Thread
from time import monotonic
import zipfile
import zlib

try:
    from . import compression as compression_streams
    from . import disk_images
except ImportError:
    import compression as compression_streams
    import disk_images


EXTENSIONS = {
    **dict.fromkeys(('txt', 'nfo', 'asc', 'me', 'diz', 'lst', 'log', 'ini', 'cfg', 'bat',
                    'c', 'h', 'asm', 'pas', 'bas', 'mak', 'msg', 'faq', 'nws', 'ans'), 'text'),
    **dict.fromkeys(('htm', 'html'), 'html'),
    **dict.fromkeys(('img', 'ima', 'dsk', 'vfd'), 'disk-image'),
    **dict.fromkeys(('lha', 'lzh'), 'lzh'),
    **{ext: ext for ext in ('zip', 'tar', 'gz', 'tgz', '7z', 'rar', 'arc', 'arj', 'cab', 'pdf', 'rtf',
                            'ff1', 'sng', 'snd', 'fig', 'fil', 'cln', 'adr', 'wks', 'hds', 'mid', 'mod',
                            'fnt', 'com', 'exe', 'dll', 'res', 'lib', 'obj', 'pif', 'doc')},
}
NATIVE_SIGNATURES = {
    b'\x0cSNG': 'sng', b'\rDOC': 'native-doc', b'\x0eWKS': 'wks',
    b'\x14FIG': 'fig', b'\x10FIG': 'fig', b'\x03FIL': 'dmdb', b'MThd': 'mid',
    b'MSCF': 'cab', b'PK\x03\x04': 'zip', b'PK\x05\x06': 'zip',
    b'\x89PNG': 'png', b'GIF8': 'gif', b'{\\rt': 'rtf',
}
LEGACY_KINDS = {'arj': 'Arj', 'cab': 'Cab', 'lzh': 'Lzh', '7z': '7z', 'rar': 'Rar', 'iso9660': 'Iso', 'udf': 'Udf', 'mz': None}
OPTICAL_KINDS = frozenset({'iso9660', 'udf', 'cd-raw', 'optical-image'})
SEVEN_OPTIONS = ('-sccUTF-8', '-spd', '-bsp0', '-p-')
CONTAINER_KINDS = frozenset({'zip', 'tar', 'gz', 'tgz', 'fat', 'disk-image', 'arc',
                            *OPTICAL_KINDS, *LEGACY_KINDS,
                            *disk_images.READERS, *compression_streams.DECODERS})
TEXT_KINDS = frozenset({'text', 'html', 'pdf', 'native-doc', 'doc', 'rtf'})
TEXT_CONTROL = re.compile(rb'[\x00-\x07\x0e-\x19\x1b-\x1f]')


@dataclass(frozen=True)
class Limits:
    input_bytes: int = 128 * 1024 * 1024
    member_bytes: int = 32 * 1024 * 1024
    total_bytes: int = 96 * 1024 * 1024
    members: int = 12_000
    text_bytes: int = 4 * 1024 * 1024
    tool_seconds: int = 25

    def __post_init__(self):
        if any(value <= 0 for value in vars(self).values()):
            raise ValueError('extraction limits must be positive')


@dataclass(frozen=True)
class Member:
    ordinal: int
    name: str
    size: int | None
    data: bytes | None
    status: str


@dataclass(frozen=True)
class Document:
    page: int
    text: str


@dataclass
class Extraction:
    members: list[Member] = field(default_factory=list)
    documents: list[Document] = field(default_factory=list)
    status: str = 'ok'
    detail: str | None = None


def _looks_text(data):
    if not data or b'\0' in data:
        return False
    return len(TEXT_CONTROL.findall(data)) * 50 <= len(data)


def optical_descriptor(path):
    """Inspect bounded volume-recognition sectors and the primary ISO descriptor."""
    size = path.stat().st_size
    if size < 17 * 2048:
        return None
    with path.open('rb') as stream:
        # Cooked logical blocks and raw Mode 1 / Mode 2 Form 1 data tracks.
        for stride, offset in ((2048, 0), (2352, 16), (2352, 24)):
            if size % stride or size < 17 * stride:
                continue
            if offset:
                stream.seek(16 * stride)
                header = stream.read(24)
                if (header[:12] != b'\0' + b'\xff' * 10 + b'\0'
                        or header[15] != (1 if offset == 16 else 2)
                        or (offset == 24 and (header[16:20] != header[20:24] or header[18] & 0x20))):
                    continue
            udf = False
            for sector in range(16, min(48, size // stride)):
                stream.seek(sector * stride + offset)
                data = stream.read(2048)
                identifier = data[1:6]
                if identifier in (b'NSR02', b'NSR03') and data[0] == 0 and data[6] == 1:
                    udf = True
                if identifier != b'CD001' or data[6] != 1:
                    continue
                if data[0] == 255:
                    break
                if data[0] != 1:
                    continue
                blocks = int.from_bytes(data[80:84], 'little')
                if (blocks != int.from_bytes(data[84:88], 'big')
                        or not 17 < blocks <= size // stride
                        or data[128:132] != b'\0\x08\x08\0'):
                    continue
                fields = {'system': (8, 40), 'volume': (40, 72), 'publisher': (318, 446),
                          'preparer': (446, 574), 'application': (574, 702),
                          'created': (813, 829)}
                return {'kind': 'cd-raw' if offset else 'iso9660', 'sector_bytes': stride,
                        'data_offset': offset, 'volume_blocks': blocks, 'metadata': {
                            name: data[start:end].decode('ascii', 'replace').strip(' \0')
                            for name, (start, end) in fields.items()}}
            if not offset and udf:
                return {'kind': 'udf', 'sector_bytes': stride, 'data_offset': offset}
    return None


def identify(path: Path, name: str) -> str:
    """Classify a file by header/geometry and then by filename or textual bytes."""
    label = PurePosixPath(name.replace('\\', '/')).name.casefold()
    extension = PurePosixPath(label).suffix[1:]
    size = path.stat().st_size
    with path.open('rb') as stream:
        data = stream.read(4096)
    if kind := NATIVE_SIGNATURES.get(data[:4]):
        return kind
    # Sector containers and compression streams carry mandatory structural
    # invariants, so they are recognised without trusting the filename.
    if kind := disk_images.identify(data):
        return kind
    if kind := compression_streams.identify_stream(data):
        return kind
    if data[:5] in (b'\xbd\x7a\0\x01\x01', b'\xbd\x7a\x01\x01\x01') and data[32:34] == b'\x2e\0':
        return 'ff1'
    if data.startswith(b'RIFF') and data[8:12] == b'WAVE':
        return 'wav'
    if data.startswith(b'Creative Voice File\x1a'):
        return 'voc'
    if data.startswith((b'II*\0', b'MM\0*')):
        return 'tiff'
    if data.startswith(b'%PDF-'):
        return 'pdf'
    if data.startswith(b'7z\xbc\xaf\x27\x1c'):
        return '7z'
    if data.startswith(b'Rar!\x1a\x07'):
        return 'rar'
    if data.startswith(b'\x60\xea'):
        return 'arj'
    if data[2:5] in (b'-lh', b'-lz') and data[6:7] == b'-':
        return 'lzh'
    if data.startswith(b'\x1f\x8b\x08'):
        # Preserve an explicit .tgz name so a decompressed opaque TAR can be named.
        return 'tgz' if extension == 'tgz' else 'gz'
    if data[257:262] == b'ustar':
        return 'tar'
    if data.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):
        return 'compound-document'
    if descriptor := optical_descriptor(path):
        return descriptor['kind']
    if extension in ('iso', 'nrg', 'mdf', 'ccd', 'cue'):
        return 'optical-image'
    if _fat_layout(data, size) is not None:
        return 'fat'
    if any(_partitions(data, size)):
        with path.open('rb') as stream:
            for _, offset, length in _partitions(data, size):
                stream.seek(offset)
                if _fat_layout(stream.read(512), length):
                    return 'fat'
    if data.startswith(b'MZ'):
        return 'zip' if zipfile.is_zipfile(path) else 'mz'
    if data[44:46] == b'\x1a\x80' and len(data) >= 114 and 0 < unpack_from('<H', data, 46)[0] <= 128:
        return 'snd'
    if data.startswith(b'\x1a') and len(data) >= 29 and 1 <= data[1] <= 11:
        member_name, nul, _padding = data[2:15].partition(b'\0')
        if nul and b'.' in member_name and re.fullmatch(rb'[!-~]{1,12}', member_name):
            return 'arc'
    if data.startswith(b'\x1a') and len(data) >= 44 and data[1] in (0, 1, 2) and data[2]:
        table_end = 16 + 28 * data[2]
        first_sample = unpack_from('<I', data, 20)[0]
        if (data[3] <= 32 or data[3] == 255) and table_end <= first_sample <= size:
            return 'snd'
    if data[:4] == b'\x03\0\0\0' and extension == 'adr':
        return 'adr'
    if re.match(rb'(?:\xef\xbb\xbf)?\s*<(?:!doctype\s+html|html|head|body)\b', data, re.I):
        return 'html'
    if extension in EXTENSIONS:
        return EXTENSIONS[extension]
    if _looks_text(data) or data.startswith((b'\xff\xfe', b'\xfe\xff')):
        return 'text'
    return 'binary'


def safe_member(name):
    """Reject ambiguous file paths even though member names are retained only as labels."""
    if not name or re.search(r'[\x00-\x1f\x7f:]', name):
        return False
    parts = name.replace('\\', '/').split('/')
    return all(part and part not in ('.', '..') for part in parts)


def _can_read(name, size, remaining, limits):
    if not safe_member(name):
        return 'unsafe-path'
    if size is not None and (size < 0 or size > min(limits.member_bytes, remaining)):
        return 'byte-limit'
    return 'ok'


def _members(entries, limits):
    result = Extraction()
    remaining = limits.total_bytes
    for ordinal, (name, size, reason, load) in enumerate(entries):
        if ordinal >= limits.members:
            result.status, result.detail = 'partial', 'member-count-limit'
            break
        reason = reason or _can_read(name, size, remaining, limits)
        data = None
        if reason == 'ok':
            cap = min(limits.member_bytes, remaining)
            try:
                data = load(cap)
                if len(data) > cap:
                    data, reason = None, 'byte-limit'
                elif size is not None and size != len(data):
                    data, reason = None, 'size-mismatch'
                else:
                    size = len(data)
                    remaining -= size
            except subprocess.TimeoutExpired:
                reason = 'tool-time-limit'
            except (OSError, ValueError, RuntimeError, EOFError, zlib.error, zipfile.BadZipFile,
                    tarfile.TarError):
                reason = 'read-error'
        if reason not in ('ok', 'directory'):
            result.status = 'partial'
        result.members.append(Member(ordinal, name, size, data, reason))
    return result


def _read(open_stream, cap):
    with open_stream() as stream:
        return stream.read(cap + 1)


def _zip(path, limits, seven_zip):
    with zipfile.ZipFile(path) as archive:
        deadline = monotonic() + limits.tool_seconds
        normalized_names = Counter(info.orig_filename.replace('\\', '/').casefold()
                                   for info in archive.infolist())

        def entries():
            for info in archive.infolist():
                mode = stat.S_IFMT(info.external_attr >> 16)
                name = info.orig_filename.rstrip('/\\') if info.is_dir() else info.orig_filename
                reason = None
                if not safe_member(name):
                    reason = 'unsafe-path'
                elif mode not in (0, stat.S_IFREG, stat.S_IFDIR) or info.external_attr & 0x400:
                    reason = 'non-regular'
                elif info.is_dir() or mode == stat.S_IFDIR:
                    reason = 'directory'
                elif info.flag_bits & 1:
                    reason = 'encrypted'

                def load(cap):
                    return _read(lambda: archive.open(info), cap)

                if not reason and info.compress_type in (1, 6):  # Shrink and Implode.
                    label = name.replace('\\', '/').casefold()
                    if seven_zip is None:
                        reason = f'unsupported-zip-method-{info.compress_type}'
                    elif name.startswith(('-', '@')) or normalized_names[label] > 1:
                        reason = 'ambiguous-path'
                    elif monotonic() >= deadline:
                        reason = 'tool-time-limit'

                    def load(cap):
                        data = _seven_member(path, seven_zip, ['-tzip'], name, info.file_size,
                                             deadline - monotonic())
                        if len(data) != info.file_size or zlib.crc32(data) != info.CRC:
                            raise ValueError('legacy ZIP member size or CRC disagrees with central directory')
                        return data

                yield name, info.file_size, reason, load
        return _members(entries(), limits)


def _tar(path, limits):
    with tarfile.open(path, mode='r:') as archive:
        def entries():
            for info in archive:
                name = info.name.rstrip('/') if info.isdir() else info.name
                reason = None
                if not safe_member(name):
                    reason = 'unsafe-path'
                elif info.isdir():
                    reason = 'directory'
                elif not info.isfile() or info.issparse():
                    reason = 'non-regular'
                yield name, info.size, reason, lambda cap: _read(lambda: archive.extractfile(info), cap)
        return _members(entries(), limits)


def _gzip(path, name, kind, limits):
    basename = PurePosixPath(name.replace('\\', '/')).name
    base = basename.rsplit('.', 1)[0] if '.' in basename else basename
    child = base + '.tar' if kind == 'tgz' else base if base != basename else 'payload'
    return _members(((child, None, None, lambda cap: _read(lambda: gzip.open(path), cap)),), limits)


@dataclass(frozen=True)
class _FATLayout:
    bits: int
    cluster_bytes: int
    cluster_count: int
    fat_start: int
    fat_bytes: int
    root_start: int
    root_bytes: int
    data_start: int


def _fat_layout(boot, size):
    # Some old floppies predate the extended BPB magic and 55AA trailer.
    if len(boot) < 512 or boot[0] not in (0xe9, 0xeb):
        return None
    sector, sectors_per_cluster, reserved, copies, root_entries, total, media, fat = unpack_from(
        '<HBHBHHBH', boot, 11)
    if (sector not in (128, 256, 512, 1024, 2048, 4096) or
            sectors_per_cluster not in (1, 2, 4, 8, 16, 32, 64, 128) or
            copies not in (1, 2) or media not in (0xf0, *range(0xf8, 0x100)) or
            not reserved or not root_entries or not fat):
        return None
    total = total or unpack_from('<I', boot, 32)[0]
    root = reserved + copies * fat
    root_sectors = (root_entries * 32 + sector - 1) // sector
    first_data = root + root_sectors
    if not first_data < total <= size // sector:
        return None
    cluster_count = (total - first_data) // sectors_per_cluster
    bits = 12 if cluster_count < 4085 else 16
    if not 0 < cluster_count < 65525 or (cluster_count + 2) * bits > fat * sector * 8:
        return None
    return _FATLayout(bits, sector * sectors_per_cluster, cluster_count,
                      reserved * sector, fat * sector, root * sector, root_entries * 32, first_data * sector)


def _partitions(boot, size):
    if boot[510:512] != b'\x55\xaa':
        return
    for index in range(4):
        offset = 446 + index * 16
        if boot[offset] not in (0, 0x80) or boot[offset + 4] not in (1, 4, 6, 0xe):
            continue
        start, count = unpack_from('<II', boot, offset + 8)
        if start and count and (start + count) * 512 <= size:
            yield index + 1, start * 512, count * 512


class _FATVolume:
    def __init__(self, stream, offset, layout):
        self.stream = stream
        self.offset = offset
        self.layout = layout
        link_bytes = ((layout.cluster_count + 2) * layout.bits + 7) // 8
        self.fat = self.read(layout.fat_start, link_bytes)
        self.directories = set()

    def read(self, offset, size):
        self.stream.seek(self.offset + offset)
        data = self.stream.read(size)
        if len(data) != size:
            raise ValueError('truncated FAT region')
        return data

    def chain(self, cluster):
        seen = set()
        layout = self.layout
        stop = 0xff8 if layout.bits == 12 else 0xfff8
        reserved = 0xff0 if layout.bits == 12 else 0xfff0
        while cluster < stop:
            if not 2 <= cluster < min(layout.cluster_count + 2, reserved) or cluster in seen:
                raise ValueError('invalid FAT cluster chain')
            seen.add(cluster)
            yield layout.data_start + (cluster - 2) * layout.cluster_bytes
            if layout.bits == 12:
                value = unpack_from('<H', self.fat, cluster + cluster // 2)[0]
                cluster = (value >> (4 * (cluster % 2))) & 0xfff
            else:
                cluster = unpack_from('<H', self.fat, cluster * 2)[0]

    def _blocks(self, cluster):
        if cluster is None:
            yield self.read(self.layout.root_start, self.layout.root_bytes)
        else:
            for offset in self.chain(cluster):
                yield self.read(offset, self.layout.cluster_bytes)

    def file(self, cluster, size):
        if not cluster and not size:
            return b''
        data = bytearray()
        for offset in self.chain(cluster):
            if len(data) >= size:
                raise ValueError('extra FAT clusters beyond file extent')
            data.extend(self.read(offset, min(self.layout.cluster_bytes, size - len(data))))
        if len(data) != size:
            raise ValueError('FAT chain is shorter than file extent')
        return bytes(data)

    def entries(self, prefix='', cluster=None, depth=0):
        for block in self._blocks(cluster):
            for cursor in range(0, len(block), 32):
                entry = block[cursor:cursor + 32]
                if not entry[0]:
                    return
                if entry[0] == 0xe5 or entry[11] & 8 or entry[:1] == b'.':
                    continue
                root = bytes([0xe5]) + entry[1:8] if entry[0] == 5 else entry[:8]
                name = root.decode('cp437').rstrip(' ')
                ext = entry[8:11].decode('cp437').rstrip(' ')
                name = prefix + name + ('.' + ext if ext else '')
                child, size = unpack_from('<HI', entry, 26)
                if entry[11] & 16:
                    invalid = child in self.directories or depth >= 24 or not safe_member(name)
                    yield name, 0, 'invalid-directory' if invalid else 'directory', None
                    if not invalid:
                        self.directories.add(child)
                        try:
                            yield from self.entries(name + '/', child, depth + 1)
                        except ValueError:
                            yield name, None, 'invalid-directory-chain', None
                else:
                    yield name, size, None, lambda cap: self.file(child, size)


def _fat(path, limits):
    size = path.stat().st_size
    with path.open('rb') as stream:
        boot = stream.read(512)
        if layout := _fat_layout(boot, size):
            return _members(_FATVolume(stream, 0, layout).entries(), limits)
        volumes = []
        for index, offset, length in _partitions(boot, size):
            stream.seek(offset)
            if layout := _fat_layout(stream.read(512), length):
                volumes.append((index, offset, layout))
        if not volumes:
            return Extraction(status='unsupported', detail='no-fat12-or-fat16-layout')

        def entries():
            for index, offset, layout in volumes:
                yield from _FATVolume(stream, offset, layout).entries(f'partition-{index}/')

        return _members(entries(), limits)


def _sector_image(path, kind, limits):
    """Normalise a sector container, then read its filesystem if it has one.

    The normalised logical-block image is a derivative written to a private
    scratch path; only its member listing and geometry summary are retained.
    """
    volume = disk_images.read(path, kind, disk_images.Bounds(
        input_bytes=limits.input_bytes, sectors=limits.members,
        sector_bytes=min(limits.member_bytes, 65536)))
    geometry = volume.geometry
    summary = (f'{volume.container}; {geometry.cylinders}c/{geometry.heads}h/'
               f'{geometry.sectors_per_track}spt x {geometry.sector_size}B; '
               f'{len(volume.sectors)} sectors')
    if volume.detail:
        summary += f'; {volume.detail}'
    if volume.warnings:
        summary += '; ' + ', '.join(volume.warnings)
    if volume.status in ('failed', 'unsupported', 'limited'):
        return Extraction(status=volume.status, detail=summary)
    normalised = disk_images.to_lba(volume)
    if normalised.status == 'unknown-geometry':
        return Extraction(status='unsupported', detail=summary + '; unknown-geometry')
    summary += (f'; lba {normalised.status} {normalised.written}/{normalised.total_sectors}')
    if normalised.missing:
        summary += f'; {len(normalised.missing)} missing'
    if normalised.conflicts:
        summary += f'; {len(normalised.conflicts)} conflicting'
    with TemporaryDirectory(prefix='deskmate-sector-') as scratch:
        staged = Path(scratch) / 'normalised.img'
        staged.write_bytes(normalised.data)
        result = _fat(staged, limits)
    result.detail = summary + ('; ' + result.detail if result.detail else '')
    # A clean filesystem read of an incomplete volume is still an incomplete
    # recovery: the container, not the filesystem, decides that status.
    if result.status == 'ok' and (volume.status != 'ok' or normalised.status != 'complete'):
        result.status = 'partial'
    return result


def _compressed(path, name, kind, limits):
    """Decode one standalone compression stream into a single opaque member."""
    decoded = compression_streams.decode(
        path.read_bytes(), kind,
        compression_streams.Bounds(output_bytes=limits.member_bytes))
    if decoded.status != 'ok':
        return Extraction(status='limited' if decoded.status == 'limited' else 'failed',
                          detail=f'{kind}; {decoded.detail}')
    basename = PurePosixPath(name.replace('\\', '/')).name
    suffix = compression_streams.SUFFIXES[kind]
    if basename.casefold().endswith(suffix):
        child = basename[:-len(suffix)]
    elif '.' in basename:
        child = basename.rsplit('.', 1)[0]
    else:
        child = basename
    detail = kind if not decoded.warnings else kind + '; ' + ', '.join(decoded.warnings)
    return Extraction(members=[Member(0, child or 'payload', len(decoded.data),
                                      decoded.data, 'ok')], detail=detail)


def _arc(path, limits, nomarch=None):
    """Inventory ARC headers and check CRCs for stored and supported compressed members."""
    size = path.stat().st_size
    deadline = monotonic() + limits.tool_seconds
    with path.open('rb') as stream:
        def entries():
            while stream.tell() < size:
                marker = stream.read(2)
                if marker == b'\x1a\0':
                    return
                if len(marker) != 2 or marker[0] != 0x1a or marker[1] == 0:
                    raise ValueError('invalid ARC member marker')
                method = marker[1]
                header = stream.read(23 if method == 1 else 27)
                if len(header) != (23 if method == 1 else 27) or b'\0' not in header[:13]:
                    raise ValueError('invalid ARC member header')
                name = header[:13].split(b'\0', 1)[0].decode('cp437')
                packed, _, _, crc = unpack_from('<IHHH', header, 13)
                unpacked = packed if method == 1 else unpack_from('<I', header, 23)[0]
                end = stream.tell() + packed
                if end > size:
                    raise ValueError('truncated ARC member')

                def load(cap):
                    if method in (1, 2):
                        data = stream.read(packed)
                    else:
                        # Isolate the exact ordinal without passing an archive-controlled
                        # path or a wildcard to the external decoder.
                        with TemporaryDirectory(prefix='deskmate-arc-') as scratch:
                            member = Path(scratch) / 'member.arc'
                            member.write_bytes(marker + header + stream.read(packed) + b'\x1a\0')
                            code, data = _capture([str(nomarch.resolve()), '-p', str(member)],
                                                  min(cap, unpacked), deadline - monotonic())
                        if code != 0:
                            raise ValueError('nomarch rejected ARC member')
                    if _arc_crc(data) != crc:
                        raise ValueError('ARC CRC mismatch')
                    return data

                reason = None
                if method in (8, 9) and nomarch is not None:
                    if packed > limits.member_bytes:
                        reason = 'packed-byte-limit'
                elif method not in (1, 2):
                    reason = f'unsupported-arc-method-{method}'
                elif packed != unpacked:
                    reason = 'size-mismatch'
                yield name, unpacked, reason, load
                stream.seek(end)
            raise ValueError('missing ARC end marker')

        return _members(entries(), limits)


def _arc_crc(data):
    crc = 0
    for byte in data:
        crc = (crc >> 8) ^ _CRC16[(crc ^ byte) & 0xff]
    return crc


def _crc16_entry(value):
    for _ in range(8):
        value = (value >> 1) ^ (0xa001 if value & 1 else 0)
    return value


_CRC16 = tuple(map(_crc16_entry, range(256)))


def _capture(args, cap, timeout):
    """Drain only bounded stdout from an inert conversion process."""
    if timeout <= 0:
        raise subprocess.TimeoutExpired(args, timeout)
    options = {'creationflags': getattr(subprocess, 'CREATE_NO_WINDOW', 0)}
    with subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, **options) as process:
        output = bytearray()
        errors = []

        def reader():
            try:
                while chunk := process.stdout.read1(min(65536, cap + 1 - len(output))):
                    output.extend(chunk)
                    if len(output) > cap:
                        if process.poll() is None:
                            process.kill()
                        return
            except OSError as exc:
                errors.append(exc)

        worker = Thread(target=reader)
        worker.start()
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise
        finally:
            worker.join()
        if len(output) > cap:
            raise ValueError('tool output exceeds byte budget')
        if errors:
            raise errors[0]
        return code, bytes(output)


def _lha0_entries(path, members):
    """Return independently checked level-zero headers or defer to 7-Zip."""
    size = path.stat().st_size
    rows = []
    with path.open('rb') as source:
        while source.tell() < size and len(rows) <= members:
            prefix = source.read(1)
            if prefix == b'\0':
                return rows if source.tell() == size else None
            checksum = source.read(1)
            header = source.read(prefix[0])
            if (len(header) != prefix[0] or len(header) < 22 or header[18] != 0 or
                    not re.fullmatch(rb'-l[hz][0-9ds]-', header[:5]) or checksum != bytes([sum(header) & 255])):
                return None
            name_end = 20 + header[19]
            if name_end + 2 > len(header):
                return None
            packed, unpacked = unpack_from('<II', header, 5)
            crc, = unpack_from('<H', header, name_end)
            next_offset = source.tell() + packed
            if next_offset > size:
                return None
            name = header[20:name_end].decode('cp437')
            rows.append((name, unpacked, crc, header[:5]))
            source.seek(next_offset)
    return None


def _lhasa(path, lhasa, limits):
    rows = _lha0_entries(path, limits.members)
    if rows is None:
        return None
    deadline = monotonic() + limits.tool_seconds
    source = str(path.resolve())
    executable = str(lhasa.resolve())
    windows = os.name == 'nt'
    counts = Counter(name.casefold() for name, _, _, _ in rows)

    def entries():
        for name, size, crc, method in rows:
            status = None
            if method == b'-lhd-':
                status = 'directory' if safe_member(name.rstrip('/\\')) else 'unsafe-path'
            elif not re.fullmatch(r'[A-Za-z0-9_$~!#%&(){}\x27^-]{1,8}(?:\.[A-Za-z0-9_$~!#%&(){}\x27^-]{1,3})?', name):
                status = 'unsafe-or-unsupported-lhasa-name'
            elif counts[name.casefold()] != 1:
                status = 'ambiguous-path'
            elif monotonic() >= deadline:
                status = 'tool-time-limit'

            def load(cap):
                code, payload = _capture([executable, 'pq', source, name.lower()],
                                         size * (2 if windows else 1), deadline - monotonic())
                if windows and len(payload) != size:
                    payload = payload.replace(b'\r\n', b'\n')
                if code or len(payload) != size or _arc_crc(payload) != crc:
                    raise ValueError('Lhasa member size or CRC disagrees with level-zero header')
                return payload

            yield name, size, status, load

    result = _members(entries(), limits)
    result.detail = 'lhasa-level-zero-crc16' + (f'; {result.detail}' if result.detail else '')
    return result


def _legacy_entries(listing):
    header, delimiter, entries = listing.partition('\n----------\n')
    if not delimiter:
        return None, []
    archive_type = re.findall(r'^Type = (\S+)$', header, re.M)
    records = []
    for block in entries.strip('\n').split('\n\n'):
        if not block:
            continue
        fields = {}
        valid = True
        for line in block.splitlines():
            key, sep, value = line.partition(' = ')
            if not sep or key in fields:
                valid = False
                break
            fields[key] = value
        name = fields.get('Path', '')
        size = fields.get('Size', '')
        attrs = fields.get('Attributes', '')
        directory = fields.get('Folder') == '+' or attrs.startswith('D')
        if not valid or not name or (not re.fullmatch(r'[0-9]{1,18}', size)
                                    and not (directory and size == '')):
            records.append((name, None, 'unparseable-tool-entry'))
            continue
        status = None
        mode = fields.get('Mode', '')
        if (not safe_member(name) or name.startswith(('-', '@')) or
                any(ch in name for ch in ('\r', '\n'))):
            status = 'unsafe-path'
        elif (any(fields.get(key) not in (None, '', '-') for key in
                   ('Symbolic Link', 'Hard Link', 'Alternate Stream')) or
              re.search(r'(?:^|\s)[lbcps][rwxStTs-]{9}(?:\s|$)', f'{attrs} {mode}')):
            status = 'non-regular'
        elif directory:
            status = 'directory'
        elif fields.get('Encrypted') == '+':
            status = 'encrypted'
        records.append((name, int(size) if size else 0, status))
    return archive_type[-1] if archive_type else None, records


def _legacy(path, kind, seven_zip, limits):
    deadline = monotonic() + limits.tool_seconds
    file_type = LEGACY_KINDS[kind]
    args = [f'-t{file_type}'] if file_type else []
    source = str(path.resolve())
    command = str(seven_zip)
    code, stdout = _capture([command, 'l', *SEVEN_OPTIONS, *args, '-slt', '--', source],
                            min(limits.members * 2048, 16 * 1024 * 1024), deadline - monotonic())
    if code:
        return Extraction(status='unhandled' if kind == 'mz' and code == 2 else 'failed',
                          detail=f'7zip-list-exit-{code}')
    file_type, rows = _legacy_entries(stdout.decode('utf-8').replace('\r\n', '\n'))
    if not file_type or file_type.casefold() in {'pe', 'elf', 'macho', 'coff'}:
        return (Extraction(status='unhandled', detail='no-supported-sfx-payload') if kind == 'mz'
                else Extraction(status='failed', detail='no-archive-listing'))
    counts = Counter(name.casefold() for name, _, _ in rows)

    def entries():
        for name, size, status in rows:
            def load(cap):
                return _seven_member(path, seven_zip, args, name, size, deadline - monotonic())

            if not status and counts[name.casefold()] > 1:
                status = 'ambiguous-path'
            if not status and monotonic() >= deadline:
                status = 'tool-time-limit'
            yield name, size, status, load

    result = _members(entries(), limits)
    result.detail = '7zip-' + file_type + (f'; {result.detail}' if result.detail else '')
    return result


def _seven_member(path, seven_zip, args, name, size, timeout):
    code, data = _capture([str(seven_zip), 'x', *SEVEN_OPTIONS, *args,
                           '-so', '-y', '--', str(path.resolve()), name], size, timeout)
    if code:
        raise ValueError('7-Zip member extraction failed')
    return data


def _pdf(path, pdftotext, limits):
    code, data = _capture([str(pdftotext), '-enc', 'UTF-8', '-layout', str(path.resolve()), '-'],
                          limits.text_bytes, limits.tool_seconds)
    if code:
        return Extraction(status='failed', detail=f'pdftotext-exit-{code}')
    pages = data.decode('utf-8').split('\f')
    documents = [Document(page, text) for page, text in enumerate(pages, 1) if text.strip()]
    return Extraction(documents=documents, status='ok' if documents else 'unsupported',
                      detail='pdftotext' if documents else 'no-pdf-text-ocr-required')


def _pypdf(path, python, limits):
    script = str(Path(__file__).resolve())
    code, data = _capture([str(python), '-I', script, '--pdf-worker', str(path.resolve()), str(limits.members)],
                          limits.text_bytes, limits.tool_seconds)
    if code:
        status = 'unsupported' if code in (2, 3) else 'failed'
        detail = {2: 'pypdf-unavailable', 3: 'encrypted-pdf'}.get(code, f'pypdf-exit-{code}')
        return Extraction(status=status, detail=detail)
    rows = [json.loads(line) for line in data.splitlines()]
    if not rows:
        return Extraction(status='failed', detail='no-pdf-worker-results')
    info = rows[0]
    documents = [Document(row['page'], row['text']) for row in rows[1:] if row.get('text', '').strip()]
    errors = sum('error' in row for row in rows[1:])
    visited = len(rows) - 1
    status = 'partial' if errors or visited < info['pages'] else 'ok' if documents else 'unsupported'
    detail = (f'pypdf-{info["version"]}; {len(documents)}/{info["pages"]} pages with text; '
              f'{visited} pages visited; {errors} page errors')
    if not documents:
        detail += '; ocr-triage'
    return Extraction(documents=documents, status=status, detail=detail)


def _pdf_worker(path, max_pages):
    """Encode bounded-process page results as JSON lines on binary stdout."""
    try:
        from pypdf import PdfReader, __version__
    except ImportError:
        return 2

    def emit(row):
        sys.stdout.buffer.write(json.dumps(row, ensure_ascii=True).encode('ascii') + b'\n')

    with path.open('rb') as stream:
        reader = PdfReader(stream)
        if reader.is_encrypted and not reader.decrypt(''):
            return 3
        pages = len(reader.pages)
        emit({'version': __version__, 'pages': pages})
        for index in range(min(pages, max_pages)):
            row = {'page': index + 1}
            try:
                row['text'] = reader.pages[index].extract_text()
            except Exception as exc:
                row['error'] = type(exc).__name__
            emit(row)
    return 0


class _HTMLText(HTMLParser):
    HIDDEN = {'script', 'style'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = None
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.HIDDEN:
            self.hidden = tag
        elif not self.hidden and tag in {'p', 'br', 'hr', 'li', 'h1', 'h2', 'h3', 'tr', 'div'}:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag == self.hidden:
            self.hidden = None
        elif not self.hidden and tag in {'title', 'td', 'th', 'div', 'p'}:
            self.parts.append(' ')

    def handle_data(self, text):
        if not self.hidden:
            self.parts.append(text)


def _plain(data):
    if data.startswith((b'\xff\xfe', b'\xfe\xff')):
        return data.decode('utf-16'), 'utf-16'
    if not _looks_text(data) and data:
        raise ValueError('binary control density')
    try:
        return data.decode('utf-8-sig'), 'utf-8'
    except UnicodeDecodeError:
        return data.decode('cp437'), 'cp437-fallback'


def _text(path, kind, limits):
    if path.stat().st_size > limits.text_bytes:
        return Extraction(status='limited', detail='text-byte-limit')
    data = path.read_bytes()
    if kind == 'native-doc' or (kind == 'doc' and data.endswith(b'\x1a')):
        try:
            from deskmate_formats.text import parse_bytes
        except ImportError:
            return Extraction(status='unsupported', detail='native-doc-reader-unavailable')
        try:
            return Extraction(documents=[Document(0, parse_bytes(data).text)], detail='deskmate-text')
        except ValueError:
            if kind == 'native-doc':
                return Extraction(status='failed', detail='native-doc-profile-rejected')
    try:
        text, method = _plain(data)
    except ValueError:
        return Extraction(status='unsupported', detail='binary-document')
    text = text.rstrip('\x1a').replace('\r\n', '\n').replace('\r', '\n')
    if kind == 'html':
        parser = _HTMLText()
        parser.feed(text)
        parser.close()
        text = ''.join(parser.parts)
        method = 'html-' + method
    if kind == 'rtf':
        return Extraction(status='unsupported', detail='rtf-reader-unavailable')
    return Extraction(documents=[Document(0, text)], detail=method)


def extract(path: Path, name: str, kind: str, limits: Limits = Limits(), *,
            seven_zip: Path | None = None, pdftotext: Path | None = None,
            lhasa: Path | None = None, pdf_python: Path | None = None,
            nomarch: Path | None = None) -> Extraction:
    """Read one identified file. The caller owns recursion, persistence and hashing."""
    # The optical helpers seek into an image; extraction and listing retain their
    # ordinary output limits. Permit one single-layer DVD-sized input.
    input_cap = max(limits.input_bytes, 5 * 1024**3) if kind in OPTICAL_KINDS else limits.input_bytes
    if path.stat().st_size > input_cap:
        return Extraction(status='limited', detail='input-byte-limit')
    try:
        if kind == 'zip':
            return _zip(path, limits, seven_zip)
        if kind == 'tar':
            return _tar(path, limits)
        if kind in ('gz', 'tgz'):
            return _gzip(path, name, kind, limits)
        if kind in ('fat', 'disk-image'):
            return _fat(path, limits)
        if kind in disk_images.READERS:
            return _sector_image(path, kind, limits)
        if kind in compression_streams.DECODERS:
            return _compressed(path, name, kind, limits)
        if kind == 'arc':
            return _arc(path, limits, nomarch)
        if kind == 'lzh' and lhasa is not None:
            if lhasa_result := _lhasa(path, lhasa, limits):
                return lhasa_result
        if kind in ('optical-image', 'cd-raw'):
            return Extraction(status='unsupported', detail='no-qualified-optical-decoder')
        if kind in LEGACY_KINDS:
            if seven_zip is None:
                return Extraction(status='unsupported', detail='7zip-unavailable')
            result = _legacy(path, kind, seven_zip, limits)
            if kind in ('iso9660', 'udf') and not result.members and result.status == 'ok':
                return Extraction(status='failed', detail='empty-optical-listing')
            return result
        if kind == 'pdf':
            if pdftotext is not None:
                return _pdf(path, pdftotext, limits)
            if pdf_python is not None:
                return _pypdf(path, pdf_python, limits)
            return Extraction(status='unsupported', detail='pdf-reader-unavailable')
        if kind in TEXT_KINDS:
            return _text(path, kind, limits)
    except (OSError, ValueError, RuntimeError, EOFError, zlib.error, zipfile.BadZipFile,
            tarfile.TarError, subprocess.SubprocessError) as exc:
        return Extraction(status='failed', detail=type(exc).__name__)
    return Extraction(status='unhandled', detail='no-extractor')


if __name__ == '__main__' and len(sys.argv) == 4 and sys.argv[1] == '--pdf-worker':
    raise SystemExit(_pdf_worker(Path(sys.argv[2]), int(sys.argv[3])))
