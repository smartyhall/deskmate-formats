"""Audit publication boundaries, preserving documented application-generated fixtures."""
from pathlib import Path, PurePosixPath
from binascii import crc32
import ast
import hashlib
import json
import re
from struct import unpack_from
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if (ROOT / 'src/deskmate_formats').is_dir():
    sys.path.insert(0, str(ROOT / 'src'))
from deskmate_formats.supervisor import draw_comparison_audit as draw_audit

EXCLUDED = {'.git', 'build', 'dist', 'local-results', 'private-fixtures', '.ruff_cache'}
FIXTURE_DIR = Path('tests/fixtures/application-generated')
LISTENING_DIR = Path('examples/music-listening/v1')
LISTENING_CASES = ('major-scale', 'minor-scale', 'chromatic-scale', 'major-cadence', 'minor-cadence')
LISTENING_BANKS = {
    'synthetic': ({9, 10, 11}, 'independent-synthetic-performance'),
    'oem': ({1, 2, 3, 4}, 'original-performance-using-tandy-instruments'),
}
LISTENING_LICENSE = 'GPL-3.0-or-later OR CC-BY-4.0'
MIN_LISTENING_FRAMES = 4 * 48_000
MAX_LISTENING_FRAMES = 20 * 48_000
MAX_MILESTONE_BYTES = 26 * 1024 * 1024
MAX_LISTENING_BYTES = 128 * 1024 * 1024
DATA_EXT = {'.cal', '.cln', '.adr', '.fil', '.pcl', '.doc', '.fig', '.wks', '.snd', '.sng'}
SYNTHETIC_DB = 'information-center/rsx-native-two-messages.db'
SYNTHETIC_NOTE_STORAGE = {
    'corkboard/rsx-two-lines/DMCORKBD',
    'corkboard/rsx-information-center-edit/DMCORKBD',
    'corkboard/rsx-cleared/DMCORKBD',
    'corkboard/305-alternate/DMCORKBD',
    'notebook/rsx-two-loans.db',
    'notebook/rsx-edited-loan.db',
    'information-center/rsx-native-removed-pilot.db',
    'collections/rsx-two-items.col',
    'collections/rsx-edited-item.col',
}
SYNTHETIC_PRINT_COMPANION = {
    'print-companion/W0414155.CRD',
    'print-companion/W0414325.NOT',
    'print-companion/W0415039.NOT',
    'print-companion/W0414444.PER',
    'print-companion/W0414359.NTG',
    'print-companion/card-ibm-graphic.prn',
    'print-companion/card-hp-laserjet.prn',
}
SYNTHETIC_FF1 = 'draw/typography-lab-grid.ff1'
SYNTHETIC_MID = {
    f'midimapper/{case}-midimapper-6.38.mid'
    for case in ('major-scale', 'minor-scale', 'pitch-spelling', 'timing-100-audible',
                 'timing-100-silent', 'channel-control', 'polyphonic-trio', 'alternate-endings',
                 'enharmonic-boundary', 'structural-control', 'timing-100-480-silent', 'timing-100-480-delay10',
                 'converter-octave-plus-one')
}
SYNTHETIC_HDS = {
    f'dm-music/{control}-dm-music-1.04.hds'
    for control in (
        'major-scale', 'major-scale-plus-one', 'duration-tempo', 'accidentals', 'alternate-endings',
        'batch-listening-chromatic-scale-v1', 'batch-listening-major-cadence-v1',
        'batch-listening-minor-cadence-v1', 'batch-listening-minor-scale-v1',
        'batch-listening-oem-chromatic-scale-v1', 'batch-listening-oem-major-cadence-v1',
        'batch-listening-oem-major-scale-v1', 'batch-listening-oem-minor-cadence-v1',
        'batch-listening-oem-minor-scale-v1', 'batch-marker-a-native',
        'batch-region-hold-tool-generated', 'batch-m01', 'batch-m02', 'batch-m03',
        'batch-m08', 'batch-m10', 'batch-m11', 'batch-m12', 'batch-m13', 'batch-m14',
        'batch-mbar', 'batch-mduet', 'batch-medit', 'batch-mextra', 'batch-mgrow',
        'batch-mloop', 'batch-mmid', 'batch-mreopen', 'batch-mtimes', 'batch-mtrio',
        'batch-mvalues', 'batch-mvol',
    )
} | {
    f'midimapper/{case}-tool-generated.hds'
    for case in ('pitch-spelling', 'timing-100', 'channel-control', 'enharmonic-boundary', 'structural-control')
}
TYPOGRAPHY_DIR = Path('examples/typography-comparison/v1')
SITE_IMAGE_DIR = Path('website/src/assets/reference')
SITE_IMAGE_MANIFEST = Path('website/reference-images.json')
# Screenshots attached to an open pull request for review. They are never copied
# into the generated site and never packaged (MANIFEST.in excludes PNGs
# globally); the allowance is path-specific so no other image can borrow it.
REVIEW_IMAGE_DIR = Path('docs/site/review')
SITE_IMAGE_MAX_BYTES = 6 * 1024 * 1024
SITE_IMAGE_MAX_PIXELS = 4_000_000
SITE_IMAGE_ORIGINS = {
    'synthetic-project-illustration',
    'documentary-software-ui-capture',
    'publisher-distributed-illustration',
}
TYPOGRAPHY_IMAGES = {
    f'{case}-{kind}.png' for case in ('lab-grid', 'bonum', 'liberation-mono')
    for kind in ('native', 'independent')
}
PRIVATE_SPOOL_FILES = {'events.jsonl', 'writer.lock'}
PRIVATE_SPOOL_FILES.update(
    database + suffix for database in ('operations.sqlite3', 'task-queue.sqlite3')
    for suffix in ('', '-journal', '-wal', '-shm')
)
TELEMETRY_FIXTURE_DIR = 'tests/fixtures/codex-exec-0.166.0/'
TELEMETRY_FIXTURES = {
    'anomalies.jsonl': 'af47f774319320c7e5e6d8cefb903e2f711e93f20ec6a529eabe3d81ebbd1a2b',
    'failure.jsonl': 'c780a82c87b33b7ce875da451614fa17a562eaa2b9a844bf7df516865e0b6576',
    'open-turn.jsonl': 'a7c8cfc883c658b7b3911224832d68b0f7f10433e5c91b088fde88298c0b02ae',
    'success.jsonl': '3a453f3cfa512c9d53e1ff6366112ac102d0bb257f4902ff697f081b3bb216c9',
}
BAD_EXT = {'.exe', '.com', '.dll', '.img', '.ima', '.iso', '.zip', '.7z',
           '.png', '.pdf', '.pdm', '.res', '.r89', '.hlp',
           '.tut', '.nvr', '.rom', '.vhd', '.vhdx', '.hdi', '.raw', '.token', '.wav', '.mid',
           '.ff1', '.otf', '.ttf', '.prn', '.hds', '.db', '.col', '.crd', '.not', '.per', '.ntg'} | DATA_EXT
