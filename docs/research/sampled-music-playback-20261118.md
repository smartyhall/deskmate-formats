# DeskMate sampled Music playback

## Fresh RSX DAC baseline

The retained instrumented 86Box executable and source patch matched their
prior SHA-256 hashes. A disposable clone used the stopped follow-up disk,
its RSX configuration and NVRAM, and seed 1. DOS booted before the new
FAT12 data floppy was mounted. Files were copied into the guest DeskMate
directory. In the guest, Sound played the control with Ctrl+E and Music played
each score with Alt+P. Every guest action used the authenticated loopback
socket. The run ended at 81,720 emulated milliseconds and 5,132 video frames.
The stopped 48 kHz mono signed 16-bit DAC stream spans exactly 81.720 seconds.
It contains the pre-mix PSSJ DAC contribution. [Setup and tap instructions](pssj-dac-capture-20261118.md) · [Hashes and windows](../evidence/sampled-music-baseline-20261118.json)

```powershell
$env:PYTHONPATH = 'src'
python tools/experimental/sampled_music_probe.py tests/fixtures/application-generated/music/m11.sng tests/fixtures/application-generated/sound/labinst-native.snd <new-directory>
```

The generated Sound files preserve LABINST's 11,000 Hz rate, root code 28,
range codes 25–63 and 5,500-frame PCM extent. Regions at frames 0–1,099,
1,100–2,199 and 2,200–5,499 contain 500, 900 and 1,400 Hz tones respectively.
Slot 9 avoids substituting the existing slot 7 file. The paired copies use
slots 10 and 11 to isolate a changed end word and cleared loop words. The
generator reproduced the exact eight privately archived probe files. The
published MARK9 and MARKLONG bytes are tool-generated and were accepted for
playback together. Sound resave and edit behavior remain untested.

| Control | Observed activity and periodic signal |
| --- | --- |
| Retained Sound tone replay | 0.50 s, about 448.6 Hz |
| M11, C4 then C5 | 0.43 s and 0.38 s, about 444.4 and 888.9 Hz by crossing estimate, 0.57 s onset interval |
| MARKLONG, whole C4 | 1.82 s, about 505 Hz then 914 Hz, with no sustained 1,400 Hz tail signature |
| MARKHI, whole C5 | 1.77 s, about 1,000 Hz then 1,828 Hz, with the intro shortened to about half its original duration |
| SHIFT, end word 1,980 | 1.79 s, with the 900 Hz source region still dominant after the intro |
| NOLOOP, both words zero | 0.50 s, with all three regions audible in sequence |
| MARKFAST, sixteenth, eighth and quarter C4 | Three intro entries. The first ends before the sustain region. The first two activity spans join at 10 ms activity resolution. |

The retained 10 ms interval analyzer reports windowed activity and
mean-crossing frequency. The zero-padded spectral method in the private
archive independently resolves the region sequence. It estimated about
504 and 908 Hz in MARKLONG, roughly 1% above the physical source
frequencies. Exact source frame endpoints and the native gate, envelope
and gain still require separate identification. The held notes gave no
evidence of a release jump into the tail. The no-loop control played the
entire tail during the held gate. Its end was independent of score length.

The private directory `music-sampled-playback/baseline` retains the input
floppy, stopped DAC stream, transition and framebuffer receipts, and
measurement outputs. The pre-existing source disk and captures remain intact.

## Instrument ranges, dynamics and combined voices

The range probes play stored pitches 25, 26, 30, 31, 32, 36 and 37 in
order. Descriptor A contains a 500 Hz source tone. Descriptor B uses 900 Hz.
Both have root code 28 unless specified. The spectra distinguish the
chosen sample after transposition. An em dash denotes no DAC activity.

| Control | Descriptor order and inclusive range | Result in pitch order |
| --- | --- | --- |
| R9 | A 26–30, B 32–36 | —, A, A, —, B, B, — |
| R10 | A 26–33, B 30–36 | —, A, B, B, B, B, — |
| R11 | B 30–36, A 26–33 | —, A, A, A, A, B, — |
| R12 | A 26–33, B unset | —, A, A, A, A, —, — |
| R13 | A 26–33, B 30–36 with root 34 | —, A, B, B, B, B, — |

