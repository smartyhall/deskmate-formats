"""Generate the original v1 listening scores and synthetic Sound instruments."""

import argparse
from math import exp, sin, tau
from pathlib import Path
from struct import pack_into

from deskmate_formats import music, sound
from sampled_music_probe import score_probe


CASES = ('major-scale', 'minor-scale', 'chromatic-scale', 'major-cadence', 'minor-cadence')
BANK_SLOTS = {
    'synthetic': ((9,), (10,), (11,), (9, 9, 9), (9, 10, 11)),
    'oem': ((1,), (2,), (3,), (2, 2, 2), (4, 1, 3)),
}
# Each component is (frequency multiplier, amplitude, exponential decay time
# in seconds). Zero decay describes an attack into a steady periodic waveform.
TIMBRES = {
    'REED': (9, 0.023, ((1, 39, 0), (3, 17, 0), (5, 6, 0), (7, 3, 0))),
    'PLUCK': (10, 0.005, ((1, 53, 0.23), (2, 28, 0.13), (3, 16, 0.09), (5, 8, 0.05))),
    'BELL': (11, 0.009, ((1, 45, 0.44), (2.41, 22, 0.14), (3.67, 14, 0.085))),
}
RATE = 11000
PERIOD = 42
ROOT_MIDI = 60
NOTE_COUNT = 5500
REED_LOOP = (1260, 3360)
DURATION_CODES = {6: 0x12, 12: 0x0e, 24: 0x0a, 48: 0x06, 72: 0x04}


def instrument(template, name):
    source = sound.parse_bytes(template)
    sample, = source.samples
    if (source.profile, source.sample_rate, source.compression, sample.sample_count, sample.midi_pitch) != (
        'sound-later-linked', RATE, 0, NOTE_COUNT, ROOT_MIDI
    ):
        raise ValueError('expected the uncompressed LABINST fixture')
    slot, attack, components = TIMBRES[name]
    loop = REED_LOOP if name == 'REED' else (0, 0)
    data = bytearray(template)
    data[:44] = f'Lab {name.title()}'.encode('ascii').ljust(44, b'\0')
    pack_into('<H', data, 48, slot)
    pack_into('<II', data, sample.descriptor_offset + 22, *loop)
    pcm = bytearray()
    for frame in range(NOTE_COUNT):
        seconds = frame / RATE
        attack_gain = min(1, seconds / attack)
        tail_gain = min(1, (NOTE_COUNT - 1 - frame) / (RATE * 0.035))
        position = frame % PERIOD if name == 'REED' else frame
        signal = sum(amplitude * sin(tau * multiple * position / PERIOD)
                     * (exp(-seconds / decay) if decay else 1)
                     for multiple, amplitude, decay in components)
        pcm.append(128 + round(signal * attack_gain * tail_gain))
    data[sample.offset:sample.offset + NOTE_COUNT] = pcm
    sound.parse_bytes(data)
    return bytes(data)


def note(pitch, ticks, *, connection=0x60, accidental=0):
    return ((0x80 | connection | DURATION_CODES[ticks]) << 8) | (
        (pitch - 32 if pitch else 0) | accidental
    )


def scale(pitches, ticks, sharp_pitches):
    ascending_and_descending = (*pitches, *pitches[-2::-1])
    notes = [note(pitch, ticks, accidental=0x40 if pitch in sharp_pitches else 0)
             for pitch in ascending_and_descending]
    return [0x7202, *notes[:-1], 0x7203, note(pitches[0], 48), note(0, 24)]


def cadence(voices, expressive):
    streams = []
    for low, middle, dominant, final in voices:
        opening = [note(low, 48), note(middle, 48), note(dominant, 48)]
        if expressive:
            opening = [note(low, 48), 0x7201, note(middle, 48), 0x7203,
                       note(dominant, 48, accidental=0x40 if dominant == 68 else 0)]
            ending = [0x7202, note(final, 48, connection=0x40),
                      0x7201, note(final, 24, connection=0x20)]
        else:
            ending = [note(final, 72)]
        streams.append([0x7202, *opening, *ending, note(0, 24)])
    return streams


def score_inputs(template):
    cases = (
        ([scale((60, 62, 64, 65, 67, 69, 71, 72), 24, ())], 14 * 24 + 72),
        ([scale((57, 59, 60, 62, 64, 65, 68, 69), 24, (68,))], 14 * 24 + 72),
        ([scale(tuple(range(60, 73)), 12, (61, 63, 66, 68, 70))], 24 * 12 + 72),
        (cadence(((60, 60, 59, 60), (64, 65, 62, 64), (67, 69, 67, 67)), False), 240),
        (cadence(((57, 57, 59, 57), (60, 62, 64, 60), (64, 65, 68, 69)), True), 240),
    )
    for bank, assignments in BANK_SLOTS.items():
        for index, (case, (voices, ticks), slots) in enumerate(zip(CASES, cases, assignments, strict=True), 1):
            streams = [[0x7300 + slot - 1, *words] for slot, words in zip(slots, voices, strict=True)]
            streams.extend([[] for _ in range(3 - len(streams))])
            case_id = f'oem-{case}' if bank == 'oem' else case
            filename = f'{"OEM" if bank == "oem" else "LAB"}{index}.SNG'
            data = score_probe(template, streams, (0x1164, 0x2000 + ticks))
            music.expand_playback(music.project(music.parse_bytes(data)))
            yield case_id, filename, data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('score_template', type=Path)
    parser.add_argument('instrument_template', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    score_template = args.score_template.read_bytes()
    instrument_template = args.instrument_template.read_bytes()
    args.destination.mkdir()
    for _, filename, data in score_inputs(score_template):
        (args.destination / filename).write_bytes(data)
    for name in TIMBRES:
        (args.destination / f'{name}.SND').write_bytes(instrument(instrument_template, name))


if __name__ == '__main__':
    main()
