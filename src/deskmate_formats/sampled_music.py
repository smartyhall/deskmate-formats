"""Independent sampled playback of a supported DeskMate Music score."""

from array import array
from bisect import bisect_right
from collections import Counter
from dataclasses import asdict, dataclass
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from struct import pack
import sys

from . import music, sound


OUTPUT_RATE = 48_000
MAX_FRAMES = 12_000_000
MAX_DECODED_BYTES = 16 * 1024 * 1024
MAX_INSTRUMENT_FILES = 128
MAX_SOURCE_BYTES = 32 * 1024 * 1024
DEFAULT_SLOTS = (1, 2, 3)
MODEL = 'rsx-dac-approximation-v1'
SAMPLE_POLICIES = ('rsx-ranges', 'strict', 'nearest-root')
# Six measured gain steps approximately scale unsigned PCM by 5/3 through
# 10 in DAC output units. The unmarked RSX default has the third step's gain.
DYNAMIC_WEIGHTS = (1, 2, 3, 4, 5, 6)
DEFAULT_DYNAMIC_WEIGHT = 3
SCORE_TO_NATIVE_CLOCK = Fraction(27_358, 28_800)
PITCH_CALIBRATION = 1.0106
PHASE_BITS = 32


class PlaybackError(music.MusicFormatError):
    """The selected score and Sound files cannot produce a bounded render."""


@dataclass(frozen=True)
class Binding:
    slot: int
    name: str
    sha256: str
    sample_indices: tuple[int, ...]


@dataclass(frozen=True)
class Note:
    voice: int
    score_offset: int
    score_tick: int
    written_end_tick: int
    native_start_seconds: Fraction
    native_end_seconds: Fraction
    start_frame: int
    gate_frame: int
    slot: int
    sample_index: int
    midi_pitch: int
    dynamic_index: int | None
    source_step: int


@dataclass(frozen=True)
class UnmappedPitch:
    slot: int
    midi_pitch: int
    note_count: int


@dataclass(frozen=True)
class RenderedMusic:
    rate: int
    frames: int
    pcm: bytes
    bindings: tuple[Binding, ...]
    notes: tuple[Note, ...]
    unmapped_pitches: tuple[UnmappedPitch, ...]
    sample_policy: str
    model: str = MODEL

    def wav(self):
        return pack('<4sI4s4sIHHIIHH4sI', b'RIFF', 36 + len(self.pcm), b'WAVE',
                    b'fmt ', 16, 1, 1, self.rate, self.rate * 2, 2, 16, b'data', len(self.pcm)) + self.pcm

    def describe(self):
        return {
            'model': self.model,
            'sample_policy': self.sample_policy,
            'rate': self.rate,
            'frames': self.frames,
            'instruments': [asdict(binding) for binding in self.bindings],
            'unmapped_pitches': [asdict(pitch) for pitch in self.unmapped_pitches],
        }


def load_instruments(directory):
    """Read a bounded directory of SND files. Recording and preview files are ignored."""
    paths = []
    for path in Path(directory).iterdir():
        if path.suffix.lower() == '.snd':
            paths.append(path)
            if len(paths) > MAX_INSTRUMENT_FILES:
                raise PlaybackError(f'instrument directory exceeds {MAX_INSTRUMENT_FILES} SND files')
    total = 0
    instruments = []
    for path in sorted(paths, key=lambda item: (item.name.casefold(), item.name)):
        if not path.is_file():
            raise PlaybackError(f'expected a regular SND file: {path.name}')
        with path.open('rb') as stream:
            source = stream.read(sound.MAX_BYTES + 1)
        total += len(source)
        if total > MAX_SOURCE_BYTES:
            raise PlaybackError('instrument collection exceeds the source byte limit')
        try:
            instrument = sound.parse_bytes(source)
        except sound.SoundFormatError as exc:
            raise PlaybackError(f'{path.name}: {exc}') from exc
        if 1 <= instrument.instrument_number <= 32:
            instruments.append(instrument)
    return tuple(instruments)


class _Clock:
    def __init__(self, conductor):
        self.ticks = [0]
        self.seconds = [Fraction(0)]
        self.steps = [self._step(music.DEFAULT_QUARTER_BPM)]
        for event in conductor:
            if event.kind == 'tempo':
                if event.tick == self.ticks[-1]:
                    self.steps[-1] = self._step(event.quarter_bpm)
                else:
                    self.seconds.append(self.at(event.tick))
                    self.ticks.append(event.tick)
                    self.steps.append(self._step(event.quarter_bpm))

    @staticmethod
    def _step(bpm):
        return SCORE_TO_NATIVE_CLOCK * Fraction(60, music.TICKS_PER_QUARTER) / Fraction(bpm)

    def at(self, tick):
        index = bisect_right(self.ticks, tick) - 1
        return self.seconds[index] + self.steps[index] * (tick - self.ticks[index])


