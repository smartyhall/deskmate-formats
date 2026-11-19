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
MAX_STREAM_FRAMES = 96_000_000
BLOCK_FRAMES = 32_768
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
# Each voice contributes at most one centered 8-bit sample per output frame.
MIX_BOUNDS = 128 * DYNAMIC_WEIGHTS[-1] * music.VOICE_COUNT
MIX_LEVELS = {value: round(value * 5 / 3) for value in range(-MIX_BOUNDS, MIX_BOUNDS + 1)}
# The observed 48 kHz frame intervals fit a 1,152-sample PSSJ block at
# 3.579545 MHz / 161. At the root pitch, two DAC updates span one source frame.
DAC_RATE = Fraction(3_579_545, 161)
DAC_BLOCK_SECONDS = 1152 / DAC_RATE
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
    continues_previous: bool
    continues_next: bool


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
    written_ticks: int
    playback_ticks: int
    model: str = MODEL

    def wav(self):
        return _wav_header(self.rate, self.frames) + self.pcm

    def describe(self):
        return _describe(self)


@dataclass(frozen=True)
class _RenderPlan:
    rate: int
    frames: int
    bindings: tuple[Binding, ...]
    notes: tuple[Note, ...]
    unmapped_pitches: tuple[UnmappedPitch, ...]
    sample_policy: str
    written_ticks: int
    playback_ticks: int
    model: str = MODEL


def _describe(playback):
    return {
        'model': playback.model,
        'sample_policy': playback.sample_policy,
        'rate': playback.rate,
        'frames': playback.frames,
        'written_ticks': playback.written_ticks,
        'playback_ticks': playback.playback_ticks,
        'instruments': [asdict(binding) for binding in playback.bindings],
        'unmapped_pitches': [asdict(pitch) for pitch in playback.unmapped_pitches],
    }


def _wav_header(rate, frames):
    size = frames * 2
    return pack('<4sI4s4sIHHIIHH4sI', b'RIFF', 36 + size, b'WAVE',
                b'fmt ', 16, 1, 1, rate, rate * 2, 2, 16, b'data', size)


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
        blocks = (60 / Fraction(bpm)) // DAC_BLOCK_SECONDS
        return blocks * DAC_BLOCK_SECONDS / music.TICKS_PER_QUARTER

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
    notes = iter(music._connected_notes(voice, split_controls=True))
    note = next(notes, None)
    slot, dynamic = default_slot, None
    for event in voice:
        if event.kind == 'instrument':
            slot = event.instrument_slot
        elif event.kind == 'dynamic':
            dynamic = event.dynamic_index
        elif note is not None and event is note[0]:
            yield *note, slot, dynamic
            note = next(notes, None)


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
            # Plain notes use a duration-dependent gate. A tie keeps the
            # source active for its written span. Slurs use a one-block gap.
            gate = duration
            continues_next = last.connection in ('start', 'continue')
            if continues_next:
                gate = max(Fraction(0), duration - DAC_BLOCK_SECONDS)
            elif first is last:
                gate = min(duration, max(Fraction(57, 400), duration * Fraction(13, 16) - Fraction(3, 40)))
            step = round((1 << PHASE_BITS) * float(DAC_RATE / (2 * rate))
                         * 2 ** ((pitch - descriptor.midi_pitch) / 12))
            notes.append(Note(voice_number, first.offset, first.tick, last.tick + last.duration_ticks,
                              start, end, round(start * rate), round((start + gate) * rate),
                              slot, index, pitch, dynamic, step, first.connection in ('continue', 'end'),
                              continues_next))
    return notes, decoded, used_slots, unmapped


@dataclass(frozen=True)
class _Span:
    first: int
    stop: int
    pcm: bytes
    phase: int
    step: int
    loop_limit: int
    loop_period: int
    weight: int


