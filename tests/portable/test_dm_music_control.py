"""Compare the independently exported original scale with its native SNG."""
import hashlib
from fractions import Fraction
import json
from pathlib import Path
import unittest

from deskmate_formats import hds
from deskmate_formats.music import parse_bytes, project


FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures/application-generated'


class DmMusicControlTests(unittest.TestCase):
    def test_major_scale_projection(self):
        source = FIXTURES / 'music/listening-major-scale-v1.sng'
        sequence = project(parse_bytes(source.read_bytes()))
        notes = [e for e in sequence.voices[0] if e.kind in ('note', 'rest')]
        expected = [60, 62, 64, 65, 67, 69, 71, 72, 71, 69, 67, 65, 64, 62, 60, None]
        self.assertEqual([n.midi_pitch for n in notes], expected)
        self.assertEqual([n.duration_ticks for n in notes], [24] * 14 + [48, 24])

        output = (FIXTURES / 'dm-music/major-scale-dm-music-1.04.hds').read_bytes()
        self.assertEqual(hashlib.sha256(output).hexdigest(),
                         '64731a55b2a583045eaccddb066b2194e941912445c589dd93b9f826a41e52e1')
        lines = output.decode('ascii').split('\r\n')
        timed = [line.split('/')[0] for line in lines if line.endswith('/x/x')]
        self.assertEqual(timed, [
            '4C3', '4D3', '4E3', '4F3', '4G3', '4A3', '4B3', '4C+2',
            '4B3', '4A3', '4G3', '4F3', '4E3', '4D3', '2C3', '4R'])
        for control in ('Pace=100', '[Tempo= 1/4 = 100]', '[Inst. 1 = 9]',
                        '[Inst. 1 dyn. = mp]', '[Inst. 1 dyn. = mf]'):
            self.assertIn(control, lines)

    def test_duration_and_accidental_controls(self):
        tempo = project(parse_bytes((FIXTURES / 'music/mtempo.sng').read_bytes()))
        self.assertEqual(tempo.conductor[0].quarter_bpm, 140)
        self.assertEqual([e.duration_ticks for e in tempo.voices[0]], [24, 24, 24, 12, 48, 96, 6, 3])
        duration = (FIXTURES / 'dm-music/duration-tempo-dm-music-1.04.hds').read_bytes()
        self.assertIn(b'Pace=100\r\n', duration)
        self.assertIn(b'[Tempo= 1/4 = 140]\r\n', duration)
        self.assertIn(b'1F3/x/x\r\n16D3/x/x\r\n32B3/x/x', duration)

        accidental = project(parse_bytes((FIXTURES / 'music/accidentals-native.sng').read_bytes()))
        self.assertEqual([e.midi_pitch for e in accidental.voices[0]], [65, 66, 65, 64])
        hds = (FIXTURES / 'dm-music/accidentals-dm-music-1.04.hds').read_bytes()
        self.assertIn(b'4F3/x/x\r\n4F#3/x/x\r\n4F3/x/x\r\n4E3/x/x', hds)

    def test_alternate_endings_preserve_control_order(self):
        synthetic = FIXTURES / 'music/alternate-endings-tool-generated.sng'
        sequence = project(parse_bytes(synthetic.read_bytes()))
        controls = [e for e in sequence.conductor if e.kind != 'advance']
        self.assertEqual([(e.kind, e.tick) for e in controls], [
            ('repeat_start', 0), ('alternate_ending', 24),
            ('alternate_ending', 48), ('repeat_end', 72)])
        self.assertEqual([e.ending_number for e in controls[1:3]], [1, 2])
        output = (FIXTURES / 'dm-music/alternate-endings-dm-music-1.04.hds').read_bytes()
        events = output.decode('ascii').split('[Notes]\r\n')[1].splitlines()
        self.assertEqual([line for line in events if line], [
            '[Repeat 2x]', '[Inst. 1 = 9]', '4C3/x/x', '[Ending 1]', '4E3/x/x',
            '[Ending 2]', '4G3/x/x', '[Repeat End]', '4A3/x/x'])

    def test_hds_parser_keeps_native_labels_and_projects_observed_durations(self):
        for source, name in (
            ('listening-major-scale-v1', 'major-scale'),
            ('mtempo', 'duration-tempo'),
            ('accidentals-native', 'accidentals'),
        ):
            with self.subTest(name=name):
                input_path = FIXTURES / f'music/{source}.sng'
                input_song = project(parse_bytes(input_path.read_bytes()))
                path = FIXTURES / f'dm-music/{name}-dm-music-1.04.hds'
                output_song = hds.read(path)
                self.assertEqual(output_song.raw, path.read_bytes())
                rows = [line for line in output_song.events if line.kind == 'row']
                self.assertEqual([line.slots[0].quarter_notes for line in rows],
                                 [Fraction(e.duration_ticks, 24) for e in input_song.voices[0]
                                  if e.kind in ('note', 'rest')])
                self.assertTrue(all([slot.kind for slot in row.slots[1:]] == ['placeholder'] * 2
                                    for row in rows))
        rows = [line for line in hds.read(FIXTURES / 'dm-music/major-scale-dm-music-1.04.hds').events
                if line.kind == 'row']
        self.assertEqual([rows[index].slots[0].pitch for index in (0, 7, -1)], ['C3', 'C+2', 'R'])

    def test_hds_preserves_uninterpreted_syntax_in_order(self):
        raw = b'[Song]\r\nName=\x80\runknown=1\n[Notes]\r\n[Future Syntax]\r\n4C3/?/x\r\n'
        song = hds.parse_bytes(raw)
        self.assertEqual(song.raw, raw)
        self.assertEqual([(line.kind, line.text) for line in song.events],
                         [('unknown', '[Future Syntax]'), ('row', '4C3/?/x')])
        self.assertEqual([slot.kind for slot in song.events[1].slots], ['note', 'unknown', 'placeholder'])
        with self.assertRaises(hds.HdsFormatError):
            hds.parse_bytes(b'[Notes]\n[Song]\n')

    def test_batch_hds_bytes_and_per_voice_durations(self):
        entries = json.loads((FIXTURES / 'manifest.json').read_bytes())['fixtures']
        batch = [item for item in entries if item['path'].startswith('dm-music/batch-')]
        self.assertGreaterEqual(len(batch), 32)
        for item in batch:
            with self.subTest(fixture=item['path']):
                score = (FIXTURES / item['source_path']).read_bytes()
                output = (FIXTURES / item['path']).read_bytes()
                self.assertEqual(hashlib.sha256(score).hexdigest(), item['source_sha256'])
                self.assertEqual(hashlib.sha256(output).hexdigest(), item['sha256'])
                self.assertEqual(len(output), item['size'])
                self.assertNotIn(b'\n', output.replace(b'\r\n', b''))
                parsed = hds.parse_bytes(output)
                self.assertFalse(any(line.kind == 'unknown' for line in parsed.lines))
                rows = [line.slots for line in parsed.events if line.kind == 'row']
                self.assertTrue(all(len(row) == 3 and all(slot.kind != 'unknown' for slot in row)
                                    for row in rows))
                sequence = project(parse_bytes(score))
                for voice, events in enumerate(sequence.voices):
                    expected = [Fraction(e.duration_ticks, 24) for e in events if e.kind in ('note', 'rest')]
                    self.assertEqual([row[voice].quarter_notes for row in rows
                                      if row[voice].kind in ('note', 'rest')], expected)

    def test_batch_written_controls_and_connection_markers(self):
        def events(case):
            return hds.read(FIXTURES / f'dm-music/batch-{case}-dm-music-1.04.hds').events

        self.assertEqual([(row.kind, row.values) for row in events('mtimes') if row.kind != 'row'],
                         [('time', (6, 8)), ('tempo', (1, 2, 75))])
        self.assertEqual(events('m14')[0].values, ('G',))
        self.assertEqual([row.slots[0].modifier for row in events('m12')], ['Sb', '', 'Se'])
        self.assertEqual([row.slots[0].quarter_notes for row in events('m10') if row.kind == 'row'][:5],
                         [Fraction(3, 2), Fraction(7, 4), *([Fraction(2, 3)] * 3)])


if __name__ == '__main__':
    unittest.main()
