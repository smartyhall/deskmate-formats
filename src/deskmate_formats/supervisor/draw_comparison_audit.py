"""Validate the Git-only Draw visual comparison publication exception."""
from binascii import crc32
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
from struct import unpack, unpack_from
from xml.etree import ElementTree
import zlib


TREE = Path('examples/draw-comparison/v1')
FIXTURES = 'tests/fixtures/application-generated/draw/'
FEATURED = ('primitives-styles', 'technical-plan', 'compound-landscape', 'typography')
DIAGNOSTIC = ('d01', 'd02', 'd04', 'd05', 'd06', 'd07c', 'd09', 'd10', 'd11', 'd12',
              'd16a', 'd16b', 'd17', 'd18', 'd19', 'd20', 'd21', 'd22', 'd23')
KINDS = ('native.png', 'renderer.png', 'diff.png', 'renderer.svg')
BASELINE = 'baseline-pr120'
REVISION = '5e1b24f8d8d262ac165b125474f7807163afbcc1'
LICENSE = 'GPL-3.0-or-later OR CC-BY-4.0'
MAX_FILE = 2 * 1024 * 1024
MAX_MILESTONE = 32 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024
MAX_PIXELS = 1_048_576
PNG = b'\x89PNG\r\n\x1a\n'


def require(condition, message):
    if not condition:
        raise ValueError('Draw comparison: ' + message)


def digest(value, width=64):
    return isinstance(value, str) and re.fullmatch(f'[0-9a-f]{{{width}}}', value) is not None


def regular_path(root, relative):
    path = root / relative
    require(all(not p.is_symlink() and not p.is_junction()
                for p in (path, *path.parents) if p.is_relative_to(root)),
            f'symlink or junction at {relative}')
    return path


def unique_keys(pairs):
    result = dict(pairs)
    require(len(result) == len(pairs), 'duplicate JSON key')
    return result


def read_json(root, relative):
    path = regular_path(root, relative)
    require(path.is_file() and path.stat().st_size <= MAX_FILE, f'missing or oversized {relative}')
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_keys)


def case_sources(spec, fixtures):
    require(spec.get('schema_version') == 1 and spec.get('suite_version') == 'v1'
            and spec.get('baseline_renderer_revision') == REVISION, 'invalid frozen suite')
    result = {}
    for key, expected in (('featured_cases', FEATURED), ('diagnostic_draw_fixtures', DIAGNOSTIC)):
        cases = spec[key]
        require([item['id'] for item in cases] == list(expected), f'unexpected identities in {key}')
        for item in cases:
            file = item['path']
            require(re.fullmatch(FIXTURES + r'[a-z0-9-]+\.fig', file) is not None
                    and (key != 'diagnostic_draw_fixtures' or file == FIXTURES + item['id'] + '.fig'),
                    f'noncanonical FIG source {file}')
            fixture = fixtures.get(file, {})
            require(item['status'] == 'native-saved' and digest(item['sha256'])
                    and fixture.get('synthetic_data') is True
                    and fixture.get('sha256') == item['sha256']
                    and fixture.get('size') == item['size'],
                    f'unpinned synthetic FIG source {file}')
            result[item['id']] = item
    require(len({item['path'] for item in result.values()}) == len(result), 'duplicated FIG source')
    return result


def image_size(width, height):
    return (type(width) is int and type(height) is int
            and 0 < width <= 2048 and 0 < height <= 2048 and width * height <= MAX_PIXELS)


