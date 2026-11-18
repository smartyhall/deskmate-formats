"""Read DeskMate Sound recordings and instrument sample descriptors."""

import argparse
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from struct import pack, unpack_from
import sys


MAX_BYTES = 1024 * 1024
MAX_SAMPLES = 16
LATER_SIGNATURE = b'\x1a\x80'
COMPRESSION = {0: 'uncompressed', 1: 'music', 2: 'speech'}


class SoundFormatError(ValueError):
    """The source lies outside the supported Sound container profiles."""


@dataclass(frozen=True)
class Sample:
    descriptor_offset: int
    descriptor: bytes
    pitch: int
    pitch_flag: int
    low_note: int
    high_note: int
    offset: int
    stored_length: int
    sample_count: int
    sustain_start: int | None
    sustain_end: int | None

    @property
    def midi_pitch(self):
        """Translate the documented A1-based pitch code to a MIDI note number."""
        return self.pitch + 32 if 1 <= self.pitch <= 63 else None


@dataclass(frozen=True)
class Sound:
    profile: str
    header: bytes
    name: str
    sample_rate: int
    instrument_number: int
    compression: int
    samples: tuple[Sample, ...]
    unassigned_regions: tuple[tuple[int, int], ...]
    source: bytes = field(repr=False)

    @property
    def kind(self):
        return 'instrument' if self.instrument_number else 'recording'

    def stored_sample(self, index):
        sample = self.samples[index]
        return self.source[sample.offset:sample.offset + sample.stored_length]

    def pcm(self, index):
        """Return exact unsigned mono PCM bytes for a supported sample."""
        stored = self.stored_sample(index)
        if not self.compression:
            return stored
        return _decode_pcm(stored, self.samples[index].sample_count)

    def wav(self, index):
        """Wrap the recovered PCM in a standard, word-aligned RIFF WAVE."""
        pcm = self.pcm(index)
        padding = b'\0' if len(pcm) % 2 else b''
        return (pack('<4sI4s4sIHHIIHH4sI', b'RIFF', 36 + len(pcm) + len(padding), b'WAVE',
                     b'fmt ', 16, 1, 1, self.sample_rate, self.sample_rate, 1, 8, b'data', len(pcm))
                + pcm + padding)


def _old(data, count, compression):
    header_end = 16 + 28 * count
    if len(data) < header_end:
        raise SoundFormatError('truncated original descriptor table')
    for position in range(16, header_end, 28):
        pitch, flag, low, high, offset, size, _, frames, start, end = unpack_from('<4B6I', data, position)
        if compression == 0 and size:
            raise SoundFormatError('nonzero compressed length in original PCM descriptor')
        length = size if compression else frames
        yield Sample(position, data[position:position + 28], pitch, flag, low, high, offset, length, frames,
                     start, end)


def _later(data, count, compression):
    position = 114
    visited = set()
    for index in range(count):
        if not 114 <= position <= len(data) - 46 or position in visited:
            raise SoundFormatError('invalid later descriptor link')
        visited.add(position)
        link = unpack_from('<I', data, position)[0]
        pitch, flag, low, high, offset, length, frames, start, end = unpack_from('<4B5I', data, position + 6)
        if (link == 0) != (index == count - 1):
            raise SoundFormatError('later descriptor link disagrees with sample count')
        if compression == 0 and length != frames:
            raise SoundFormatError('later PCM length disagrees with sample count')
        yield Sample(position, data[position:position + 46], pitch, flag, low, high, offset, length, frames,
                     start, end)
        position = link


def _decode_pcm(data, count):
    """Decode a DeskMate delta stream up to the descriptor's exact sample count."""
    if len(data) < 30:
        raise SoundFormatError('truncated compression table')
    *deltas, silence_base = unpack_from('>14hH', data)
    nibbles = iter(value for byte in memoryview(data)[30:] for value in (byte >> 4, byte & 15))
    pcm = bytearray()
    sample = 128
    try:
        while len(pcm) < count:
            code = next(nibbles)
            if code < 14:
                # The native predictor adds a signed 16-bit word before clipping.
                value = ((sample + deltas[code] + 32768) & 0xffff) - 32768
                sample = min(255, max(0, value))
                pcm.append(sample)
            elif code == 14:
                sample = next(nibbles) * 16 + next(nibbles)
                pcm.append(sample)
            else:
                mode = next(nibbles)
                if mode < 14:
                    length = mode + 1
                else:
                    length = next(nibbles) * 16 + next(nibbles)
                    if mode == 14:
                        sample = 128
                        length = (length + silence_base + 1) & 0xffff
                    else:
                        length += 14
                pcm.extend(bytes([sample]) * min(length, count - len(pcm)))
    except StopIteration as exc:
        raise SoundFormatError('compressed sample ended before its declared sample count') from exc
    return bytes(pcm)