The later linked profile selected the last explicit matching descriptor.
The unset descriptor did not cover or fill a gap in the explicit range.
An uncovered pitch was silent for an instrument with explicit ranges.
The result does not establish how an all-unset file or duplicate slot
resolves. The open voice screens showed default slots 1, 2 and 3.

The single-voice gain probe used six successive quarter C4 notes with
indices 0–5. Native RMS values were approximately 55.5, 111, 170, 219, 279
and 338 DAC units. The default unmarked note was closest to index 2 in
amplitude, although the editor showed mf. All six windows were about
414.5 ms. In the semitone probe, ten in-range notes sounded at 505.3,
534.8, 566.4, 600.0, 635.6, 672.6, 756.0, 1,010.6, 1,512.7 and
2,021.2 Hz at stored pitches 28, 29, 30, 31, 32, 33, 35, 40, 47 and 52.
Each quarter step was 27,358 PCM frames at 48 kHz. The active periods varied
by multiples of about 2,487 frames. These data support a block-based
timing hypothesis, with the exact gate and pitch arithmetic still open.

The three isolated voices used the 500, 900 and 1,400 Hz sources respectively.
With starts aligned and each isolated voice offset by at most one frame,
the first 40 ms steady window of each combination correlates 0.9941
and 0.9948 with the isolated sum for two and three voices. The residual RMS
was 28.1 and 38.4 units, compared to mix RMS of 238.9 and 287.6.
This supports additive contributions in the captured DAC path. Residuals
exceed zero, and clipping under higher levels and PSG contribution remain
untested. The successful voice and range runs took 91,628 and 76,036
emulated milliseconds respectively. The first voice attempt missed
the intended editor state for several controls and was excluded.
[Measurements and hashes](../evidence/sampled-music-renderer-20261118.json)

## Independent renderer

```powershell
deskmate-music composition.sng --instruments <snd-directory> --wav composition.wav
```

The Python entry point is `sampled_music.render(score, instruments)` with
parsed `music.Score` and `sound.Sound` inputs. It returns mono 16-bit PCM,
WAV bytes, scheduled note offsets, selected descriptor indices and SND
hashes. Directory input is explicit. Desktop recordings and the slot 255
preview file are skipped. Distinct files claiming the same numbered slot
are rejected. By default, inclusive ranges take the last matching sample.
An uncovered note in a file with explicit ranges keeps its time and emits a
diagnostic. `strict` treats gaps and overlaps as errors.
`nearest-root` explicitly permits a unique nearest-root approximation
through gaps or overlaps. Output rate can be set to 8–96 kHz with
`--rate` and playback is bounded by 12 million output frames.

The independent model is labeled `rsx-dac-approximation-v1`. It uses
measured default slots and DAC-clock scaling, calibrated equal-tempered
pitch, zero-order resampling, end-exclusive sustain wrapping, an empirical
gate with immediate cut and approximate linear gain. Unlooped PCM can
finish early. The score and sample readers retain every original word and
descriptor. The table below records the initial comparison, before the
follow-up changes for articulations and additional score controls.

| Control | Native and independent active duration | RMS, native / independent | First 40 ms onset-aligned correlation |
| --- | --- | --- | --- |
| M11 C4, C5 | 414.5, 362.6 ms vs. 388.0, 388.0 ms | 219 / 223, 216 / 223 | 0.994, 0.994 |
| Marked held C4 | 1,813.5 vs. 1,777.3 ms | 166 / 170 | 0.994 |
| Unlooped held C4 | 494.7 vs. 494.7 ms | 164 / 170 | 0.994 |
| Range and overlap sequence | 362.6–362.7 vs. 388.0 ms | 161–171 / 170–171 | 0.763–0.990 |
| Two simultaneous voices | 1,813.5 vs. 1,777.3 ms | 237 / 240 | 0.980 |
| Three simultaneous voices | 1,813.5 vs. 1,777.3 ms | 286 / 294 | 0.979 |

The measurements compare first-nonzero onset deltas, active-span lengths,
levels and local spectra. Early waveform correlation does not measure
whole-note phase coherence. The region signatures agree through the
tested loop and unlooped tail, and independent range selections reproduce
the five observed starts and two silent gaps in R10. The exported WAV keeps
the planned timeline including silence. Host playback and PSG are outside
the DAC comparison.

The analysis utility takes the exact emulated-millisecond bounds and a
48 kHz renderer WAV. NumPy is required only for this research utility.