def comparison_manifest(root, fixtures):
    base = regular_path(root, TREE)
    if not base.exists():
        return {}, set()
    paths = sorted(base.glob('*/manifest.json'))
    suite_path = TREE.parent / 'suite-v1.json'
    if not paths and not regular_path(root, suite_path).exists():
        return {}, set()
    sources = case_sources(read_json(root, suite_path), fixtures)
    index, metadata = {}, set()
    total = 0
    require(base / BASELINE / 'manifest.json' in paths, 'missing pinned baseline')
    for path in paths:
        relative = path.relative_to(root)
        milestone = path.parent.name
        require(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+){0,5}', milestone) is not None,
                f'invalid milestone {milestone}')
        manifest = read_json(root, relative)
        require(manifest['schema_version'] == 1 and manifest['milestone'] == milestone
                and manifest['suite_version'] == 'v1'
                and manifest['publication'] == 'original-synthetic-drawing-crops'
                and digest(manifest['renderer_revision'], 40)
                and (milestone != BASELINE or manifest['renderer_revision'] == REVISION),
                f'invalid provenance for {milestone}')
        cases = manifest['cases']
        require([case['id'] for case in cases] == list(sources), 'missing or duplicate case')
        metadata.update((relative.as_posix(), relative.as_posix() + '.license',
                         (relative.parent / 'README.md').as_posix(),
                         (relative.parent / 'README.md.license').as_posix()))
        subtotal = 0
        for case in cases:
            source = sources[case['id']]
            capture = case['native_capture']
            width, height = case['dimensions']
            require(case['source_path'] == source['path'] and case['source_sha256'] == source['sha256']
                    and digest(capture['framebuffer_sha256']) and capture['source_role'] in
                    ('fresh-native-reopen', 'verified-identical-native-recapture', 'prior-native-reference')
                    and (capture['source_role'] != 'prior-native-reference' or capture.get('reuse_reason'))
                    and image_size(width, height), f'invalid source, capture or size for {case["id"]}')
            crop = capture['crop_xyxy']
            require(len(crop) == 4 and all(type(n) is int for n in crop)
                    and 0 <= crop[0] < crop[2] <= 2048 and 0 <= crop[1] < crop[3] <= 2048
                    and (crop[2] - crop[0], crop[3] - crop[1]) == (width, height),
                    f'invalid crop for {case["id"]}')
            artifacts = case['artifacts']
            require(set(artifacts) == set(KINDS), f'incomplete outputs for {case["id"]}')
            for kind, artifact in artifacts.items():
                rel = (relative.parent / f'{case["id"]}-{kind}').as_posix()
                require(artifact['path'] == rel and rel not in index and digest(artifact['sha256'])
                        and type(artifact['size']) is int and 0 < artifact['size'] <= MAX_FILE
                        and artifact['license'] == LICENSE, f'invalid artifact {rel}')
                index[rel] = artifact | {'dimensions': (width, height)}
                metadata.add(rel + '.license')
                subtotal += artifact['size']
        require(subtotal <= MAX_MILESTONE, 'milestone exceeds byte budget')
        total += subtotal
    require(total <= MAX_TOTAL, 'library exceeds byte budget')
    return index, metadata


def check_png(data, dimensions):
    require(data.startswith(PNG), 'invalid PNG signature')
    cursor = len(PNG)
    parts = []
    width, height = dimensions
    channels = 0
    while cursor + 12 <= len(data):
        size, kind = unpack_from('>I4s', data, cursor)
        end = cursor + 12 + size
        require(end <= len(data), 'truncated PNG chunk')
        payload = data[cursor + 8:end - 4]
        require(crc32(kind + payload) == unpack_from('>I', data, end - 4)[0], 'invalid PNG CRC')
        if cursor == len(PNG):
            require(kind == b'IHDR' and size == 13, 'invalid PNG header')
            w, h, bits, pixel_type, compression, filtering, interlace = unpack('>IIBBBBB', payload)
            require((w, h) == dimensions and image_size(w, h) and bits == 8 and pixel_type in (2, 6)
                    and (compression, filtering, interlace) == (0, 0, 0), 'invalid PNG pixel profile')
            channels = 3 if pixel_type == 2 else 4
        elif kind == b'IDAT':
            require(size > 0, 'empty PNG data chunk')
            parts.append(payload)
        elif kind == b'IEND':
            require(size == 0 and end == len(data) and parts, 'invalid PNG end or trailing bytes')
            break
        else:
            raise ValueError('Draw comparison: forbidden PNG chunk')
        cursor = end
    else:
        raise ValueError('Draw comparison: missing PNG end')
    stride = 1 + channels * width
    expected = stride * height
    decoder = zlib.decompressobj()
    try:
        raw = decoder.decompress(b''.join(parts), expected + 1)
    except zlib.error as exc:
        raise ValueError('Draw comparison: invalid compressed PNG data') from exc
    require(len(raw) == expected and decoder.eof and not decoder.unused_data
            and not decoder.unconsumed_tail and all(value <= 4 for value in raw[::stride]),
            'invalid PNG scanlines or excess compressed data')