PATTERNS = {
    'host Windows user path': r'(?i)[a-z]:[\\/]Users[\\/]',
    'host POSIX user path': r'/(?:home|Users)/[^/\s]+',
    'GitHub credential': r'gh' + r'[pousr]_[A-Za-z0-9]{20,}',
    'fine-grained credential': r'github_' + r'pat_[A-Za-z0-9_]{20,}',
    'API credential': r'sk-' + r'[A-Za-z0-9]{20,}',
    'private key': r'-----BEGIN ' + r'(?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'credential in URL': r'https?://[^\s/@:]+:[^\s/@]+@',
    'archive access query': r'(?i)[?&](?:access_token|auth_token|api_key|token)=[A-Za-z0-9_%.-]{8,}',
}


def site_image_manifest():
    """Allow only declared site illustrations; never infer publication rights from origin."""
    location = ROOT / SITE_IMAGE_MANIFEST
    if not location.is_file():
        return {}
    spec = json.loads(location.read_text(encoding='utf-8'))
    if spec.get('schema_version') != 1 or type(spec.get('images')) is not list:
        raise ValueError('invalid site image manifest')
    entries, ids = {}, set()
    for entry in spec['images']:
        if not isinstance(entry, dict):
            raise ValueError('invalid site image entry')
        name = entry.get('path')
        if (not isinstance(name, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_./-]*\.png', name)
                or '..' in PurePosixPath(name).parts or str(PurePosixPath(name)) != name
                or len(name) > 160):
            raise ValueError('unsafe site image path')
        rel = (SITE_IMAGE_DIR / name).as_posix()
        identifier = entry.get('id')
        if (rel in entries or not isinstance(identifier, str)
                or not re.fullmatch(r'ui\.[a-z0-9]+(?:[.-][a-z0-9]+)*', identifier)
                or identifier in ids):
            raise ValueError('duplicate or invalid site image identifier')
        ids.add(identifier)
        if not is_digest(entry.get('sha256')) or not is_digest(entry.get('source_sha256')):
            raise ValueError('missing site image digest or source provenance')
        width, height = entry.get('width'), entry.get('height')
        if (type(width) is not int or type(height) is not int or width < 1 or height < 1
                or width > 4096 or height > 4096 or width * height > SITE_IMAGE_MAX_PIXELS
                or type(entry.get('size')) is not int or not 0 < entry['size'] <= SITE_IMAGE_MAX_BYTES):
            raise ValueError('invalid site image dimensions or size')
        if entry.get('origin') not in SITE_IMAGE_ORIGINS:
            raise ValueError('unreviewed site image origin')
        for key in ('caption', 'alt', 'source_id', 'rights_note'):
            value = entry.get(key)
            if not isinstance(value, str) or not value.strip() or len(value) > 500:
                raise ValueError('missing site image ' + key)
            if key == 'source_id' and not re.fullmatch(r'[a-zA-Z0-9_.-]{8,100}', value):
                raise ValueError('invalid site image source identifier')
            if any(re.search(pattern, value) for pattern in PATTERNS.values()):
                raise ValueError('private data in site image metadata')
        entries[rel] = entry
    return entries


