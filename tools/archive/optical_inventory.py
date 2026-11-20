"""Inventory large, verified ZIP-wrapped optical discs without expanding their trees."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from subprocess import SubprocessError
from struct import unpack_from
from time import monotonic
from tempfile import TemporaryDirectory
from fnmatch import fnmatchcase
from zipfile import BadZipFile, ZipFile

from archive_intelligence import contained, read_receipts, read_transfer_state
from intelligence_extract import (SEVEN_OPTIONS, _capture, _legacy_entries, _seven_member, optical_descriptor, safe_member)

MAX_IMAGE_BYTES = 850 * 1024**2
MAX_MEMBER_BYTES = 2 * 1024**2


def executable_header(data):
    if len(data) < 64 or data[:2] != b'MZ':
        return None
    offset = unpack_from('<I', data, 0x3c)[0]
    if offset < 64 or offset + 64 > len(data) or data[offset:offset + 2] != b'NE':
        return {'format': 'MZ-family'}
    resident, = unpack_from('<H', data, offset + 0x26)
    nonresident, = unpack_from('<I', data, offset + 0x2c)
    nonresident_size, = unpack_from('<H', data, offset + 0x20)

    def first_name(position, end):
        if not 0 < position < end <= len(data):
            return None
        size = data[position]
        if not size or position + size + 3 > end or data[position + size + 1:position + size + 3] != b'\0\0':
            return None
        return data[position + 1:position + 1 + size].decode('cp437')

    return {'format': 'NE', 'target_os': data[offset + 0x36],
            'resident_name': first_name(offset + resident, len(data)) if resident >= 64 else None,
            'description': first_name(nonresident, nonresident + nonresident_size)}


def inspect(source, tool, output, member_select=()):
    with ZipFile(source) as zf:
        candidates = [i for i in zf.infolist() if Path(i.filename).suffix.lower() in ('.iso', '.bin', '.img')]
        if not candidates:
            return []
        if len(candidates) > 8:
            raise ValueError('too many optical image candidates')
        recordings = []
        for i in candidates:
            if (not safe_member(i.filename) or not 0 < i.file_size <= MAX_IMAGE_BYTES
                    or i.flag_bits & 1 or i.is_dir()):
                raise ValueError('unsafe or oversized optical candidate')
            with TemporaryDirectory(dir=output.parent) as scratch:
                p = Path(scratch) / 'track.img'
                with zf.open(i) as src, p.open('xb') as dst:
                    shutil.copyfileobj(src, dst, length=1024**2)
                if p.stat().st_size != i.file_size:
                    raise ValueError('optical candidate size mismatch')
                with p.open('rb') as data:
                    sha = hashlib.file_digest(data, 'sha256').hexdigest()
                descriptor = optical_descriptor(p)
                recording = {'member': i.filename, 'bytes': i.file_size, 'sha256': sha,
                             'descriptor': descriptor, 'state': 'unlisted'}
                if descriptor and descriptor['kind'] in ('iso9660', 'udf'):
                    fmt = 'Iso' if descriptor['kind'] == 'iso9660' else 'Udf'
                    code, listing = _capture([str(tool), 'l', *SEVEN_OPTIONS, f'-t{fmt}',
                                              '-slt', '--', str(p)], 16 * 1024**2, 45)
                    if code != 0:
                        raise ValueError(f'optical listing failed ({code})')
                    actual, rows = _legacy_entries(listing.decode('utf-8').replace('\r\n', '\n'))
                    if actual != fmt:
                        raise ValueError(f'unexpected optical filesystem: {actual}')
                    counts = {}
                    for name, _, _ in rows:
                        counts[name.casefold()] = counts.get(name.casefold(), 0) + 1
                    extracted = []
                    deadline = monotonic() + 45
                    for name, size, status in rows:
                        if not member_select or not any(fnmatchcase(name.casefold().replace('\\','/'), pattern)
                                                       for pattern in member_select):
                            continue
                        member = {'name': name, 'size': size}
                        extracted.append(member)
                        if status or counts[name.casefold()] != 1 or size > MAX_MEMBER_BYTES:
                            member['state'] = status or 'ambiguous-or-over-limit'
                            continue
                        if len(extracted) > 40 or monotonic() >= deadline:
                            member['state'] = 'batch-limit'
                            continue
                        try:
                            data = _seven_member(p, tool, [f'-t{fmt}'], name, size, deadline - monotonic())
                            if len(data) != size:
                                raise ValueError('extracted member size mismatch')
                            member.update(state='extracted', sha256=hashlib.sha256(data).hexdigest(),
                                          executable=executable_header(data))
                            # Preserve short text excerpts in the private report for attribution.
                            if Path(name).suffix.lower() in ('.txt', '.ini') and b'\0' not in data[:8192]:
                                member['text_prefix'] = data[:8192].decode('cp437')
                        except (OSError, ValueError, RuntimeError, SubprocessError, BadZipFile) as error:
                            member.update(state='failed', error=str(error))
                    recording.update(state='listed', extracted=extracted, members=[
                        {'name': name, 'size': size, 'status': status or 'file'} for name, size, status in rows])
                recordings.append(recording)
        return recordings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mirror', type=Path)
    parser.add_argument('output', type=Path, help='private results directory')
    parser.add_argument('--seven-zip', required=True, type=Path)
    parser.add_argument('--select', required=True, action='append')
    parser.add_argument('--member-select', default=[], action='append')
    args = parser.parse_args()
    root = args.mirror.resolve(strict=True)
    output = args.output.resolve()
    if output.is_relative_to(root):
        parser.error('output must be outside the mirror')
    output.mkdir(parents=True, exist_ok=True)
    rows = read_receipts(read_transfer_state(root / 'transfer-state/mirror.sqlite3'))
    for row in rows:
        if not any(fnmatchcase(row['rel'].casefold(), pat.casefold()) for pat in args.select):
            continue
        if row['status'] != 'verified' or not row['rel'].casefold().endswith('.zip'):
            continue
        p = contained(root, row['local'])
        selection = sorted(set(pat.casefold() for pat in args.member_select))
        name = hashlib.sha256(json.dumps([row['url'], row['sha256'], selection]).encode()).hexdigest()
        receipt = output / (name + '.json')
        if receipt.exists():
            continue
        try:
            with p.open('rb') as src:
                sha = hashlib.file_digest(src, 'sha256').hexdigest()
            if sha != row['sha256'] or p.stat().st_size != row['bytes']:
                raise ValueError('original differs from transfer receipt')
            records = inspect(p, args.seven_zip.resolve(strict=True), receipt, selection)
            result = {'source': row['rel'], 'url': row['url'], 'source_sha256': sha,
                      'recordings': records}
            with receipt.with_suffix('.partial').open('w', encoding='utf-8') as dst:
                json.dump(result, dst, indent=2)
            receipt.with_suffix('.partial').rename(receipt)
            print(json.dumps({'source': row['rel'], 'recordings': len(records),
                              'listed_members': sum(len(r.get('members', [])) for r in records)}), flush=True)
        except (OSError, ValueError, RuntimeError, SubprocessError, BadZipFile) as error:
            print(json.dumps({'source': row['rel'], 'error': str(error)}), flush=True)


if __name__ == '__main__':
    main()
