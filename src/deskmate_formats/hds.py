"""Lossless reader for observed DM_Music and MidiMapper HDS syntax."""

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import re


class HdsFormatError(ValueError):
    """The input is outside the supported HDS syntax or projection."""


@dataclass(frozen=True)
class NoteField:
    """One slot on a timed row. Retain pitch spelling in the HDS namespace."""

    raw: str
    denominator: int | None = None
    pitch: str | None = None
    dots: int = 0
    modifier: str = ''

    @property
    def quarter_notes(self) -> Fraction | None:
        if self.denominator is None:
            return None
        duration = Fraction(4, self.denominator) * (2 - Fraction(1, 2**self.dots))
        return duration * Fraction(2, 3) if self.modifier.upper().endswith('T') else duration

    @property
    def kind(self) -> str:
        if self.raw.lower() == 'x':
            return 'placeholder'
        if self.pitch in ('R', 'r'):
            return 'rest'
        if self.pitch is not None:
            return 'note'
        return 'unknown'


@dataclass(frozen=True)
class Line:
    number: int
    section: str | None
    text: str
    kind: str
    values: tuple[str | int, ...] = ()
    slots: tuple[NoteField, ...] = ()


@dataclass(frozen=True)
class Song:
    raw: bytes
    lines: tuple[Line, ...]

    @property
    def events(self) -> tuple[Line, ...]:
        return tuple(line for line in self.lines if line.section == 'Notes'
                     and line.kind not in ('section', 'comment', 'blank'))


@dataclass(frozen=True)
class TimedNote:
    line: int
    start_quarters: Fraction
    duration_quarters: Fraction
    midi_pitch: int


@dataclass(frozen=True)
class Voice:
    notes: tuple[TimedNote, ...]
    end_quarters: Fraction


_KEY = r'[A-G][#b]?'
_OCTAVES = r'\++|-+'
_BRIDGE = r'[0-9]{0,2}'
_PITCH = re.compile(rf'({_KEY})({_OCTAVES})?({_BRIDGE})', re.IGNORECASE | re.ASCII)
_NOTE = re.compile(
    rf'((?:Sb|Se|Lb|Le)?T?)(1|2|4|8|16|32)(\.{{0,2}})(R|{_KEY}(?:{_OCTAVES})?{_BRIDGE})',
    re.IGNORECASE | re.ASCII,
)
_HEADERS = {'Name', 'Beats Per Measure', 'Single Beat Note', 'Pace', 'PolyDur', 'PolyPhony'}
_MIDI_NUMBER = r'([0-9]{1,3}|&[hH][0-9a-fA-F]{1,2})'
_MIDI = re.compile(r'\[Midi\s+' + r'\s+'.join([_MIDI_NUMBER] * 3) + r'\]')
_CONTROLS = (
    ('tempo', re.compile(r'\[Tempo=\s*(\d+)/(\d+)\s*=\s*(\d+)\]')),
    ('dynamic', re.compile(r'\[Inst\.\s+(\d+)\s+dyn\.\s*=\s*(pp|p|mp|mf|f|ff)\]')),
    ('instrument', re.compile(r'\[Inst\.\s+(\d+)\s*=\s*(\d+)\]')),
    ('repeat_start', re.compile(r'\[Repeat\s+(\d+)x\]')),
    ('alternate_ending', re.compile(r'\[Ending\s+(\d+)\]')),
    ('repeat_end', re.compile(r'\[Repeat End\]')),
    ('bar', re.compile(r'\[Bar\s+(\d+)\]')),
    ('time', re.compile(r'\[Time\s+(\d+)/(\d+)\]')),
    ('key', re.compile(r'\[Key sig=\s*([^\[\]]+)\]')),
    ('score_marker', re.compile(r'\[Score marker ([A-Z])\]')),
)


_SEMITONES = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4,
              'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9,
              'A#': 10, 'Bb': 10, 'B': 11}


def midi_pitch(spelling: str) -> int:
    """Convert a supported HDS pitch spelling to a MIDI note number.

    Unsigned C is middle C. Each sign shifts one octave, and the trailing
    bridge number is independent of pitch. Reject unsupported accidentals
    and out-of-range notes rather than imitating player fallback behavior.
    """
    match = _PITCH.fullmatch(spelling)
    if match is None:
        raise ValueError(f'Invalid HDS pitch spelling: {spelling!r}')
    key, signs, _bridge = match.groups()
    semitone = _SEMITONES.get(key[0].upper() + key[1:].lower())
    if semitone is None:
        raise ValueError(f'Unsupported HDS accidental: {spelling!r}')
    signs = signs or ''
    pitch = 60 + semitone + 12 * (signs.count('+') - signs.count('-'))
    if not 12 <= pitch <= 127:
        raise ValueError(f'HDS pitch is outside the supported MIDI range 12–127: {spelling!r}')
    return pitch