def check_site_image(rel, data, entry):
    """Validate documented PNG bytes; reject arbitrary binary and embedded metadata."""
    if len(data) != entry['size'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
        raise ValueError('site image digest or size mismatch: ' + rel)
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('site image is not a PNG: ' + rel)
    allowed = {b'IHDR', b'PLTE', b'tRNS', b'IDAT', b'IEND', b'gAMA', b'sRGB', b'pHYs'}
    offset, first, last, has_data = 8, True, False, False
    while offset + 12 <= len(data):
        length, kind = unpack_from('>I4s', data, offset)
        end = offset + 12 + length
        if kind not in allowed or end > len(data):
            raise ValueError('unsafe site PNG chunk or metadata: ' + rel)
        payload = data[offset + 8:end - 4]
        if crc32(kind + payload) != unpack_from('>I', data, end - 4)[0]:
            raise ValueError('site PNG CRC mismatch: ' + rel)
        if first:
            if kind != b'IHDR' or length != 13:
                raise ValueError('site PNG header missing: ' + rel)
            width, height, depth, color, compression, filtering, interlace = unpack_from('>IIBBBBB', payload)
            if ((width, height) != (entry['width'], entry['height'])
                    or (depth, color) not in {(8, 2), (8, 3), (8, 6), (4, 3), (2, 3), (1, 3)}
                    or (compression, filtering, interlace) != (0, 0, 0)):
                raise ValueError('site PNG header dimensions or profile mismatch: ' + rel)
        elif kind == b'IHDR':
            raise ValueError('duplicate site PNG header: ' + rel)
        if kind == b'IDAT':
            has_data = True
        if kind == b'IEND':
            if length != 0 or end != len(data) or not has_data:
                raise ValueError('site PNG malformed end: ' + rel)
            last = True
            break
        first = False
        offset = end
    if not last:
        raise ValueError('site PNG missing end: ' + rel)

def source_files():
    for path in sorted(ROOT.rglob('*')):
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDED or part.startswith('.venv') or
               part.endswith('.egg-info') or part == '__pycache__' for part in rel.parts):
            continue
        if path.is_symlink() or path.is_junction() or path.is_file():
            yield path


