"""Preserve one byte snapshot and verify the portable artifacts it produced."""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import ntpath
from os import scandir
from pathlib import Path
import re
import stat

from .. import __version__
from . import audio, graphic_docs, native, pim, sheet
from .model import PreservationError
from .render import json_bytes


FORMAT = 'deskmate-preservation-bundle'
VERSION = 1
MANIFEST = 'manifest.json'
MAX_MANIFEST_BYTES = 4 * 1024 * 1024
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
MAX_BUNDLE_BYTES = 96 * 1024 * 1024
MAX_ARTIFACTS = 256
EFFECTS = ('approximation', 'omission', 'opaque', 'notice')
CONVERTERS = {'worksheet': sheet.convert, 'text': graphic_docs.convert_text,
              'draw': graphic_docs.convert_draw, 'filer': graphic_docs.convert_filer,
              'calendar': pim.convert_calendar, 'addressbook': pim.convert_addressbook,
              'sound': audio.convert_sound, 'music': audio.convert_music}


@dataclass(frozen=True)
class PreparedBundle:
    manifest: dict
    files: dict[str, bytes]


def read_bounded(path, limit, *, code):
    path = Path(path)
    if not stat.S_ISREG(path.stat().st_mode):
        raise PreservationError('not_regular_file', f'Expected a regular file: {path.name}')
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise PreservationError(code, f'{path.name} exceeds the {limit}-byte limit.')
    return data


def _identity(path, data):
    return {'path': path, 'size': len(data), 'sha256': sha256(data).hexdigest()}


def prepare(path, *, application=None):
    """Read and interpret a bounded source snapshot without writing files."""
    path = Path(path)
    data = read_bounded(path, native.MAX_SOURCE_BYTES, code='input_too_large')
    document = native.open_native(data, application)
    conversion = CONVERTERS[document.application](document.value, path.name)
    source_path = 'original.' + native.EXTENSIONS[document.application]
    files = {'content.json': json_bytes(conversion.content), **conversion.artifacts}
    manifest = {
        'format': FORMAT,
        'version': VERSION,
        'source': {'filename': path.name, **_identity(source_path, data)},
        'application': document.application,
        'profile': document.profile,
        'parser': {'entry_point': document.parser, 'package_version': __version__},
        'inspection': 'measured_profile',
        'diagnostics': [asdict(item) for item in conversion.diagnostics],
        'artifacts': [_identity(name, value) for name, value in sorted(files.items())],
    }
    files[source_path] = data
    return PreparedBundle(manifest, files)


def publish(bundle, output):
    """Create a new directory exclusively. Write the completion manifest last."""
    output = Path(output)
    _validate_manifest(bundle.manifest)
    manifest_bytes = json_bytes(bundle.manifest)
    if len(manifest_bytes) > MAX_MANIFEST_BYTES:
        raise PreservationError('manifest_too_large', 'The generated manifest exceeds the verification limit.')
    expected = {entry['path'] for entry in [bundle.manifest['source'], *bundle.manifest['artifacts']]}
    if set(bundle.files) != expected:
        raise PreservationError('invalid_bundle', 'Prepared files disagree with the manifest inventory.')
    output.mkdir()
    created_files = []
    created_dirs = [output]
    try:
        for name, data in [*sorted(bundle.files.items()), (MANIFEST, manifest_bytes)]:
            target = output / name
            if target.parent not in created_dirs:
                target.parent.mkdir()
                created_dirs.append(target.parent)
            with target.open('xb') as stream:
                created_files.append(target)
                stream.write(data)
        return verify(output)
    except BaseException:
        for target in reversed(created_files):
            target.unlink(missing_ok=True)
        for directory in reversed(created_dirs):
            if directory.exists() and not any(directory.iterdir()):
                directory.rmdir()
        raise


def export(path, output, *, application=None):
    """Export one input document into a newly created output directory."""
    return publish(prepare(path, application=application), output)


def _require(condition, message):
    if not condition:
        raise PreservationError('invalid_manifest', message)


def _keys(value, keys):
    return isinstance(value, dict) and value.keys() == set(keys.split())


def _string(value):
    return isinstance(value, str) and bool(value)


def _filename(value):
    return _string(value) and value not in ('.', '..') and '/' not in value and '\x00' not in value


def _portable_path(value):
    return isinstance(value, str) and re.fullmatch(
        r'(?:assets/)?[a-z0-9][a-z0-9-]*\.[a-z0-9]+', value,
    ) is not None and not ntpath.isreserved(value)


def _entry(value, *, source=False):
    _require(_keys(value, 'filename path size sha256' if source else 'path size sha256'),
             'Unexpected file identity fields.')
    _require(_portable_path(value['path']), 'Invalid portable artifact path.')
    size_limit = native.MAX_SOURCE_BYTES if source else MAX_ARTIFACT_BYTES
    _require(type(value['size']) is int and 0 <= value['size'] <= size_limit,
             'File size outside verification bounds.')
    _require(isinstance(value['sha256'], str) and re.fullmatch(r'[a-f0-9]{64}', value['sha256']),
             'Expected a lowercase SHA-256 digest.')


