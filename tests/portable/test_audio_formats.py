"""Audio regressions independent of Tandy executables and the live emulator."""

from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
from io import BytesIO, StringIO
import json
from pathlib import Path
from struct import pack, pack_into, unpack_from
import tempfile
import unittest
from unittest.mock import patch
import wave

from deskmate_formats import music, sampled_music, sound
from deskmate_formats.preservation.bundle import export, verify
from deskmate_formats.preservation.cli import main as preserve_main


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
    def test_opt_in_sector_padding_preserves_opaque_tail(self):
        source = score_bytes(((0x4010,), (), ()))
        trailer = bytes(range(128 - len(source)))
        padded = source + trailer
        with self.assertRaisesRegex(music.MusicFormatError, 'declared Music extent'):
            music.parse_bytes(padded)
        parsed = music.parse_bytes(padded, allow_sector_padding=True)
        self.assertEqual(parsed.trailer, trailer)
        self.assertEqual(parsed.voices, music.parse_bytes(source).voices)
        for invalid in (padded[:-1], padded + bytes(128)):
            with self.assertRaisesRegex(music.MusicFormatError, 'declared Music extent'):
                music.parse_bytes(invalid, allow_sector_padding=True)

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

    def test_native_three_voices_and_external_slot(self):
        source = (FIXTURES / 'music/m08.sng').read_bytes()
        score = music.parse_bytes(source)
        sequence = music.project(score)
        self.assertEqual(source, (FIXTURES / 'music/mreopen.sng').read_bytes())
        change = sequence.voices[0][0]
        self.assertEqual((change.kind, change.tick, change.word, change.instrument_slot),
                         ('instrument', 0, 0x7306, 7))
        instrument = sound.parse_bytes((FIXTURES / 'sound/labinst-native.snd').read_bytes())
        self.assertEqual(change.instrument_slot, instrument.instrument_number)
        notes = [[(e.tick, e.midi_pitch, e.duration_ticks) for e in voice if e.kind == 'note']
                 for voice in sequence.voices]
        self.assertEqual(notes, [[(0, 60, 24), (24, 67, 24)], [(0, 64, 24)], [(0, 69, 48)]])
        self.assertEqual(sequence.voice_ticks, (48, 48, 48))
        midi = music.to_midi(sequence)
        for track in ('00 90 3c 40 18 80 3c 00', '00 91 40 40 18 81 40 00', '00 92 45 40 30 82 45 00'):
            self.assertIn(bytes.fromhex(track), midi)

    def test_native_modifiers_barline_and_text_alignment(self):
        score = music.parse_bytes((FIXTURES / 'music/m10.sng').read_bytes())
        self.assertEqual((score.title, score.author, score.text_padding), ('Lab Arcs', 'Lab Control', b'b'))
        sequence = music.project(score)
        events = sequence.voices[0]
        self.assertEqual((events[0].kind, events[0].dynamic_index), ('dynamic', 4))
        self.assertEqual([e.duration_ticks for e in events[1:]], [36, 42, 16, 16, 16, 24, 24])
        self.assertEqual([e.midi_pitch for e in events[1:]], [60, 62, 64, 65, 67, 61, 72])
        self.assertEqual(sequence.written_ticks, 174)
        line = sequence.conductor[-1]
        self.assertEqual((line.kind, line.bar_number, line.tick), ('barline', 1, 174))
        self.assertTrue(music.to_midi(sequence).startswith(b'MThd'))

    def test_native_growth_and_middle_deletion(self):
        before, after = (music.parse_bytes((FIXTURES / f'music/{n}.sng').read_bytes())
                         for n in ('mgrow', 'medit'))
        words = [item.word for item in before.voices[0]]
        self.assertEqual(len(words), 33)
        self.assertEqual([item.word for item in after.voices[0]], words[:1] + words[2:])
        self.assertEqual((music.project(before).written_ticks, music.project(after).written_ticks), (792, 768))

    def test_native_mid_score_tempo_and_meter(self):
        score = music.parse_bytes((FIXTURES / 'music/mtimes.sng').read_bytes())
        sequence = music.project(score)
        _, tempo, meter, _ = sequence.conductor
        self.assertEqual((tempo.tick, tempo.tempo_bpm, tempo.tempo_note_denominator, tempo.quarter_bpm),
                         (24, 75, 2, 150))
        self.assertEqual((meter.tick, meter.meter_numerator, meter.meter_denominator), (24, 6, 8))
        midi = music.to_midi(sequence)
        self.assertIn(bytes.fromhex('00 ff 51 03 09 27 c0 18 ff 51 03 06 1a 80'), midi)
        self.assertIn(bytes.fromhex('00 ff 58 04 06 03 18 08'), midi)

    def test_odd_eighth_tempo_preserves_fractional_quarter_bpm(self):
        source = score_bytes(((0xea1c, 0xea23), (), ()), (0x2018, 0x1297, 0x2018))
        sequence = music.project(music.parse_bytes(source))
        tempo = sequence.conductor[1]
        self.assertEqual((tempo.tick, tempo.tempo_note_denominator, tempo.quarter_bpm), (24, 8, 75.5))
        self.assertIn(b'\x18\xff\x51\x03' + round(60_000_000 / 75.5).to_bytes(3, 'big'),
                      music.to_midi(sequence))

    def test_native_repeat_is_preserved_in_written_order(self):
        source = (FIXTURES / 'music/mloop.sng').read_bytes()
        sequence = music.project(music.parse_bytes(source))
        start, _, end = sequence.conductor
        self.assertEqual((start.kind, start.tick, start.repeat_count), ('repeat_start', 0, 2))
        self.assertEqual((end.kind, end.tick), ('repeat_end', 48))
        expanded = music.expand_playback(sequence)
        self.assertEqual(expanded.written_ticks, 96)
        notes = [item for item in expanded.voices[0] if item.kind == 'note']
        self.assertEqual([item.tick for item in notes], [0, 24, 48, 72])
        self.assertEqual([item.offset for item in notes[:2]], [item.offset for item in notes[2:]])
        self.assertEqual(sequence.written_ticks, 48)
        self.assertTrue(music.to_midi(sequence).startswith(b'MThd'))

    def test_native_tie_slur_and_key_signature(self):
        keys = ('m12', 'm13', 'm14')
        tie, slur, key = (music.project(music.parse_bytes((FIXTURES / f'music/{n}.sng').read_bytes()))
                          for n in keys)
        self.assertEqual([event.connection for event in tie.voices[0]], ['start', 'continue', 'end'])
        self.assertIn(bytes.fromhex('00 90 3c 40 48 80 3c 00 00 ff 2f 00'), music.to_midi(tie))
        self.assertIn(bytes.fromhex('00 90 3c 40 18 80 3c 00 00 90 43 40 18 80 43 00'), music.to_midi(slur))
        self.assertEqual(key.conductor[0].key_code, 9)
        self.assertEqual([(event.midi_pitch, event.accidental_flags) for event in key.voices[0]],
                         [(60, 0), (67, 0), (66, 0), (65, 0xc0)])

    def test_rejects_unpaired_note_connections(self):
        for word in (0xca1c, 0x8a1c, 0xaa1c):
            with self.subTest(word=word):
                score = score_bytes(((word,), (), ()), (0x2018,))
                with self.assertRaisesRegex(music.MusicFormatError, 'tie or slur'):
                    music.to_midi(music.project(music.parse_bytes(score)))

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


