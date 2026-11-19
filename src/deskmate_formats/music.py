"""Read DeskMate Music scores and preserve their serialized event streams."""

import argparse
from bisect import bisect_left, bisect_right
from dataclasses import asdict, dataclass, replace
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
MAX_PLAYBACK_EVENTS = 131_072
MAX_REPEAT_DEPTH = 8
# Positive tick counts in the OEM duration lookup. Three signed entries
# need their own rounding/notation study before projection.
NOTE_TICKS = {
    0xe0: 168, 0xe1: 144, 0xe2: 96, 0xe3: 84, 0xe4: 72, 0xe5: 64,
    0xe6: 48, 0xe7: 42, 0xe8: 36, 0xe9: 32, 0xea: 24, 0xeb: 21,
    0xec: 18, 0xed: 16, 0xee: 12, 0xf0: 9, 0xf1: 8, 0xf2: 6,
    0xf5: 4, 0xf6: 3, 0xf7: 2,
}
NOTE_CONNECTION = {0x00: 'continue', 0x20: 'end', 0x40: 'start', 0x60: None}
TEMPO_DENOMINATORS = {0x10: 2, 0x11: 4, 0x12: 8}
METER_DENOMINATORS = (2, 4, 8, 16, 32)


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
    quarter_bpm: int | float | None = None
    instrument_slot: int | None = None
    dynamic_index: int | None = None
    bar_number: int | None = None
    connection: str | None = None
    accidental_flags: int | None = None
    tempo_bpm: int | None = None
    tempo_note_denominator: int | None = None
    meter_numerator: int | None = None
    meter_denominator: int | None = None
    key_code: int | None = None
    repeat_count: int | None = None
    ending_number: int | None = None
    marker: str | None = None


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
            duration_code = code | 0x60
            pitch, accidental = value & 0x3f, value & 0xc0
            connection = NOTE_CONNECTION[code & 0x60]
            if code == 0x73 and value < 32:
                events.append(Event(item.offset, item.word, 'instrument', tick, instrument_slot=value + 1))
            elif code == 0x72 and value < 6:
                events.append(Event(item.offset, item.word, 'dynamic', tick, dynamic_index=value))
            elif duration_code in NOTE_TICKS and (pitch or not value):
                duration = NOTE_TICKS[duration_code]
                kind = 'note' if pitch else 'rest'
                midi_pitch = 32 + pitch if pitch else None
                events.append(Event(item.offset, item.word, kind, tick, duration, midi_pitch,
                                    connection=connection, accidental_flags=accidental if pitch else None))
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
        code, value = item.word >> 8, item.word & 0xff
        family = item.word & 0xf000
        numerator, denominator = (item.word >> 6) & 0x3f, item.word & 0x3f
        if family == 0x2000:
            duration = item.word & 0xfff
            conductor.append(Event(item.offset, item.word, 'advance', tick, duration))
            tick += duration
        elif code in TEMPO_DENOMINATORS and value:
            beat = TEMPO_DENOMINATORS[code]
            whole, remainder = divmod(value * 4, beat)
            quarter_bpm = whole + remainder / beat if remainder else whole
            conductor.append(Event(item.offset, item.word, 'tempo', tick, quarter_bpm=quarter_bpm,
                                   tempo_bpm=value, tempo_note_denominator=beat))
        elif family == 0x6000 and 2 <= numerator <= 32 and denominator in METER_DENOMINATORS:
            conductor.append(Event(item.offset, item.word, 'meter', tick,
                                   meter_numerator=numerator, meter_denominator=denominator))
        elif code == 0x70 and value < 32:
            conductor.append(Event(item.offset, item.word, 'key', tick, key_code=value))
        elif code == 0x71:
            conductor.append(Event(item.offset, item.word, 'barline', tick, bar_number=value + 1))
        elif code == 0x30 and value >= 2:
            conductor.append(Event(item.offset, item.word, 'repeat_start', tick, repeat_count=value))
        elif code == 0x40 and 1 <= value <= 10:
            conductor.append(Event(item.offset, item.word, 'alternate_ending', tick, ending_number=value))
        elif item.word == 0x50ff:
            conductor.append(Event(item.offset, item.word, 'repeat_end', tick))
        elif code == 0x74 and 0x41 <= value <= 0x5a:
            conductor.append(Event(item.offset, item.word, 'score_marker', tick, marker=chr(value)))
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
    micros = round(60_000_000 / bpm)
    return b'\xff\x51\x03' + micros.to_bytes(3, 'big')


