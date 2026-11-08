"""Generate separate one-contact ADR files; multi-contact insertion is unverified."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

from deskmate_formats.addressbook import create_contact, write_new
from deskmate_formats.addressbook.samples import contacts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('empty_source', type=Path)
    parser.add_argument('new_directory', type=Path)
    parser.add_argument('--count', type=int, default=25)
    args = parser.parse_args(argv)
    try:
        with args.empty_source.open('rb') as handle:
            source = handle.read(10241)
        items = contacts(args.count)
        # Validate and compute every result before publishing any output.
        outputs = [create_contact(source, item) for item in items]
        args.new_directory.mkdir()  # Refuse an existing batch; never retry over it.
        manifest = {'receipt_version': 1, 'source_sha256': hashlib.sha256(source).hexdigest(),
                    'file_count': len(outputs), 'contacts_per_file': 1,
                    'native_opened': False, 'native_save_tested': False, 'files': []}
        for n, (data, contact) in enumerate(zip(outputs, items, strict=True), 1):
            name = f'contact-{n:03d}.adr'
            write_new(args.new_directory / name, data)
            manifest['files'].append({'name': name, 'sha256': hashlib.sha256(data).hexdigest(),
                                      'size': len(data), 'contact': asdict(contact)})
        with (args.new_directory / 'manifest.json').open('x', encoding='utf-8') as handle:
            json.dump(manifest, handle, indent=2)
            handle.write('\n')
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps({'file_count': len(outputs), 'contacts_per_file': 1, 'native_opened': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
