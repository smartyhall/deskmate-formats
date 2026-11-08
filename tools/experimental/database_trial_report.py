"""Read-only, independent raw-byte reports for the Phase II database trials.

No production codec imports, guest access, file writes or allocation semantics.
Redirect stdout to a NEW PRIVATE receipt: reports contain full input row bytes.
Unknown framing fails; policy mismatches are reported, never silently accepted.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

PAGE = 1024
HEADER = (b'\xff' * 9 + b'\0') * 4
A01 = '19215ea147c65b259eb963fd240e9931d96e77f92d1001f0f7edf89024076ac8'
GROWTH = {
    'e15': {
        'before': 'ed43356dac2b6351429f785e4b868b4458f6bc1a68f05f447477da30021862a4',
        'after': '42517ab1f90f9e7b6c5cf184219bc301254db33adf3f875a36347237743f1380',
        'pages': [6, 7], 'new_target': [6, 0, 33],
        'header': {0x26: [255, 0], 0x27: [143, 111], 0x2A: [240, 143], 0x2B: [0, 255]}},
    'e19': {
        'before': 'f70406212f170065a5dec83f11d8a55e1ec05f58dda1d57b6c9973d5d6b9d0ed',
        'after': 'ad6683ae34d3367026e47aeddd91ca93502551c557f02f7762039ff2d82011a1',
        'pages': [7, 8], 'new_target': [7, 0, 46],
        'header': {0x29: [255, 0], 0x2A: [143, 127], 0x2B: [255, 248],
                   0x2C: [0, 255], 0x2D: [0, 240]}}
}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def byte_changes(before, after, start=0, end=None):
    """Every fixed-offset difference, including null for bytes outside an input."""
    end = max(len(before), len(after)) if end is None else end
    return [{'offset': n, 'before': before[n] if n < len(before) else None,
             'after': after[n] if n < len(after) else None}
            for n in range(start, end)
            if (before[n] if n < len(before) else None) !=
               (after[n] if n < len(after) else None)]


def snapshot(data, name):
    """Independently walk the single-index, low-ID DATA/PERSONAL trial profile.

    Scan only starting/live-index-targeted pages. Unreferenced pages remain opaque.
    This is a trial diagnostic, not a general DMDB reader or schema validator.
    """
    check(6 * PAGE <= len(data) <= 64 * PAGE and len(data) % PAGE == 0, 'page bounds')
    check(name in ('DATA', 'PERSONAL'), 'unknown trial table')
    check(data[:4] == (b'\x03FIL' if name == 'PERSONAL' else b'\x03\0\0\0'), 'magic')
    descriptors, cursor = {}, PAGE
    while cursor < 2 * PAGE and data[cursor] != 3:
        stop = data.find(b'\x01\x02', cursor, 2 * PAGE)
        check(stop >= 0, 'directory terminator')
        tokens = data[cursor:stop].split(b'\x01')
        check(len(tokens) >= 8 and tokens[0] == b'T', 'directory framing')
        check(all(tokens[n].isdigit() for n in (2, 3, 4, 6, 7)), 'directory decimal')
        table = tokens[1].decode('ascii')
        check(table and table not in descriptors, 'duplicate/empty table')
        descriptors[table] = (cursor, tokens)
        cursor = stop + 2
    check(cursor < 2 * PAGE and data[cursor] == 3 and not any(data[cursor + 1:2 * PAGE]),
          'directory tail')
    check(name in descriptors, 'missing trial table')
    start, tokens = descriptors[name]
    page, columns, count, next_id, index = [int(tokens[n]) for n in (2, 3, 4, 6, 7)]
    check(columns == (7 if name == 'PERSONAL' else 16), 'trial column count')
    check((page, index) == (4, 5), 'trial page roles')
    check(count <= 163, 'index capacity/sentinel')
    base = index * PAGE
    check(data[base:base + 40] == HEADER, 'index header')
    triples = [list(struct.unpack_from('<HHH', data, base + 40 + 6 * n)) for n in range(count)]
    check(not any(data[base + 40 + 6 * count:base + PAGE]), 'index sentinel/tail')
    other_pages = {0, 1, index}
    for table, (_, values) in descriptors.items():
        if table != name:
            other_pages.update((int(values[2]), int(values[7])))
    check(all(2 <= p < len(data) // PAGE and p not in other_pages and 0 <= off < PAGE
              and 16 <= rid < 128 for p, off, rid in triples), 'index target bounds/alias/ID')
    check(len({rid for _, _, rid in triples}) == count and
          len({(p, off) for p, off, _ in triples}) == count, 'duplicate index ID/target')
    rows, retired, markers = {}, [], {}
    for p in sorted({page} | {p for p, _, _ in triples}):
        cursor, limit = p * PAGE, (p + 1) * PAGE
        while cursor < limit and data[cursor] != 3:
            prefix = data[cursor]
            check(prefix == 128 or (name == 'PERSONAL' and prefix == 68), 'row prefix')
            check(cursor + 1 < limit and 16 <= data[cursor + 1] < 128, 'row ID')
            stop = data.find(b'\x01\x02', cursor + 2, limit)
            check(stop >= 0, 'row terminator')
            fields = data[cursor + 2:stop].split(b'\x01')
            check(len(fields) == columns, 'row field count')
            rid = data[cursor + 1]
            row = {'id': rid, 'offset': cursor, 'end': stop + 2,
                   'raw_hex': data[cursor:stop + 2].hex(),
                   'fields_hex': [v.hex() for v in fields]}
            if prefix == 128:
                check(rid not in rows, 'duplicate physical ID')
                rows[rid] = row
            else:
                retired.append(row)
            cursor = stop + 2
        check(cursor < limit and data[cursor] == 3 and not any(data[cursor + 1:limit]),
              'row marker/tail')
        markers[p] = cursor
    check(set(rows) == {rid for _, _, rid in triples}, 'physical/index coverage')
    for p, off, rid in triples:
        check(rows[rid]['offset'] == p * PAGE + off, 'index pointer/framing mismatch')
    check(not {r['id'] for r in retired} & set(rows), 'retired/live ID collision')
    return {'sha256': sha(data), 'size': len(data), 'pages': len(data) // PAGE,
            'descriptor_offset': start, 'tokens_hex': [t.hex() for t in tokens],
            'count': count, 'next_id_candidate': next_id, 'triples': triples,
            'rows': rows, 'retired_rows': retired, 'page_markers': markers}


def compare(before, after, name):
    old, new = snapshot(before, name), snapshot(after, name)
    changes = byte_changes(before, after)
    preserved = {rid: rid in new['rows'] and new['rows'][rid] == row
                 for rid, row in old['rows'].items()}
    return {'evidence_class': 'offline independent raw-byte diagnostic; native execution not observed',
            'before': old, 'after': new, 'changes': changes,
            'header_changes': [v for v in changes if v['offset'] < PAGE],
            'old_rows_preserved_at_address': preserved,
            'new_ids': sorted(set(new['rows']) - set(old['rows'])),
            'page_hashes': [{'page': p,
                             'before': sha(before[p * PAGE:(p + 1) * PAGE]) if p < old['pages'] else None,
                             'after': sha(after[p * PAGE:(p + 1) * PAGE]) if p < new['pages'] else None}
                            for p in range(max(old['pages'], new['pages']))]}


def addressbook_trial(before, after):
    report = compare(before, after, 'DATA')
    old, new = report['before'], report['after']
    expected = [b'', b'ZULU', b'ALPHA', b'', b'', b'', b'', b'', b'555-0100',
                b'', b'', b'Birthday', b'', b'Anniversary', b'', b'n']
    added = new['rows'].get(17)
    fields_match = bool(added and added['fields_hex'] == [v.hex() for v in expected])
    # This is a prediction being tested, not a writer or a statement of native policy.
    append_match = bool(added and added['offset'] == old['page_markers'][4])
    allowed = set(range(5 * PAGE + 40, 5 * PAGE + 40 + 18))
    tokens = [bytes.fromhex(t) for t in old['tokens_hex']]
    for token in (4, 6):
        pos = old['descriptor_offset'] + sum(len(t) + 1 for t in tokens[:token])
        allowed.update(range(pos, pos + 5))
    if added:
        allowed.update(range(added['offset'], added['end'] + 1))
    unrelated = [c['offset'] for c in report['changes'] if c['offset'] not in allowed]
    order = [t[2] for t in new['triples']]
    report['trial_checks'] = {
        'before_is_published_A01': old['sha256'] == A01,
        'ten_pages_unchanged_size': old['size'] == new['size'] == 10240,
        'counts_1_to_2_next_17_to_18': (old['count'], new['count'], old['next_id_candidate'],
                                       new['next_id_candidate']) == (1, 2, 17, 18),
        'exactly_new_id_17': report['new_ids'] == [17],
        'new_fields_match': fields_match,
        'physical_append_prediction_matches': append_match,
        'old_rows_preserved': all(report['old_rows_preserved_at_address'].values()),
        'other_descriptor_tokens_preserved': all(old['tokens_hex'][i] == new['tokens_hex'][i]
                                               for i in range(len(tokens)) if i not in (4, 6))
            if len(old['tokens_hex']) == len(new['tokens_hex']) else False,
        'unrelated_changed_offsets': unrelated}
    report['index_order_observation'] = (
        'new before old; consistent with last-name ordering for this pair' if order == [17, 16]
        else 'old before new; consistent with first-name or insertion ordering for this pair'
        if order == [16, 17] else 'outside the two-contact prediction')
    report['policy_limit'] = 'One pair cannot establish secondary ordering, ties, collation or capacity.'
    return report


def growth_trial(before, after, case):
    report = compare(before, after, 'PERSONAL')
    oracle = GROWTH[case]
    observed = {c['offset']: [c['before'], c['after']] for c in report['header_changes']}
    new_triples = [t for t in report['after']['triples'] if t not in report['before']['triples']]
    report['published_observation_checks'] = {
        'before_hash_matches': sha(before) == oracle['before'],
        'after_hash_matches': sha(after) == oracle['after'],
        'page_counts_match': [len(before) // PAGE, len(after) // PAGE] == oracle['pages'],
        'exact_header_delta_matches': observed == oracle['header'],
        'one_expected_new_target': new_triples == [oracle['new_target']],
        'old_rows_preserved': all(report['old_rows_preserved_at_address'].values()),
        'old_index_relative_order_preserved':
            [t for t in report['after']['triples'] if t in report['before']['triples']]
            == report['before']['triples'],
        'retired_rows_preserved': all(row in report['after']['retired_rows']
                                      for row in report['before']['retired_rows'])}
    report['policy_limit'] = 'Header delta correlation does not decode allocation or authorize generation.'
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trial', choices=('addressbook', 'e15', 'e19'))
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    args = parser.parse_args(argv)
    try:
        # Bound reads even for an accidentally selected large disk or RAM file.
        inputs = []
        for path in (args.before, args.after):
            with path.open('rb') as stream:
                data = stream.read(64 * PAGE + 1)
            check(len(data) <= 64 * PAGE, 'input exceeds 64-page trial bound')
            inputs.append(data)
        report = (addressbook_trial(*inputs) if args.trial == 'addressbook'
                  else growth_trial(*inputs, args.trial))
    except (OSError, ValueError) as exc:
        parser.exit(2, f'trial report failed: {exc}\n')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