def playback_instrument(*, slot=9, payload=b'\x80\x84\x88\x8c\x90\x94', loop=(2, 4),
                        pitch=28, note_range=(1, 63), rate=11000):
    return sound.parse_bytes(pack('<4B10sH4B6I', 26, 0, 1, slot, b'Lab sample', rate,
                                  pitch, 0, *note_range, 44, 0, 0, len(payload), *loop) + payload)


class SampledMusicTests(unittest.TestCase):
    def test_loop_tail_and_octave_phase(self):
        score = music.parse_bytes(score_bytes(((0x7308, 0xea1c, 0xea28), (), ()), (0x2030,)))
        looped = sampled_music.render(score, [playback_instrument()], rate=11000)
        self.assertEqual((looped.bindings[0].slot, looped.bindings[0].sample_indices), (9, (0,)))
        self.assertEqual(unpack_from('<8h', looped.pcm), (0, 20, 40, 60, 40, 60, 40, 60))
        second = looped.notes[1]
        self.assertEqual((second.score_tick, second.midi_pitch), (24, 72))
        self.assertEqual(unpack_from('<5h', looped.pcm, second.start_frame * 2), (0, 40, 40, 40, 40))
        linear = sampled_music.render(score, [playback_instrument(loop=(0, 0))], rate=11000)
        self.assertEqual(unpack_from('<8h', linear.pcm), (0, 20, 40, 60, 80, 100, 0, 0))
        with wave.open(BytesIO(looped.wav()), 'rb') as wav:
            self.assertEqual((wav.getnchannels(), wav.getsampwidth(), wav.getframerate()), (1, 2, 11000))
            self.assertEqual(wav.readframes(wav.getnframes()), looped.pcm)

    def test_ties_tempo_dynamics_and_three_voice_mix(self):
        score = music.parse_bytes(score_bytes(((0xca1c, 0xaa1c), (0x7200, 0xe21c), (0x7205, 0xe21c)),
                                              (0x2018, 0x104b, 0x2048)))
        instruments = [playback_instrument(slot=slot, payload=bytes([140]), loop=(0, 1))
                       for slot in (1, 2, 3)]
        played = sampled_music.render(score, instruments)
        self.assertEqual(len(played.notes), 3)
        self.assertEqual(played.notes[0].written_end_tick, 48)
        self.assertEqual(played.notes[0].native_end_seconds,
                         18 * sampled_music.DAC_BLOCK_SECONDS)  # 11 and 7 native blocks
        self.assertEqual(unpack_from('<h', played.pcm)[0], 200)
        self.assertEqual(unpack_from('<h', played.pcm, played.notes[0].gate_frame * 2)[0], 140)

    def test_resolution_and_bounded_errors(self):
        score = music.parse_bytes(score_bytes(((0x7308, 0xea1c), (), ()), (0x2018,)))
        for instruments, matches in (
                ([], 'missing instrument slot 9'),
                ([playback_instrument(), playback_instrument(pitch=40)], 'conflicting Sound files'),
                ([playback_instrument(note_range=(29, 31))], 'no unambiguous sample range'),
                ([playback_instrument(pitch=255)], 'invalid root pitch'),
                ([playback_instrument(loop=(4, 8))], 'invalid sustain bounds')):
            with self.subTest(matches=matches), self.assertRaisesRegex(sampled_music.PlaybackError, matches):
                sampled_music.render(score, instruments, sample_policy='strict')
        with self.assertRaisesRegex(sampled_music.PlaybackError, 'output limit'):
            sampled_music.render(score, [playback_instrument()], max_frames=128)
        with self.assertRaisesRegex(sampled_music.PlaybackError, 'unsupported score word'):
            unsupported = music.parse_bytes(score_bytes(((0x8f00,), (), ()), (0x2018,)))
            sampled_music.render(unsupported, [])
        fallback = sampled_music.render(score, [playback_instrument(note_range=(29, 31))],
                                        sample_policy='nearest-root')
        self.assertEqual(fallback.notes[0].sample_index, 0)
        gap = sampled_music.render(score, [playback_instrument(note_range=(29, 31))])
        self.assertFalse(any(gap.pcm))
        self.assertEqual(gap.unmapped_pitches, (sampled_music.UnmappedPitch(9, 60, 1),))

    def test_rsx_inclusive_range_and_last_descriptor_precedence(self):
        encoded = bytearray(later_linked_sound())
        encoded[178:180] = bytes((28, 37))
        instrument = sound.parse_bytes(encoded)
        score = music.parse_bytes(score_bytes(((0x7310, 0xea1b, 0xea1c, 0xea25, 0xea26), (), ()), (0x2060,)))
        rendered = sampled_music.render(score, [instrument])
        self.assertEqual([note.sample_index for note in rendered.notes], [0, 1, 1])
        self.assertEqual(rendered.unmapped_pitches, (sampled_music.UnmappedPitch(17, 70, 1),))
        with self.assertRaisesRegex(sampled_music.PlaybackError, 'ambiguous sample ranges'):
            sampled_music.render(score, [instrument], sample_policy='strict')

    def test_replay_carries_tempo_instrument_and_dynamic_state(self):
        source = score_bytes(((0x7308, 0xea1c, 0xea20, 0x7309, 0x7201, 0xea23, 0xea25), (), ()),
                             (0x2018, 0x3003, 0x2018, 0x117d, 0x2018, 0x50ff, 0x2018))
        score = music.parse_bytes(source)
        played = sampled_music.render(score, [playback_instrument(), playback_instrument(slot=10)])
        self.assertEqual((played.written_ticks, played.playback_ticks), (96, 192))
        self.assertEqual([n.slot for n in played.notes], [9, 9, 10, 10, 10, 10, 10, 10])
        self.assertEqual([n.dynamic_index for n in played.notes], [None, None, 1, 1, 1, 1, 1, 1])
        self.assertEqual([b.start_frame - a.start_frame for a, b in zip(played.notes, played.notes[1:])],
                         [27358, 27358, 22384, 22384, 22383, 22384, 22384])

    def test_native_tempo_quantization_with_three_beat_units(self):
        voice = (0x7308, *([0xea1c] * 12))
        conductor = (0x114b, 0x2048, 0x1178, 0x2048, 0x104b, 0x2048, 0x1297, 0x2048)
        score = music.parse_bytes(score_bytes((voice, (), ()), conductor))
        playback = sampled_music.render(score, [playback_instrument()])
        intervals = [b.start_frame - a.start_frame for a, b in zip(playback.notes, playback.notes[1:])]
        native = [37306, 37306, 37307, 22384, 22383, 22384, 17410, 17410, 17409, 37307, 37306]
        self.assertTrue(all(abs(estimate - capture) <= 1 for estimate, capture in zip(intervals, native, strict=True)))

    def test_connected_rest_advances_time_and_pauses_sample_position(self):
        encoded = score_bytes(((0x7308, 0xca1c, 0x8a00, 0xaa1c), (), ()), (0x2048,))
        score = music.parse_bytes(encoded)
        pcm = bytes([128, 128, *([160] * 4000)])
        played = sampled_music.render(score, [playback_instrument(payload=pcm, loop=(2, 4002))])
        first, last = played.notes
        self.assertEqual(last.score_tick, 48)
        self.assertFalse(any(played.pcm[first.gate_frame * 2:last.start_frame * 2]))
        self.assertNotEqual(unpack_from('<h', played.pcm, last.start_frame * 2)[0], 0)
        self.assertIn(b'\x18\x80\x3c\x00\x18\x90\x3c\x40', music.to_midi(music.project(score)))

    def test_zero_pitch_starts_ends_and_triplet_rests(self):
        voice = (0x7308, 0xca00, 0xaa1c, 0xca20, 0xae00, 0xea23, 0xd600, 0xea25)
        score = music.parse_bytes(score_bytes((voice, (), ()), (0x2087,)))
        sequence = music.project(score)
        rests = [event for event in sequence.voices[0] if event.kind == 'rest']
        self.assertEqual([(e.duration_ticks, e.connection) for e in rests], [(24, 'start'), (12, 'end'), (3, 'start')])
        wav = sampled_music.render(score, [playback_instrument()])
        self.assertEqual([note.score_tick for note in wav.notes], [24, 48, 84, 111])
        self.assertFalse(any(wav.pcm[:wav.notes[0].start_frame * 2]))
        self.assertEqual(unpack_from('<h', wav.pcm, wav.notes[0].start_frame * 2)[0], 40)
        self.assertEqual(unpack_from('<h', wav.pcm, wav.notes[-1].start_frame * 2)[0], 0)

    def test_connected_instrument_and_dynamic_changes_keep_compatible_phase(self):
        voice = (0x7308, 0xca1c, 0x7200, 0x7309, 0x8a1c, 0x7205, 0xaa1c)
        score = music.parse_bytes(score_bytes((voice, (), ()), (0x2048,)))
        source = [playback_instrument(slot=slot, payload=bytes([128, 128, *([amplitude] * 4000)]),
                                      loop=(2, 4002)) for slot, amplitude in ((9, 140), (10, 152))]
        audio = sampled_music.render(score, source)
        self.assertEqual([(n.slot, n.dynamic_index) for n in audio.notes], [(9, None), (10, 0), (10, 5)])
        self.assertEqual([unpack_from('<h', audio.pcm, n.start_frame * 2)[0] for n in audio.notes], [0, 40, 240])

    def test_rsx_music_uses_same_step_for_three_declared_rates(self):
        score = music.parse_bytes(score_bytes(((0x7308, 0xea1c), (), ()), (0x2018,)))
        outputs = [sampled_music.render(score, [playback_instrument(rate=rate)]).pcm
                   for rate in (5500, 11000, 22000)]
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[1], outputs[2])

    def test_streaming_wav_keeps_phase_across_blocks_and_checks_budget_before_writing(self):
        voices = ((0x7308, 0xca1c, 0x7200, 0x8a23, 0xaa23), (),
                  (0x7309, 0xea20, 0xea1c, 0xea20))
        score = music.parse_bytes(score_bytes(voices, (0x2048,)))
        payload = bytes((i * 19) % 256 for i in range(201))
        source = [playback_instrument(slot=9, payload=payload, loop=(19, 67)),
                  playback_instrument(slot=10, payload=payload, loop=(0, 0))]
        expected = sampled_music.render(score, source, rate=8000)
        stream = BytesIO()
        with patch.object(sampled_music, 'BLOCK_FRAMES', 113):
            description = sampled_music.write_wav(score, source, stream, rate=8000)
        self.assertEqual(stream.getvalue(), expected.wav())
        self.assertEqual(description, expected.describe())
        stream = BytesIO()
        with self.assertRaisesRegex(sampled_music.PlaybackError, 'output limit'):
            sampled_music.write_wav(score, source, stream, rate=8000, max_frames=1024)
        self.assertEqual(stream.getvalue(), b'')

    def test_interleaved_model_uses_dac_midpoints_and_distinct_code_levels(self):
        score = music.parse_bytes(score_bytes(((0x7308, 0x7205, 0xea1c), (), ()), (0x2018,)))
        source = [playback_instrument(payload=bytes([0, 255, 128, 128]), loop=(0, 0))]
        stream = BytesIO()
        info = sampled_music.write_wav(score, source, stream, model=sampled_music.INTERLEAVED_MODEL)
        self.assertEqual(info['model'], 'rsx-dac-interleaved-v2')
        # 0 maps to DAC byte 85 and 255 to 170 at ff. The intervening byte
        # is floor((85 + 170) / 2) = 127; the initial midpoint is 106.
        self.assertEqual(unpack_from('<9h', stream.getvalue(), 44),
                         (-657, -657, -657, -1284, -1284, -29, -29, 1254, 1254))

    def test_repeat_boundaries_and_expansion_limits(self):
        for voice, conductor, error in (
                ((0xea1c,), (0x2018, 0x50ff), 'no start'),
                ((0xea1c,), (0x3002, 0x2018), 'unclosed'),
                ((), (0x3002, 0x50ff), 'empty repeat'),
                ((0xea1c,), (0x200c, 0x3002, 0x200c, 0x50ff), 'boundary crosses'),
                ((0xca1c, 0xaa1c), (0x3002, 0x2018, 0x50ff, 0x2018), 'boundary crosses'),
                ((0xea1c,) * 520, (0x30ff, 0x2fff, 0x2fff, 0x2fff, 0x20cf, 0x50ff), 'event limit')):
            with self.subTest(error=error), self.assertRaisesRegex(music.MusicFormatError, error):
                music.expand_playback(music.project(music.parse_bytes(score_bytes((voice, (), ()), conductor))))

    def test_0x80_accidental_preserves_pitch_and_flag_in_two_keys(self):
        voice = (0xea21, 0xea22, 0xeaa1, 0xeaa2, 0xeae1, 0xea61)
        for key in (0, 9):
            with self.subTest(key=key):
                source = score_bytes((voice, (), ()), (0x7000 + key, 0x2090))
                sequence = music.project(music.parse_bytes(source))
                self.assertEqual([event.midi_pitch for event in sequence.voices[0]], [65, 66, 65, 66, 65, 65])
                self.assertEqual([event.accidental_flags for event in sequence.voices[0]], [0, 0, 128, 128, 192, 64])
                music.to_midi(sequence)
        saved = music.parse_bytes((FIXTURES / 'music/accidentals-native.sng').read_bytes())
        events = music.project(saved).voices[0]
        self.assertEqual([event.midi_pitch for event in events], [65, 66, 65, 64])
        self.assertEqual([event.accidental_flags for event in events], [0, 64, 0, 128])

    def test_nested_repeats_and_numbered_endings(self):
        voice = (0xea1c, 0xea20, 0xea23, 0xea25)
        for conductor, pitches in (
                ((0x3002, 0x2018, 0x4001, 0x2018, 0x4002, 0x2018, 0x50ff, 0x2018),
                 [60, 64, 60, 67, 69]),
                ((0x3003, 0x2018, 0x4001, 0x2018, 0x4003, 0x2018, 0x50ff, 0x2018),
                 [60, 64, 60, 64, 60, 67, 69]),
                ((0x3002, 0x2018, 0x4001, 0x2018, 0x50ff, 0x2030),
                 [60, 64, 60, 67, 69]),
                ((0x3002, 0x2018, 0x3003, 0x2018, 0x50ff, 0x2018, 0x50ff, 0x2018),
                 [60, 64, 64, 64, 67, 60, 64, 64, 64, 67, 69])):
            with self.subTest(conductor=conductor):
                source = score_bytes((voice, (), ()), conductor)
                written = music.project(music.parse_bytes(source))
                playback = music.expand_playback(written)
                self.assertEqual([note.midi_pitch for note in playback.voices[0]], pitches)
                self.assertEqual([note.tick for note in playback.voices[0]], list(range(0, 24 * len(pitches), 24)))
                self.assertEqual(written.written_ticks, 96)
                midi = music.to_midi(written)
                self.assertEqual(midi.count(b'\x90'), len(pitches))

    def test_native_playback_accepted_alternate_ending_fixture(self):
        score = music.parse_bytes((FIXTURES / 'music/alternate-endings-tool-generated.sng').read_bytes())
        instrument = sound.parse_bytes((FIXTURES / 'sound/region-marked-tool-generated.snd').read_bytes())
        playback = sampled_music.render(score, [instrument])
        self.assertEqual([note.midi_pitch for note in playback.notes], [60, 64, 60, 67, 69])
        self.assertEqual((playback.written_ticks, playback.playback_ticks), (96, 120))

    def test_score_marker_retains_tick_letter_and_midi_annotation(self):
        source = score_bytes(((0xea1c, 0xea20), (), ()), (0x2018, 0x7441, 0x2018, 0x745a))
        sequence = music.project(music.parse_bytes(source))
        markers = [(e.tick, e.marker) for e in sequence.conductor if e.kind == 'score_marker']
        self.assertEqual(markers, [(24, 'A'), (48, 'Z')])
        self.assertIn(b'\x18\xff\x06\x01A\x18\xff\x06\x01Z', music.to_midi(sequence))
        saved = (FIXTURES / 'music/marker-a-native.sng').read_bytes()
        score = music.project(music.parse_bytes(saved))
        marker, advance = score.conductor
        self.assertEqual((marker.word, marker.marker, marker.tick), (0x7441, 'A', 0))
        self.assertEqual(advance.duration_ticks, 96)

    def test_render_committed_held_score_through_cli(self):
        score = FIXTURES / 'music/region-hold-tool-generated.sng'
        instrument = FIXTURES / 'sound/region-marked-tool-generated.snd'
        with tempfile.TemporaryDirectory() as folder, redirect_stdout(StringIO()) as stdout:
            folder = Path(folder)
            (folder / 'mark9.SND').write_bytes(instrument.read_bytes())
            destination = folder / 'render.wav'
            self.assertEqual(music.main([str(score), '--wav', str(destination), '--instruments', str(folder)]), 0)
            content = json.loads(stdout.getvalue())['sampled_playback']
            self.assertEqual(content['model'], sampled_music.MODEL)
            self.assertEqual(content['instruments'][0]['sha256'], sha256(instrument.read_bytes()).hexdigest())
            with wave.open(str(destination), 'rb') as wav:
                self.assertEqual(wav.getnframes(), 109432)
                self.assertTrue(any(wav.readframes(4800)))
            with redirect_stderr(StringIO()) as stderr:
                midi_path = folder / 'new.mid'
                self.assertEqual(music.main([str(score), '--midi', str(midi_path), '--wav',
                                             str(destination), '--instruments', str(folder)]), 2)
                self.assertIn('File exists', stderr.getvalue())
                self.assertFalse(midi_path.exists())

    def test_workbench_sampled_audio_and_missing_instrument(self):
        score = FIXTURES / 'music/region-hold-tool-generated.sng'
        instrument = FIXTURES / 'sound/region-marked-tool-generated.snd'
        with tempfile.TemporaryDirectory() as folder, redirect_stdout(StringIO()):
            folder = Path(folder)
            bank = folder / 'bank'
            bank.mkdir()
            (bank / 'mark.snd').write_bytes(instrument.read_bytes())
            bundle = folder / 'sampled'
            self.assertEqual(preserve_main(['export', str(score), '--output-dir', str(bundle),
                                            '--instruments', str(bank)]), 0)
            verified = verify(bundle)
            self.assertIn('sampled_playback_model', {d['code'] for d in verified['diagnostics']})
            self.assertEqual((bundle / 'original.sng').read_bytes(), score.read_bytes())
            self.assertTrue((bundle / 'composition.mid').is_file())
            with wave.open(str(bundle / 'assets/composition.wav'), 'rb') as wav:
                self.assertEqual(wav.getnframes(), 109432)
            preview = (bundle / 'preview.html').read_text(encoding='utf-8')
            self.assertIn('media-src', preview)
            self.assertIn('<audio controls', preview)
            metadata = json.loads((bundle / 'content.json').read_bytes())['sampled_playback']
            self.assertEqual(metadata['instruments'][0]['sample_indices'], [0])
            self.assertEqual(metadata['instruments'][0]['sha256'], sha256(instrument.read_bytes()).hexdigest())

            omitted = folder / 'omitted'
            manifest = export(score, omitted, instruments=())
            self.assertIn('sampled_playback_omitted', {d['code'] for d in manifest['diagnostics']})
            self.assertFalse((omitted / 'assets').exists())
            self.assertTrue((omitted / 'composition.mid').is_file())
            self.assertEqual(verify(omitted), manifest)