def native_text_export(path):
    return (path == FIXTURE_DIR / 'aol/rsxnote.txt'
            or (path.parent == FIXTURE_DIR / 'text' and path.suffix.lower() == '.txt'))


def fixture_manifest():
    entries = json.loads((ROOT / FIXTURE_DIR / 'manifest.json').read_text(encoding='utf-8'))['fixtures']
    if not isinstance(entries, list):
        raise ValueError('fixture manifest must be a list')
    index = {}
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError('invalid fixture entry')
        name = item.get('path')
        if not isinstance(name, str) or not name or '\\' in name or ':' in name:
            raise ValueError('invalid fixture path')
        rel = PurePosixPath(name)
        if rel.is_absolute() or '..' in rel.parts or len(rel.parts) < 2:
            raise ValueError('unsafe fixture path: ' + name)
        if (rel.suffix.lower() not in DATA_EXT and not native_text_export(FIXTURE_DIR / rel)
                and name not in (SYNTHETIC_DB, SYNTHETIC_FF1)
                and name not in SYNTHETIC_NOTE_STORAGE and name not in SYNTHETIC_PRINT_COMPANION
                and name not in SYNTHETIC_MID and name not in SYNTHETIC_HDS):
            raise ValueError('unexpected fixture extension: ' + name)
        if (FIXTURE_DIR / name).as_posix() in index or not re.fullmatch(r'[0-9a-f]{64}', str(item.get('sha256', ''))):
            raise ValueError('duplicate or invalid fixture digest: ' + name)
        if type(item.get('size')) is not int or item['size'] < 0:
            raise ValueError('invalid fixture size: ' + name)
        if item.get('synthetic_data') is not True or not item.get('origin'):
            raise ValueError('fixture must declare synthetic origin: ' + name)
        index[(FIXTURE_DIR / name).as_posix()] = item
    return index


def check_telemetry_file(path, data):
    if PurePosixPath(path).suffix.lower() not in ('.jsonl', '.ndjson'):
        return False
    digest = TELEMETRY_FIXTURES.get(path.removeprefix(TELEMETRY_FIXTURE_DIR))
    if not path.startswith(TELEMETRY_FIXTURE_DIR) or digest is None:
        raise ValueError('unlisted JSONL trace: ' + path)
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('synthetic JSONL fixture digest mismatch: ' + path)
    return True


