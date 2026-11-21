# MidiMapper 6.38 HDS semantics

Native tests extended the [single major-scale reference](midimapper-win98-20261120.md)
using the same Win98 SE 4.10.2222 A installation and VB6 SP6 runtime.
The original installed disk was copied and both images matched SHA-256
`109cc2c9290ecae39032e3b09e973ecd50816e9d07f71a2f9026bafcb65e4d1b`
before boot. The ASUS P/I-P55T2P4 clone retained its 200 MHz Pentium MMX,
128 MiB RAM, S3 ViRGE, SB16 PnP and disabled network links. The
86Box 7.0 executable SHA-256 was
`e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d`.
The ROMs and installed application identities follow the earlier report.
The device chooser showed Creative Music Synth [220]. Recording used
tempo meta events unless a test explicitly described another setting.
An initial boot with the data floppy mounted stalled before Win98.
Ejecting it and resetting the disposable guest gave the desktop at
102,000 ms on the cumulative clock.

## Pitch

The byte-exact 374-byte minor-scale MIDI has two occurrences of wire
pitch 57 for `A-3`. All 15 pitches agree with the independent native
SNG projection. The table covers additional tool-authored controls.
The bridge numbers denote hammered dulcimer positions. They did not
change the wire pitch in these tests.

| HDS spellings | Native MIDI pitches |
| --- | --- |
| `C`, `C1`, `C2`, `C3`, `C4`, `C99` | 60 |
| `C-`, `C-3`, `C+`, `C+3` | 48, 48, 72, 72 |
| `C++3`, `C--3`, `C+++3`, `C---3`, `C----3` | 84, 36, 96, 24, 12 |
| `c#3` / `Db3`, `D#3` / `Eb3`, `F#3` / `Gb3`, `G#3` / `Ab3`, `A#3` / `Bb3` | 61, 63, 66, 68, 70 |
| `A-3`, `a-3`, `B-3` | 57, 57, 59 |
| `B#3`, `Cb3`, `E#3`, `Fb3` | 60 in each test |
| `B#-3`, `Cb+3` | 48, 72 |
| `C-----3`, `G+++++3` | 24, 127 |

The unsupported accidental results are consistent with a C fallback
before octave adjustment. The 24 observed for `C-----3` conflicts
with an unqualified linear formula that predicts 0. The new
`hds.midi_pitch` converts the measured natural and common accidental
spellings over the supported 12–127 range and rejects unsupported cases.
It preserves literal pitch spelling separately in the lossless reader.
The boundary trial hit a Win98 floppy retry, dismissed with Escape.
All 14 note pitches and the recording completion were present.
This take supplies pitch evidence only.

## Converter octave adjustment

The pinned DM_Music 1.04 executable (caption version 1.4, SHA-256
`b84f1a9a9dab3252c6c85127a7c9d25f68c0cde53a572ede80a4674230a02150`)
converted the original synthetic `SCALE.SNG` at Change octave +1.
The independently read 398-byte HDS moved every pitch by 12
semitones from the published +0 case, changing the lower tonic
from `C3` to `C+2` and the upper tonic to `C++2`.
The conversion completed by 777,741 ms. MidiMapper then opened the
exact HDS and confirmed a 390-byte, 480 PPQ silent export by
829,626 ms. All 15 wire pitches matched the independent projection
at 72–84. The shape and final rest of the source score are retained.
Both application outputs are pinned in the fixture manifest.

## Timing and note boundaries

The same original timing phrase uses repeated C, a quarter rest, a
half note, dotted eighth, sixteenth, thirty-second, three eighth
triplets and a double-dotted quarter. The 120 PPQ nominal note
durations are 120, 120, 240, 90, 30, 15, 40, 40, 40, 210.

| Pace | PPQ | Silent | Note OFF/ON delay | Result |
| --- | --- | --- | --- | --- |
| 60 BPM | 120 | Yes | 0 ms | Nominal durations, usual gap 1 tick |
| 100 BPM | 120 | Yes | 0 ms | Nominal durations, usual gap 1 tick |
| 180 BPM | 120 | Yes | 0 ms | Nominal durations, usual gap 3 ticks |
| 100 BPM | 120 | No | 0 ms | Eight of ten durations extended by 1 tick, usual gap 1 tick |
| 100 BPM | 480 | Yes | 0 ms | All ten durations extended by 1 tick, usual gap 6 ticks |
| 100 BPM | 480 | Yes | 10 ms | Same durations as the 0 ms trial, usual gap 14 ticks |

Here a usual gap is the next note-on tick minus the previous
note-off tick for adjacent notes without an intervening score rest.
At 480 PPQ and 100 BPM the 10 ms setting added exactly 8 ticks per
ordinary transition. It added 16 ticks to the onset interval spanning a
rest. The program's configured delay explains the controlled
difference. The baseline gaps at 0 ms and the small duration error
vary with tempo, resolution and audible recording. The remaining
timing overhead could involve player scheduling and guest timer
quantization. This run did not isolate the Windows clock from emulation.

