# DeskMate Music v1 listening baseline

The [listening suite](../../examples/music-listening/README.md) contains ten
matched native and independent performances across five original passages.
The independent renderer is byte-unchanged from PR #118. The
[suite specification](../../examples/music-listening/suite-v1.json) records
each word, voice, pitch, duration, dynamic and connection. The
[milestone manifest](../../examples/music-listening/v1/baseline-pr118/manifest.json)
records all WAV hashes, native input and guest identities, raw capture
identities, exact frame windows and metrics.

## Reproduce the inputs

The ten scores are tool-generated operations on the synthetic M11 template.
Music opened and played the exact authored bytes. Independent FAT16 and
7-Zip extractions from the stopped guests agreed with the inputs. These
scores have playback acceptance evidence. They have no native Save As
receipt.

From the repository, with `src` on the Python module path, generate a
fresh copy into a new private directory.

```powershell
$env:PYTHONPATH = 'src'
python tools/experimental/music_listening_inputs.py tests/fixtures/application-generated/music/m11.sng tests/fixtures/application-generated/sound/labinst-native.snd $newInputs
```

The three uncompressed instruments use 5,500 unsigned 8-bit samples, an
11 kHz stored rate and MIDI root 60. Each has explicit MIDI range 57–95.
The 42-sample period corresponds to about 261.905 Hz. Lab Reed uses
integer harmonics and loops frames 1,260 through 3,359. Pluck and Bell
use decaying components and have no sustain loop. The generator lists
all amplitudes, frequency multipliers, attack times and decay constants.
Native Sound opened each SND, played it and saved it with a new filename
after loading it from the experiment floppy. Independent FAT16 and 7-Zip
agreed on all three saves. The resulting files match their generated
inputs byte for byte. Music used those exact saved bytes in slots 9–11.

The OEM bank uses Clarinet, Piano, Bells and Cello in slots 1–4.
Each installed SND matched its counterpart on Disk 2 of the archived
RSX DeskMate 3.04 distribution. Both playback paths used those identities.
The score and descriptor manifest records the compatible ranges for these
passages. The RSX distribution index identifies Disk 2 as the Music and
Sound disk. The historical Music and Sound manuals in `musicsnd.zip`
and `mussnd89.zip` describe composing and selecting supplied instruments.
Their software terms restrict copying and disassembly of the software.
The reviewed notices give no express license or express prohibition for
publication of new musical performances. The operator's 2026-11-18
intended-use decision is the basis for including these performances.
Project attribution and licenses cover the original contributions and
rights held by the project. The underlying instrument material retains
its own rights. [Historical archive sources](audio-historical-corpus-20261118.md)

## Native capture and independent output

Use the [retained instrumented build](pssj-dac-capture-20261118.md)
and a fresh clone of the stopped follow-up RSX machine for each run.
Preserve the source configuration and NVRAM and remove the initial floppy
binding from the clone. Launch with seed 1 and a new
`DESKMATE_RESEARCH_PSSJ_CAPTURE` path. Use the authenticated loopback
socket to advance 10,500 emulated milliseconds to DOS, change to
`\DESKMATE`, attach the experiment floppy and copy its contents.
Launch `desk music LAB1.SNG` or the desired input name. Start playback
with Alt+P and advance the receipt's playback interval. Verify playback
and return to DOS before moving to the next score. Use separate runs for
scales and cadences in each bank to fit inside the original tap's
96-second cap. The first OEM cadence run reached the end of its planned
window while OEM5 was still playing. The retained retry allowed 10.8
and 11.8 seconds after the play commands and returned to DOS for both
scores. The original attempt remains in the private archive.

| Retained run | Elapsed emulated milliseconds |
| --- | ---: |
| Sound import, playback and saves | 63,558 |
| Synthetic scales | 73,228 |
| Synthetic cadences | 47,192 |
| OEM scales | 73,228 |
| OEM cadences | 54,792 |

Use the pinned renderer with an explicit instrument directory containing
only the bank for that performance. The project Music CLI takes the
score, `--instruments`, `--rate 48000` and `--wav`. Pair the stopped DAC
capture and the unpadded render using the command below. Supply the
start and stop times from the exact recorded playback command and use
`--polyphonic` for cadences. NumPy is required for the comparison tool.

```powershell
python tools/experimental/music_listening_pair.py $raw $startMs $stopMs $renderWav $outputStem
```

Each pair shares the first frame exceeding ±25 PCM units at frame 7,200
(150 ms). The native file is a contiguous frame crop of the stopped tap.
The independent file contains the full render PCM with zero padding to
align it and share the native duration. A 400 ms allowance follows the
longer of the last above-threshold native frame and the full independent
timeline. The manifest retains the native play-command latency separately.
Audio uses 48 kHz mono signed 16-bit PCM, at original levels, without EQ,
normalization or time warping.

## Baseline observations

| Passage | Synthetic RMS envelope correlation | OEM RMS envelope correlation |
| --- | ---: | ---: |
| Major scale | 0.731 | 0.925 |
| Minor scale | 0.993 | 0.953 |
| Chromatic scale | 0.851 | 0.867 |
| Major cadence | 0.952 | 0.998 |
| Minor cadence | 0.937 | 0.931 |

These are Pearson correlations of 50 ms RMS blocks after a single
onset alignment. Whole-recording waveform correlations range from
−0.319 to 0.843. No 16-bit clipping was observed. The synthetic reed
major scale exposes substantial differences in active durations. The
Piano, Bells and Cello performances sometimes sustain across note or
chord boundaries. The activity detector merges nonzero intervals with
gaps at most 5 ms, so the number of spans can differ from the number
of written notes. The comparison reports onset, duration and local
waveform deltas only when the span counts match. Dominant spectral
component deltas are limited to comparable single-voice spans, and
can represent a harmonic. The mix has no isolated per-voice trace and
this baseline does not measure exact sustain transitions or final output
including PSG. The retained comparison is the RSX pre-mix DAC stream.