def _instrument_map(instruments):
    by_slot = {}
    total = 0
    for index, instrument in enumerate(instruments):
        if index >= MAX_INSTRUMENT_FILES:
            raise PlaybackError(f'instrument collection exceeds {MAX_INSTRUMENT_FILES} files')
        total += len(instrument.source)
        if total > MAX_SOURCE_BYTES:
            raise PlaybackError('instrument collection exceeds the source byte limit')
        slot = instrument.instrument_number
        if not 1 <= slot <= 32:
            raise PlaybackError(f'Sound file {instrument.name!r} has no Music instrument number')
        previous = by_slot.setdefault(slot, instrument)
        if previous.source != instrument.source:
            raise PlaybackError(f'conflicting Sound files for slot {slot}: {previous.name!r}, {instrument.name!r}')
    return by_slot


def _sample_index(instrument, pitch, policy):
    matches = []
    explicit_ranges = False
    for index, sample in enumerate(instrument.samples):
        low, high = sample.low_note, sample.high_note
        if (low, high) == (255, 255):
            continue
        if not 1 <= low <= high <= 63:
            raise PlaybackError(f'invalid range for slot {instrument.instrument_number}, sample {index + 1}: {low}–{high}')
        explicit_ranges = True
        if low <= pitch - 32 <= high:
            matches.append(index)
    if policy == 'rsx-ranges' and explicit_ranges:
        return matches[-1] if matches else None
    if len(matches) == 1:
        return matches[0]
    if policy == 'nearest-root':
        candidates = matches or range(len(instrument.samples))
        distances = [(abs(instrument.samples[index].midi_pitch - pitch), index) for index in candidates
                     if instrument.samples[index].midi_pitch is not None]
        if distances:
            closest = min(distance for distance, _ in distances)
            nearest = [index for distance, index in distances if distance == closest]
            if len(nearest) == 1:
                return nearest[0]
    reason = 'ambiguous sample ranges' if len(matches) > 1 else 'no unambiguous sample range'
    raise PlaybackError(f'{reason} for slot {instrument.instrument_number}, MIDI pitch {pitch}')


def _sample_data(instrument, index):
    descriptor = instrument.samples[index]
    label = f'slot {instrument.instrument_number}, sample {index + 1}'
    if descriptor.midi_pitch is None or not descriptor.sample_count:
        raise PlaybackError(f'invalid root pitch or empty PCM for {label}')
    start, end = descriptor.sustain_start, descriptor.sustain_end
    if (start, end) != (0, 0) and not 0 <= start < end <= descriptor.sample_count:
        raise PlaybackError(f'invalid sustain bounds for {label}: {start}–{end}')
    try:
        pcm = instrument.pcm(index)
    except sound.SoundFormatError as exc:
        raise PlaybackError(f'{label}: {exc}') from exc
    return pcm, start, end


def _voice_notes(voice, default_slot):
    controls = iter(event for event in voice if event.kind in ('instrument', 'dynamic'))
    control = next(controls, None)
    slot, dynamic = default_slot, None
    for first, last in music._connected_notes(voice):
        while control is not None and control.offset < first.offset:
            if control.kind == 'instrument':
                slot = control.instrument_slot
            else:
                dynamic = control.dynamic_index
            control = next(controls, None)
        yield first, last, slot, dynamic