def _connected_notes(voice, *, split_controls=False):
    """Yield the first and last written event of each sounding pitch."""
    first = last = None
    open_connection = None
    for event in voice:
        if event.kind == 'rest' and event.connection is not None:
            if first is not None:
                yield first, last
                first = last = None
            if event.connection == 'start':
                open_connection = 'rest'
            elif event.connection == 'end':
                open_connection = None
            continue
        if event.kind in ('dynamic', 'instrument'):
            if split_controls and first is not None:
                yield first, last
                first = last = None
            continue
        if event.kind != 'note':
            if open_connection == 'note':
                raise MusicFormatError(f'interrupted tie or slur at {event.offset}')
            open_connection = None
            continue
        if event.connection in ('continue', 'end'):
            if open_connection is None:
                raise MusicFormatError(f'tie or slur has no start at {event.offset}')
            if first is not None and first.midi_pitch != event.midi_pitch:
                yield first, last
                first = None
            if first is None:
                first = event
        elif open_connection == 'note':
            raise MusicFormatError(f'tie or slur has no end before {event.offset}')
        else:
            first = event
        last = event
        open_connection = 'note' if event.connection in ('start', 'continue') else None
        if open_connection is None:
            yield first, last
            first = last = None
    if open_connection == 'note':
        raise MusicFormatError('tie or slur ends outside the voice stream')


def _midi_notes(voice):
    for first, last in _connected_notes(voice):
        yield first.tick, last.tick + last.duration_ticks, first.midi_pitch


def _require_interpreted(sequence):
    opaque = sequence.opaque
    if opaque:
        first = opaque[0]
        raise MusicFormatError(f'{len(opaque)} unsupported score word(s), first {first.word:04x} at {first.offset}')
    if any(tick > sequence.written_ticks for tick in sequence.voice_ticks):
        raise MusicFormatError('voice duration exceeds the conductor timeline')


def _repeat_sections(conductor):
    sections = {}
    stack = []
    for index, event in enumerate(conductor):
        if event.kind == 'repeat_start':
            if len(stack) >= MAX_REPEAT_DEPTH:
                raise MusicFormatError(f'repeat depth exceeds {MAX_REPEAT_DEPTH} at {event.offset}')
            stack.append((index, []))
        elif event.kind == 'alternate_ending':
            if not stack:
                raise MusicFormatError(f'alternate ending lies outside a repeat at {event.offset}')
            begin, endings = stack[-1]
            if not endings and event.ending_number != 1:
                raise MusicFormatError(f'first alternate ending must start at pass 1 at {event.offset}')
            if endings and event.ending_number <= conductor[endings[-1]].ending_number:
                raise MusicFormatError(f'alternate ending numbers are out of order at {event.offset}')
            if event.ending_number > conductor[begin].repeat_count:
                raise MusicFormatError(f'alternate ending exceeds repeat count at {event.offset}')
            endings.append(index)
        elif event.kind == 'repeat_end':
            if not stack:
                raise MusicFormatError(f'repeat end has no start at {event.offset}')
            begin, endings = stack.pop()
            opening = conductor[begin]
            if opening.tick == event.tick:
                raise MusicFormatError(f'empty repeat at {opening.offset}')
            sections[begin] = index, endings
    if stack:
        raise MusicFormatError(f'unclosed repeat at {conductor[stack[-1][0]].offset}')
    return sections


def _playback_chunks(conductor, sections, first, last, left, right):
    cursor = first
    while cursor < last:
        if cursor not in sections:
            cursor += 1
            continue
        end, endings = sections[cursor]
        start_tick = conductor[cursor].tick
        yield left, start_tick, conductor[first:cursor]
        common_end = endings[0] if endings else end
        ending_numbers = [conductor[index].ending_number for index in endings]
        ending_limits = [*endings[1:], end]
        for play in range(1, conductor[cursor].repeat_count + 1):
            yield from _playback_chunks(conductor, sections, cursor + 1, common_end,
                                        start_tick, conductor[common_end].tick)
            if endings and play <= ending_numbers[-1]:
                choice = bisect_right(ending_numbers, play) - 1
                begin, limit = endings[choice], ending_limits[choice]
                yield from _playback_chunks(conductor, sections, begin + 1, limit,
                                            conductor[begin].tick, conductor[limit].tick)
        left = conductor[end].tick
        cursor = first = end + 1
    yield left, right, conductor[first:last]


def _validate_repeat_notes(voice, boundaries):
    connected = False
    for event in voice:
        if event.kind not in ('note', 'rest'):
            continue
        if event.kind == 'note':
            connected = event.connection in ('start', 'continue')
        elif event.connection != 'continue':
            connected = event.connection == 'start'
        end = event.tick + event.duration_ticks
        index = bisect_right(boundaries, event.tick)
        if index < len(boundaries):
            boundary = boundaries[index]
            if boundary < end or (boundary == end and connected):
                raise MusicFormatError(f'repeat boundary crosses a note, rest or connection at {event.offset}')


