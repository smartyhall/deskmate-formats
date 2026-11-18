"""Summarize control families across distinct local DeskMate Music files."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path

from deskmate_formats import music


SPECIAL_DURATIONS = {0xef, 0xf3, 0xf4}
NOTATION_DURATIONS = set(music.NOTE_TICKS) | SPECIAL_DURATIONS


def voice_family(event):
    code, value = divmod(event.word, 256)
    duration = code | 0x60
    if event.kind in ("instrument", "dynamic"):
        return event.kind, f"{value:02x}"
    if duration in NOTATION_DURATIONS:
        if duration in SPECIAL_DURATIONS:
            return "special_duration", f"{duration:02x}"
        if value & 0xc0 == 0x80:
            return "unresolved_accidental_80", f"{value & 0x3f:02x}"
        if event.kind == "note" and event.accidental_flags:
            return "recognized_accidental_bits", f"{event.accidental_flags:02x}"
    if event.kind == "opaque":
        return ("instrument_outside_range" if code == 0x73 else
                "dynamic_outside_range" if code == 0x72 else "other_voice_opaque"), f"{event.word:04x}"
    return None


def conductor_family(event):
    if event.kind == "advance":
        return None
    family = event.word >> 12
    name = event.kind
    if name == "opaque":
        name = {
            0x1: "other_tempo_candidate", 0x3: "other_repeat_start_candidate",
            0x4: "alternate_ending_candidate", 0x5: "other_repeat_end_candidate",
            0x6: "other_meter_candidate",
        }.get(family, "other_conductor_opaque")
        if event.word >> 8 == 0x70:
            name = "other_key_candidate"
        elif event.word >> 8 == 0x74:
            name = "score_marker_candidate"
    return name, f"{event.word:04x}"


def inventory(root):
    seen = set()
    families = defaultdict(Counter)
    placements = defaultdict(Counter)
    stream_ids = defaultdict(Counter)
    values = defaultdict(Counter)
    blockers = Counter()
    file_counts = defaultdict(set)
    flags = Counter()
    header_profiles = set()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() != ".sng":
            continue
        with path.open("rb") as source:
            data = source.read(music.MAX_BYTES + 1)
        if len(data) > music.MAX_BYTES:
            raise music.MusicFormatError("Music input exceeds the bounded profile")
        digest = sha256(data).digest()
        if digest in seen:
            continue
        seen.add(digest)
        score = music.parse_bytes(data)
        sequence = music.project(score)
        header_profiles.add(score.header[4:22])
        flags[len(score.text_padding), len(score.trailer)] += 1
        try:
            music.to_midi(sequence)
        except music.MusicFormatError as error:
            message = str(error)
            blockers[
                "opaque_words" if "unsupported score word" in message else
                "repeat_playback" if message.startswith("score repeats") else
                "other_sequence_constraint"
            ] += 1
        else:
            blockers["accepted"] += 1
        for number, stream in enumerate((*sequence.voices, sequence.conductor)):
            in_stream = set()
            classifier = conductor_family if number == 3 else voice_family
            for position, event in enumerate(stream):
                family = classifier(event)
                if family is None:
                    continue
                name, value = family
                in_stream.add(name)
                families[name]["opaque" if event.kind == "opaque" else "projected"] += 1
                stream_ids[name][("voice_1", "voice_2", "voice_3", "conductor")[number]] += 1
                placements[name][("early", "middle", "late")[3 * position // len(stream)]] += 1
                values[name][value] += 1
            for name in in_stream:
                file_counts[name].add(digest)
    prevalence = {name: len(digests) for name, digests in file_counts.items()}
    return {
        "schema_version": 1, "distinct_scores": len(seen), "midi_results": dict(blockers),
        "distinct_header_profiles": len(header_profiles),
        "container_variants": [
            {"text_pad_bytes": pad, "trailer_bytes": trailer, "scores": count}
            for (pad, trailer), count in sorted(flags.items())
        ],
        "families": [
            {"name": name, "scores": prevalence[name], "events": dict(families[name]),
             "streams": dict(stream_ids[name]), "stream_thirds": dict(placements[name]),
             "values": dict(sorted(values[name].items()))}
            for name in sorted(families, key=lambda key: (-prevalence[key], key))
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    args = parser.parse_args()
    if not args.corpus.is_dir():
        parser.error("expected a corpus directory")
    print(json.dumps(inventory(args.corpus), indent=2))
