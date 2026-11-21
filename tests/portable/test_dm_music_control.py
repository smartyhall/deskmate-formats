"""Compare the independently exported original scale with its native SNG."""
import hashlib
from fractions import Fraction
import json
from pathlib import Path
import unittest

from deskmate_formats import hds
from deskmate_formats.music import parse_bytes, project
from tools.experimental.midimapper_controls import controls


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

    def test_midimapper_syntax_preserves_pitch_and_combined_modifiers(self):
        raw = (b'[Song]\r\nPolyDur=True\r\nPolyPhony=4\r\n[Notes]\r\n'
               b'1E-2\r\nSbT8.c#++1/Se8A---3/Lb4C/X\r\nLe4d3/8r/x/x\r\n'
               b'[Midi 192 11 0]\r\n[Midi &hB0 7 &H40]\r\n[Midi 300 7 64]\r\n')
        song = hds.parse_bytes(raw)
        self.assertEqual(song.raw, raw)
        self.assertEqual(song.lines[2].values, ('PolyPhony', '4'))
        monophonic, first, second, decimal, hexadecimal, malformed = song.events
        self.assertEqual([slot.pitch for slot in monophonic.slots], ['E-2'])
        self.assertEqual([slot.pitch for slot in first.slots], ['c#++1', 'A---3', 'C', None])
        self.assertEqual([slot.modifier for slot in first.slots], ['SbT', 'Se', 'Lb', ''])
        self.assertEqual(first.slots[0].quarter_notes, Fraction(1, 2))
        self.assertEqual([slot.kind for slot in second.slots], ['note', 'rest', 'placeholder', 'placeholder'])
        self.assertEqual((decimal.kind, decimal.values), ('midi', (192, 11, 0)))
        self.assertEqual((hexadecimal.kind, hexadecimal.values), ('midi', (176, 7, 64)))
        self.assertEqual(malformed.kind, 'unknown')

    def test_midimapper_octaves_and_accidentals(self):
        expected = {'C': 60, 'C1': 60, 'C2': 60, 'C4': 60, 'C+2': 72, 'c#3': 61, 'Db3': 61,
                    'C++3': 84, 'C---3': 24, 'A-3': 57, 'a-3': 57, 'C----3': 12, 'G+++++3': 127}
        for spelling, number in expected.items():
            with self.subTest(spelling=spelling):
                self.assertEqual(hds.midi_pitch(spelling), number)
        for spelling in ('C-+2', 'B#3', 'Cb3', 'E#3', 'Fb3', 'C-----3', 'G#+++++3'):
            with self.subTest(spelling=spelling), self.assertRaises(ValueError):
                hds.midi_pitch(spelling)

    def test_linear_polydur_projection(self):
        fixture = FIXTURES / 'dm-music/batch-mtrio-dm-music-1.04.hds'
        voices = hds.project_linear_voices(hds.read(fixture))
        self.assertEqual([voice.end_quarters for voice in voices], [2, 2, 2])
        self.assertEqual([[(n.midi_pitch, n.start_quarters, n.duration_quarters) for n in voice.notes]
                          for voice in voices], [[(60, 0, 1), (67, 1, 1)], [(64, 0, 1)], [(69, 0, 2)]])
        fixture = FIXTURES / 'dm-music/batch-listening-minor-scale-v1-dm-music-1.04.hds'
        voice = hds.project_linear_voices(hds.read(fixture))[0]
        self.assertEqual([note.midi_pitch for note in voice.notes],
                         [57, 59, 60, 62, 64, 65, 68, 69, 68, 65, 64, 62, 60, 59, 57])
        self.assertEqual(voice.end_quarters, 17)

    def test_native_converter_octave_setting_transposes_every_pitch(self):
        base = FIXTURES / 'dm-music'
        source, transposed = (hds.project_linear_voices(hds.read(base / f'{name}-dm-music-1.04.hds'))[0]
                              for name in ('major-scale', 'major-scale-plus-one'))
        self.assertEqual([b.midi_pitch - a.midi_pitch for a, b in zip(source.notes, transposed.notes, strict=True)],
                         [12] * 15)
        self.assertEqual(source.end_quarters, transposed.end_quarters)

    def test_linear_projection_refuses_unmodeled_controls(self):
        for line in (b'[Repeat 2x]', b'Sb4C3/x/x', b'4C3/x', b'[Midi 192 11 0]'):
            with self.subTest(line=line), self.assertRaisesRegex(hds.HdsFormatError, 'line 4'):
                song = hds.parse_bytes(b'[Song]\nPolyDur=True\n[Notes]\n' + line + b'\n')
                hds.project_linear_voices(song)

    def test_published_midimapper_inputs_and_native_exports(self):
        entries = json.loads((FIXTURES / 'manifest.json').read_bytes())['fixtures']
        exports = [entry for entry in entries if entry['path'].startswith('midimapper/')
                   and entry['path'].endswith('.mid')]
        self.assertEqual(len(exports), 13)
        for entry in exports:
            with self.subTest(fixture=entry['path']):
                output = (FIXTURES / entry['path']).read_bytes()
                source = (FIXTURES / entry['source_path']).read_bytes()
                self.assertEqual(hashlib.sha256(output).hexdigest(), entry['sha256'])
                self.assertEqual(hashlib.sha256(source).hexdigest(), entry['source_sha256'])
                self.assertEqual(len(output), entry['size'])
                self.assertEqual(output[:12], bytes.fromhex('4d5468640000000600010002'))
                self.assertEqual(int.from_bytes(output[12:14], 'big'), entry.get('ticks_per_quarter', 120))
        generated = controls()
        for dos, case in (('PITCH', 'pitch-spelling'), ('T100', 'timing-100'), ('CHANNEL', 'channel-control'),
                          ('STRUCT', 'structural-control'), ('ENHARM', 'enharmonic-boundary')):
            with self.subTest(control=case):
                path = FIXTURES / f'midimapper/{case}-tool-generated.hds'
                self.assertEqual(path.read_bytes(), generated[f'{dos}.HDS'])

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