class NativeSoundTests(unittest.TestCase):
    def test_region_marked_playback_candidates(self):
        source = (FIXTURES / 'sound/region-marked-tool-generated.snd').read_bytes()
        sample = sound.parse_bytes(source)
        descriptor, = sample.samples
        self.assertEqual((sample.instrument_number, sample.sample_rate), (9, 11000))
        self.assertEqual((descriptor.pitch, descriptor.low_note, descriptor.high_note), (28, 25, 63))
        self.assertEqual((descriptor.sustain_start, descriptor.sustain_end), (1100, 2200))
        pcm = sample.pcm(0)
        self.assertEqual(len(pcm), 5500)
        for lo, hi, cycles in ((0, 1100, 50), (1100, 2200, 90), (2200, 5500, 420)):
            self.assertEqual(sum(pcm[i] <= 128 < pcm[i + 1] for i in range(lo, hi - 1)), cycles)

        source = (FIXTURES / 'music/region-hold-tool-generated.sng').read_bytes()
        sequence = music.project(music.parse_bytes(source))
        slot, held = sequence.voices[0]
        self.assertEqual((slot.instrument_slot, held.midi_pitch, held.duration_ticks), (9, 60, 96))
        self.assertEqual(sequence.written_ticks, 96)

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

    def test_native_codec_modes_match_native_uncompressed_resaves(self):
        directory = FIXTURES / 'sound'
        for mode in ('music', 'speech'):
            with self.subTest(mode=mode):
                encoded = sound.parse_bytes((directory / f'tone-native-{mode}.snd').read_bytes())
                native_pcm = sound.parse_bytes((directory / f'tone-{mode}-decoded-native.snd').read_bytes())
                self.assertEqual(encoded.samples[0].stored_length, 3001)
                self.assertEqual(unpack_from('>h', encoded.stored_sample(0), 26)[0], -256)
                self.assertEqual(encoded.pcm(0), native_pcm.pcm(0))
                self.assertEqual(len(encoded.pcm(0)), 5500)

    def test_native_empty_silence_odd_lengths_and_instrument_regions(self):
        directory = FIXTURES / 'sound'
        for name, rate, frames in (('empty', 11000, 0), ('recorded-silence', 11000, 1104),
                                   ('odd-5500', 5500, 555), ('pulses-22000', 22000, 511)):
            with self.subTest(name=name):
                document = sound.parse_bytes((directory / f'{name}-native.snd').read_bytes())
                with wave.open(BytesIO(document.wav(0)), 'rb') as reader:
                    self.assertEqual((reader.getframerate(), reader.getnframes()), (rate, frames))
                    self.assertEqual(reader.readframes(frames), document.stored_sample(0))
                if name == 'recorded-silence':
                    self.assertEqual(document.pcm(0), b'\x80' * 1104)

        instrument = sound.parse_bytes((directory / 'two-sample-native.snd').read_bytes())
        first, second = instrument.samples
        self.assertEqual(instrument.instrument_number, 8)
        self.assertEqual((first.pitch, first.low_note, first.high_note), (28, 25, 63))
        self.assertEqual((first.sustain_start, first.sustain_end), (1100, 2200))
        self.assertEqual((second.pitch, second.offset, second.sample_count), (40, 5706, 1100))
        self.assertEqual(instrument.pcm(1), instrument.pcm(0)[1100:2200])

    def test_original_profile_native_import_controls(self):
        directory = FIXTURES / 'sound'
        original = sound.parse_bytes((directory / 'tone-original-tool-generated.snd').read_bytes())
        other = (directory / 'original-unadjusted-resave.snd').read_bytes()
        self.assertEqual(other, (directory / 'original-tl-resave.snd').read_bytes())
        self.assertEqual(original.profile, 'sound-original-table')
        self.assertEqual(sound.parse_bytes(other).pcm(0), original.pcm(0))
