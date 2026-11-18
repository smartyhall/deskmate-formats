"""Read DeskMate Music scores and preserve their serialized event streams."""

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from struct import pack, unpack_from
import sys


SIGNATURE = b'\x0cSNG'
MAX_BYTES = 22 + 65_535 + 1
VOICE_COUNT = 3
STREAM_START = 0x7ffe
STREAM_END = 0x7fff
TICKS_PER_QUARTER = 24
DEFAULT_QUARTER_BPM = 100
# Positive tick counts in the OEM duration lookup. Three signed entries
# need their own rounding/notation study before projection.
NOTE_TICKS = {
    0xe0: 168, 0xe1: 144, 0xe2: 96, 0xe3: 84, 0xe4: 72, 0xe5: 64,
    0xe6: 48, 0xe7: 42, 0xe8: 36, 0xe9: 32, 0xea: 24, 0xeb: 21,
    0xec: 18, 0xed: 16, 0xee: 12, 0xf0: 9, 0xf1: 8, 0xf2: 6,
    0xf5: 4, 0xf6: 3, 0xf7: 2,
}


class MusicFormatError(ValueError):
    """The source lies outside the supported Music profile."""


@dataclass(frozen=True)
class Instruction:
    offset: int
    word: int


@dataclass(frozen=True)
class Score:
    header: bytes
    title: str
    author: str
    text_padding: bytes
    voices: tuple[tuple[Instruction, ...], ...]
    conductor: tuple[Instruction, ...]
    trailer: bytes


@dataclass(frozen=True)
class Event:
    offset: int
    word: int
    kind: str
    tick: int | None
    duration_ticks: int | None = None
    midi_pitch: int | None = None
    quarter_bpm: int | None = None
    instrument_slot: int | None = None
    dynamic_index: int | None = None
    bar_number: int | None = None


@dataclass(frozen=True)
class Sequence:
    voices: tuple[tuple[Event, ...], ...]
    conductor: tuple[Event, ...]
    written_ticks: int
    voice_ticks: tuple[int | None, ...]

    @property
    def opaque(self):
        return tuple(event for stream in (*self.voices, self.conductor) for event in stream
                     if event.kind == 'opaque')


def _stream(data, offset, end):
    if offset + 4 > end or unpack_from('<H', data, offset)[0] != STREAM_START:
        raise MusicFormatError(f'missing stream start at offset {offset}')
    offset += 2
    instructions = []
    while offset + 2 <= end:
        word = unpack_from('<H', data, offset)[0]
        if word == STREAM_END:
            return tuple(instructions), offset + 2
        if word == STREAM_START:
            raise MusicFormatError(f'nested stream start at offset {offset}')
        instructions.append(Instruction(offset, word))
        offset += 2
    raise MusicFormatError('missing stream end within declared score extent')


def parse_bytes(source):
    """Split the bounded SNG container into three voice streams and a conductor."""
    if not isinstance(source, (bytes, bytearray, memoryview)) or not 42 <= memoryview(source).nbytes <= MAX_BYTES:
        raise MusicFormatError('invalid Music file size')
    data = bytes(source)
    if data[:4] != SIGNATURE:
        raise MusicFormatError('unrecognized Music signature')
    end = 22 + unpack_from('<H', data, 22)[0]
    if end % 2 or not 42 <= end <= len(data) or len(data) - end > 1:
        raise MusicFormatError('invalid declared Music extent')

    title_end = data.find(b'\0', 24, end - 16)
    if title_end == -1:
        raise MusicFormatError('unterminated Music title')
    author_end = data.find(b'\0', title_end + 1, end - 16)
    if author_end == -1:
        raise MusicFormatError('unterminated Music author')
    text_end = author_end + 1
    offset = text_end + text_end % 2
    streams = []
    for _ in range(VOICE_COUNT + 1):
        events, offset = _stream(data, offset, end)
        streams.append(events)
    if offset != end:
        raise MusicFormatError('data after the fourth Music stream')
    return Score(data[:24], data[24:title_end].decode('cp437'), data[title_end + 1:author_end].decode('cp437'),
                 data[text_end:text_end + text_end % 2], tuple(streams[:VOICE_COUNT]), streams[-1], data[end:])


