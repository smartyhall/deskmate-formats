"""Replay archived DeskMate 3.05 dialog evidence without an emulator."""

import argparse
import json
from pathlib import Path
import re
from struct import unpack

from calendar_window_context import WINDOW_RECORD_SIZE, compare_triplet


DMCSR_SHA256 = '085edb2f2c67ae323343d9efedd7c731778f5fbb8dc59ed8bd6560006b45da75'
CALENDAR_SHA256 = '819df5658b663aa69b15584abf805062679e97f587f3404738f6e82876e4bd23'
DMCSR_ANCHORS = (
    (0x2444, 41, 'b1e14c261de76dfdd239ae458b61c4d4852dafea4ce4147515d36f14a8405819'),
    (0x2477, 25, 'af83d2c31b27165ca30e753a3652763d23e2292b102f13f648d826733a51ec16'),
)
CALENDAR_ANCHORS = (
    (0xC775, 23, '1ea0bd0bc8da6ba56b3ee25d76d97d3a745bfca5fadda5a6e6fdfe195a22dae9'),
    (0xE2B4, 19, 'aa3287bd17373ac67fae6998c74b0cd4a2123d3c2933490f0c80775093727e03'),
)
MZ_HEADER = 0x200
WINDOW_WORDS = 0x0F9C
OUTER_SIZE = 0x18
FOCUS_WORDS = 0x22C9
MAX_INPUT = 65536
FORMS = {
    (3, 10): ('change-event-style', (0x1194, 0x0B2C)),
    (3, 4): ('find-date-style', (0x0AF0, 0x044C)),
}
TESTED_FOCUS = {1: 'Start Time', 5: 'Description'}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def counter(value):
    require(type(value) is int and value >= 0, 'invalid clock, frame, or reset counter')
    return value


def identity(value):
    require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,96}', value),
            'invalid evidence identity')
    return value


def base(value):
    require(type(value) is int and 0x500 <= value < 0xA0000 and value % 16 == 0,
            'invalid conventional-RAM segment base')
    return value


def span_identity(span, address, length):
    require(all(type(span[key]) is int for key in ('address', 'length', 'width')) and
            address >= 0x500 and address + length <= 0xA0000 and
            (span['address'], span['length'], span['view'], span['width']) == (address, length, 'normal', 1),
            'span mapping or read view mismatch')


def verify_anchors(anchors, code_base, reference):
    require(len(anchors) == len(reference), 'missing code anchors')
    for span, (offset, length, digest) in zip(anchors, reference, strict=True):
        span_identity(span, code_base + offset - MZ_HEADER, length)
        require(span['sha256'] == digest, 'code anchor mismatch')


def read_span(span, address, length):
    span_identity(span, address, length)
    raw = bytes.fromhex(span['hex'])
    require(len(raw) == length, 'incomplete data span')
    return raw


def checkpoint(sample):
    require(sample['held'] is True and sample['paused'] is False, 'checkpoint was not held and unpaused')
    require(len(sample['reset']) == 3, 'invalid reset identity')
    return {
        'capture_id': identity(sample['capture_id']), 'source_id': identity(sample['source_id']),
        'launch_id': identity(sample['launch_id']), 'guest_ms': counter(sample['guest_ms']),
        'frame': counter(sample['frame']), 'observed_at_ms': counter(sample['observed_at_ms']),
        'reset': [counter(value) for value in sample['reset']],
    }


def decode_focus(sample, evidence, *, as_of_ms, max_age_ms):
    """Interpret the two previously live-validated focus indices with a same-capture visual witness."""
    observed = checkpoint(sample)
    age = counter(as_of_ms) - observed['observed_at_ms']
    require(0 <= age <= counter(max_age_ms), 'stale or future focus evidence')
    require(checkpoint(evidence) == observed, 'focus evidence is from a different checkpoint')
    require(evidence['reviewed_dialog'] == 'change-event', 'focus lacks an independent Change Event label')
    visual_source = identity(evidence['visual_source'])
    require(evidence['module_sha256'] == CALENDAR_SHA256, 'Calendar source identity mismatch')
    verify_anchors(evidence['anchors'], base(evidence['code_base']), CALENDAR_ANCHORS)
    current, prior = read_span(evidence['indices'], base(evidence['data_base']) + FOCUS_WORDS, 2)
    require(current == prior and current in TESTED_FOCUS, 'focus index lacks settled live corroboration')
    return {'control': TESTED_FOCUS[current], 'index': current, 'visual_source': visual_source,
            'checkpoint': observed, 'age_ms': age}


