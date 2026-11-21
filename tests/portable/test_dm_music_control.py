"""Compare the independently exported original scale with its native SNG."""
import hashlib
from pathlib import Path
import unittest

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


if __name__ == '__main__':
    unittest.main()
