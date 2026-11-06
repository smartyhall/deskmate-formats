"""Synthetic archived inputs exercise the Calendar interpretation gates."""

from copy import deepcopy
import importlib
from pathlib import Path
from struct import pack
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools' / 'experimental'))
try:
    decoder = importlib.import_module('calendar_dialog_state')
finally:
    sys.path.pop(0)


def span(address, data):
    return {'address': address, 'length': len(data), 'hex': data.hex(), 'view': 'normal', 'width': 1}


def anchors(code_base, reference):
    return [dict(address=code_base + offset - 0x200, length=length, sha256=digest, view='normal', width=1)
            for offset, length, digest in reference]


def triplet(kind):
    code, context = 0x10000, 0x20000
    day = (0x07D8, 0x0F9C, 1)
    during, size = {
        'idle': (day, None),
        'change': ((0x088C, 0x0EFC, 7), (0x1194, 0x0B2C)),
        'find': ((0x088C, 0x0F5C, 8), (0x0AF0, 0x044C)),
    }[kind]
    samples = [dict(label=label, capture_id=f'capture-{label}', launch_id='example-launch',
                    source_id='example-archive', held=True, paused=False, reset=[1, 1, 610],
                    guest_ms=i*10, frame=i, observed_at_ms=100+i*10,
                    anchors=anchors(code, decoder.DMCSR_ANCHORS),
                    window=span(context+0x0F9C, pack('<3H', *words)))
               for i, (label, words) in enumerate(zip('ABC', (day, during, day), strict=True), 1)]
    if size:
        samples[1]['geometry'] = span(context+0x07D8+0x3C+0x18, pack('<2H', *size))
    return dict(mapping=dict(module_sha256=decoder.DMCSR_SHA256, code_base=code, context_base=context),
                samples=samples)


class DialogStateTests(unittest.TestCase):
    def replay(self, archive, age=40):
        return decoder.replay(archive, as_of_ms=140, max_age_ms=age)

    def test_tested_contexts_and_stale_geometry_at_day_view(self):
        for kind, expected in (('idle', 'no-tested-modal-context'), ('change', 'change-event-style'),
                               ('find', 'find-date-style')):
            with self.subTest(kind=kind):
                archive = triplet(kind)
                archive['samples'][0]['geometry'] = {'hex': 'ffffffff'}
                result = self.replay(archive)
                self.assertEqual(result['classification'], expected)
                self.assertIsNone(result['focus'])
                self.assertEqual(result['age_ms'], 20)
                if kind != 'idle':
                    self.assertTrue(result['geometry_corroborated'])
                    self.assertEqual(result['add_event_possible'], kind == 'change')

    def test_missing_geometry_keeps_add_ambiguity(self):
        archive = triplet('change')
        del archive['samples'][1]['geometry']
        result = self.replay(archive)
        self.assertEqual(result['classification'], 'change-event-style')
        self.assertFalse(result['geometry_corroborated'])
        self.assertTrue(result['add_event_possible'])

    def test_rejects_stale_evidence(self):
        result = self.replay(triplet('change'), age=19)
        self.assertEqual(result['classification'], 'unknown')
        self.assertIn('stale', result['reason'])

    def test_rejects_unrecognized_counts_and_failed_restoration(self):
        archive = triplet('change')
        samples = archive['samples']
        samples[1]['window']['hex'] = pack('<3H', 0x088C, 0x0F4C, 7).hex()
        self.assertIn('unrecognized', self.replay(archive)['reason'])
        samples[2]['window']['hex'] = pack('<3H', 0x07D8, 0x0F9C, 7).hex()
        self.assertIn('did not restore', self.replay(archive)['reason'])

    def test_rejects_conflicting_geometry_or_identity(self):
        for mutation, reason in (
            (lambda a: a['mapping'].update(module_sha256='0'*64), 'source identity'),
            (lambda a: a['samples'][2]['anchors'][0].update(sha256='0'*64), 'anchor mismatch'),
            (lambda a: a['samples'][1]['geometry'].update(address=0x2082D), 'span mapping'),
            (lambda a: a['samples'][1]['geometry'].update(hex='00000000'), 'geometry conflicts'),
            (lambda a: a['samples'][2].update(reset=[1, 2, 611]), 'launch/reset'),
        ):
            with self.subTest(reason=reason):
                archive = triplet('change')
                mutation(archive)
                result = self.replay(archive)
                self.assertEqual(result['classification'], 'unknown')
                self.assertIn(reason, result['reason'])

    def test_focus_requires_same_capture_and_reviewed_change_event(self):
        archive = triplet('change')
        evidence = deepcopy(archive['samples'][1])
        evidence.update(module_sha256=decoder.CALENDAR_SHA256, code_base=0x28000, data_base=0x36000,
                        anchors=anchors(0x28000, decoder.CALENDAR_ANCHORS),
                        indices=span(0x36000+0x22C9, bytes((5, 5))),
                        reviewed_dialog='change-event', visual_source='reviewed-frame')
        archive['focus'] = evidence
        result = self.replay(archive)
        self.assertEqual(result['focus']['control'], 'Description')
        evidence['capture_id'] = 'other-capture'
        self.assertIsNone(self.replay(archive)['focus'])
        evidence['capture_id'] = archive['samples'][1]['capture_id']
        evidence['reviewed_dialog'] = 'add-event'
        self.assertIsNone(self.replay(archive)['focus'])


if __name__ == '__main__':
    unittest.main()