def replay(archive, *, as_of_ms, max_age_ms):
    """Return a scoped interpretation of the archived B sample with A and C as controls."""
    result = {'classification': 'unknown', 'focus': None}
    try:
        mapping = archive['mapping']
        require(mapping['module_sha256'] == DMCSR_SHA256, 'DMCSR source identity mismatch')
        code_base, context_base = base(mapping['code_base']), base(mapping['context_base'])
        samples = archive['samples']
        require([sample['label'] for sample in samples] == ['A', 'B', 'C'], 'expected A/B/C in order')
        evidence = [checkpoint(sample) for sample in samples]
        a, b, c = evidence
        require(len({item['capture_id'] for item in evidence}) == 3 and all(
            (item['launch_id'], item['reset']) == (a['launch_id'], a['reset']) for item in evidence),
            'checkpoint or launch/reset identity mismatch')
        require(all(a[field] <= b[field] <= c[field] for field in ('observed_at_ms', 'guest_ms', 'frame')) and
                a['guest_ms'] < b['guest_ms'] < c['guest_ms'], 'checkpoint time order mismatch')
        age = counter(as_of_ms) - b['observed_at_ms']
        result.update(age_ms=age, checkpoints=evidence, module_sha256=DMCSR_SHA256,
                      code_base=code_base, context_base=context_base)
        require(as_of_ms >= c['observed_at_ms'] and age <= counter(max_age_ms), 'stale or future dialog evidence')
        for sample in samples:
            verify_anchors(sample['anchors'], code_base, DMCSR_ANCHORS)
        transition = compare_triplet(*(read_span(sample['window'], context_base + WINDOW_WORDS, 6)
                                       for sample in samples))
        require(transition['a_equals_c'], 'window context did not restore at C')
        counts = transition['a_to_b_window_records'], transition['a_to_b_small_records']
        handle_changed = transition['a_to_b_selected_id_changed']
        if counts == (0, 0) and not handle_changed:
            result['classification'] = 'no-tested-modal-context'
            return result
        require(counts in FORMS and handle_changed, 'unrecognized window-context transition')
        style, size = FORMS[counts]
        geometry = samples[1].get('geometry')
        if geometry is not None:
            parent = transition['checkpoints']['A']['window_record_top']
            outer = parent + WINDOW_RECORD_SIZE
            require(outer + WINDOW_RECORD_SIZE <= transition['checkpoints']['B']['window_record_top'],
                    'outer dialog window is not allocated')
            words = unpack('<2H', read_span(geometry, context_base + outer + OUTER_SIZE, 4))
            require(words == size, 'geometry conflicts with the tested context')
        result.update(classification=style, geometry_corroborated=geometry is not None,
                      add_event_possible=style == 'change-event-style')
        focus = archive.get('focus')
        if style == 'change-event-style' and focus is not None:
            try:
                result['focus'] = decode_focus(samples[1], focus, as_of_ms=as_of_ms, max_age_ms=max_age_ms)
            except (KeyError, TypeError, ValueError) as error:
                result['focus_warning'] = str(error)
    except (KeyError, TypeError, ValueError) as error:
        result['reason'] = str(error)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--as-of-ms', type=int, required=True)
    parser.add_argument('--max-age-ms', type=int, required=True)
    args = parser.parse_args(argv)
    try:
        with args.archive.open('rb') as stream:
            raw = stream.read(MAX_INPUT + 1)
        require(len(raw) <= MAX_INPUT, 'archive exceeds input limit')
        archive = json.loads(raw)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(replay(archive, as_of_ms=args.as_of_ms, max_age_ms=args.max_age_ms), indent=2))


if __name__ == '__main__':
    main()
