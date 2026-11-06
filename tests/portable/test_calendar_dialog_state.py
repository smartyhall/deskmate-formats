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


def with_form(kind, token=None, *, index=5):
    archive = triplet(kind)
    sample = archive['samples'][1]
    form = {key: sample[key] for key in ('capture_id', 'source_id', 'launch_id', 'guest_ms', 'frame',
                                        'observed_at_ms', 'held', 'paused', 'reset')}
    code, data = 0x28000, 0x36000
    form.update(module_sha256=decoder.CALENDAR_SHA256, code_base=code, data_base=data,
                anchors=anchors(code, decoder.TITLE_ANCHORS), outer_record=0x0814,
                owner_source='reviewed-register-trace', visual_source='reviewed-frame')
    if kind == 'find':
        form.update(descriptor=0x1AA0, frame_offset=0x1A2C, component_table=0x1A9A, component_count=3,
                    reviewed_dialog='find-date')
    else:
        form.update(descriptor=0x22C6, frame_offset=0x211C, component_table=0x22B4, component_count=9,
                    reviewed_dialog='add-event' if token == 0x0536 else 'change-event',
                    title=span(data + 0x2124, pack('<H', token)),
                    indices=span(data + 0x22C9, bytes((index, index))))
    archive['form'] = form
    return archive


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

    def test_editor_title_disambiguates_identical_allocation_and_geometry(self):
        for token, label, index, control in ((0x0536, 'active-add-event', 1, 'Start Time'),
                                             (0x0540, 'active-change-event', 5, 'Description')):
            with self.subTest(token=token):
                archive = with_form('change', token, index=index)
                semantic = self.replay(archive)['semantic']
                self.assertEqual(semantic['classification'], label)
                self.assertEqual(semantic['title_token'], token)
                self.assertEqual(semantic['focus_index'], index)
                self.assertEqual(semantic['focus_control'], control)
                for stage in ('ownership', 'frame', 'component_table'):
                    self.assertEqual(semantic[stage], 'corroborated')

    def test_retained_editor_slot_cannot_activate_idle_or_rename_find_date(self):
        archive = with_form('change', 0x0540)
        idle = triplet('idle')
        idle['form'] = archive['form']
        idle['samples'][1]['geometry'] = archive['samples'][1]['geometry']
        self.assertEqual(self.replay(idle)['semantic']['classification'], 'no-verified-active-modal-context')
        find = with_form('find')
        find['form']['title'] = archive['form']['title']
        result = self.replay(find)['semantic']
        self.assertEqual(result['classification'], 'active-find-date')
        self.assertNotIn('title_token', result)
        self.assertNotIn('focus_index', result)

    def test_known_context_with_missing_owner_or_unrecognized_title(self):
        for archive in (triplet('change'), with_form('change', 0x9999), triplet('find')):
            result = self.replay(archive)['semantic']
            self.assertEqual(result['classification'], 'verified-modal-unknown-identity')
            self.assertEqual(result['allocation'], 'geometry-corroborated')

    def test_form_rejects_missing_conflicting_or_mismatched_evidence(self):
        for mutation, reason in (
            (lambda a: a['samples'][1].pop('window'), 'window'),
            (lambda a: a['samples'][1].pop('geometry'), 'requires allocated outer geometry'),
            (lambda a: a['samples'][1]['window'].update(hex=pack('<3H', 0x088C, 0x0EFC, 0xFFFF).hex()),
             'unrecognized'),
            (lambda a: a['form'].update(module_sha256='0'*64), 'Calendar source identity'),
            (lambda a: a['form']['anchors'][0].update(sha256='0'*64), 'anchor mismatch'),
            (lambda a: a['form'].update(capture_id='other-capture'), 'different checkpoint'),
            (lambda a: a['form'].update(data_base=0x36010), 'span mapping'),
            (lambda a: a['form'].update(outer_record=0x088C), 'does not own'),
            (lambda a: a['form'].update(descriptor=0x1AA0), 'does not own'),
            (lambda a: a['form'].update(owner_source='reviewed-frame'), 'separate owner and visual'),
            (lambda a: a['form'].update(frame_offset=0x1A2C), 'frame conflicts'),
            (lambda a: a['form'].update(component_table=0x1A9A), 'component table'),
            (lambda a: a['form']['indices'].update(hex='0909'), 'focus index'),
            (lambda a: a['form']['indices'].update(hex='0501'), 'focus index'),
            (lambda a: a['form'].update(reviewed_dialog='add-event'), 'visual label'),
        ):
            with self.subTest(reason=reason):
                archive = with_form('change', 0x0540)
                mutation(archive)
                result = self.replay(archive)['semantic']
                self.assertEqual(result['classification'], 'insufficient-or-contradictory-evidence')
                self.assertIn(reason, result['reason'])

    def test_stale_form_cannot_upgrade_legacy_context(self):
        result = self.replay(with_form('change', 0x0536), age=19)['semantic']
        self.assertEqual(result['classification'], 'insufficient-or-contradictory-evidence')
        self.assertIn('stale', result['reason'])


if __name__ == '__main__':
    unittest.main()
