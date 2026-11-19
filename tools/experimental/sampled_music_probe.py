"""Generate the region-marked Sound controls and paired Music scores."""

import argparse
from math import sin, tau
from pathlib import Path
from struct import pack, pack_into

from deskmate_formats import music, sound


REGIONS = ((0, 1100, 500), (1100, 2200, 900), (2200, 5500, 1400))
SCORES = {
    'MARKLONG.SNG': ((0x7308, 0xe21c), 96),
    'MARKFAST.SNG': ((0x7308, 0xf21c, 0xee1c, 0xea1c), 42),
    'MARKHI.SNG': ((0x7308, 0xe228), 96),
    'SHIFT.SNG': ((0x7309, 0xe21c), 96),
    'NOLOOP.SNG': ((0x730a, 0xe21c), 96),
}
ALTERNATE_VOICE = (0x7308, 0xea1c, 0xea20, 0xea23, 0xea25)
ALTERNATE_CONDUCTOR = (0x3002, 0x2018, 0x4001, 0x2018, 0x4002, 0x2018, 0x50ff, 0x2018)


def score_probe(source, voices, conductor):
    """Replace the streams of an explicitly supplied synthetic score."""
    score = music.parse_bytes(source)
    streams = (*score.voices, score.conductor)
    first = len(source) - len(score.trailer) - sum(4 + 2 * len(stream) for stream in streams)
    encoded = bytearray(source[:first])
    for stream in (*voices, conductor):
        words = (music.STREAM_START, *stream, music.STREAM_END)
        encoded.extend(pack(f'<{len(words)}H', *words))
    pack_into('<H', encoded, 22, len(encoded) - 22)
    encoded.extend(score.trailer)
    music.parse_bytes(encoded)
    return bytes(encoded)


def region_instrument(source, number, loop):
    instrument = sound.parse_bytes(source)
    sample, = instrument.samples
    if (instrument.profile != 'sound-later-linked' or instrument.compression
            or instrument.sample_rate != 11000 or sample.sample_count != 5500
            or sample.pitch != 28):
        raise ValueError('expected the uncompressed LABINST control')
    encoded = bytearray(source)
    pack_into('<H', encoded, 48, number)
    pack_into('<II', encoded, sample.descriptor_offset + 22, *loop)
    for start, end, frequency in REGIONS:
        encoded[sample.offset + start:sample.offset + end] = bytes(
            128 + round(48 * sin(tau * frequency * frame / instrument.sample_rate))
            for frame in range(end - start))
    sound.parse_bytes(encoded)
    return bytes(encoded)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('score', type=Path)
    parser.add_argument('instrument', type=Path)
    parser.add_argument('output', type=Path, help='new directory for generated controls')
    parser.add_argument('--alternate-ending', action='store_true',
                        help='generate the validated alternate-ending score and slot 9 instrument')
    args = parser.parse_args(argv)
    with args.score.open('rb') as stream:
        score = stream.read(music.MAX_BYTES + 1)
    with args.instrument.open('rb') as stream:
        source = stream.read(sound.MAX_BYTES + 1)
    files = {'MARK9.SND': region_instrument(source, 9, (1100, 2200))}
    if args.alternate_ending:
        files['ALTGOOD.SNG'] = score_probe(score, (ALTERNATE_VOICE, (), ()), ALTERNATE_CONDUCTOR)
    else:
        files.update({name: score_probe(score, (voice, (), ()), (0x2000 + ticks,))
                      for name, (voice, ticks) in SCORES.items()})
        files['SHIFT10.SND'] = region_instrument(source, 10, (1100, 1980))
        files['NOLOOP11.SND'] = region_instrument(source, 11, (0, 0))
    args.output.mkdir()
    for name, payload in files.items():
        (args.output / name).write_bytes(payload)


if __name__ == '__main__':
    main()