_VOICE_METADATA = {'header', 'tempo', 'dynamic', 'instrument', 'bar', 'time', 'key', 'score_marker'}


def project_linear_voices(song: Song) -> tuple[Voice, ...]:
    """Project note placement for linear PolyDur scores in exact quarter units.

    Placeholders leave a voice clock unchanged and rests advance it. Header
    tempo, instrument and other recognized metadata stay on the source Song.
    This projection excludes repeats, connected articulation and MIDI commands.
    """
    headers = {}
    for line in song.lines:
        if line.kind == 'header' and line.values[0] in ('PolyDur', 'PolyPhony'):
            key, value = line.values
            if key in headers:
                raise HdsFormatError(f'Duplicate {key} at line {line.number}')
            headers[key] = value
    if headers.get('PolyDur', '').casefold() != 'true':
        raise HdsFormatError('Linear voice projection requires PolyDur=True')
    declared = headers.get('PolyPhony', '3')
    if re.fullmatch(r'(?:[1-9]|1[0-6])', declared) is None:
        raise HdsFormatError('PolyPhony must be from 1 to 16')
    count = int(declared)
    clocks = [Fraction(0) for _ in range(count)]
    voices = [[] for _ in range(count)]
    for line in song.events:
        if line.kind in _VOICE_METADATA:
            continue
        if line.kind != 'row' or len(line.slots) != count:
            raise HdsFormatError(f'Unsupported PolyDur row or command at line {line.number}')
        for i, slot in enumerate(line.slots):
            if slot.kind == 'placeholder':
                continue
            duration = slot.quarter_notes
            if duration is None or slot.modifier.upper() not in ('', 'T'):
                raise HdsFormatError(f'Unsupported note field at line {line.number}: {slot.raw!r}')
            if slot.kind == 'note':
                voices[i].append(TimedNote(line.number, clocks[i], duration, midi_pitch(slot.pitch)))
            clocks[i] += duration
    return tuple(Voice(tuple(notes), end) for notes, end in zip(voices, clocks))


def _note(token: str) -> NoteField:
    match = _NOTE.fullmatch(token)
    if match is None:
        return NoteField(token)
    modifier, denominator, dots, pitch = match.groups()
    return NoteField(token, int(denominator), pitch, len(dots), modifier or '')


def _line(number: int, section: str | None, text: str) -> Line:
    content = text.strip()
    if not content:
        return Line(number, section, text, 'blank')
    if content.startswith(';'):
        return Line(number, section, text, 'comment')
    if section == 'Song' and '=' in content:
        key, _, value = content.partition('=')
        if key.strip() in _HEADERS:
            return Line(number, section, text, 'header', (key.strip(), value.strip()))
    if section == 'Notes':
        for kind, pattern in _CONTROLS:
            if match := pattern.fullmatch(content):
                values = tuple(int(value) if value.isdecimal() else value for value in match.groups())
                return Line(number, section, text, kind, values)
        if match := _MIDI.fullmatch(content):
            values = tuple(int(value[2:], 16) if value.startswith('&') else int(value)
                           for value in match.groups())
            if 0x80 <= values[0] <= 0xFF and all(value < 0x80 for value in values[1:]):
                return Line(number, section, text, 'midi', values)
        if not content.startswith('['):
            slots = tuple(_note(token.strip()) for token in content.split('/'))
            if any(slot.kind != 'unknown' for slot in slots):
                return Line(number, section, text, 'row', slots=slots)
    return Line(number, section, text, 'unknown')


def parse_bytes(raw: bytes) -> Song:
    """Recognize the envelope and preserve every original byte and line."""
    section = None
    lines = []
    song_seen = notes_seen = False
    # Use only CR/LF as delimiters, preserving any other control bytes as text.
    decoded = raw.decode('cp1252', errors='surrogateescape')
    for number, text in enumerate(re.split(r'\r\n|\r|\n', decoded), 1):
        content = text.strip()
        if content == '[Song]' and not song_seen:
            song_seen = True
            section = 'Song'
        elif content == '[Notes]' and song_seen and not notes_seen:
            notes_seen = True
            section = 'Notes'
        else:
            lines.append(_line(number, section, text))
            continue
        lines.append(Line(number, section, text, 'section'))
    if not notes_seen:
        raise HdsFormatError('Expected [Song] followed by [Notes]')
    return Song(raw, tuple(lines))


def read(path: str | Path) -> Song:
    return parse_bytes(Path(path).read_bytes())