SVG_ATTRIBUTES = {
    'svg': {'viewBox'}, 'desc': set(),
    'g': {'aria-label', 'stroke', 'fill', 'stroke-width'},
    'rect': {'x', 'y', 'width', 'height', 'fill', 'stroke', 'stroke-width', 'vector-effect'},
    'ellipse': {'cx', 'cy', 'rx', 'ry', 'fill', 'stroke', 'stroke-width', 'vector-effect'},
    'line': {'x1', 'y1', 'x2', 'y2', 'stroke', 'stroke-width', 'vector-effect'},
    'path': {'d', 'fill', 'stroke', 'stroke-width', 'vector-effect'},
    'polygon': {'points', 'fill', 'stroke', 'stroke-width', 'vector-effect'},
    'polyline': {'points', 'fill', 'stroke', 'stroke-width', 'vector-effect'},
}
NUMBER = r'-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?'
QUADRATIC_PATH = re.compile(rf'M {NUMBER} {NUMBER} Q(?: {NUMBER}){{4}}')
OUTLINE_CONTOUR = re.compile(rf'M(?: {NUMBER}){{2}}(?: L(?: {NUMBER}){{2}}| C(?: {NUMBER}){{6}})+ Z')


def checked_path(value):
    if QUADRATIC_PATH.fullmatch(value):
        return True
    pos = 0
    while match := OUTLINE_CONTOUR.match(value, pos):
        pos = match.end()
        if pos == len(value):
            return True
        if value[pos] != ' ':
            return False
        pos += 1
    return False


def check_svg(data):
    require(b'<!' not in data and b'<?' not in data, 'SVG declarations are forbidden')
    try:
        svg = ElementTree.fromstring(data.decode('utf-8'))
    except (ElementTree.ParseError, UnicodeError) as exc:
        raise ValueError('Draw comparison: invalid SVG') from exc
    ns = '{http://www.w3.org/2000/svg}'
    require(svg.tag == ns + 'svg', 'invalid SVG root')
    for node in svg.iter():
        name = node.tag.removeprefix(ns)
        require(node.tag.startswith(ns) and name in SVG_ATTRIBUTES
                and SVG_ATTRIBUTES[name].issuperset(node.attrib) and (node is svg or name != 'svg'),
                'forbidden SVG element or attribute')
        for key, value in node.attrib.items():
            if key in ('fill', 'stroke'):
                valid = re.fullmatch(r'none|#[0-9a-f]{6}', value)
            elif key == 'vector-effect':
                valid = value == 'non-scaling-stroke'
            elif key == 'viewBox':
                valid = re.fullmatch(rf'{NUMBER}(?: {NUMBER}){{3}}', value)
            elif key == 'points':
                pair = rf'{NUMBER},{NUMBER}'
                valid = all(re.fullmatch(pair, point) for point in value.split())
            elif key == 'd':
                valid = checked_path(value)
            elif key == 'aria-label':
                valid = len(value) <= 256
            else:
                valid = re.fullmatch(NUMBER, value)
            require(valid, f'forbidden SVG {key} value')
        require(not (node.tail or '').strip() and (name == 'desc' or not (node.text or '').strip()),
                'unexpected SVG text')


def check_artifact(root, rel, entry):
    path = regular_path(root, rel)
    require(path.stat().st_size == entry['size'], f'wrong size for {rel}')
    data = path.read_bytes()
    require(len(data) == entry['size'] and sha256(data).hexdigest() == entry['sha256'],
            f'wrong digest for {rel}')
    notice = regular_path(root, rel + '.license')
    require(notice.is_file() and notice.stat().st_size <= 4096, f'missing license for {rel}')
    lines = notice.read_text(encoding='utf-8').splitlines()
    require(f'SPDX-License-Identifier: {LICENSE}' in lines
            and any(line.startswith('SPDX-FileCopyrightText: ') for line in lines),
            f'incorrect license for {rel}')
    if path.suffix == '.png':
        check_png(data, entry['dimensions'])
    else:
        check_svg(data)


def check_complete(root, index, found):
    metadata_only = (root / 'PKG-INFO').is_file() and not (root / '.git').exists() and not found
    require(found == set(index) or metadata_only, 'declared artifacts are missing')


def packaged_projection(name):
    path = PurePosixPath(name)
    length = len(TREE.parts)
    return path.suffix.lower() == '.svg' and (
        path.parts[:length] == TREE.parts or path.parts[1:length + 1] == TREE.parts
    )
