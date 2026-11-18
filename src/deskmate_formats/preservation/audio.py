"""Offline audio artifacts and metadata."""

from hashlib import sha256

from .. import music, sound
from .model import Conversion, Diagnostic
from .render import html_page, html_table, html_text


def convert_sound(document, filename):
    content = sound.describe(document)
    diagnostics = []
    artifacts = {}
    rows = []
    players = []
    if document.compression:
        diagnostics.append(Diagnostic(
            'lossy_native_compression', 'notice',
            'WAV contains the decoded samples of the lossy native stream.'))
    if document.unassigned_regions:
        diagnostics.append(Diagnostic(
            'unassigned_source_bytes', 'opaque',
            'Bytes outside the header, descriptors and sample regions remain in the preserved source.'))
    for index, sample in enumerate(content['samples']):
        label = f'Sample {index + 1}'
        try:
            wav = document.wav(index)
        except sound.SoundFormatError as exc:
            diagnostics.append(Diagnostic('unsupported_sample_stream', 'omission', str(exc), label))
        else:
            path = f'assets/sample-{index + 1:02}.wav'
            artifacts[path] = wav
            frames = memoryview(wav)[44:44 + sample['sample_count']]
            sample['pcm_sha256'] = sha256(frames).hexdigest()
            players.append(f'<p>{label} <audio controls preload="none" src="{path}"></audio> '
                           f'<a href="{path}">Download WAV</a></p>')
        rows.append((index + 1, sample['sample_count'], f"{sample['sample_count'] / document.sample_rate:.4f}",
                     sample['midi_pitch'] if sample['midi_pitch'] is not None else '',
                     f"{sample['low_note']}–{sample['high_note']}" if sample['low_note'] != 255 else '',
                     f"{sample['sustain_start']}–{sample['sustain_end']}" if sample['sustain_end'] else ''))
    title = document.name or filename
    subtitle = f"DeskMate Sound {document.kind} · {document.sample_rate} Hz · {content['compression']}"
    body = (f'<p>Instrument number {html_text(document.instrument_number)}</p>' if document.instrument_number else '')
    body += html_table(('Sample', 'Frames', 'Seconds', 'MIDI pitch', 'Native range', 'Native sustain'),
                       rows, 'Sample descriptors') + ''.join(players)
    artifacts['preview.html'] = html_page(title, subtitle, body, diagnostics=diagnostics, local_audio=True)
    return Conversion(content, diagnostics, artifacts)


MUSIC_PREVIEW_EVENTS = 120


def convert_music(score, filename):
    sequence = music.project(score)
    content = music.describe(score, sequence)
    diagnostics = []
    artifacts = {}
    try:
        artifacts['composition.mid'] = music.to_midi(sequence)
    except music.MusicFormatError as exc:
        diagnostics.append(Diagnostic('midi_omitted', 'omission', str(exc)))
    else:
        diagnostics.append(Diagnostic(
            'neutral_midi_playback', 'notice',
            'MIDI uses neutral velocity and default playback instruments. '
            'Native instrument and dynamic changes remain in the score metadata.'))
        if any(event.connection for voice in sequence.voices for event in voice):
            diagnostics.append(Diagnostic('midi_connected_notes', 'notice',
                                          'MIDI joins ties and schedules slurred pitches without a rest.'))
    body = (f'<p>{html_text(score.author)}</p>' if score.author else '')
    body += f'<p>{music.TICKS_PER_QUARTER} ticks per quarter note. Default tempo {music.DEFAULT_QUARTER_BPM} BPM.</p>'
    if 'composition.mid' in artifacts:
        body += '<p><a href="composition.mid">Download MIDI</a></p>'
    streams = (*sequence.voices, sequence.conductor)
    for label, events in zip(('Voice 1', 'Voice 2', 'Voice 3', 'Conductor'), streams, strict=True):
        rows = (_music_row(event) for event in events[:MUSIC_PREVIEW_EVENTS])
        body += html_table(('Tick', 'Event', 'Duration', 'Native word'), rows, label)
        if len(events) > MUSIC_PREVIEW_EVENTS:
            diagnostics.append(Diagnostic(
                'music_preview_limit', 'omission', f'All {len(events)} words are available in content.json.', label))
    artifacts['preview.html'] = html_page(score.title or filename, 'DeskMate Music score', body, diagnostics=diagnostics)
    return Conversion(content, diagnostics, artifacts)


def _music_row(event):
    details = {
        'note': f'MIDI pitch {event.midi_pitch}' + (f' · connection {event.connection}' if event.connection else ''),
        'tempo': f'{event.quarter_bpm} BPM',
        'meter': f'Time signature {event.meter_numerator}/{event.meter_denominator}',
        'key': f'Key code {event.key_code}',
        'instrument': f'Instrument slot {event.instrument_slot}',
        'dynamic': f'Dynamic index {event.dynamic_index}',
        'barline': f'Barline {event.bar_number}',
        'repeat_start': f'Repeat start, count {event.repeat_count}',
        'repeat_end': 'Repeat end',
    }
    return (event.tick if event.tick is not None else '', details.get(event.kind, event.kind),
            event.duration_ticks if event.duration_ticks is not None else '', f'{event.word:04X}')