def _plan(sequence, by_slot, clock, rate, sample_policy, default_slots):
    decoded = {}
    selections = {}
    notes = []
    used_slots = set()
    unmapped = Counter()
    decoded_bytes = 0
    for voice_number, (voice, default_slot) in enumerate(zip(sequence.voices, default_slots, strict=True), 1):
        for first, last, slot, dynamic in _voice_notes(voice, default_slot):
            pitch = first.midi_pitch
            instrument = by_slot.get(slot)
            if instrument is None:
                raise PlaybackError(f'missing instrument slot {slot} for voice {voice_number} at offset {first.offset}')
            used_slots.add(slot)
            selection = slot, pitch
            if selection not in selections:
                selections[selection] = _sample_index(instrument, pitch, sample_policy)
            index = selections[selection]
            if index is None:
                unmapped[selection] += 1
                continue
            key = slot, index
            descriptor = instrument.samples[index]
            if key not in decoded:
                decoded_bytes += descriptor.sample_count
                if decoded_bytes > MAX_DECODED_BYTES:
                    raise PlaybackError('selected samples exceed the decoded byte limit')
                decoded[key] = _sample_data(instrument, index)
            start, end = clock.at(first.tick), clock.at(last.tick + last.duration_ticks)
            duration = end - start
            # Approximate the duration-dependent gate from short, quarter
            # and whole-note controls. Slurred pitches retrigger without a gap.
            gate = duration
            if last.connection not in ('start', 'continue'):
                gate = min(duration, max(Fraction(57, 400), duration * Fraction(13, 16) - Fraction(3, 40)))
            step = round((1 << PHASE_BITS) * instrument.sample_rate / rate
                         * 2 ** ((pitch - descriptor.midi_pitch) / 12) * PITCH_CALIBRATION)
            notes.append(Note(voice_number, first.offset, first.tick, last.tick + last.duration_ticks,
                              start, end, round(start * rate), round((start + gate) * rate),
                              slot, index, pitch, dynamic, step))
    return notes, decoded, used_slots, unmapped


def _mix(notes, decoded, frames):
    output = array('i', [0]) * frames
    for note in notes:
        pcm, loop_start, loop_end = decoded[note.slot, note.sample_index]
        weight = DEFAULT_DYNAMIC_WEIGHT if note.dynamic_index is None else DYNAMIC_WEIGHTS[note.dynamic_index]
        phase = 0
        loop_limit = loop_end << PHASE_BITS
        loop_period = (loop_end - loop_start) << PHASE_BITS
        limit = len(pcm) << PHASE_BITS
        for frame in range(note.start_frame, note.gate_frame):
            if loop_end and phase >= loop_limit:
                phase = loop_limit - loop_period + (phase - loop_limit) % loop_period
            elif phase >= limit:
                break
            output[frame] += (pcm[phase >> PHASE_BITS] - 128) * weight
            phase += note.source_step
    clipped = array('h', (max(-32768, min(32767, round(value * 5 / 3))) for value in output))
    if sys.byteorder == 'big':
        clipped.byteswap()
    return clipped.tobytes()


def render(score, instruments, *, rate=OUTPUT_RATE, sample_policy='rsx-ranges', default_slots=DEFAULT_SLOTS,
           max_frames=MAX_FRAMES):
    """Render parsed Score and Sound objects to bounded mono signed 16-bit PCM."""
    if type(rate) is not int or not 8_000 <= rate <= 96_000:
        raise PlaybackError('output rate must be an integer from 8000 to 96000 Hz')
    if type(max_frames) is not int or not 1 <= max_frames <= MAX_FRAMES:
        raise PlaybackError(f'output frame budget must be from 1 to {MAX_FRAMES}')
    if sample_policy not in SAMPLE_POLICIES:
        raise PlaybackError(f'unknown sample selection policy {sample_policy!r}')
    if len(default_slots) != music.VOICE_COUNT or any(
            type(slot) is not int or not 1 <= slot <= 32 for slot in default_slots):
        raise PlaybackError('each of the three voices requires a default slot from 1 to 32')
    sequence = music.project(score)
    try:
        music._require_linear(sequence)
        clock = _Clock(sequence.conductor)
        frames = round(clock.at(sequence.written_ticks) * rate)
        if frames > max_frames:
            raise PlaybackError(f'render needs {frames} frames and exceeds the {max_frames}-frame output limit')
        by_slot = _instrument_map(instruments)
        notes, decoded, used_slots, unmapped = _plan(sequence, by_slot, clock, rate, sample_policy, default_slots)
    except PlaybackError:
        raise
    except music.MusicFormatError as exc:
        raise PlaybackError(str(exc)) from exc

    selected = {slot: [] for slot in used_slots}
    for slot, index in decoded:
        selected[slot].append(index)
    bindings = tuple(Binding(slot, by_slot[slot].name, sha256(by_slot[slot].source).hexdigest(), tuple(sorted(indices)))
                     for slot, indices in sorted(selected.items()))
    omitted = tuple(UnmappedPitch(slot, pitch, count) for (slot, pitch), count in sorted(unmapped.items()))
    return RenderedMusic(rate, frames, _mix(notes, decoded, frames), bindings, tuple(notes), omitted, sample_policy)
