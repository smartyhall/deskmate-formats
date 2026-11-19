"""Process a directory into independently verifiable bundles and an offline index."""
from os import scandir
from pathlib import Path
import re

from . import bundle, native
from .model import PreservationError, error_report
from .render import html_page, html_text, json_bytes


FORMAT = 'deskmate-preservation-collection'
MANIFEST = 'collection.json'
INDEX = 'index.html'
MAX_FILES = 1024


def _input_files(directory):
    paths = []
    with scandir(directory) as children:
        for child in children:
            if child.is_dir(follow_symlinks=False) and not child.is_junction():
                continue
            if len(paths) >= MAX_FILES:
                raise PreservationError('collection_limit', f'A collection can contain up to {MAX_FILES} inputs.')
            paths.append(Path(child.path))
    return sorted(paths, key=lambda path: (path.name.casefold(), path.name))


def _directory_name(number, filename):
    slug = re.sub(r'[^a-z0-9]+', '-', filename.lower()).strip('-')[:52].rstrip('-')
    return f'{number:04}-{slug or "document"}'


def _index(entries):
    items = []
    for item in entries:
        name = html_text(item['filename'])
        if item['status'] == 'exported':
            directory = item['directory']
            application = html_text(item['application'])
            items.append(f'<li><a href="{directory}/preview.html">{name}</a> · {application} · '
                         f'<a class="small" href="{directory}/manifest.json">Manifest</a></li>')
        else:
            items.append(f'<li>{name} · {html_text(item["failure"]["message"])}</li>')
    exported = sum(item['status'] == 'exported' for item in entries)
    body = '<ul>' + ''.join(items) + '</ul>' if items else '<p>No input files found.</p>'
    return html_page('DeskMate Preservation Workbench',
                     f'{exported} exported · {len(entries) - exported} failed', body)


def export(directory, output, *, application=None, instruments=None, sample_policy='rsx-ranges', outline_faces=None):
    """Export direct files in stable order. Each per-file failure is recorded."""
    paths = _input_files(directory)
    output = Path(output)
    output.mkdir()
    entries = []
    for number, source in enumerate(paths, 1):
        directory_name = _directory_name(number, source.name)
        target = output / directory_name
        try:
            if not bundle.regular_file(source):
                raise PreservationError('not_regular_file', 'Batch inputs must be regular files.')
            result = bundle.export(source, target, application=application,
                                   instruments=instruments, sample_policy=sample_policy, outline_faces=outline_faces)
        except (PreservationError, OSError) as exc:
            entries.append({'filename': source.name, 'status': 'failed', 'failure': error_report(exc)})
        else:
            entries.append({'filename': source.name, 'status': 'exported',
                            'directory': directory_name, 'application': result['application'],
                            'manifest': bundle._identity(bundle.MANIFEST, json_bytes(result))})
    index = _index(entries)
    document = {'format': FORMAT, 'version': bundle.VERSION, 'entries': entries,
                'index': bundle._identity(INDEX, index)}
    _validate_manifest(document)
    manifest_bytes = json_bytes(document)
    if len(manifest_bytes) > bundle.MAX_MANIFEST_BYTES:
        raise PreservationError('manifest_too_large', 'The collection manifest exceeds the verification limit.')
    for name, value in [(INDEX, index), (MANIFEST, manifest_bytes)]:
        with (output / name).open('xb') as stream:
            stream.write(value)
    return document


def _validate_manifest(document):
    require = bundle._require
    require(bundle._keys(document, 'format version entries index'), 'Unexpected collection fields.')
    require(document['format'] == FORMAT and type(document['version']) is int
            and document['version'] == bundle.VERSION, 'Expected a version 1 preservation collection.')
    bundle._entry(document['index'])
    require(document['index']['path'] == INDEX, 'Invalid collection index path.')
    entries = document['entries']
    require(isinstance(entries, list) and len(entries) <= MAX_FILES, 'Expected a bounded collection list.')
    filenames = set()
    for number, entry in enumerate(entries, 1):
        require(isinstance(entry, dict) and bundle._filename(entry.get('filename'))
                and entry['filename'] not in filenames, 'Invalid or duplicate collection filename.')
        filenames.add(entry['filename'])
        if entry.get('status') == 'exported':
            require(bundle._keys(entry, 'filename status directory application manifest')
                    and entry['directory'] == _directory_name(number, entry['filename'])
                    and entry['application'] in native.APPLICATIONS, 'Invalid collection bundle entry.')
            bundle._entry(entry['manifest'])
            require(entry['manifest']['path'] == bundle.MANIFEST
                    and entry['manifest']['size'] <= bundle.MAX_MANIFEST_BYTES, 'Invalid child manifest identity.')
        else:
            require(bundle._keys(entry, 'filename status failure') and entry['status'] == 'failed'
                    and bundle._keys(entry['failure'], 'error message')
                    and all(map(bundle._string, entry['failure'].values())), 'Invalid collection failure entry.')


def verify(output):
    """Verify the collection index and every exported child. Report input failures."""
    root = Path(output)
    if not bundle.regular_directory(root) or not bundle.regular_file(root / MANIFEST):
        raise PreservationError('invalid_bundle', f'Expected a real collection directory with {MANIFEST}.')
    document = bundle.read_json(root / MANIFEST)
    _validate_manifest(document)
    successes = [entry for entry in document['entries'] if entry['status'] == 'exported']
    expected = {MANIFEST, INDEX, *(entry['directory'] for entry in successes)}
    bundle.check_inventory(root, expected)
    bundle.verify_file(root, document['index'])
    for entry in successes:
        child = root / entry['directory']
        if not bundle.regular_directory(child):
            raise PreservationError('invalid_bundle', f'Missing or linked bundle: {child.name}')
        bundle.verify_file(child, entry['manifest'])
        manifest = bundle.verify(child)
        if manifest['source']['filename'] != entry['filename'] or manifest['application'] != entry['application']:
            raise PreservationError('invalid_manifest', f'Collection entry disagrees with child: {child.name}')
    return {'verified': True, 'bundle_count': len(successes),
            'failed_count': len(document['entries']) - len(successes)}
