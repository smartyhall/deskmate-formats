"""Validate the archival capability registry and render its documentation.

The registry is deliberately separate from the proposed-format backlog: a
backlog entry is a candidate, whereas a registry record is a claim about
behaviour that has actually been exercised. This module makes the claim
checkable by requiring every named implementation entry point to exist and by
generating the human-readable document from the same records.
"""

import argparse
import json
import re
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
OPERATIONS = ('identify', 'metadata', 'list', 'extract', 'validate', 'recover')
STATUSES = ('qualified', 'partial', 'identify-only', 'unsupported', 'planned', 'blocked')
APPROACHES = ('native', 'library', 'external-adapter', 'mockable-adapter')
LAYERS = ('archive', 'compression', 'sector-image', 'filesystem', 'disk-layout',
          'optical', 'document', 'executable', 'recording')
IDENTIFIER = re.compile(r'^[a-z0-9][a-z0-9-]{0,63}$')
TABLE_ORDER = ('qualified', 'partial', 'identify-only', 'unsupported', 'planned', 'blocked')


def load(path):
    """Read a registry document as JSON."""
    return json.loads(Path(path).read_text(encoding='utf-8'))


def validate(registry):
    """Raise ValueError on the first structural or semantic problem found."""
    if registry.get('schema_version') != 1:
        raise ValueError('unsupported registry schema_version')
    if tuple(registry.get('operations', ())) != OPERATIONS:
        raise ValueError('registry operations must list every operation in order')
    meanings = registry.get('status_meanings')
    if not isinstance(meanings, dict) or set(meanings) != set(STATUSES):
        raise ValueError('status_meanings must describe exactly the known statuses')
    formats = registry.get('formats')
    if not isinstance(formats, list) or not formats:
        raise ValueError('registry must contain at least one format record')
    seen = set()
    for record in formats:
        identifier = record.get('id')
        if not isinstance(identifier, str) or not IDENTIFIER.match(identifier):
            raise ValueError(f'invalid format id: {identifier!r}')
        if identifier in seen:
            raise ValueError(f'duplicate format id: {identifier}')
        seen.add(identifier)
        if not record.get('title'):
            raise ValueError(f'{identifier}: a title is required')
        if record.get('layer') not in LAYERS:
            raise ValueError(f'{identifier}: unknown layer {record.get("layer")!r}')
        operations = record.get('operations')
        if not isinstance(operations, dict) or set(operations) != set(OPERATIONS):
            raise ValueError(f'{identifier}: operations must name exactly {OPERATIONS}')
        for operation, status in operations.items():
            if status not in STATUSES:
                raise ValueError(f'{identifier}.{operation}: unknown status {status!r}')
        implementation = record.get('implementation')
        if implementation is None:
            # A record without an implementation may only claim non-support,
            # so a gap can never be mistaken for qualified behaviour.
            unsupported = set(STATUSES) - {'planned', 'blocked', 'unsupported'}
            claimed = unsupported & set(operations.values())
            if claimed:
                raise ValueError(f'{identifier}: claims {sorted(claimed)} without an implementation')
            continue
        if not isinstance(implementation, dict):
            raise ValueError(f'{identifier}: implementation must be an object or null')
        if implementation.get('approach') not in APPROACHES:
            raise ValueError(f'{identifier}: unknown approach {implementation.get("approach")!r}')
        for key in ('module', 'entry'):
            if not isinstance(implementation.get(key), str) or not implementation[key]:
                raise ValueError(f'{identifier}: implementation.{key} is required')
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', implementation['entry']):
            raise ValueError(f'{identifier}: implementation.entry must be an identifier')
        if operations['identify'] in ('planned', 'blocked', 'unsupported'):
            raise ValueError(f'{identifier}: an implemented format must identify its input')
        for spec in record.get('specifications', ()):
            if not str(spec.get('url', '')).startswith(('http://', 'https://')):
                raise ValueError(f'{identifier}: specification needs an http(s) URL')
        if not record.get('evidence'):
            raise ValueError(f'{identifier}: an evidence statement is required')
        if not record.get('limitations'):
            raise ValueError(f'{identifier}: an explicit limitations statement is required')
    return registry