def _parse_profile(data, later):
    if later:
        if len(data) < 114:
            raise SoundFormatError('truncated later Sound header')
        profile, header_end, records = 'sound-later-linked', 114, _later
        count, number = unpack_from('<HH', data, 46)
        compression = unpack_from('<H', data, 66)[0]
        rate = unpack_from('<H', data, 88)[0]
        name = data[:10]
    else:
        profile, header_end, records = 'sound-original-table', 16, _old
        compression, count, number = data[1:4]
        rate = unpack_from('<H', data, 14)[0]
        name = data[4:14]

    if compression not in COMPRESSION or not 1 <= count <= MAX_SAMPLES or rate == 0:
        raise SoundFormatError('unsupported compression, sample count or rate')
    if (number == 0 and count != 1) or not (0 <= number <= 32 or number == 255):
        raise SoundFormatError('unsupported recording/instrument number or count')

    samples = tuple(records(data, count, compression))
    regions = [(0, header_end)]
    for sample in samples:
        offset, length, frames = sample.offset, sample.stored_length, sample.sample_count
        if (not header_end <= offset <= len(data) or length > len(data) - offset
                or frames > MAX_BYTES or bool(length) != bool(frames)):
            raise SoundFormatError(f'invalid sample bounds at descriptor {sample.descriptor_offset}')
        regions.append((sample.descriptor_offset, sample.descriptor_offset + len(sample.descriptor)))
        if length:
            regions.append((offset, offset + length))
    gaps = []
    end = 0
    for start, stop in sorted(regions):
        if start < end:
            raise SoundFormatError('overlapping Sound header, descriptor or payload regions')
        if start > end:
            gaps.append((end, start))
        end = stop
    if end < len(data):
        gaps.append((end, len(data)))
    return Sound(profile, data[:header_end], name.split(b'\0', 1)[0].decode('cp437'),
                 rate, number, compression, samples, tuple(gaps), data)


def parse_bytes(source):
    """Validate descriptor ownership and payload bounds before exposing source regions."""
    if not isinstance(source, (bytes, bytearray, memoryview)) or not 16 <= memoryview(source).nbytes <= MAX_BYTES:
        raise SoundFormatError('invalid Sound file size')
    data = bytes(source)
    original = data[0] == 0x1a
    later = data[44:46] == LATER_SIGNATURE
    if not (original or later):
        raise SoundFormatError('unrecognized Sound signature')
    if not (original and later):
        return _parse_profile(data, later)

    # A recording can happen to contain the later marker at its first PCM byte.
    matches = []
    details = []
    for candidate in (False, True):
        try:
            matches.append(_parse_profile(data, candidate))
        except SoundFormatError as exc:
            details.append(str(exc))
    if len(matches) == 1:
        return matches[0]
    if matches:
        raise SoundFormatError('ambiguous original and later Sound profiles')
    raise SoundFormatError('invalid overlapping Sound signatures: ' + ' | '.join(details))


def describe(sound):
    """Describe metadata and exact source-region identities for JSON inspection."""
    return {
        'profile': sound.profile,
        'header_hex': sound.header.hex(),
        'name': sound.name,
        'kind': sound.kind,
        'instrument_number': sound.instrument_number,
        'compression_code': sound.compression,
        'compression': COMPRESSION[sound.compression],
        'sample_rate': sound.sample_rate,
        'descriptor_count': len(sound.samples),
        'channels': 1,
        'pcm_encoding': 'unsigned 8-bit',
        'samples': [
            {**asdict(sample), 'descriptor': sample.descriptor.hex(), 'midi_pitch': sample.midi_pitch,
             'stored_sha256': sha256(sound.stored_sample(index)).hexdigest()}
            for index, sample in enumerate(sound.samples)
        ],
        'unassigned_regions': sound.unassigned_regions,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--sample', type=int, default=1, help='one-based sample for PCM or WAV output')
    output = parser.add_mutually_exclusive_group()
    output.add_argument('--wav', type=Path, help='write the selected sample to a new WAV file')
    output.add_argument('--pcm', type=Path, help='write decoded unsigned 8-bit mono samples to a new file')
    args = parser.parse_args(argv)
    try:
        with args.source.open('rb') as stream:
            sound = parse_bytes(stream.read(MAX_BYTES + 1))
        if args.wav or args.pcm:
            if not 1 <= args.sample <= len(sound.samples):
                raise SoundFormatError('sample number is outside the file')
            data = sound.wav(args.sample - 1) if args.wav else sound.pcm(args.sample - 1)
            with (args.wav or args.pcm).open('xb') as stream:
                stream.write(data)
        print(json.dumps(describe(sound), indent=2))
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
