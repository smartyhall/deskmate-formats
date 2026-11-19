"""Crop a stopped PSSJ capture and pair it with a 48 kHz independent render."""

import argparse
from hashlib import sha256
import json
from math import log2
from pathlib import Path
import wave

from compare_sampled_music import correlation, describe, rms
import numpy as np


RATE = 48_000
LEAD = 7_200
TAIL = 19_200
THRESHOLD = 25


def digest(data):
    return sha256(data).hexdigest()


def first_signal(pcm):
    indices = np.flatnonzero(np.abs(pcm.astype(np.int32)) > THRESHOLD)
    if not len(indices):
        raise ValueError('no signal above the alignment threshold')
    return int(indices[0]), int(indices[-1])


def wav_frames(path):
    with wave.open(str(path), 'rb') as source:
        if (source.getframerate(), source.getnchannels(), source.getsampwidth()) != (RATE, 1, 2):
            raise ValueError('expected a mono 16-bit 48 kHz comparison WAV')
        if not 0 < source.getnframes() <= 20 * RATE:
            raise ValueError('independent comparison duration exceeds bound')
        data = source.readframes(source.getnframes())
        if len(data) != source.getnframes() * 2:
            raise ValueError('short comparison WAV')
    return data


def write_wav(path, pcm):
    with path.open('xb') as destination, wave.open(destination, 'wb') as output:
        output.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        output.writeframes(pcm)
    data = path.read_bytes()
    return {'sha256': digest(data), 'size': len(data), 'frames': len(pcm) // 2}


def measure(native, rendered, polyphonic):
    def stats(pcm):
        return {
            'peak': int(np.max(np.abs(pcm))),
            'rms': round(rms(pcm), 4),
            'clipped_frames': int(np.count_nonzero((pcm == -32768) | (pcm == 32767))),
            'activity': describe(pcm, 3 if polyphonic else 1),
        }

    def envelope(pcm):
        blocks = pcm[:len(pcm) // 2400 * 2400].reshape((-1, 2400))
        return np.sqrt(np.mean(blocks * blocks, axis=1))

    left, right = (np.frombuffer(pcm, dtype='<i2').astype(float) for pcm in (native, rendered))
    ns, rs = stats(left), stats(right)
    events = []
    if len(ns['activity']) == len(rs['activity']):
        for observed, modeled in zip(ns['activity'], rs['activity'], strict=True):
            pitch = None
            if not polyphonic:
                a, b = [span['spectral_windows_hz'].get('45', []) for span in (observed, modeled)]
                if a and b and 0.94 <= b[0] / a[0] <= 1.06:
                    pitch = round(1200 * log2(b[0] / a[0]), 3)
            a, b = (span['first_frame'] for span in (observed, modeled))
            events.append({
                'onset_delta_ms': round((b - a) / 48, 4),
                'active_duration_delta_ms': round(modeled['active_ms'] - observed['active_ms'], 4),
                'dominant_component_pitch_delta_cents': pitch,
                'first_40ms_onset_aligned_correlation': correlation(left[a:a + 1920], right[b:b + 1920]),
            })
    return {
        'native': ns, 'renderer': rs, 'by_order_when_activity_counts_match': events,
        'whole_waveform_correlation': correlation(left, right),
        'rms_envelope_50ms_correlation': correlation(envelope(left), envelope(right)),
    }


def pair(raw, start, stop, render_pcm, polyphonic):
    if len(raw) % 2:
        raise ValueError('partial frame in raw DAC capture')
    capture = np.frombuffer(raw, dtype='<i2')
    rendered = np.frombuffer(render_pcm, dtype='<i2')
    if not 0 <= start < stop <= len(capture):
        raise ValueError('playback transition exceeds DAC capture')
    onset, last = first_signal(capture[start:stop])
    render_onset, _ = first_signal(rendered)
    if render_onset > LEAD:
        raise ValueError('initial independent silence exceeds lead allowance')
    first_frame = start + onset - LEAD
    frames = max(LEAD + last - onset + 1, LEAD - render_onset + len(rendered)) + TAIL
    if not 0 <= first_frame or first_frame + frames > stop:
        raise ValueError('capture bounds do not contain the paired recording')
    if np.any(capture[first_frame:start]):
        raise ValueError('playback lead-in overlaps earlier native activity')
    native = raw[first_frame * 2:(first_frame + frames) * 2]
    render_start = LEAD - render_onset
    padded = b'\0\0' * render_start + render_pcm
    padded = padded.ljust(frames * 2, b'\0')
    return native, padded, {
        'native': {'tap': 'pssj-dac-pre-mix', 'first_capture_frame': first_frame,
                   'raw_frames': len(capture), 'raw_sha256': digest(raw),
                   'command_start_frame': start, 'command_stop_frame': stop,
                   'command_to_threshold_frames': onset},
        'renderer': {'first_render_frame': render_start, 'render_frames': len(rendered),
                     'render_pcm_sha256': digest(render_pcm), 'rate': RATE},
        'metrics': measure(native, padded, polyphonic),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw', type=Path)
    parser.add_argument('start_ms', type=int)
    parser.add_argument('stop_ms', type=int)
    parser.add_argument('render_wav', type=Path)
    parser.add_argument('output_stem', type=Path)
    parser.add_argument('--polyphonic', action='store_true')
    args = parser.parse_args()
    with args.raw.open('rb') as source:
        raw = source.read(96 * RATE * 2 + 1)
    if len(raw) > 96 * RATE * 2:
        raise ValueError('capture exceeds this baseline tap limit')
    pcm = wav_frames(args.render_wav)
    native, rendered, receipt = pair(raw, args.start_ms * 48, args.stop_ms * 48, pcm, args.polyphonic)
    for role, samples in (('native', native), ('renderer', rendered)):
        path = args.output_stem.with_name(f'{args.output_stem.name}-{role}.wav')
        receipt[role].update(write_wav(path, samples))
    print(json.dumps(receipt, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
