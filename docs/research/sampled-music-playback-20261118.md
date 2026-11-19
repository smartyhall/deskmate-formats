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
playback together. A later native Sound Save As reproduced MARK9 byte
for byte.

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
retains the sample phase for compatible sample geometry. Exact phase and
tie release beyond score time remain open.

Outside a note connection, `8a00` was a timed silent quarter. The paired
`8e00` and `8600` controls gave silent eighth and half intervals.
Inside a C4 connection, `8a00` gave a silent quarter and the following
note resumed the sustain region without its intro. The interpreter
preserves these as rests with continuation flags. The later start, end
and triplet controls below extend that result to the other zero-pitch
forms in the historical corpus.

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

## Tempo quantization and native saves

In the editor trial, quarter = 100, half = 50 and eighth = 200 produced
the same 27,358-frame quarter. A second score used quarter = 75,
quarter = 120, half = 75 and eighth = 151. The corresponding quarters
spanned about 37,306, 22,384, 17,410 and 37,306 frames at 48 kHz.
Along with the 125 BPM repeat, the observations fit whole blocks of
1,152 samples at 3,579,545 Hz divided by 161. One block is about
51.8144 ms, and a quarter is the integer number of blocks that fit in
the requested quarter duration. The longest error after onset alignment
was one output frame in the tested tempo sequence. The same clock with
two DAC updates per source frame predicts the observed sustain-pulse
spacing. The divisor and block size are inferred from capture timing and
the emulator's PSSJ clock equation. The guest register writes were not
recorded. Musical ticks, native scheduling time, and the sampled output
frame clock remain separate in the renderer's note plan.

In Music, the scratch UICOMP starts with slot 9 and four quarters
C4, E4, G4 and A4. It uses M11 as the source for `score_probe`, voice
words `7308 ea1c ea20 ea23 ea25`, two empty voices and conductor `2060`.
The native Insert menu added marker A. After moving the cursor away,
Search → Score marker returned to A. Save As produced UIMARK.SNG,
with conductor words `7441 2060` and the voice streams preserved.
Sound played MARK9 and saved it as SND9. Its 5,660 bytes, including
the marked PCM and sustain metadata, match the generated input exactly.
Independent FAT16 and 7-Zip extraction agreed for both outputs.
The editor trial ran for 86,050 emulated milliseconds. [Save identities and tempo measurements](../evidence/sampled-music-tempo-editor-20261118.json)

## Controls during note connections and repeat cuts

Changing the dynamic between connected C4 quarters changed the gain
on the next note boundary. The marked waveform resumed in the sustain
region at pp and again at ff, with first steady-window RMS of about
170, 55 and 333. Changing from slot 9 to slot 10 at the first connected
boundary moved from the 900 Hz source region to slot 10's 1,100 Hz
region without playing slot 10's 700 Hz intro. Both samples share the
same extent and loop coordinates. The renderer keeps phase for this
geometry and starts a new sample for incompatible geometry. Other
release and gain details remain approximate.

Three in-phase ff voices with a nearly full-scale source peaked at
±3,763 DAC units. The measured waveform stayed within the signed 16-bit
range without visible wrap. A duplicate-slot control selected the first
of two files in the test's FAT and filename order. The rename comparison
below distinguishes those orders within the tested folder. The independent
renderer rejects distinct files claiming the same slot.

In separate controls, a repeat boundary fell inside a rest, inside an
entry note or inside an ending note. Each yielded the written-order
notes once, and the editor remained in its playing state past the
expected repeated section. Playback was cancelled before leaving
Music. The interpreter rejects these cuts instead of assuming a
repeat expansion. The two trials ended at 29,818 and 83,752
emulated milliseconds. [Capture boundaries and note windows](../evidence/sampled-music-boundaries-20261118.json)

## Native accidental entry and the remaining zero-pitch words

In a disposable copy of M00 in C major, Music saved F4 and Shift+F
as `EA21 EA62` with Using Sharps selected. Ctrl+U selected Using Flats.
Another F4 and Shift+F saved as `EA21 EAA0`. The unmarked F4 remained
F4 after an accidental, and the last note showed F-flat with encoded
sounding pitch E4. Together with the G-major natural control M14 and the
C/G DAC comparisons, these establish sharp `40h`, flat `80h` and
natural `C0h` as notation metadata on already resolved sounding pitches.
The independent FAT16 and 7-Zip extractions agreed on the native ACCBITS
save. The reader includes its original flags, pitch bits and words.

The auxiliary zero-pitch controls tested the seven remaining serialized
words seen in the corpus. `9500` advances four ticks in silence.
`AA00` and `AE00` end a connection with a quarter and an eighth of
silence respectively. A normal note following the end rest starts its
intro again. `CA00`, `D100`, `D500` and `D600` open a connection with
24, 8, 4 and 3 silent ticks. A following connected note began in its
sustain region, including the case at the start of the score. Following
an unconnected note instead produced an ordinary attack. The independent
model uses the loop entry for a connected attack opened by a silent rest.
The exact native phase at that attack is unquantified.