```powershell
python tools/experimental/compare_sampled_music.py <baseline-pssj.raw> 39836 42544 <marked.wav>
```

## Sustain endpoints, rates and note connections

The POINTS instrument has isolated PCM values on both sides of each
sustain boundary. After the one-shot 1,099 marker, the steady loop
repeated its marker group every 4,749 or 4,750 DAC frames. The recurring
group included the negative markers at 2,198–2,199 and the positive
markers at 1,100–1,101. It excluded the positive 2,200–2,201 markers.
The period is consistent with 1,100 source frames at the measured
roughly 11.12 kHz. This supports inclusive start and exclusive end.
Intermediate output levels between marked source frames suggest native
interpolation. The independent renderer preserves the observed bounds
with zero-order resampling. Exact interpolation remains open.

RATE55 and RATE22 change the declared rate to 5,500 and 22,000 Hz while
keeping the waveform and root. Both Music captures matched the 11,000 Hz
control within 0.1 Hz on the intro and sustain windows and within one DAC
frame on gate duration. The independent RSX model uses an 11,000 Hz base
for Music. Sound file inspection and direct WAV extraction still follow the
declared rate. Raising only the stored root from 28 to 40 reduced the intro
from about 505.3 Hz to 250.7 Hz. The independent half-rate approximation
predicts 252.7 Hz. This identifies a residual in the native step arithmetic.

TIE9, three same-pitch quarters, had one intro and 1,761.6 ms of active
signal. The independent model plays the full tied score interval of
1,709.9 ms. SLUR9, C4 to G4, resumed the sustain waveform at the new pitch
without replaying the intro. The first span ended 51.9 ms before the new
onset. The independent model uses one measured DAC block for this gap and
retains the sample phase if the same descriptor remains selected. Exact
phase, tie release beyond score time and slurs that cross sample ranges
remain open.

Outside a note connection, `8a00` was a timed silent quarter. The paired
`8e00` and `8600` controls gave silent eighth and half intervals.
Inside a C4 connection, `8a00` gave a silent quarter and the following
note resumed the sustain region without its intro. The interpreter now
preserves these words as rests with continuation flags. Other zero-pitch
word variants still require tests.

## Repeats, endings, pitch flags and markers

RESTATE covered a three-pass repeat between ordinary notes. The first
repeat note on pass one used the prior instrument, dynamic and 100 BPM.
After the in-repeat slot, dynamic and 125 BPM changes, those settings
persisted into the first note of later passes and into the following
section. The onset intervals moved from 27,358 to about 22,384 DAC frames.
RELINE applied a three-pass region to both active voices. NEST played the
three-pass inner repeat on each of the two outer passes.

Both numbered endings precede the repeat end in ALTGOOD. The observed
playback is C4, E4, C4, G4, A4. ALT13 repeats the first ending on passes
one and two and chooses ending 3 on pass three. ALT1 skips the sole
ending on the second pass, then proceeds beyond the repeat.
In an earlier candidate with ending 2 after the repeat end, Music returned
to DOS during playback. The independent interpreter rejects endings
outside a repeat, unbalanced structures and cuts inside a note, rest or
active connection. Expansion limits depth to eight and total work to
131,072 events and slices. The observed nesting was two levels. The
written-order events and offsets are available independently of the expanded
timeline. Repeated playback events retain offsets into the original score.

To regenerate the committed alternate-ending fixture with the marked
instrument, add `--alternate-ending` to the probe command above. Its
108 bytes match ALTGOOD from the disposable run. The fixture documents
native playback acceptance of this synthetic input.

In C and G major, the same stored F4 and F-sharp 4 pitches sounded at
about 672.6 and 714.5 Hz, respectively, with the marked source. Setting
`80h` did not change either frequency. The printed accidental glyphs
differed across the flagged notes. The reader retains the exact accidental
bits and projects pitch from the six pitch bits, without reapplying the
key signature. Score markers A and Z appeared in the native editor. The
paired score without markers gave the same pitches and onset intervals.
Tandy's manual documents markers as editor navigation anchors. The
interpreter preserves their letter and position, and MIDI emits Marker
events. [Tandy Music manual archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/musicsnd.zip)

The sequence trials ran for 51,510, 73,678, 92,212 and 91,464 emulated
milliseconds respectively. [Exact words, capture hashes and comparison windows](../evidence/sampled-music-sequencing-20261118.json)
