"""Audit publication boundaries, preserving documented application-generated fixtures."""
from pathlib import Path, PurePosixPath
import ast
import hashlib
import json
import re
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'.git', 'build', 'dist', 'local-results', 'private-fixtures', '.ruff_cache'}
FIXTURE_DIR = Path('tests/fixtures/application-generated')
DATA_EXT = {'.cln', '.adr', '.fil', '.pcl'}
PRIVATE_SPOOL_FILES = {'events.jsonl', 'writer.lock'}
TELEMETRY_FIXTURE_DIR = 'tests/fixtures/codex-exec-0.166.0/'
TELEMETRY_FIXTURES = {
    'anomalies.jsonl': 'af47f774319320c7e5e6d8cefb903e2f711e93f20ec6a529eabe3d81ebbd1a2b',
    'failure.jsonl': 'c780a82c87b33b7ce875da451614fa17a562eaa2b9a844bf7df516865e0b6576',
    'open-turn.jsonl': 'a7c8cfc883c658b7b3911224832d68b0f7f10433e5c91b088fde88298c0b02ae',
    'success.jsonl': '3a453f3cfa512c9d53e1ff6366112ac102d0bb257f4902ff697f081b3bb216c9',
}
BAD_EXT = {'.exe', '.com', '.dll', '.img', '.ima', '.iso', '.zip', '.7z', '.cln',
           '.png', '.pdf', '.pdm', '.res', '.r89', '.fil', '.adr', '.pcl', '.hlp',
           '.tut', '.nvr', '.rom', '.vhd', '.vhdx', '.hdi', '.raw', '.token'}
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


def source_files():
    for path in sorted(ROOT.rglob('*')):
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDED or part.startswith('.venv') or
               part.endswith('.egg-info') or part == '__pycache__' for part in rel.parts):
            continue
        if path.is_file():
            yield path


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
        if rel.suffix.lower() not in DATA_EXT:
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


def audit():
    allowed = fixture_manifest()
    found = set()
    count = 0
    telemetry_count = 0
    for path in source_files():
        rel_path = path.relative_to(ROOT)
        rel = rel_path.as_posix()
        if path.is_symlink():
            raise ValueError('symlink is not permitted: ' + rel)
        if path.name.lower() in PRIVATE_SPOOL_FILES:
            raise ValueError('private Observatory spool file: ' + rel)
        data = path.read_bytes()
        telemetry_count += check_telemetry_file(rel, data)
        if rel in allowed and rel_path.suffix.lower() in DATA_EXT:
            if data.startswith(b'MZ'):
                raise ValueError('executable disguised as fixture: ' + rel)
            entry = allowed[rel]
            if len(data) != entry['size'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise ValueError('fixture digest or size mismatch: ' + rel)
            # Native binary structure is permitted, not credentials or host paths.
            for text_variant in (data.decode('latin-1'),
                                 data.replace(b'\x00', b'').decode('latin-1')):
                for label, pattern in PATTERNS.items():
                    if re.search(pattern, text_variant):
                        raise ValueError(label + ': ' + rel)
            found.add(rel)
            count += 1
            continue
        if path.suffix.lower() in BAD_EXT or path.name.startswith('.env'):
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
            if Path(name).suffix.lower() in BAD_EXT:
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
            'synthetic_jsonl_fixtures_checked': telemetry_count,
            'excluded': 'Commercial software, private data and unlisted binary files.'}


if __name__ == '__main__':
    try:
        print(json.dumps(audit(), indent=2))
    except (ValueError, UnicodeError, SyntaxError, KeyError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
