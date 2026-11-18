"""Audio regressions independent of Tandy executables and the live emulator."""

from collections import Counter
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from struct import pack, pack_into, unpack_from
import tempfile
import unittest
import wave

from deskmate_formats import music, sound
from deskmate_formats.preservation.bundle import export, verify


FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures/application-generated'


def original_sound(payload, *, compression=0, frames=None):
    if frames is None:
        frames = len(payload)
    return (pack('<4B10sH4B6I', 26, compression, 1, 0, b'Lab pulse', 5500, 255, 0, 255, 255,
                 44, len(payload) if compression else 0, 0, frames, 0, 0)
            + payload)


def later_linked_sound():
    # The next descriptor lives after the first sample. A descriptor parser
    # that assumes contiguous records will seek into the sample or the gap.
    data = bytearray(222)
    data[:8] = b'Lab tone'
    pack_into('<2sHH', data, 44, b'\x1a\x80', 2, 17)
    pack_into('<H', data, 88, 11000)
    pack_into('<IH4B5I', data, 114, 170, 0, 28, 0, 1, 37, 160, 3, 3, 1, 2)
    data[160:163] = b'\x80\xb0\x70'
    pack_into('<IH4B5I', data, 170, 0, 0, 40, 255, 38, 63, 216, 6, 6, 0, 0)
    data[216:222] = b'\x80\xa0\x60\x01\xff\x80'
    return bytes(data)


def score_bytes(voices, conductor=(), *, trailer=b'', alignment=0):
    header = bytearray(music.SIGNATURE + bytes(20))
    data = header + b'Lab\0Author\0'
    data += bytes([alignment])
    for words in (*voices, conductor):
        data.extend(pack(f'<{len(words) + 2}H', 0x7ffe, *words, 0x7fff))
    pack_into('<H', data, 22, len(data) - 22)
    return bytes(data) + trailer


class SoundTests(unittest.TestCase):
    def test_odd_pcm_and_original_signature_collision(self):
        pcm = b'\x1a\x80\xff'
        source = original_sound(pcm)
        parsed = sound.parse_bytes(source)
        self.assertEqual(parsed.profile, 'sound-original-table')
        self.assertEqual(parsed.kind, 'recording')
        self.assertEqual(parsed.pcm(0), pcm)
        wav = parsed.wav(0)
        self.assertEqual(len(wav), 48)
        self.assertEqual(unpack_from('<I', wav, 4)[0], 40)
        with wave.open(BytesIO(wav), 'rb') as decoded:
            self.assertEqual((decoded.getframerate(), decoded.getnchannels(),
                              decoded.getsampwidth(), decoded.getnframes()), (5500, 1, 1, 3))
            self.assertEqual(decoded.readframes(5), pcm)

    def test_linked_descriptors_and_gaps(self):
        parsed = sound.parse_bytes(later_linked_sound())
        self.assertEqual(parsed.profile, 'sound-later-linked')
        self.assertEqual(parsed.instrument_number, 17)
        self.assertEqual(parsed.unassigned_regions, ((163, 170),))
        self.assertEqual([s.descriptor_offset for s in parsed.samples], [114, 170])
        self.assertEqual([s.midi_pitch for s in parsed.samples], [60, 72])
        self.assertEqual((parsed.samples[0].sustain_start, parsed.samples[0].sustain_end), (1, 2))

    def test_delta_literal_saturation_and_runs(self):
        # Delta +7, literal 254, +7 clips to 255, short repeat twice,
        # long repeat of 14 and explicit silence of 25 + 2 + 1.
        compressed = pack('>14hH', 7, *([0] * 13), 25) + bytes.fromhex('0e fe 0f 1f f0 0f e0 20')
        output = bytes([135, 254]) + b'\xff' * 17 + b'\x80' * 28
        for mode in (1, 2):
            with self.subTest(mode=mode):
                parsed = sound.parse_bytes(original_sound(compressed, compression=mode, frames=len(output)))
                self.assertEqual(parsed.pcm(0), output)
                clipped = sound.parse_bytes(original_sound(compressed, compression=mode, frames=len(output) - 5))
                self.assertEqual(clipped.pcm(0), output[:-5])
                short = sound.parse_bytes(original_sound(compressed[:-3], compression=mode, frames=len(output)))
                with self.assertRaises(sound.SoundFormatError):
                    short.pcm(0)

    def test_rejects_bad_bounds_and_loops(self):
        source = later_linked_sound()
        for offset, value in ((114, 114), (124, 150), (128, 999), (170, 114), (180, 160)):
            with self.subTest(offset=offset):
                damaged = bytearray(source)
                pack_into('<I', damaged, offset, value)
                with self.assertRaises(sound.SoundFormatError):
                    sound.parse_bytes(damaged)
        with self.assertRaises(sound.SoundFormatError):
            sound.parse_bytes(original_sound(b'\x80\xff')[:-1])

    def test_sound_workbench_preserves_original_and_catalogs_wavs(self):
        source = later_linked_sound()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'sample.bin'
            path.write_bytes(source)
            archive = Path(folder) / 'bundle'
            manifest = export(path, archive)
            self.assertEqual(manifest['application'], 'sound')
            self.assertEqual(verify(archive), manifest)
            self.assertEqual((archive / 'original.snd').read_bytes(), source)
            self.assertEqual(sorted(p.name for p in (archive / 'assets').iterdir()),
                             ['sample-01.wav', 'sample-02.wav'])
            self.assertIn('media-src', (archive / 'preview.html').read_text(encoding='utf-8'))
            self.assertEqual(len(json.loads((archive / 'content.json').read_bytes())['samples']), 2)


