"""Inventory First Publisher's exact 720 KiB distributions and FNT maps."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from
from zipfile import ZipFile


def identity(data):
    return {'size': len(data), 'sha256': sha256(data).hexdigest()}


def fat12(image):
    """Extract the measured flat FAT12 layout independently of archive tools."""
    if len(image) != 737280 or image[11:24] != bytes.fromhex('0002020100027000a005f90300'):
        raise ValueError('unexpected Publisher floppy geometry')
    fat = image[512:2048]
    if fat != image[2048:3584] or fat[:3] != b'\xf9\xff\xff':
        raise ValueError('inconsistent FAT12 copies')
    root_at, data_at = 3584, 7168
    result = {}
    for pos in range(root_at, data_at, 32):
        entry = image[pos:pos+32]
        if not entry[0]:
            break
        if entry[0] == 229 or entry[11] & 8:
            continue
        if entry[11] & 16:
            raise ValueError('unexpected Publisher subdirectory')
        name = '.'.join(part.decode('ascii').rstrip() for part in (entry[:8], entry[8:11])).rstrip('.')
        cluster, size = unpack_from('<HI', entry, 26)
        contents = bytearray()
        seen = set()
        while cluster < 0xff8 and (size or cluster):
            if not 2 <= cluster < 715 or cluster in seen:
                raise ValueError(f'invalid FAT12 chain for {name}')
            seen.add(cluster)
            offset = data_at + (cluster - 2) * 1024
            contents.extend(image[offset:offset+1024])
            link, = unpack_from('<H', fat, cluster + cluster // 2)
            cluster = (link >> (4 * (cluster % 2))) & 0xfff
        if name in result or len(contents) != (size + 1023) // 1024 * 1024:
            raise ValueError(f'inconsistent FAT12 file extent for {name}')
        result[name] = bytes(contents[:size])
    return result


def fnt(data):
    """Read one FONT-only Macintosh-style resource map with Pascal names."""
    base, directory, data_size, map_size = unpack_from('>IIII', data)
    if base + data_size != directory or directory + map_size != len(data):
        raise ValueError('invalid FNT sections')
    types, names = unpack_from('>HH', data, directory + 24)
    types += directory
    names += directory
    count, font_type, entries, refs = unpack_from('>H4sHH', data, types)
    if count or font_type != b'FONT' or types + refs + 12 * (entries + 1) > names:
        raise ValueError('unexpected FNT map')
    result = []
    for offset in range(types + refs, types + refs + 12 * (entries + 1), 12):
        ident, name_at, payload, _ = unpack_from('>hHII', data, offset)
        pos = names + name_at
        payload_at = base + (payload & 0xffffff)
        size, = unpack_from('>I', data, payload_at)
        if not names <= pos < pos + 1 + data[pos] <= len(data) or payload_at + 4 + size > directory:
            raise ValueError('invalid FNT reference')
        fields = data[pos+1:pos+1+data[pos]].decode('ascii').strip('.;')
        metadata = dict(item.split(':', 1) for item in fields.split(';') if ':' in item)
        result.append({'id': ident, 'name': metadata.get('n'), 'family': metadata.get('b'),
                       'points': metadata.get('p'), 'style': metadata.get('s'),
                       'resource_attributes': payload >> 24, 'payload_size': size})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private', type=Path, help='directory holding the archives and 7-Zip extractions')
    args = parser.parse_args()
    path = args.private
    with ZipFile(path / 'dm305dk9.zip') as archive:
        disk9 = {name: identity(archive.read(name)) for name in sorted(archive.namelist())}
    result = {'disk9': disk9, 'publisher': {}, 'font_libraries': {}}
    for image in sorted((path / 'publisher').rglob('FPDISK?.IMG')):
        data = image.read_bytes()
        files = fat12(data)
        assert files == {p.name: p.read_bytes() for p in (path / image.stem).iterdir() if p.is_file()}
        result['publisher'][image.name] = {**identity(data), 'files': {
            name: identity(content) for name, content in sorted(files.items())
        }}
        for name, content in files.items():
            if name.endswith('.FNT'):
                result['font_libraries'][name] = {'file_count': len(fnt(content)), 'fonts': fnt(content)}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
