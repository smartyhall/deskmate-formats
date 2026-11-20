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


if __name__ == '__main__':
    unittest.main()