In the renamed duplicate-slot trial, AAA12 and ZZZ12 occupied different
FAT directory entries and held 500 Hz and 900 Hz source tones. Exchanging
the filenames left the 500 Hz bytes in the earlier directory entry under
ZZZ12. Both captures selected those bytes at about 505.3 Hz. That
distinguishes directory order from filename sorting for this same-folder
case. Search across folders remains open. These two trials ended at
87,628 and 61,294 emulated milliseconds. [Native saves, clock bounds and rest windows](../evidence/sampled-music-rests-accidentals-20261118.json)

## Historical corpus and Workbench

The campaign repeated the audit on all 62 distinct historical scores,
deduplicated by SHA-256. The explicit bank used the retained later OEM
Clarinet, Piano, Bells and Cello for slots 1–4 and the later Marimba for
slot 6. Marimba's four explicit ranges overlap and share the same upper
bound. The bank identifies the comparison configuration. Earlier
Personal DeskMate 2 releases can use different instruments for those
numbers.

| Checkpoint | Structural | All written words interpreted | MIDI exports | Complete sampled outputs at 48 kHz |
| --- | ---: | ---: | ---: | ---: |
| Before the campaign | 62 | 19 | 15 | — |
| Repeat, ending, marker and accidental interpretation | 62 | 49 | 42 | 33 |
| Initial connected rests | 62 | 51 | 42 | 33 |
| Final | 62 | 62 | 51 | 37 |

The 37 complete WAVs contain signal and have every pitch mapped under
the explicit bank. The nearest-root policy produced the same acceptance
count. The first remaining blockers were 11 repeat cuts, 10 missing
instrument bindings and four frame-limit failures. Three of the four
long scores then rendered successfully at 24 kHz, bringing complete
coverage to 40. The remaining long score needs an unavailable slot 5
instrument. Written-word acceptance describes the interpreter's syntax
coverage. Render and MIDI acceptance also require supported execution.

```powershell
$env:PYTHONPATH = 'src'
python tools/experimental/music_playback_inventory.py <extracted-corpus> <explicit-snd-bank>
```

Four representative WAVs remain in the private lab. The comparison
below aligns first activity above 25 PCM units, then correlates RMS
over 50 ms blocks without additional time warping. It compares the
native DAC with the model using the later OEM instruments on both sides.

| Private comparator | Measured activity | First 40 ms waveform correlation | 50 ms RMS-envelope correlation |
| --- | --- | ---: | ---: |
| Earlier two-voice linear score | Native 12.487 s, independent 12.263 s | 0.989 | 0.845 |
| Later OEM two-voice demo | Native 29.741 s, independent 29.563 s | 0.706 | 0.957 |
| Earlier three-voice score with dynamics and an alternate ending | 72.95 s paired prefix of a 105.08 s independent WAV | 0.947 | 0.892 |
| Earlier three-voice repeated score | 49.74 s independent WAV | — | — |

The first two historical captures used 80,620 emulated milliseconds.
The alternate-ending capture ran for 96,746 emulated milliseconds
and reached the tap's 96-second file cap. Its paired window covers the
opening and first ending. The comparison leaves the remaining playback
unmeasured. The native and independent peak 50 ms RMS levels were
405.6 / 416.0, 312.2 / 321.7 and 888.2 / 909.5 DAC units respectively.
Quantizing tempo improved the first and third envelope correlations
from 0.180 to 0.845 and from 0.613 to 0.892. These results measure
useful concordance while leaving audible articulation and mixing
differences. [Aggregate counts and comparison identities](../evidence/sampled-music-corpus-20261118.json)

Workbench exports preserve the original SNG, the complete written
event JSON and available MIDI. Supplying an explicit SND directory also
adds a playable local WAV, a model label, instrument hashes, selected
descriptor indices and omissions. The committed synthetic alternate score
and region-marked instrument were verified through both installed CLI
entry points. [Reproduce the offline bundle](../preservation-workbench.md#reproduce-the-native-demo)

The highest-value continuation is a native repeat-cut experiment on
the affected original scores and a provenance search for slot 5.
Capturing DAC register writes and the PSG path would help separate
native interpolation, gain and gate calculations from the renderer's
approximations. A targeted capture that starts at playback could
cover the full alternate-ending comparator.

## Recurring listening comparisons

The operator requested a permanent, versioned
[synthetic listening suite](../../examples/music-listening/README.md).
Establish paired native and independent WAV references using the current
renderer before changing its behavior, and regenerate that fixed suite at
major renderer-fidelity milestones. This complements rather than replaces
the private historical comparisons above.