class MusicTests(unittest.TestCase):
    def test_streams_and_unassigned_bytes(self):
        encoded = score_bytes(((0xea1c,), (0xea00, 0xea28), ()), (0x2030,),
                              trailer=b'\x1a', alignment=0x72)
        score = music.parse_bytes(encoded)
        self.assertEqual((score.title, score.author), ('Lab', 'Author'))
        self.assertEqual(score.text_padding, b'\x72')
        self.assertEqual(score.trailer, b'\x1a')
        self.assertEqual(Counter(x.word for voice in score.voices for x in voice),
                         Counter([0xea00, 0xea1c, 0xea28]))
        self.assertEqual(score.conductor[0].word, 0x2030)
        for voice in score.voices:
            for event in voice:
                self.assertEqual(unpack_from('<H', encoded, event.offset)[0], event.word)

    def test_rejects_malformed_score(self):
        example = score_bytes(((0xea1c,), (), ()), (0x2018,))
        for damaged in (example[:-1], example + b'00', b'.SNG' + example[4:],
                        example[:38] + b'\xfe\x7f' + example[40:]):
            with self.assertRaises(music.MusicFormatError):
                music.parse_bytes(damaged)

    def test_native_note_values_tempo_and_midi(self):
        score = music.parse_bytes((FIXTURES / 'music/mtempo.sng').read_bytes())
        sequence = music.project(score)
        self.assertEqual(sequence.written_ticks, 237)
        self.assertEqual(sequence.voice_ticks, (237, 0, 0))
        self.assertEqual([(e.tick, e.duration_ticks, e.midi_pitch) for e in sequence.voices[0]],
                         [(0, 24, 60), (24, 24, 67), (48, 24, None), (72, 12, 64),
                          (84, 48, 69), (132, 96, 65), (228, 6, 62), (234, 3, 71)])
        self.assertEqual((sequence.conductor[0].tick, sequence.conductor[0].quarter_bpm), (0, 140))
        midi = music.to_midi(sequence)
        self.assertEqual(unpack_from('>4sIHHH', midi), (b'MThd', 6, 1, 4, 24))
        self.assertIn(bytes.fromhex('00 ff 51 03 06 8a 1b'), midi)
        self.assertIn(bytes.fromhex('00 90 3c 40 18 80 3c 00 00 90 43 40'), midi)
        self.assertIn(bytes.fromhex('18 90 40 40'), midi)

    def test_opaque_music_projects_to_json_with_no_midi_asset(self):
        source = score_bytes(((0xea1c, 0x7320, 0xea1d), (), ()), (0x2030, 0x7400))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'unknown.bin'
            path.write_bytes(source)
            archive = Path(folder) / 'music'
            manifest = export(path, archive)
            self.assertEqual((archive / 'original.sng').read_bytes(), source)
            self.assertEqual(verify(archive), manifest)
            self.assertFalse((archive / 'composition.mid').exists())
            self.assertIn('midi_omitted', {d['code'] for d in manifest['diagnostics']})
            events = json.loads((archive / 'content.json').read_bytes())['voices'][0]
            self.assertEqual([event['kind'] for event in events], ['note', 'opaque', 'note'])
            self.assertIsNone(events[-1]['tick'])


class NativeSoundTests(unittest.TestCase):
    def test_native_tone_sample_bytes(self):
        source = (FIXTURES / 'sound/tone-native-pcm.snd').read_bytes()
        document = sound.parse_bytes(source)
        pcm = document.pcm(0)
        self.assertEqual(document.name, 'LAB TONE')
        self.assertEqual((len(pcm), document.sample_rate), (5500, 11000))
        self.assertEqual(sha256(pcm).hexdigest(),
                         'e5788ae0618e3167842ee0de426973800c06ad85f48b01228a6cd3e7b868b795')
        with wave.open(BytesIO(document.wav(0)), 'rb') as reader:
            self.assertEqual(reader.readframes(5500), source[160:])