def check_implementations(registry, modules):
    """Confirm that every named entry point exists in its module."""
    for record in registry['formats']:
        implementation = record.get('implementation')
        if implementation is None:
            continue
        module = modules.get(implementation['module'])
        if module is None:
            raise ValueError(f'{record["id"]}: unknown module {implementation["module"]!r}')
        if not hasattr(module, implementation['entry']):
            raise ValueError(f'{record["id"]}: {implementation["module"]}.{implementation["entry"]} '
                             'does not exist')


def _cell(status):
    return {'qualified': 'yes', 'partial': 'partial', 'identify-only': 'identify only',
            'unsupported': 'no', 'planned': 'planned', 'blocked': 'blocked'}[status]


def render_markdown(registry):
    """Render the registry as deterministic Markdown documentation."""
    lines = [
        '# Archival format capabilities',
        '',
        '<!-- Generated by tools/archive/capabilities.py from docs/archive-capabilities.json.',
        '     Do not edit by hand: change the registry and regenerate. -->',
        '',
        'This is a record of behaviour that has actually been exercised, not a list of',
        'formats the project hopes to support. A format may be recognised without being',
        'decoded, so identification and extraction are tracked as separate operations.',
        'The proposed-format [backlog](archive-format-backlog.json) is a different',
        'document and is not a capability claim.',
        '',
    ]
    formats = registry['formats']
    lines.append(f'Registered records: {len(formats)}.')
    lines.append('')
    lines.append('## Status vocabulary')
    lines.append('')
    for status in STATUSES:
        lines.append(f'- **{status}**: {registry["status_meanings"][status]}')
    lines.append('')
    layers = []
    for record in formats:
        if record['layer'] not in layers:
            layers.append(record['layer'])
    for layer in layers:
        members = [record for record in formats if record['layer'] == layer]
        lines.append(f'## {layer.replace("-", " ").capitalize()}')
        lines.append('')
        header = '| Format | ' + ' | '.join(name.capitalize() for name in OPERATIONS) + ' |'
        lines.append(header)
        lines.append('| --- |' + ' --- |' * len(OPERATIONS))
        for record in members:
            cells = ' | '.join(_cell(record['operations'][name]) for name in OPERATIONS)
            lines.append(f'| {record["title"]} | {cells} |')
        lines.append('')
    lines.append('## Qualification notes')
    lines.append('')
    for record in formats:
        lines.append(f'### {record["title"]}')
        lines.append('')
        implementation = record.get('implementation')
        if implementation:
            lines.append(f'- Implementation: `{implementation["module"]}.{implementation["entry"]}` '
                         f'({implementation["approach"]}).')
        else:
            lines.append('- Implementation: none.')
        dependencies = record.get('dependencies') or []
        if dependencies:
            named = ', '.join(
                f'{item["name"]} ({item["used_for"]})' if item.get('used_for') else item['name']
                for item in dependencies)
            lines.append(f'- Optional dependencies: {named}.')
        lines.append(f'- Evidence: {record["evidence"]}')
        lines.append(f'- Limitations: {record["limitations"]}')
        for spec in record.get('specifications', ()):
            lines.append(f'- Reference: [{spec["title"]}]({spec["url"]})')
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def _modules():
    tools = ROOT / 'tools' / 'archive'
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    import compression
    import disk_images
    import intelligence_extract
    return {'compression': compression, 'disk_images': disk_images,
            'intelligence_extract': intelligence_extract}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--registry', default=str(ROOT / 'docs' / 'archive-capabilities.json'))
    parser.add_argument('--output', default=str(ROOT / 'docs' / 'archive-capabilities.md'))
    parser.add_argument('--write', action='store_true',
                        help='rewrite the generated document instead of checking it')
    options = parser.parse_args(argv)
    registry = validate(load(options.registry))
    check_implementations(registry, _modules())
    rendered = render_markdown(registry)
    output = Path(options.output)
    if options.write:
        output.write_text(rendered, encoding='utf-8', newline='\n')
        print(f'wrote {output}')
        return 0
    current = output.read_text(encoding='utf-8') if output.exists() else ''
    if current != rendered:
        print(f'{output} is stale; rerun with --write', file=sys.stderr)
        return 1
    print(f'{output} is current')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