def expand_playback(sequence):
    """Expand supported repeats and endings to a separate timeline with source offsets."""
    _require_interpreted(sequence)
    sections = _repeat_sections(sequence.conductor)
    if not sections:
        return sequence
    boundaries = sorted({sequence.conductor[i].tick for begin, (end, endings) in sections.items()
                         for i in (begin, end, *endings)})
    voice_ticks = [tuple(event.tick for event in voice) for voice in sequence.voices]
    for voice in sequence.voices:
        _validate_repeat_notes(voice, boundaries)
    voices = [[] for _ in sequence.voices]
    conductor = []
    elapsed = size = 0
    chunks = _playback_chunks(sequence.conductor, sections, 0, len(sequence.conductor), 0, sequence.written_ticks)
    current = next(chunks)
    while current is not None:
        lo, hi, events = current
        current = next(chunks, None)
        shift = elapsed - lo
        size += len(events) + 1
        for ticks, source, target in zip(voice_ticks, sequence.voices, voices, strict=True):
            first = bisect_left(ticks, lo)
            last = len(ticks) if current is None else bisect_left(ticks, hi)
            size += last - first
            if size > MAX_PLAYBACK_EVENTS:
                raise MusicFormatError(f'repeat expansion exceeds the {MAX_PLAYBACK_EVENTS}-event limit')
            target.extend(replace(event, tick=event.tick + shift) for event in source[first:last])
        conductor.extend(replace(event, tick=event.tick + shift) for event in events)
        elapsed += hi - lo
    ends = tuple(voice[-1].tick + (voice[-1].duration_ticks or 0) if voice else 0 for voice in voices)
    return Sequence(tuple(tuple(voice) for voice in voices), tuple(conductor), elapsed, ends)


def to_midi(sequence):
    """Project the supported playback timeline to Standard MIDI File type 1."""
    sequence = expand_playback(sequence)
    tempos = [(0, _midi_tempo(DEFAULT_QUARTER_BPM))]
    annotations = []
    for event in sequence.conductor:
        if event.kind == 'tempo':
            if event.quarter_bpm < 4:
                raise MusicFormatError('tempo is outside the Standard MIDI File representation')
            entry = (event.tick, _midi_tempo(event.quarter_bpm))
            if tempos[-1][0] == event.tick:
                tempos[-1] = entry
            else:
                tempos.append(entry)
        elif event.kind == 'meter':
            exponent = event.meter_denominator.bit_length() - 1
            annotations.append((event.tick, b'\xff\x58\x04' + bytes((event.meter_numerator, exponent, 24, 8))))
        elif event.kind == 'score_marker':
            annotations.append((event.tick, b'\xff\x06\x01' + event.marker.encode('ascii')))
    conductor = sorted(tempos + annotations, key=lambda item: item[0])
    tracks = [_midi_track(conductor, sequence.written_ticks)]
    for channel, voice in enumerate(sequence.voices):
        messages = []
        for start, end, pitch in _midi_notes(voice):
            messages.append((start, bytes((0x90 | channel, pitch, 64))))
            messages.append((end, bytes((0x80 | channel, pitch, 0))))
        tracks.append(_midi_track(messages, sequence.written_ticks))
    return pack('>4sIHHH', b'MThd', 6, 1, len(tracks), TICKS_PER_QUARTER) + b''.join(tracks)


def main(argv=None):
    from . import sampled_music

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--midi', type=Path, help='write a fully interpreted score to a new MIDI file')
    parser.add_argument('--wav', type=Path, help='write approximate sampled playback to a new WAV file')
    parser.add_argument('--instruments', type=Path, help='directory of explicit SND instruments for --wav')
    parser.add_argument('--rate', type=int, help='WAV sample rate (default 48000 Hz)')
    parser.add_argument('--sample-policy', choices=sampled_music.SAMPLE_POLICIES,
                        help='sample range resolution for WAV output (default rsx-ranges)')
    args = parser.parse_args(argv)
    if bool(args.wav) != bool(args.instruments):
        parser.error('--wav and --instruments must be supplied together')
    if not args.wav and (args.rate is not None or args.sample_policy is not None):
        parser.error('--rate and --sample-policy require --wav')
    created = []
    try:
        with args.source.open('rb') as stream:
            score = parse_bytes(stream.read(MAX_BYTES + 1))
        sequence = project(score)
        result = describe(score, sequence)
        outputs = []
        if args.midi:
            outputs.append((args.midi, to_midi(sequence)))
        if args.wav:
            instruments = sampled_music.load_instruments(args.instruments)
            playback = sampled_music.render(score, instruments,
                                            rate=sampled_music.OUTPUT_RATE if args.rate is None else args.rate,
                                            sample_policy=args.sample_policy or 'rsx-ranges')
            outputs.append((args.wav, playback.wav()))
            result['sampled_playback'] = playback.describe()
        for path, data in outputs:
            with path.open('xb') as stream:
                created.append(path)
                stream.write(data)
    except (OSError, ValueError) as exc:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