def project(score):
    """Translate measured events and retain every unrecognized word and offset."""
    voices = []
    voice_ticks = []
    for stream in score.voices:
        events = []
        tick = 0
        for item in stream:
            code, value = item.word >> 8, item.word & 0xff
            if code == 0x73 and value < 32:
                events.append(Event(item.offset, item.word, 'instrument', tick, instrument_slot=value + 1))
            elif code == 0x72 and value < 6:
                events.append(Event(item.offset, item.word, 'dynamic', tick, dynamic_index=value))
            elif code in NOTE_TICKS and value < 128 and value != 64:
                duration = NOTE_TICKS[code]
                pitch = value & 0x3f
                kind = 'note' if pitch else 'rest'
                midi_pitch = 32 + pitch if pitch else None
                events.append(Event(item.offset, item.word, kind, tick, duration, midi_pitch))
                if tick is not None:
                    tick += duration
            else:
                events.append(Event(item.offset, item.word, 'opaque', tick))
                tick = None
        voices.append(tuple(events))
        voice_ticks.append(tick)

    conductor = []
    tick = 0
    for item in score.conductor:
        if item.word & 0xf000 == 0x2000:
            duration = item.word & 0xfff
            conductor.append(Event(item.offset, item.word, 'advance', tick, duration))
            tick += duration
        elif item.word >> 8 == 0x11 and item.word & 0xff:
            conductor.append(Event(item.offset, item.word, 'tempo', tick, quarter_bpm=item.word & 0xff))
        elif item.word >> 8 == 0x71:
            conductor.append(Event(item.offset, item.word, 'barline', tick, bar_number=(item.word & 0xff) + 1))
        else:
            conductor.append(Event(item.offset, item.word, 'opaque', tick))
    return Sequence(tuple(voices), tuple(conductor), tick, tuple(voice_ticks))


def describe(score, sequence=None):
    """Return an ordered JSON representation with source offsets."""
    if sequence is None:
        sequence = project(score)
    return {
        'profile': 'music-0c-sng-four-stream',
        'header_hex': score.header.hex(),
        'title': score.title,
        'author': score.author,
        'text_padding_hex': score.text_padding.hex(),
        'trailer_hex': score.trailer.hex(),
        'ticks_per_quarter': TICKS_PER_QUARTER,
        'default_quarter_bpm': DEFAULT_QUARTER_BPM,
        **asdict(sequence),
    }


def _variable(value):
    if not 0 <= value <= 0x0fffffff:
        raise MusicFormatError('MIDI delta is outside the four-byte limit')
    groups = [value & 0x7f]
    value >>= 7
    while value:
        groups.append(0x80 | (value & 0x7f))
        value >>= 7
    return bytes(reversed(groups))


def _midi_track(events, end):
    payload = bytearray()
    last = 0
    for tick, message in events:
        payload.extend(_variable(tick - last))
        payload.extend(message)
        last = tick
    payload.extend(_variable(end - last))
    payload.extend(b'\xff\x2f\x00')
    return pack('>4sI', b'MTrk', len(payload)) + payload


def _midi_tempo(bpm):
    micros = (60_000_000 + bpm // 2) // bpm
    return b'\xff\x51\x03' + micros.to_bytes(3, 'big')


def to_midi(sequence):
    """Project a fully interpreted linear score to Standard MIDI File type 1."""
    opaque = sequence.opaque
    if opaque:
        first = opaque[0]
        raise MusicFormatError(f'{len(opaque)} unsupported score word(s), first {first.word:04x} at {first.offset}')
    if any(tick > sequence.written_ticks for tick in sequence.voice_ticks):
        raise MusicFormatError('voice duration exceeds the conductor timeline')
    tempos = [(0, _midi_tempo(DEFAULT_QUARTER_BPM))]
    for event in sequence.conductor:
        if event.kind == 'tempo':
            if event.quarter_bpm < 4:
                raise MusicFormatError('tempo is outside the Standard MIDI File representation')
            entry = (event.tick, _midi_tempo(event.quarter_bpm))
            if tempos[-1][0] == event.tick:
                tempos[-1] = entry
            else:
                tempos.append(entry)
    tracks = [_midi_track(tempos, sequence.written_ticks)]
    for channel, voice in enumerate(sequence.voices):
        messages = []
        for event in voice:
            if event.kind == 'note':
                messages.append((event.tick, bytes((0x90 | channel, event.midi_pitch, 64))))
                messages.append((event.tick + event.duration_ticks, bytes((0x80 | channel, event.midi_pitch, 0))))
        tracks.append(_midi_track(messages, sequence.written_ticks))
    return pack('>4sIHHH', b'MThd', 6, 1, len(tracks), TICKS_PER_QUARTER) + b''.join(tracks)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--midi', type=Path, help='write a fully interpreted linear score to a new MIDI file')
    args = parser.parse_args(argv)
    try:
        with args.source.open('rb') as stream:
            score = parse_bytes(stream.read(MAX_BYTES + 1))
        sequence = project(score)
        if args.midi:
            midi = to_midi(sequence)
            with args.midi.open('xb') as stream:
                stream.write(midi)
        print(json.dumps(describe(score, sequence), indent=2))
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