def _voice_spans(notes, decoded):
    previous = None
    previous_geometry = None
    phase = 0
    for note in notes:
        pcm, loop_start, loop_end = decoded[note.slot, note.sample_index]
        weight = DEFAULT_DYNAMIC_WEIGHT if note.dynamic_index is None else DYNAMIC_WEIGHTS[note.dynamic_index]
        geometry = len(pcm), loop_start, loop_end
        previous_connected = previous is not None and previous.continues_next
        if not note.continues_previous or (previous_connected and previous_geometry != geometry):
            phase = 0
        elif not previous_connected:
            # A silent connection start has no preceding PCM phase to carry.
            phase = loop_start << PHASE_BITS
        loop_limit = loop_end << PHASE_BITS
        loop_period = (loop_end - loop_start) << PHASE_BITS
        length = note.gate_frame - note.start_frame
        if not loop_period:
            available = (len(pcm) << PHASE_BITS) - phase
            length = min(length, max(0, (available + note.source_step - 1) // note.source_step))
        if length:
            yield _Span(note.start_frame, note.start_frame + length, pcm, phase,
                        note.source_step, loop_limit, loop_period, weight)
            # Carry the phase after the last audible frame, including loop wrap.
            last_phase = phase + (length - 1) * note.source_step
            if loop_period and last_phase >= loop_limit:
                last_phase = loop_limit - loop_period + (last_phase - loop_limit) % loop_period
            phase = last_phase + note.source_step
        previous = note
        previous_geometry = geometry


def _mix_blocks(notes, decoded, frames):
    voices = [[] for _ in range(music.VOICE_COUNT)]
    for note in notes:
        voices[note.voice - 1].append(note)
    sources = [_voice_spans(voice, decoded) for voice in voices]
    pending = [next(source, None) for source in sources]
    for begin in range(0, frames, BLOCK_FRAMES):
        end = min(begin + BLOCK_FRAMES, frames)
        output = array('h', [0]) * (end - begin)
        for index, source in enumerate(sources):
            span = pending[index]
            while span is not None and span.first < end:
                first, stop = max(begin, span.first), min(end, span.stop)
                step, pcm, weight = span.step, span.pcm, span.weight
                loop_limit, loop_period = span.loop_limit, span.loop_period
                phase = span.phase + (first - span.first) * step
                for frame in range(first - begin, stop - begin):
                    if loop_period and phase >= loop_limit:
                        phase = loop_limit - loop_period + (phase - loop_limit) % loop_period
                    output[frame] += (pcm[phase >> PHASE_BITS] - 128) * weight
                    phase += step
                if span.stop > end:
                    break
                span = next(source, None)
            pending[index] = span
        pcm_output = array('h', map(MIX_LEVELS.__getitem__, output))
        if sys.byteorder == 'big':
            pcm_output.byteswap()
        yield pcm_output.tobytes()


def _prepare(score, instruments, rate, sample_policy, default_slots, max_frames, hard_limit):
    if type(rate) is not int or not 8_000 <= rate <= 96_000:
        raise PlaybackError('output rate must be an integer from 8000 to 96000 Hz')
    if type(max_frames) is not int or not 1 <= max_frames <= hard_limit:
        raise PlaybackError(f'output frame budget must be from 1 to {hard_limit}')
    if sample_policy not in SAMPLE_POLICIES:
        raise PlaybackError(f'unknown sample selection policy {sample_policy!r}')
    if len(default_slots) != music.VOICE_COUNT or any(
            type(slot) is not int or not 1 <= slot <= 32 for slot in default_slots):
        raise PlaybackError('each of the three voices requires a default slot from 1 to 32')
    written = music.project(score)
    try:
        sequence = music.expand_playback(written)
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
    return (_RenderPlan(rate, frames, bindings, tuple(notes), omitted, sample_policy,
                        written.written_ticks, sequence.written_ticks), decoded)


def render(score, instruments, *, rate=OUTPUT_RATE, sample_policy='rsx-ranges', default_slots=DEFAULT_SLOTS,
           max_frames=MAX_FRAMES):
    """Render parsed Score and Sound objects to bounded mono signed 16-bit PCM."""
    plan, decoded = _prepare(score, instruments, rate, sample_policy, default_slots, max_frames, MAX_FRAMES)
    pcm = b''.join(_mix_blocks(plan.notes, decoded, plan.frames))
    return RenderedMusic(rate, plan.frames, pcm, plan.bindings, plan.notes, plan.unmapped_pitches,
                         sample_policy, plan.written_ticks, plan.playback_ticks)


def write_wav(score, instruments, stream, *, rate=OUTPUT_RATE, sample_policy='rsx-ranges',
              default_slots=DEFAULT_SLOTS, max_frames=MAX_FRAMES):
    """Stream a WAV to a binary writer and return the playback description."""
    plan, decoded = _prepare(score, instruments, rate, sample_policy, default_slots, max_frames, MAX_STREAM_FRAMES)
    header = _wav_header(rate, plan.frames)
    if stream.write(header) != len(header):
        raise OSError('incomplete Music WAV header write')
    for pcm in _mix_blocks(plan.notes, decoded, plan.frames):
        if stream.write(pcm) != len(pcm):
            raise OSError('incomplete Music WAV PCM write')
    return _describe(plan)