The 140 BPM duration control preserved its tempo change as 428,571
microseconds per quarter. The eight score rows yielded seven sounded
notes with the nominal durations after the scored rest was excluded.
Several exports for scores ending on a note include an unmatched
final note-off. The minor scale, which ends on a rest, did not.
There is also a nonzero startup offset before the first note. None of
these recording details are part of the new rational score projection.

## Voices and control flow

The native DM_Music duet yielded notes on wire channels 0 and 1.
The native converter's trio began with C, E and A in channels 0, 1
and 2 on the same MIDI tick. Channel 0 then sounded G while
the channel-2 A was still active. The score projection retains per-voice
clocks, pitches and durations in quarter-note units. A rest advances its
own voice and an `x` placeholder leaves that voice clock intact.
This is the `hds.project_linear_voices` API for linear PolyDur.
It refuses repeats, articulation or raw MIDI commands at their source
lines and retains all of them in the parsed Song.

The major and minor scale HDS labels 9 and 10 still initialized
program 0. A separate two-voice control initialized both sounding
channels with program 0 despite HDS labels 41 and 74. Its in-song
raw MIDI commands selected wire programs 11 and 73 on channels 0
and 1. Its `pp` and `ff` produced velocities 48 and 115, in contrast
to the scales' 77 (`mp`) and 90 (`mf`). Measurements describe the
tested settings. The app's general program selection and other engines'
instrument numbering are separate.

- The DM_Music alternate-ending control recorded
  60, 64, 60, 67, 69. Both passes and each designated ending were
  already expanded into notes in the SMF.
- The separate structural control recorded pitches
  60, 64, 65, 60, 67, 69, 67. A tied C pair became one note of
  242 ticks at 120 PPQ. Changing-pitch slur and legato test notes
  remained distinct. The last legato A had duration 38 ticks versus
  60 nominal. This was one control with the displayed slur velocity
  factor 0.75. It does not establish a general articulation rule.
- The same clip wrote 6/8 as a time-signature meta event, and
  the key and score marker as textual MIDI marker events.
  `[Tempo= 1/8 = 120]` produced a 1,000,000 µs quarter tempo.
  The named bar did not appear as a separate meta event in this take.

## Historical corpus

All 33 supplied HDS songs were inventoried and hashed privately.
The reader preserves the original bytes for all 33. Comparing with
the baseline parser on the same files, recognized timed rows rose
from 11,842 to 12,035. Unknown event lines dropped from 334 to 6
and unknown fields in recognized rows from 4,470 to 13.
The new lexical coverage includes single-slot rows, omitted bridge
numbers, repeated octave signs, case, combined slur-triplet modifiers,
the PolyPhony header, and decimal or VB hexadecimal MIDI directives.
The residual timed tokens include notes without durations and one
rest with a bridge-like suffix. Their literal bytes remain available.

The bundled Guitar Standard Tuning file opened and ran in audible
mode. It exported six notes at pitches 52, 57, 62, 67, 71, 76.
Each took 480 ticks at 480 PPQ, although the HDS used whole-note
spellings with an initial beat unit of 1 and 60 beats per minute.
The export used 60 quarter-note BPM and a 4/1 time-signature event.
This legacy beat-unit behavior falls outside the linear PolyDur API.
The historical duet opened and completed a silent native export with
302 paired notes and no unmatched terminations. Neither historical
recording is in Git. The guitar FRT and dulcimer DLC are image and
note-location mappings. Their definitions include bitmap resources,
coordinates, key names, and DLC bridges. They supply instrument
visualization evidence. In-song program changes are independently
observed on the MIDI wire.

## Workflow and preservation

Use the preserved Win98 installation or a byte-verified writable clone.
Boot from the hard disk with a blank floppy drive. Prepare a new FAT12
data floppy, place the source file on it byte-for-byte, and attach it
after boot. Regenerate the original tool controls with:

```powershell
python tools/experimental/midimapper_controls.py <new-output-directory>
```

The private socket driver captured the exact loaded-file, export
options and completion states. It stopped on unexpected frames.
Load the DOS-named file from File → Load song, verify the MIDI device,
and choose File → Save as .mid file with a distinct output name.
Check the tempo event, PPQ, meter and silent-mode controls before
recording. Give the guest time to finish the floppy write, acknowledge
the completed-file modal, eject, extract with 7-Zip 26.05 and verify
both the source and output digests. Mido 1.3.3 pairs wire events by
track, channel and pitch and retains unmatched events.

The original synthetic input and export identities, sizes and recording
options are in the [fixture manifest](../../tests/fixtures/application-generated/manifest.json).
The first batch held a verified case completion by 446,730 ms, the
second by 703,757 ms, and the delay comparison by 738,660 ms.
The private `semantics-20261120` evidence directory holds both image
snapshots and their extracted files, source and output comparisons,
the 33-file corpus inventory, framebuffer captures and the native
socket journal. It also holds the scripts for staged media and
recording. Use unique volume serials when swapping media on Win98
and retain the previous image for recovery.

The practical next timing experiment is to repeat the same 480 PPQ
zero-delay control with different guest timer or audio configuration
and record enough repeats to estimate jitter. For articulation,
use separate one-factor controls for ties across bars, changing-pitch
slurs and legato. For instruments, change the player UI's selected
program with otherwise identical HDS and compare its initialized
wire program to the raw-MIDI control.
