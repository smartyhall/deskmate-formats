# DeskMate Music listening comparison suite

The PR #118 baseline includes ten matched pairs. Native tracks are the
Tandy 1000 RSX pre-mix PSSJ DAC contribution. The two tracks in each pair
keep their original levels, which can be quiet at ordinary listening volume.

| Original passage | Synthetic instruments | Tandy instruments |
| --- | --- | --- |
| major scale | [native](v1/baseline-pr118/major-scale-native.wav?raw=true) · [renderer](v1/baseline-pr118/major-scale-renderer.wav?raw=true) | [native](v1/baseline-pr118/oem-major-scale-native.wav?raw=true) · [renderer](v1/baseline-pr118/oem-major-scale-renderer.wav?raw=true) |
| minor scale | [native](v1/baseline-pr118/minor-scale-native.wav?raw=true) · [renderer](v1/baseline-pr118/minor-scale-renderer.wav?raw=true) | [native](v1/baseline-pr118/oem-minor-scale-native.wav?raw=true) · [renderer](v1/baseline-pr118/oem-minor-scale-renderer.wav?raw=true) |
| chromatic scale | [native](v1/baseline-pr118/chromatic-scale-native.wav?raw=true) · [renderer](v1/baseline-pr118/chromatic-scale-renderer.wav?raw=true) | [native](v1/baseline-pr118/oem-chromatic-scale-native.wav?raw=true) · [renderer](v1/baseline-pr118/oem-chromatic-scale-renderer.wav?raw=true) |
| major cadence | [native](v1/baseline-pr118/major-cadence-native.wav?raw=true) · [renderer](v1/baseline-pr118/major-cadence-renderer.wav?raw=true) | [native](v1/baseline-pr118/oem-major-cadence-native.wav?raw=true) · [renderer](v1/baseline-pr118/oem-major-cadence-renderer.wav?raw=true) |
| minor cadence | [native](v1/baseline-pr118/minor-cadence-native.wav?raw=true) · [renderer](v1/baseline-pr118/minor-cadence-renderer.wav?raw=true) | [native](v1/baseline-pr118/oem-minor-cadence-native.wav?raw=true) · [renderer](v1/baseline-pr118/oem-minor-cadence-renderer.wav?raw=true) |

Download or clone the directory and open the [offline player](compare.html)
to restart pairs together and switch between tracks. See the [frozen scores
and banks](suite-v1.json), [capture and measurement manifest](v1/baseline-pr118/manifest.json)
and [reproduction report](../../docs/research/music-listening-v1-20261118.md).
The renderer is `rsx-dac-approximation-v1` at
`f9fe4f174790b6fa19801d5c107994db8e57f0dc`.

## Purpose

Provide a small, easily accessible set of musical examples that can be
listened to side by side, using actual native DeskMate playback and the
independent renderer. Retain the same tests across improvements to pitch,
timing, sample selection, gating, sustain, gain, interpolation and mixing.
This is a listening regression suite as well as experimental evidence.
It is not a substitute for isolated controls or private historical scores.

## Fixed listening material, initial v1

Use short original test sequences, no copyrighted-song excerpts, and at
least three distinguishable, independently synthesized instruments (e.g.,
soft reed-like sustained, bright plucked/decaying, and rounded bell-like).
These timbre descriptions are design targets, not claims to reproduce any
OEM sample. Generate and document the unsigned PCM and sustain regions
deterministically, then verify native Sound saves, pitches, ranges, slots
and playback. Use distinct free instrument numbers (e.g., 9, 10, 11) in
an explicit bank with no duplicates and a shared known rate/root pitch
where appropriate. Retain these measurements as the synthetic bank.

Create the scores within native DeskMate Music where feasible, save and
extract the exact SNG files, document the written events, and use those
same bytes and the same SND bank for both playback paths. A tool-generated
control is acceptable when needed, with native acceptance and provenance
explicitly distinguished from native Save As. Keep the first frozen suite
small: approximately five cases, ideally 5–15 seconds of music each,
at a common quarter-note tempo (100 BPM suggested):

