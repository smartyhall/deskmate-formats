# DeskMate Music listening comparison suite

**Status:** Operator-approved design, 2026-11-18. No audio fixtures have
been captured for this suite yet. Implement in the next sampled Music
research campaign. Baseline renderer revision:
`f9fe4f174790b6fa19801d5c107994db8e57f0dc`
(merged PR #118, `rsx-dac-approximation-v1`).

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
where appropriate. No stock/OEM or commercial sample bytes in public audio.

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

## Paired audio and milestones

Suggested layout (actual binary bytes, not just hashes):

- `examples/music-listening/README.md`: direct links to each WAV and
  milestone, listening instructions and reference status.
- `examples/music-listening/suite-v1.json`: musical specification and
  native input paths/hashes (SNG and SND remain in the existing
  application-generated fixture area with its manifest).
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
The scope is eligible project-authored test notes and generated sample
PCM only. Historical scores, OEM instrument recordings, source executables,
raw capture streams, screenshots and other private material are not
authorized for publication. Verify actual content and provenance before
committing. Use the existing licensing categories for contributed synthetic
test content (GPL-3.0-or-later OR CC-BY-4.0, to the extent rights exist);
add accurate adjacent REUSE sidecars and license documentation. Do not
apply that grant to vendor samples or upstream code.

The current repository intentionally ignores/rejects WAV everywhere.
Implement the narrow exception for manifest-listed suite WAVs beneath
`examples/music-listening/v1/` (and explicitly reviewed future version
directories). Keep `.gitignore` exceptions specific to this tree.
Extend the publication audit with a separate strict manifest: canonical
relative paths, allowed names, no symlinks, unique entries, source score
and synthetic bank hashes, provenance, size limits, verified hashes and
valid bounded PCM WAV structure; reject unexpected audio and extra
non-audio RIFF payloads. Add tests for accepted eligible fixtures and
rejected unlisted, malformed, tampered and out-of-scope WAVs. Keep the
default ban on all other WAV, raw captures and commercial inputs. Ensure
all audio and native binary fixtures remain excluded from wheel/sdist;
metadata-only sdist audit must continue to work. Do not use a blanket
force-add or weaken other audit rules. Keep each case/pair small (target
a few MB for the entire five-case milestone, justify larger results).
Use ordinary Git for these small files, not an external service or
hash-only placeholder. Actual listening files and manifests belong in
the reviewed PR. Test installed package behavior without proprietary inputs.

The baseline, suite generator, audit/packaging exception, native capture
procedure and first paired files are the first deliverable of the next
campaign. Thereafter the standing instructions require this suite for
major renderer improvements. See the
[research report](../../docs/research/sampled-music-playback-20261118.md)
and [DAC capture reproduction](../../docs/research/pssj-dac-capture-20261118.md).
