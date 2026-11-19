"""Trace-informed RSX sample progression and interleaved DAC output."""

from array import array
import sys

from .sampled_music import BLOCK_FRAMES, DAC_RATE, DEFAULT_DYNAMIC_WEIGHT, DYNAMIC_WEIGHTS


# Transfer-derived increments for root 28. Treat their use at other roots as
# a model assumption. The long-output approximation continues to use v1.
MEASURED_STEPS = dict(zip(range(-12, 13), (
    128, 135, 143, 152, 161, 170, 181, 191, 203, 215, 228, 241,
    256, 271, 287, 304, 322, 341, 362, 383, 406, 430, 456, 483, 512,
), strict=True))
MEASURED_STEPS.update({19: 767, 24: 1024})
HALF_BUFFER_RESET = frozenset((-11, -7, -5, -3, -1, 1, 5, 7, 9, 11, 19))
DAC_LEVELS = {value: int(value * 448 / 15) for value in range(-128, 128)}


def _endpoints(plan, decoded, root_pitches):
    # Each endpoint maps to a midpoint and an endpoint byte on the DAC clock.
    count = round(plan.frames * DAC_RATE / (2 * plan.rate)) + 2
    output = array('h', [0]) * count
    previous = None
    carry = 0
    for note in plan.notes:
        key = note.slot, note.sample_index
        pcm, loop_start, loop_end = decoded[key]
        connected = previous is not None and previous.voice == note.voice and previous.continues_next
        if note.continues_previous and connected and key == (previous.slot, previous.sample_index):
            initial = carry
        elif note.continues_previous and not connected:
            initial = loop_start << 8
        else:
            initial = 0
        semitones = note.midi_pitch - root_pitches[key]
        step = MEASURED_STEPS.get(semitones)
        if step is None:
            step = round(256 * 2 ** (semitones / 12))
        # Two phase-reset patterns fit the first four traced endpoint blocks.
        # Start the simplified pattern at the attack and retain the existing gate.
        half_reset = semitones in HALF_BUFFER_RESET
        remainder = ((288 if half_reset else 576) * step) % 256
        weight = DEFAULT_DYNAMIC_WEIGHT if note.dynamic_index is None else DYNAMIC_WEIGHTS[note.dynamic_index]
        carry = initial
        for index, frame in enumerate(range(note.start_frame, note.gate_frame)):
            cuts = (index + (288 if half_reset else 0)) // 576
            phase = initial + index * step - cuts * remainder
            position = phase >> 8
            if loop_end and position >= loop_end:
                position = loop_start + (position - loop_end) % (loop_end - loop_start)
            if position >= len(pcm):
                break
            output[frame] += (pcm[position] - 128) * weight
            carry = ((position << 8) if loop_end else initial + index * step) + step
        previous = note
    # The measured single-voice ff transfer fits this divisor exactly.
    # Other dynamics and simultaneous voices use this approximate quantizer.
    return array('b', (value // 18 for value in output))


def blocks(plan, decoded):
    """Yield 48 kHz or resampled mono PCM with the experimental DAC model."""
    endpoints = _endpoints(plan, decoded, plan.root_pitches)
    rate_scale = plan.rate * DAC_RATE.denominator
    clock = DAC_RATE.numerator
    for begin in range(0, plan.frames, BLOCK_FRAMES):
        pcm = array('h')
        for frame in range(begin, min(begin + BLOCK_FRAMES, plan.frames)):
            elapsed = (frame * clock) // rate_scale
            offset, odd = divmod(elapsed, 2)
            value = endpoints[offset]
            if not odd:
                previous = endpoints[offset - 1] if offset else 0
                value = (value + previous) // 2
            pcm.append(DAC_LEVELS[value])
        if sys.byteorder == 'big':
            pcm.byteswap()
        yield pcm.tobytes()