| ID | Musical material | Primary listening comparison |
| --- | --- | --- |
| major-scale | C major, ascending and descending over an octave; sustained instrument | Intonation, attacks, gates, note spacing |
| minor-scale | A harmonic minor, up and down an octave; plucked/decaying instrument | Accidentals, pitch, short-sample decay |
| chromatic-scale | Twelve semitones plus octave, ascending/descending; contrasting instrument | Semitone ratios, octave transposition, timing |
| major-cadence | C–F–G–C (I–IV–V–I), three voices, two quarter beats per chord or longer | Simultaneous voices, consonance, balance, sustain |
| minor-cadence | Am–Dm–E–Am (i–iv–V–i), three voices with contrasting timbres and deliberate dynamic/connection changes | Expressive gain, sustain, repeated attacks and ties |

Freeze exact MIDI-equivalent pitches and voicings, durations, voice and
instrument assignments, dynamics, connections, tempo, native input hashes,
generator revision and machine profile in a versioned suite manifest at
the initial baseline. Use notes inside the verified pitch ranges. Include
one all-same-instrument chord passage and one contrasting-instrument
passage. If needed, adjust initial lengths or native notation to practical
editor behavior, then freeze the actual recorded specification. Do not
silently change it to make a later renderer look better. Any new cases or
altered inputs get a new suite version, retaining v1 for continuity.

### Original Tandy instrument bank — operator direction, 2026-11-18

The synthetic controls are not a substitute for listening to historically
recognizable instruments. Include a second, fixed bank with the genuine
Tandy-supplied Piano, Clarinet, Bells and Cello (where the instrument
identity, source and compatible pitch range are verified). Use the same
musical material, tempo, pitches and articulation as the synthetic bank
where practical, varying instrument assignments explicitly. At minimum,
include an ascending/descending scale and a three-voice chord progression;
prefer counterparts for all five musical cases if the ranges permit.
Freeze exact score bytes, slot assignments, source instrument hashes,
OEM release/machine profile and musical specification as distinct
`oem-<case>` entries in the v1 manifest. Use source archive/member
identification sufficient for an authorized local user to locate the
instruments; do not commit the actual OEM instrument files.

Publish genuine native and independently rendered WAV performances of the
new original musical passages. The operator's stated rationale is that
Tandy supplied the instruments for users to create their own compositions;
audible performances of such compositions are distinct from redistribution
of a sample library. This is an operator-approved intended-use basis,
not a verified express license from Tandy. Inspect available license
notices for terms applicable to musical output, document findings or
absence, and flag concrete conflicting terms for operator review. Do not
treat lack of a located express output license alone as a reason to
substitute synthetic timbres or abandon the comparison. The recordings
must be new musical performances, not raw samples, isolated sample
auditions designed to reconstruct a bank, or repackaged OEM demos.
Do not claim project licensing covers underlying third-party sample rights.
Keep original SNDs, extracted waveforms and isolated sample-level controls
private. Compare and regenerate the OEM musical cases at the same fidelity
milestones as the synthetic bank. Retain both banks, rather than replacing
one with the other.

## Paired audio and milestones

Suggested layout (actual binary bytes, not just hashes):

- `examples/music-listening/README.md`: direct links to each WAV and
  milestone, listening instructions and reference status.
- `examples/music-listening/suite-v1.json`: musical specification and
  native input paths/hashes (eligible original SNG and synthetic SND remain
  in the existing application-generated fixture area with its manifest;
  OEM SNDs are private, identified by provenance and hashes).
- `examples/music-listening/v1/baseline-pr118/<case>-native.wav`
  and `<case>-renderer.wav`, with a milestone manifest in that directory.
- `examples/music-listening/v1/<milestone-id>/`: later paired files,
  comparison receipt and exact renderer revision/hash recorded in the
  manifest. Do not overwrite earlier baselines or confuse output revisions.