def is_digest(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def check_listening_path(path):
    if any(parent.is_symlink() or parent.is_junction()
           for parent in (path, *path.parents) if parent.is_relative_to(ROOT)):
        raise ValueError(f'symlink is not permitted: {path.relative_to(ROOT)}')


def listening_json(path):
    check_listening_path(path)
    if path.stat().st_size > 1_000_000:
        raise ValueError(f'oversized listening manifest: {path.relative_to(ROOT)}')
    return json.loads(path.read_text(encoding='utf-8'))


def listening_manifest(fixtures):
    base = ROOT / LISTENING_DIR
    check_listening_path(base)
    if not base.exists():
        return {}, set()
    spec = listening_json(base.parent / 'suite-v1.json')
    if spec['schema_version'] != 1 or set(spec['banks']) != set(LISTENING_BANKS):
        raise ValueError('unsupported listening suite or bank')
    banks = {}
    for bank, (slots, rights) in LISTENING_BANKS.items():
        instruments = spec['banks'][bank]
        index = {entry['slot']: entry['sha256'] for entry in instruments}
        if (set(index) != slots or len(instruments) != len(slots)
                or not all(is_digest(digest) for digest in index.values())):
            raise ValueError(f'invalid listening instrument bank: {bank}')
        for entry in instruments:
            if bank == 'synthetic':
                path = entry['fixture_path']
                if (not path.startswith(f'{FIXTURE_DIR.as_posix()}/sound/')
                        or not path.endswith('.snd')
                        or fixtures.get(path, {}).get('sha256') != entry['sha256']):
                    raise ValueError(f'unpinned listening instrument: {path}')
            elif not entry['archive_member'] or not entry['source_archive']:
                raise ValueError('missing OEM listening instrument provenance')
        banks[bank] = (index, rights)
    cases = spec['cases']
    expected = {case: 'synthetic' for case in LISTENING_CASES}
    expected.update({f'oem-{case}': 'oem' for case in LISTENING_CASES})
    if len(cases) != len(expected) or {item['id']: item['bank'] for item in cases} != expected:
        raise ValueError('unexpected listening case identities')
    scores = {}
    for case in cases:
        path = case['score_path']
        if (not path.startswith(f'{FIXTURE_DIR.as_posix()}/music/') or not path.endswith('.sng')
                or not is_digest(case['score_sha256'])
                or fixtures.get(path, {}).get('sha256') != case['score_sha256']):
            raise ValueError(f'unpinned listening score: {path}')
        scores[case['id']] = case['score_sha256']

    index, metadata = {}, set()
    baseline_path = base / 'baseline-pr118/manifest.json'
    manifests = sorted(base.glob('*/manifest.json'), key=lambda path: (path != baseline_path, path))
    if not manifests or manifests[0] != baseline_path:
        raise ValueError('missing baseline listening manifest')
    total = 0
    for manifest_path in manifests:
        milestone = manifest_path.parent.name
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+){0,5}', milestone):
            raise ValueError(f'invalid listening milestone: {milestone}')
        metadata.update({manifest_path.relative_to(ROOT).as_posix(),
                         manifest_path.relative_to(ROOT).as_posix() + '.license'})
        manifest = listening_json(manifest_path)
        if manifest['schema_version'] != 1 or manifest['milestone'] != milestone:
            raise ValueError('invalid listening milestone manifest')
        if (not is_digest(manifest['emulator_sha256']) or not is_digest(manifest['renderer_sha256'])
                or not re.fullmatch(r'[0-9a-f]{40}', manifest['renderer_revision'])
                or manifest['authorization'] != 'operator-2026-11-18'):
            raise ValueError('invalid listening milestone provenance')
        if (milestone == 'baseline-pr118'
                and manifest['renderer_revision'] != 'f9fe4f174790b6fa19801d5c107994db8e57f0dc'):
            raise ValueError('unexpected baseline renderer revision')
        pairs = set()
        milestone_bytes = 0
        for entry in manifest['recordings']:
            case, role = entry['case'], entry['playback']
            if case not in expected or role not in {'native', 'renderer'} or (case, role) in pairs:
                raise ValueError('unknown or duplicate listening recording')
            pairs.add((case, role))
            bank = expected[case]
            bank_hashes, rights = banks[bank]
            rel = (LISTENING_DIR / milestone / f'{case}-{role}.wav').as_posix()
            canonical = (LISTENING_DIR / 'baseline-pr118' / f'{case}-native.wav').as_posix()
            reuse = (role == 'native' and milestone != 'baseline-pr118' and entry['path'] == canonical)
            if ((entry['path'] != rel and not reuse) or entry['bank'] != bank or entry['classification'] != rights
                    or entry['license'] != LISTENING_LICENSE or entry['score_sha256'] != scores[case]
                    or entry['instrument_sha256'] != {str(k): v for k, v in bank_hashes.items()}
                    or not is_digest(entry['sha256'])):
                raise ValueError(f'invalid listening identity or rights: {rel}')
            frames, size = entry['frames'], entry['size']
            if (type(frames) is not int or not MIN_LISTENING_FRAMES <= frames <= MAX_LISTENING_FRAMES
                    or type(size) is not int or size != frames * 2 + 44):
                raise ValueError(f'invalid listening size: {rel}')
            if role == 'native':
                start = entry['first_capture_frame']
                if (entry['tap'] != 'pssj-dac-pre-mix' or not is_digest(entry['raw_sha256'])
                        or type(start) is not int or start < 0
                        or type(entry['raw_frames']) is not int or start + frames > entry['raw_frames']):
                    raise ValueError(f'invalid native capture provenance: {rel}')
            elif (not is_digest(entry['render_pcm_sha256']) or entry['rate'] != 48_000
                    or not entry['model']
                    or (milestone == 'baseline-pr118' and entry['model'] != 'rsx-dac-approximation-v1')):
                raise ValueError(f'invalid independent render provenance: {rel}')
            if reuse:
                baseline = index.get(canonical)
                if (entry.get('native_reference') != 'fresh-byte-identical'
                        or not baseline
                        or any(entry[field] != baseline[field] for field in ('frames', 'size', 'sha256'))):
                    raise ValueError(f'unverified canonical listening reference: {rel}')
            else:
                index[rel] = entry
                metadata.add(rel + '.license')
            milestone_bytes += size
        if pairs != {(case, role) for case in expected for role in ('native', 'renderer')}:
            raise ValueError(f'incomplete listening comparison: {milestone}')
        if milestone_bytes > MAX_MILESTONE_BYTES:
            raise ValueError(f'listening milestone exceeds byte limit: {milestone}')
        total += milestone_bytes
    if total > MAX_LISTENING_BYTES:
        raise ValueError('listening suite exceeds aggregate byte limit')
    return index, metadata


