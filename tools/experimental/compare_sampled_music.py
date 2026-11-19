"""Compare a 48 kHz independent WAV with a selected PSSJ DAC capture window."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import wave

import numpy as np

from pssj_capture import decode, MAX_BYTES, RATE


def active_spans(samples):
    """Group nonzero frames separated by at most five milliseconds."""
    nonzero = np.flatnonzero(samples)
    if len(nonzero):
        breaks = np.flatnonzero(np.diff(nonzero) > RATE // 200) + 1
        return [(int(group[0]), int(group[-1]) + 1) for group in np.split(nonzero, breaks)]
    return []


def rms(samples):
    return float(np.sqrt(np.mean(samples * samples)))


def peaks(samples, count=1):
    """Find the strongest separated spectral peaks in a Hann-tapered window."""
    if len(samples) < 480 or not np.any(samples):
        return []
    size = 1 << max(15, (len(samples) * 8 - 1).bit_length())
    spectrum = np.abs(np.fft.rfft((samples - samples.mean()) * np.hanning(len(samples)), n=size))
    lower, upper = round(120 * size / RATE), round(4200 * size / RATE)
    found = []
    for _ in range(count):
        index = lower + int(np.argmax(spectrum[lower:upper]))
        if spectrum[index] < 1:
            break
        left, center, right = np.log(np.maximum(spectrum[index - 1:index + 2], 1e-9))
        curvature = left + right - 2 * center
        offset = (left - right) / (2 * curvature) if curvature else 0
        found.append(round((index + offset) * RATE / size, 3))
        radius = round(70 * size / RATE)
        spectrum[max(0, index - radius):index + radius + 1] = 0
    return found


def describe(samples, peak_count):
    spans = active_spans(samples)
    if not spans:
        return []
    onset = spans[0][0]
    intervals = []
    for lo, hi in spans:
        window = samples[lo:hi]
        intervals.append({
            'first_frame': lo,
            'relative_onset_ms': round((lo - onset) * 1000 / RATE, 4),
            'active_ms': round((hi - lo) * 1000 / RATE, 4),
            'peak': int(np.max(np.abs(window))),
            'rms': round(rms(window), 4),
            'clipped_frames': int(np.count_nonzero((window == -32768) | (window == 32767))),
            'spectral_windows_hz': {
                str(delay): peaks(window[48 * delay:48 * delay + 1440], peak_count)
                for delay in (10, 45, 115, 245) if len(window) >= 48 * delay + 1440
            },
        })
    return intervals


def correlation(left, right):
    count = min(len(left), len(right))
    left, right = left[:count], right[:count]
    if count < 2:
        return None
    left, right = left - left.mean(), right - right.mean()
    length = np.linalg.norm(left) * np.linalg.norm(right)
    return round(float(np.dot(left, right) / length), 6) if length else None


def compare(native, rendered, peak_count=1):
    native_spans, rendered_spans = describe(native, peak_count), describe(rendered, peak_count)
    paired = []
    for native_span, render_span in zip(native_spans, rendered_spans):
        start_native, start_render = native_span['first_frame'], render_span['first_frame']
        first = native[start_native:start_native + 1920]
        early = rendered[start_render:start_render + 1920]
        paired.append(correlation(first, early))
    return {'native': native_spans, 'rendered': rendered_spans, 'first_40ms_onset_aligned_correlation': paired}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('start_ms', type=int)
    parser.add_argument('stop_ms', type=int)
    parser.add_argument('wav', type=Path)
    parser.add_argument('--peaks', choices=(1, 2, 3), type=int, default=1)
    args = parser.parse_args(argv)
    try:
        with args.capture.open('rb') as stream:
            data = stream.read(MAX_BYTES + 1)
        capture = decode(data)
        start, stop = args.start_ms * 48, args.stop_ms * 48
        if not 0 <= start < stop <= len(capture):
            raise ValueError('native bounds are outside the capture')
        with wave.open(str(args.wav), 'rb') as source:
            if (source.getframerate(), source.getnchannels(), source.getsampwidth()) != (RATE, 1, 2):
                raise ValueError('expected a 48 kHz mono 16-bit render')
            count = source.getnframes()
            if count > 12_000_000:
                raise ValueError('render exceeds the comparison frame limit')
            payload = source.readframes(count)
            if len(payload) != count * 2:
                raise ValueError('incomplete WAV frames')
        rendered = np.frombuffer(payload, dtype='<i2').astype(float)
        result = compare(np.asarray(capture[start:stop], dtype=float), rendered, args.peaks)
    except (OSError, ValueError, wave.Error) as error:
        parser.error(str(error))
    print(json.dumps({
        'capture_sha256': sha256(data).hexdigest(),
        'start_ms': args.start_ms,
        'stop_ms': args.stop_ms,
        'render_pcm_sha256': sha256(payload).hexdigest(),
        **result,
    }, indent=2))


if __name__ == '__main__':
    main()