Before changing the existing renderer, generate the v1 baseline with the
pinned PR #118 code, including genuine native playback captures. Regenerate
the same set in DeskMate and independently at each major **fidelity**
milestone, not for every unrelated commit. Capture both under a comparable
machine/timing configuration and save them before beginning new work.
If a repeat capture is byte-identical to the immutable earlier native
reference, retain one canonical copy and link its path and hash from the
new receipt, recording that it was re-captured and verified. If genuinely
different, preserve the new capture separately. If native replay is
blocked, retain the prior reference explicitly as such and report the
blocker; never manufacture a new native file from the renderer.

Use uncompressed mono signed 16-bit PCM WAV at 48 kHz as the primary
comparison format, with transparent, reproducible capture cropping and
no independent normalization, fades, EQ, compression, time stretching
or post-processing that hides fidelity differences. Preserve a defined
lead-in/tail and the true playback timeline; document trimming by exact
frame offsets. The initial primary native reference is the pre-mix PSSJ
DAC contribution, not acoustic audio or full emulator output. If a later
capture tap adds PSG or final mixing, retain the comparable DAC reference
and label the additional output separately. Use a stated common listening
gain for both members of a pair only in optional listening copies/player
controls, not in the measurement originals; avoid clipping. Native DAC
levels can be quiet. Note this explicitly in the README. An optional
offline HTML comparison page with local audio controls is encouraged;
plain direct WAV links must remain usable.

Use reproducible measurement scripts to report onset offsets, pitch
errors, active durations, region transitions, RMS/peak, waveform and
envelope correlations where meaningful, and limitations. Keep the raw
uncropped private capture hash, capture recipe and boundaries, machine
and emulator build identities, renderer revision/model/settings, instrument
hashes, exact WAV SHA-256, sizes/rates/frame counts, and test/validation
status in each milestone receipt. For comparisons across milestones keep
alignment, thresholds and metric definitions fixed or identify changes.
Report improvements and regressions; do not claim bit identity from
an envelope correlation.

## Publication and validation

The operator explicitly requests publication of these synthetic WAV pairs.
The scope is original project-authored musical passages, using either
independently generated instruments or actual Tandy-supplied musical
instruments under the operator's intended-use direction above. Historical
scores, OEM sample files, isolated sample dumps, OEM demonstration songs,
source executables, raw capture streams, screenshots and other private
material are not authorized for publication. Verify actual content and
provenance before committing. Apply the existing licensing categories
for contributed synthetic test content (GPL-3.0-or-later OR CC-BY-4.0,
to the extent rights exist) only to rights the project can grant in the
original composition/performance contributions; add accurate adjacent
REUSE sidecars and notices distinguishing any underlying OEM material.
See [licensing policy](../../LICENSING.md). Do not apply that grant to
vendor samples or upstream code.

The current repository intentionally ignores/rejects WAV everywhere.
Implement the narrow exception for manifest-listed suite WAVs beneath
`examples/music-listening/v1/` (and explicitly reviewed future version
directories). Keep `.gitignore` exceptions specific to this tree.
Extend the publication audit with a separate strict manifest: canonical
relative paths, allowed names, no symlinks, unique entries, source score
and instrument bank hashes, provenance class (synthetic or OEM original
musical performance), operator-approved rights basis, size limits, verified hashes and
valid bounded PCM WAV structure; reject unexpected audio and extra
non-audio RIFF payloads. Add tests for accepted eligible fixtures and
rejected unlisted, malformed, tampered and out-of-scope WAVs. Keep the
default ban on all other WAV, raw captures and commercial inputs. Ensure
all audio and native binary fixtures remain excluded from wheel/sdist;
metadata-only sdist audit must continue to work. Do not use a blanket
force-add or weaken other audit rules. Keep each case/pair small (target
a few MB per bank per milestone, justify larger results).
Use ordinary Git for these small files, not an external service or
hash-only placeholder. Actual listening files and manifests belong in
the reviewed PR. Test installed package behavior without proprietary inputs.

The baseline, suite generator, audit/packaging exception, native capture
procedure and first paired files are the first deliverable of the next
campaign. Thereafter the standing instructions require this suite for
major renderer improvements. See the
[research report](../../docs/research/sampled-music-playback-20261118.md)
and [DAC capture reproduction](../../docs/research/pssj-dac-capture-20261118.md).
