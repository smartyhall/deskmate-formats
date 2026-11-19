"""Measure aggregate DeskMate Music compatibility using a local Sound collection."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from deskmate_formats import music, sampled_music
from music_control_inventory import distinct_scores


def failure(error):
    message = str(error)
    for fragment, label in (
            ('unsupported score word', 'opaque_score_words'),
            ('boundary crosses', 'repeat_boundary'),
            ('voice duration exceeds', 'voice_extends_past_conductor'),
            ('tie or slur', 'connection'),
            ('missing instrument slot', 'missing_instrument'),
            ('unambiguous sample range', 'sample_range'),
            ('conflicting Sound files', 'conflicting_instrument'),
            ('output limit', 'output_limit')):
        if fragment in message:
            return label
    return 'other_constraint'


def inventory(root, instruments, *, rate=sampled_music.OUTPUT_RATE):
    counts = dict.fromkeys(('distinct', 'structural', 'interpreted_words', 'midi'), 0)
    midi_failures = Counter()
    rendered = {policy: Counter(full=0, unmapped=0, no_audio=0)
                for policy in ('rsx-ranges', 'nearest-root')}
    opaque_words = Counter()
    for _, data, _ in distinct_scores(root):
        counts['distinct'] += 1
        try:
            score = music.parse_bytes(data)
        except music.MusicFormatError:
            continue
        counts['structural'] += 1
        sequence = music.project(score)
        counts['interpreted_words'] += not sequence.opaque
        opaque_words.update({f'{event.word:04x}' for event in sequence.opaque})
        try:
            music.to_midi(sequence)
        except music.MusicFormatError as exc:
            midi_failures[failure(exc)] += 1
        else:
            counts['midi'] += 1
        for policy, results in rendered.items():
            try:
                audio = sampled_music.render(score, instruments, rate=rate, sample_policy=policy)
            except sampled_music.PlaybackError as exc:
                results[failure(exc)] += 1
            else:
                status = 'no_audio' if not any(audio.pcm) else 'unmapped' if audio.unmapped_pitches else 'full'
                results[status] += 1
    return {
        'model': sampled_music.MODEL,
        'output_rate': rate,
        'instruments': [{'slot': instrument.instrument_number, 'sha256': sha256(instrument.source).hexdigest()}
                        for instrument in sorted(instruments, key=lambda item: item.instrument_number)],
        'counts': counts,
        'midi_failures': dict(midi_failures),
        'render_results': {policy: dict(results) for policy, results in rendered.items()},
        'remaining_opaque_words_by_score': dict(sorted(opaque_words.items())),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corpus', type=Path)
    parser.add_argument('instruments', type=Path)
    parser.add_argument('--rate', type=int, default=sampled_music.OUTPUT_RATE)
    args = parser.parse_args()
    if not args.corpus.is_dir():
        parser.error('expected a corpus directory')
    try:
        instruments = sampled_music.load_instruments(args.instruments)
        if not 8_000 <= args.rate <= 96_000:
            parser.error('output rate must be from 8000 to 96000 Hz')
        report = inventory(args.corpus, instruments, rate=args.rate)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
