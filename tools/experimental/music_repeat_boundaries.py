"""Inventory strict repeat-boundary rejections in a local historical corpus."""

import argparse
from itertools import islice
import json
from pathlib import Path

from deskmate_formats import music
from music_control_inventory import distinct_scores


def describe(path, digest, sequence):
    sections = music._repeat_sections(sequence.conductor)
    controls = [event for event in sequence.conductor
                if event.kind in ('repeat_start', 'alternate_ending', 'repeat_end')]
    crossings = []
    for number, voice in enumerate(sequence.voices, 1):
        active = False
        for event in voice:
            if event.kind not in ('note', 'rest'):
                continue
            if event.kind == 'note' or event.connection != 'continue':
                active = event.connection in ('start', 'continue')
            end = event.tick + event.duration_ticks
            for control in controls:
                inside = event.tick < control.tick < end
                open_at_boundary = event.tick < end == control.tick and active
                if inside or open_at_boundary:
                    crossings.append({
                        'voice': number, 'offset': event.offset, 'word': f'{event.word:04x}',
                        'start_tick': event.tick, 'end_tick': end, 'event': event.kind,
                        'midi_pitch': event.midi_pitch, 'connection': event.connection,
                        'crossing': 'open_connection' if open_at_boundary else f'inside_{event.kind}',
                        'boundary_tick': control.tick, 'boundary': control.kind,
                        'boundary_offset': control.offset,
                    })
    slices = music._playback_chunks(sequence.conductor, sections, 0, len(sequence.conductor),
                                    0, sequence.written_ticks)
    timeline = [[lo, hi] for lo, hi, _ in islice(slices, 4096)]
    return {
        'name': path.name, 'sha256': digest.hex(), 'written_ticks': sequence.written_ticks,
        'written_voice_ticks': sequence.voice_ticks,
        'repeat_controls': [{'tick': e.tick, 'kind': e.kind, 'offset': e.offset, 'word': f'{e.word:04x}',
                             'repeat_count': e.repeat_count, 'ending_number': e.ending_number}
                            for e in controls],
        'conductor_only_slices': timeline,
        'slices_truncated': next(slices, None) is not None,
        'crossings': crossings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corpus', type=Path)
    args = parser.parse_args()
    if not args.corpus.is_dir():
        parser.error('expected a corpus directory')
    total = 0
    cases = []
    for path, payload, digest in distinct_scores(args.corpus):
        total += 1
        sequence = music.project(music.parse_bytes(payload))
        try:
            music.expand_playback(sequence)
        except music.MusicFormatError as error:
            if 'repeat boundary crosses' in str(error):
                cases.append(describe(path, digest, sequence))
    print(json.dumps({'distinct_scores': total, 'repeat_boundary_cases': cases}, indent=2))


if __name__ == '__main__':
    main()
