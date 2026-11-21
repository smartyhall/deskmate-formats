"""Qualify distinct DeskMate document candidates in a private archive index."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import re

if __package__:
    from .archive_intelligence import contained, open_index
else:
    from archive_intelligence import contained, open_index

from deskmate_formats import ff1, music
from deskmate_formats.preservation.model import PreservationError
from deskmate_formats.preservation.native import open_native


APPLICATIONS = {
    'adr': 'addressbook', 'cln': 'calendar', 'doc': 'text', 'native-doc': 'text',
    'dmdb': None, 'fig': None, 'fil': 'filer', 'sng': 'music', 'snd': 'sound',
    'wks': 'worksheet', 'ff1': None,
}
MAX_BYTES = 16 * 1024 * 1024


def qualify(data, kind, *, allow_sector_padding=False):
    if kind == 'ff1':
        font = ff1.parse_resource(data)
        return {'application': 'ff1', 'roundtrip_identical': ff1.serialize_resource(font) == data}
    if kind == 'sng':
        score = music.parse_bytes(data, allow_sector_padding=allow_sector_padding)
        result = {'application': 'music', 'profile': 'music-0c-sng-four-stream',
                  'trailer_bytes': len(score.trailer)}
        sequence = music.project(score)
        try:
            music.to_midi(sequence)
        except ValueError as exc:
            result['midi_error'] = str(exc)
        else:
            result['midi'] = True
        return result
    doc = open_native(data, APPLICATIONS[kind])
    result = {'application': doc.application, 'profile': doc.profile}
    if doc.application == 'sound':
        sound = doc.value
        result.update(slot=sound.instrument_number, sample_rate=sound.sample_rate,
                      descriptors=len(sound.samples), compression=sound.compression)
        try:
            result['decoded_pcm_frames'] = sum(len(sound.pcm(i)) for i in range(len(sound.samples)))
        except ValueError as exc:
            result['pcm_error'] = str(exc)
    return result


def inventory(db, known, *, allow_sector_padding=False):
    store = Path(db.execute("SELECT value FROM configuration WHERE key='store'").fetchone()[0])
    grouped = defaultdict(list)
    for row in db.execute(
        "SELECT o.id,o.name,o.chain,o.kind,o.size,o.digest,o.depth,s.snapshot,s.local,s.url "
        "FROM occurrence o JOIN source s ON s.id=o.source_id "
        "WHERE o.digest IS NOT NULL ORDER BY s.rel,o.chain,o.id"
    ):
        if row['kind'] in APPLICATIONS:
            grouped[row['kind'], row['digest']].append(row)
    counts = defaultdict(Counter)
    records = []
    for (kind, digest), rows in sorted(grouped.items()):
        row = rows[0]
        result = {'kind': kind, 'sha256': digest, 'size': row['size'], 'known_hash': digest in known,
                  'sources': [{'id': r['id'], 'name': r['name'], 'url': r['url'],
                               'chain': json.loads(r['chain'])} for r in rows]}
        try:
            if row['size'] > MAX_BYTES:
                raise ValueError('candidate size exceeds read budget')
            path = (store / digest[:2] / digest if row['depth'] else
                    contained(Path(row['snapshot']), row['local']))
            with path.open('rb') as stream:
                data = stream.read(MAX_BYTES + 1)
            if len(data) != row['size'] or sha256(data).hexdigest() != digest:
                raise ValueError('candidate no longer matches index')
            result.update(qualify(data, kind, allow_sector_padding=allow_sector_padding), status='accepted')
        except (ValueError, OSError) as exc:
            result.update(status='rejected', error=str(exc))
            if isinstance(exc, PreservationError):
                result['error_code'] = exc.code
        records.append(result)
        counts[kind]['occurrences'] += len(rows)
        counts[kind]['distinct'] += 1
        counts[kind][result['status']] += 1
        if result['status'] == 'accepted' and digest not in known:
            counts[kind]['accepted_outside_comparison'] += 1
    return {'summary': counts, 'records': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database', type=Path)
    parser.add_argument('--compare', type=Path, action='append', default=[],
                        help='prior JSON receipt containing SHA-256 keys or values')
    parser.add_argument('--summary', action='store_true')
    parser.add_argument('--allow-sector-padding', action='store_true',
                        help='qualify SNG candidates with trailers ending at the next 128-byte boundary')
    args = parser.parse_args()
    known = set()
    for receipt in args.compare:
        known.update(re.findall(r'"([a-fA-F0-9]{64})"', receipt.read_text(encoding='utf-8-sig').lower()))
    with closing(open_index(args.database)) as db:
        result = inventory(db, known, allow_sector_padding=args.allow_sector_padding)
    print(json.dumps(result['summary'] if args.summary else result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