def check_listening_wav(rel, data, entry):
    if len(data) != entry['size'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
        raise ValueError('listening WAV digest or size mismatch: ' + rel)
    header = unpack_from('<4sI4s4sIHHIIHH4sI', data)
    if header != (b'RIFF', len(data) - 8, b'WAVE', b'fmt ', 16, 1, 1, 48_000,
                  96_000, 2, 16, b'data', len(data) - 44):
        raise ValueError('expected PCM-only 48 kHz mono 16-bit WAV: ' + rel)
    if entry['playback'] == 'renderer':
        payload_start, payload_frames = entry['first_render_frame'], entry['render_frames']
        if (type(payload_start) is not int or type(payload_frames) is not int
                or payload_start < 0 or payload_frames <= 0
                or payload_start + payload_frames > entry['frames']):
            raise ValueError('invalid listening render frame range: ' + rel)
        lo, hi = 44 + payload_start * 2, 44 + (payload_start + payload_frames) * 2
        if (any(data[44:lo]) or any(data[hi:])
                or hashlib.sha256(data[lo:hi]).hexdigest() != entry['render_pcm_sha256']):
            raise ValueError('listening render PCM or zero padding mismatch: ' + rel)
    sidecar = ROOT / (rel + '.license')
    check_listening_path(sidecar)
    notice = sidecar.read_text(encoding='utf-8')
    if f'SPDX-License-Identifier: {LISTENING_LICENSE}' not in notice.splitlines():
        raise ValueError('missing listening REUSE license: ' + rel)
    if entry['bank'] == 'oem' and 'Tandy' not in notice:
        raise ValueError('missing underlying Tandy material notice: ' + rel)


def typography_manifest():
    relative = TYPOGRAPHY_DIR / 'manifest.json'
    if not (ROOT / relative).exists():
        return {}, set()
    manifest = draw_audit.read_json(ROOT, relative)
    if manifest.get('schema_version') != 1 or set(manifest.get('images', {})) != TYPOGRAPHY_IMAGES:
        raise ValueError('unexpected typography comparison manifest')
    metadata = {(TYPOGRAPHY_DIR / name).as_posix()
                for name in ('manifest.json', 'manifest.json.license', 'README.md', 'README.md.license')}
    result = {}
    for name, entry in manifest['images'].items():
        if (entry.get('dimensions') != [640, 418] or not draw_audit.digest(entry.get('sha256'))
                or type(entry.get('size')) is not int or not 0 < entry['size'] <= 512 * 1024):
            raise ValueError('invalid typography comparison image identity: ' + name)
        path = (TYPOGRAPHY_DIR / name).as_posix()
        result[path] = {**entry, 'dimensions': tuple(entry['dimensions'])}
        metadata.add(path + '.license')
    return result, metadata


def audit():
    allowed = fixture_manifest()
    comparisons, comparison_metadata = draw_audit.comparison_manifest(ROOT, allowed)
    typography, typography_metadata = typography_manifest()
    comparisons.update(typography)
    comparison_metadata.update(typography_metadata)
    comparisons_found = set()
    site_images = site_image_manifest()
    site_images_found = set()
    listening, listening_metadata = listening_manifest(allowed)
    listening_found = set()
    found = set()
    count = 0
    telemetry_count = 0
    for path in source_files():
        rel_path = path.relative_to(ROOT)
        rel = rel_path.as_posix()
        if path.is_symlink() or path.is_junction():
            raise ValueError('symlink is not permitted: ' + rel)
        if path.name.lower() in PRIVATE_SPOOL_FILES:
            raise ValueError('private Observatory spool file: ' + rel)
        if rel in site_images:
            sidecar = ROOT / (rel + '.license')
            if not sidecar.is_file() or 'SPDX-License-Identifier:' not in sidecar.read_text(encoding='utf-8'):
                raise ValueError('site image requires accurate REUSE sidecar: ' + rel)
            check_site_image(rel, path.read_bytes(), site_images[rel])
            site_images_found.add(rel)
            count += 1
            continue
        if rel_path.is_relative_to(REVIEW_IMAGE_DIR):
            if rel.endswith('.png'):
                sidecar = ROOT / (rel + '.license')
                if not (sidecar.is_file() and 'SPDX-License-Identifier:' in
                        sidecar.read_text(encoding='utf-8')):
                    raise ValueError('review image requires a REUSE sidecar: ' + rel)
                count += 1
                continue
            if rel.endswith(('.png.license', '.md', '.md.license')):
                continue
            raise ValueError('unexpected review attachment: ' + rel)
        if rel_path.is_relative_to(SITE_IMAGE_DIR):
            if not (rel.endswith('.png.license') and rel[:-8] in site_images):
                raise ValueError('unlisted site image or sidecar: ' + rel)
        if rel in comparisons:
            draw_audit.check_artifact(ROOT, rel, comparisons[rel])
            comparisons_found.add(rel)
            count += 1
            continue
        if rel_path.is_relative_to(TYPOGRAPHY_DIR) and rel not in comparison_metadata:
            raise ValueError('unlisted typography comparison file: ' + rel)
        if rel_path.is_relative_to(draw_audit.TREE) and rel not in comparison_metadata:
            if rel_path.name not in ('README.md', 'README.md.license') or len(rel_path.parts) != 5:
                raise ValueError('unlisted Draw comparison file: ' + rel)
        if rel in listening:
            if path.stat().st_size != listening[rel]['size']:
                raise ValueError('listening WAV digest or size mismatch: ' + rel)
            check_listening_wav(rel, path.read_bytes(), listening[rel])
            listening_found.add(rel)
            count += 1
            continue
        if rel_path.is_relative_to(LISTENING_DIR) and rel not in listening_metadata:
            raise ValueError('unlisted listening file: ' + rel)
        if path.suffix.lower() in ('.wav', '.raw'):
            raise ValueError('excluded evidence/software type: ' + rel)
        data = path.read_bytes()
        telemetry_count += check_telemetry_file(rel, data)
        if rel in allowed:
            if data.startswith(b'MZ'):
                raise ValueError('executable disguised as fixture: ' + rel)
            entry = allowed[rel]
            if len(data) != entry['size'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise ValueError('fixture digest or size mismatch: ' + rel)
            if rel == (FIXTURE_DIR / SYNTHETIC_FF1).as_posix():
                from deskmate_formats.ff1 import serialize_resource
                from deskmate_formats.ff1_geometric import geometric_face

                if data != serialize_resource(geometric_face('Labgrid', face_id=28)):
                    raise ValueError('FF1 fixture does not reproduce from the independent generator: ' + rel)
            # Native binary structure is permitted, not credentials or host paths.
            for text_variant in (data.decode('latin-1'),
                                 data.replace(b'\x00', b'').decode('latin-1')):
                for label, pattern in PATTERNS.items():
                    if re.search(pattern, text_variant):
                        raise ValueError(label + ': ' + rel)
            found.add(rel)
            count += 1
            continue
        if (path.suffix.lower() in BAD_EXT or path.name.upper() == 'DMCORKBD'
                or native_text_export(rel_path) or path.name.startswith('.env')):
            raise ValueError('excluded evidence/software type: ' + rel)
        if data.startswith((b'MZ', bytes((3, 70, 73, 76)))):
            raise ValueError('software/database bytes outside fixture area: ' + rel)
        text = data.decode('utf-8')
        if '\0' in text:
            raise ValueError('binary content: ' + rel)
        for label, pattern in PATTERNS.items():
            if re.search(pattern, text):
                raise ValueError(label + ': ' + rel)
        if path.suffix == '.py':
            ast.parse(text, filename=rel)
        count += 1
    # An extracted sdist carries provenance metadata but intentionally omits the
    # Git-only binary research fixtures. A source checkout requires every entry.
    if found != set(allowed) and not (ROOT / 'PKG-INFO').is_file():
        raise ValueError('missing declared fixtures: ' + ', '.join(sorted(set(allowed) - found)))
    if listening_found != set(listening) and (
            listening_found or (ROOT / '.git').exists() or not (ROOT / 'PKG-INFO').is_file()):
        raise ValueError('missing declared listening WAVs')
    draw_audit.check_complete(ROOT, comparisons, comparisons_found)
    if site_images_found != set(site_images) and not (ROOT / 'PKG-INFO').is_file():
        raise ValueError('missing declared site images: ' +
                         ', '.join(sorted(set(site_images) - site_images_found)))
    # Git-only binary fixtures are excluded. Pinned synthetic JSONL ships in the sdist.
    for path in (ROOT / 'dist').glob('*'):
        if path.suffix == '.whl':
            with zipfile.ZipFile(path) as archive:
                members = [(n, archive.read(n)) for n in archive.namelist() if not n.endswith('/')]
        elif path.name.endswith('.tar.gz'):
            with tarfile.open(path, 'r:gz') as archive:
                members = [(m.name, archive.extractfile(m).read()) for m in archive.getmembers() if m.isfile()]
        else:
            raise ValueError('unexpected build artifact: ' + path.name)
        for name, data in members:
            if any(part in EXCLUDED or part.startswith('.venv') for part in Path(name).parts):
                raise ValueError('excluded directory in archive: ' + name)
            if (Path(name).suffix.lower() in BAD_EXT
                    or PurePosixPath(name).name.upper() == 'DMCORKBD'
                    or draw_audit.packaged_projection(name)
                    or native_text_export(Path(name.partition('/')[2]))
                    or native_text_export(Path(name))):
                raise ValueError('excluded file in archive: ' + name)
            if PurePosixPath(name).name.lower() in PRIVATE_SPOOL_FILES:
                raise ValueError('private Observatory spool file in archive: ' + name)
            if PurePosixPath(name).suffix.lower() in ('.jsonl', '.ndjson'):
                if path.suffix == '.whl':
                    raise ValueError('JSONL trace in wheel: ' + name)
                check_telemetry_file(name.partition('/')[2], data)
            text = data.decode('utf-8')
            for label, pattern in PATTERNS.items():
                if re.search(pattern, text):
                    raise ValueError(label + ' in archive: ' + name)
    return {'source_files_checked': count, 'status': 'passed',
            'application_generated_fixtures_checked': len(found),
            'listening_wavs_checked': len(listening_found),
            'draw_comparison_artifacts_checked': len(comparisons_found),
            'documentary_site_images_checked': len(site_images_found),
            'synthetic_jsonl_fixtures_checked': telemetry_count,
            'excluded': 'Commercial software, private data and unlisted binary files.'}


if __name__ == '__main__':
    try:
        print(json.dumps(audit(), indent=2))
    except (ValueError, UnicodeError, SyntaxError, KeyError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