def _validate_manifest(value):
    _require(_keys(value, 'format version source application profile parser inspection diagnostics artifacts'),
             'Unexpected bundle fields.')
    _require(value['format'] == FORMAT and type(value['version']) is int and value['version'] == VERSION,
             'Expected a version 1 preservation manifest.')
    application = value['application']
    _require(application in native.APPLICATIONS and _string(value['profile'])
             and value['inspection'] == 'measured_profile', 'Invalid application, profile or inspection state.')
    parser = value['parser']
    _require(_keys(parser, 'entry_point package_version') and all(map(_string, parser.values())),
             'Invalid parser identity.')
    source = value['source']
    _entry(source, source=True)
    _require(source['path'] == 'original.' + native.EXTENSIONS[application]
             and _filename(source['filename']),
             'Invalid source identity.')
    diagnostics = value['diagnostics']
    _require(isinstance(diagnostics, list), 'Expected a diagnostics list.')
    for item in diagnostics:
        _require(_keys(item, 'code effect location message') and _string(item['code'])
                 and re.fullmatch(r'[a-z0-9_]+', item['code']) and item['effect'] in EFFECTS
                 and _string(item['message']) and (item['location'] is None or _string(item['location'])),
                 'Invalid diagnostic.')
    artifacts = value['artifacts']
    _require(isinstance(artifacts, list) and 1 <= len(artifacts) <= MAX_ARTIFACTS,
             'Expected a bounded artifact list.')
    paths = {source['path'], MANIFEST}
    for artifact in artifacts:
        _entry(artifact)
        _require(artifact['path'] not in paths, 'Duplicate artifact path.')
        paths.add(artifact['path'])
    _require('content.json' in paths, 'Missing content.json entry.')
    _require(source['size'] + sum(item['size'] for item in artifacts) <= MAX_BUNDLE_BYTES,
             'The bundle byte count exceeds the verification limit.')


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, 'Duplicate JSON property.')
        result[key] = value
    return result


def _reject_constant(value):
    raise PreservationError('invalid_manifest', f'Invalid JSON constant {value}.')


def read_json(path):
    try:
        return json.loads(read_bounded(path, MAX_MANIFEST_BYTES, code='manifest_too_large').decode('utf-8'),
                          object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except PreservationError:
        raise
    except (ValueError, RecursionError) as exc:
        raise PreservationError('invalid_manifest', 'Invalid UTF-8 JSON manifest.') from exc


def regular_directory(path):
    return not (path.is_symlink() or path.is_junction()) and path.is_dir()


def regular_file(path):
    return not (path.is_symlink() or path.is_junction()) and path.is_file()


def check_inventory(directory, expected, *, prefix=''):
    with scandir(directory) as children:
        for child in children:
            if child.name not in expected:
                raise PreservationError('unexpected_artifact', f'Unlisted item: {prefix}{child.name}')


def verify_file(root, entry):
    rel = entry['path']
    target = root / rel
    if ((target.parent != root and not regular_directory(target.parent)) or not regular_file(target)):
        raise PreservationError('missing_or_unsafe_artifact', f'Missing or linked file: {rel}')
    with target.open('rb') as stream:
        remaining = entry['size']
        if stream.seek(0, 2) != remaining:
            raise PreservationError('size_mismatch', f'Size differs: {rel}')
        stream.seek(0)
        digest = sha256()
        while remaining:
            chunk = stream.read(min(remaining, 1024 * 1024))
            if not chunk:
                raise PreservationError('size_mismatch', f'Size differs: {rel}')
            digest.update(chunk)
            remaining -= len(chunk)
        if stream.read(1):
            raise PreservationError('size_mismatch', f'Size differs: {rel}')
        if digest.hexdigest() != entry['sha256']:
            raise PreservationError('hash_mismatch', f'SHA-256 differs: {rel}')


def verify(output):
    """Check a bundle's shape, inventory and hashes without loading native readers."""
    root = Path(output)
    if not regular_directory(root):
        raise PreservationError('invalid_bundle', 'Expected a real bundle directory.')
    manifest_path = root / MANIFEST
    if not regular_file(manifest_path):
        raise PreservationError('invalid_bundle', f'Missing or linked {MANIFEST}.')
    manifest = read_json(manifest_path)
    _validate_manifest(manifest)
    entries = [manifest['source'], *manifest['artifacts']]
    names = {entry['path'] for entry in entries}
    assets = {name.split('/')[1] for name in names if name.startswith('assets/')}
    root_names = {name for name in names if '/' not in name} | {MANIFEST}
    if assets:
        root_names.add('assets')
    check_inventory(root, root_names)
    if assets:
        if not regular_directory(root / 'assets'):
            raise PreservationError('missing_or_unsafe_artifact', 'Missing or linked assets directory.')
        check_inventory(root / 'assets', assets, prefix='assets/')
    for entry in entries:
        verify_file(root, entry)
    return manifest
