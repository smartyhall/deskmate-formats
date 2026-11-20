"""Lossless reader for the observed DM_Music 1.04 HDS interchange syntax."""

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import re


class HdsFormatError(ValueError):
    """The input has no supported HDS song envelope."""


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
        return duration * Fraction(2, 3) if self.modifier == 'T' else duration

    @property
    def kind(self) -> str:
        if self.raw == 'x':
            return 'placeholder'
        if self.pitch == 'R':
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


_NOTE = re.compile(r'(T|Sb|Se)?(1|2|4|8|16|32)(\.{0,2})(R|[A-G][#b]?[+-]?\d{1,2})')
_HEADERS = {'Name', 'Beats Per Measure', 'Single Beat Note', 'Pace', 'PolyDur'}
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
        if not content.startswith('[') and '/' in content:
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
