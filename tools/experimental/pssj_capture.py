"""Measure tone intervals in a stopped 48 kHz signed little-endian PSSJ DAC tap."""

import argparse
from array import array
import hashlib
import json
from pathlib import Path
from statistics import median
import sys


RATE = 48_000
BLOCK = RATE // 100
MAX_BYTES = 96 * RATE * 2


def decode(data):
    if len(data) % 2 or not 0 < len(data) <= MAX_BYTES:
        raise ValueError("expected a nonempty, complete capture within the 96-second tap limit")
    samples = array("h")
    samples.frombytes(data)
    if sys.byteorder == "big":
        samples.byteswap()
    return samples


def tone(samples):
    if len(samples) < 600 or max(samples) - min(samples) <= 25:
        return None
    center = sum(samples) / len(samples)
    crossings = []
    for index in range(1, len(samples)):
        low, high = samples[index - 1], samples[index]
        if low < center <= high:
            crossings.append(index - 1 + (center - low) / (high - low))
    if len(crossings) < 4:
        return None
    gaps = [right - left for left, right in zip(crossings, crossings[1:])]
    period = median(gaps)
    if sum(abs(gap - period) <= 0.1 * period for gap in gaps) < 0.9 * len(gaps):
        return None
    frequency = RATE / period
    return round(frequency, 2) if 120 <= frequency <= 2400 else None


def measure(samples, start, stop):
    if not 0 <= start < stop <= len(samples) / RATE:
        raise ValueError("selector is outside the capture")
    first, last = round(start * RATE), round(stop * RATE)
    intervals = []
    onset = None
    for pos in range(first, last + 1, BLOCK):
        block = samples[pos:pos + BLOCK]
        active = pos + BLOCK <= last and max(block) - min(block) > 25
        if active and onset is None:
            onset = pos
        elif not active and onset is not None:
            if pos - onset >= 2 * BLOCK:
                intervals.append((onset, pos))
            onset = None
    report = []
    for lo, hi in intervals:
        frequencies = []
        for pos in range(lo, hi - round(0.030 * RATE), round(0.050 * RATE)):
            zone = samples[pos + round(0.008 * RATE):min(hi, pos + round(0.047 * RATE))]
            frequency = tone(zone)
            if frequency is not None:
                frequencies.append([round((pos - lo) / RATE, 3), frequency])
        report.append({
            "start": round(lo / RATE, 6), "end": round(hi / RATE, 6),
            "duration": round((hi - lo) / RATE, 6), "frequencies": frequencies,
            "peak": max(abs(sample) for sample in samples[lo:hi]),
        })
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("selectors", nargs="*", metavar="NAME:START:STOP")
    args = parser.parse_args()
    try:
        with args.capture.open("rb") as source:
            data = source.read(MAX_BYTES + 1)
        samples = decode(data)
        selectors = args.selectors or [f"capture:0:{len(samples) / RATE}"]
        measurements = {}
        for selector in selectors:
            name, start, stop = selector.split(":")
            if not name or name in measurements:
                raise ValueError("selector names must be nonempty and unique")
            measurements[name] = measure(samples, float(start), float(stop))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps({"sha256": hashlib.sha256(data).hexdigest(), "raw_bytes": len(data),
                      "rate": RATE, "elapsed": len(samples) / RATE, "measurements": measurements},
                     indent=2))


if __name__ == "__main__":
    main()
