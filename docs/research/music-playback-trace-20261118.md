# RSX playback trace, long WAV output, and historical controls

The [v1 listening baseline](../../examples/music-listening/README.md)
preceded these experiments. The streaming writer preserves PR #118's
acoustic model. Its unpadded PCM matches the published renderer payload
in all ten comparisons, including both banks.

## Direct PSSJ observations

The trace build uses 86Box revision
`855258da966f1594f568350be59e8e1eca082ed1` and the same RSX profile as
the baseline. A private follow-up patch instruments `snd_pssj.c`
and its SN76489 write path. The two affected translation units were
rebuilt with the retained UCRT64 compile flags and linked against the
original object set. The baseline source and executable were preserved.
The follow-up diff SHA-256 is
`fa75457b5d744865dce10a7761a47950da32c0811ccd2565d8c4a8d158026d62`.
The trace executable SHA-256 is
`77ac785fde9992b96625086766048ec2ca4683e42d3287ed1ae5aff83bed5969`.

The lab runner sets three new-output paths through
`DESKMATE_RESEARCH_PSSJ_CAPTURE`, `DESKMATE_RESEARCH_PSSJ_TRACE`,
and `DESKMATE_RESEARCH_PSSJ_GATE`. The presence of the last file
arms recording at the next mixer block. The runner advances 250
emulated ms while the gate is present before sending Alt+P and
advances another 250 ms after removing it to record the end marker.
Guest control uses the authenticated loopback socket. The recorder
caps PCM at 180 seconds and fine trace events at 500,000. Start,
end and close markers carry absolute 48 kHz frame positions. PCM
continues after the fine trace cap. The private archive preserves
the build script, patch, launch and socket receipts, raw streams and
analysis scripts. This tap captures the PSSJ DAC contribution;
it also counts register activity on the PSG path. Final mixed audio
was outside these runs.

In POINTS, RATE55 and ROOT40, direct writes to ports 01E6h and 01E7h
selected divisor 161, and the effective DAC amplitude was 14.
The observed callback gaps were two or three 48 kHz frames, as expected
for 3,579,545 / 161 updates per second. DMA channel 1 terminal counts
were separated by exactly 1,152 completed transfers. This directly
confirms the clock and buffer relationship inferred for PR #118.
Reconstructing the capture from the transferred byte changes held until
the next callback, with signed truncation of
`(byte - 128) * 32 * 14 / 15`, matched every checked pre-mix frame
between the first and last transfer of each control. No PSSJ PSG writes
were observed in those windows. The run elapsed 51,172 emulated ms,
with three gated windows totaling 555,840 frames.

A later 49,316 ms run used two new controls. One stepped through
13 constant source levels at each of the six dynamics. For an input
level of 0, the DMA byte was 121, 114, 106, 99, 92 or 85 from pp to ff.
For input 255 it was 135, 142, 149, 156, 163 or 170. The tested ff
plateaus fit `128 + floor((input - 128) / 3)` for one voice. The
other five levels require more precision than a single symmetric
linear rule.

The second control used 27 pitches and a reproducible dense PCM
pattern with strongly different neighboring bytes. At every pitch
the first 1,023 interior midpoint bytes equaled the floor of the
average of the two neighboring DMA endpoint bytes. This included
octave shifts, where successive endpoints advance by two or four
source positions. Thus Music interleaves averaged **output** values
between selected endpoints, rather than simply interpolating the
original source between every adjacent pair. The first 288 endpoints
for each measured pitch agreed exactly with source indexing at an
integer increment over 256. For stored semitone indices 28–39 at
root 28 the observed increments were 256, 271, 287, 304, 322, 341,
362, 383, 406, 430, 456, 483. The two octave points 40 and 52 fit
512 and 1,024. Several pitches require a buffer-local phase model
after the first portion. A single continuous fractional accumulator
failed to reproduce their later endpoint bytes. These observations
leave complete pitch arithmetic across roots, all dynamics and
connected-note boundaries open.

## Complete private historical comparison

The 96-second boot-to-quit tap used in PR #118 recorded 72.95 seconds
of a three-voice alternate-ending comparator. The gated follow-up
recorded 5,508,480 frames, beginning at absolute mixer frame 1,142,400.
The guest stopped after 140,568 emulated ms. The two private WAVs share
5,070,215 frames, with 104.743 s of above-threshold native activity and
104.605 s for the renderer. Across 105.05 s of equal aligned 50 ms blocks,
the RMS-envelope correlation was 0.876, compared with 0.892 on the
earlier truncated prefix. First-40-ms correlation was 0.948 and
whole-waveform correlation was 0.710. The renderer PCM matches the
earlier renderer for this score. The difference in envelope correlation
covers a longer observation window. Raw data and both historical
recordings remain in the private laboratory.

## Repeat boundary evidence

The [boundary inventory](../evidence/music-repeat-boundaries-20261118.json)
enumerates crossings in all eleven hash-distinct rejected scores.
It records affected events and conductor-only repeat slices. These
slices describe the repeat controls without interpreting the crossing
notes and rests. Four variants share the same written crossing at
tick 12,036 inside notes in voices 1 and 3.

Two originals received a bounded native run. A 24-second region in
each capture strongly matched a later region, using 10 ms RMS blocks.
The alternate-ending case had a correlation of 0.984 at a 59.07 s lag.
The repeat-end case had a correlation of 0.981 at a 36.48 s lag.
These lags are consistent with the respective encoded repeat
sections. Both were still producing changing DAC output after the
114.76-second capture and were explicitly cancelled before exiting
the application. Elapsed emulated times were 142,342 and 142,358 ms.
The evidence establishes repeat re-entry for these real scores even
though an open connection touches the boundary. It leaves the fate
of the affected voice and the full native end state unresolved.
The strict independent player still rejects those boundaries.

## Slot 5 archive result

The archive search inspected Oldskool DeskMate 3.00, 3.02, 3.03 and
3.05 distributions, the supplied RSX and TL/2 inventories, Baldwin's
converter documentation and separate instrument/sample archives.
Baldwin identifies later slot 5 as baritone horn and Personal
DeskMate 2 slot 5 as Cello. The Oldskool `baritone.zip` has an
instrument named `baritone` that declares slot 5. Its exact identity
and the Sax and Violin slot-6 alternatives are in the
[archive catalog](../evidence/music-instrument-archive-20261118.json).
The archive source does not establish that this copy shipped with a
particular release. [Oldskool archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/)

The archived original-format Baritone contains 12,469 PCM frames.
Its sustain indices (17,896 and 18,666) exceed the PCM extent.
Native RSX Music displayed “Instrument Not Found” for slot 5 with
the original bytes in the application directory (33,234 emulated ms).
A private later-format control with identical decoded PCM, valid
descriptor fields and no sustain loop appeared by name. That trial
did not complete playback, including a retry that ended after
33,708 emulated ms. The original bank has no verified RSX slot-5
addition. Compatibility totals use the established RSX instruments
and retained Marimba. 7-Zip decoded seven Sound files from the user-group
archive `snd001.zip`. All seven declare slot 0.

## Interleaved renderer milestone

The explicit `--playback-model rsx-dac-interleaved-v2` option selects
integer source increments, buffer-local phase resets, alternating
endpoint and midpoint transfers, and the observed PSSJ DAC scale.
The measured pattern clears fractional phase at the first boundary
(288 or 576 endpoint samples depending on pitch) and then every 576
endpoints. It reproduced 31,104 endpoint bytes and 31,077 intervening
midpoints across 27 ff attacks on the dense root-28 sample. The
renderer extends this measured pattern to its approximate handling of
other roots and connected notes. Pitch increments outside the measured
set are derived from equal temperament.

V2 keeps the prior note-gate model and uses approximate mixing,
dynamics, connected transitions and sustain phase. Its explicit frame
limit is 12 million. The default CLI and Preservation Workbench retain
the original acoustic model. The larger streaming frame budget
applies to that original model.

All ten cases were replayed in four fresh, disposable RSX runs,
using the exact frozen v1 scores and banks. Nine fresh native crops
matched their prior WAV bytes. The synthetic minor cadence uses a
new native WAV. Its native crop differs from the first baseline run
and is measured independently at this milestone.

| Bank and passage | PR #118 waveform correlation | Interleaved waveform correlation | PR #118 → interleaved envelope |
| --- | ---: | ---: | ---: |
| Synthetic major scale | −0.319 | 0.827 | 0.731 → 0.724 |
| Synthetic minor scale | 0.843 | 0.986 | 0.993 → 0.992 |
| Synthetic chromatic scale | 0.686 | 0.840 | 0.851 → 0.851 |
| Synthetic major cadence | 0.204 | 0.947 | 0.952 → 0.952 |
| Synthetic minor cadence | 0.152 | 0.898 | 0.937 → 0.937 |
| OEM major scale | −0.010 | 0.888 | 0.925 → 0.927 |
| OEM minor scale | 0.681 | 0.958 | 0.953 → 0.952 |
| OEM chromatic scale | 0.559 | 0.865 | 0.867 → 0.865 |
| OEM major cadence | 0.591 | 0.987 | 0.998 → 0.999 |
| OEM minor cadence | 0.220 | 0.918 | 0.931 → 0.934 |

The comparisons use the baseline onset rule and 50 ms RMS windows.
The largest envelope regression is the synthetic major scale, where
note durations are still approximate. These are correlations on
aligned recordings at original levels. [Exact metrics and identities](../../examples/music-listening/v1/interleaved-v2/manifest.json)

## Bounded streaming output

`deskmate-music --wav` now streams 32,768-frame PCM blocks. The
existing 12-million-frame default stays in place. An explicit
`--max-frames` value allows up to 96 million frames. The default
in-memory API keeps its previous limit. Integer sample phase,
sustain loops, envelope approximations and mix arithmetic carry
across output blocks, with byte equality verified against the
ten pinned baseline renderer payloads.

At 48 kHz, the streaming inventory with the established bank yielded
40 complete audio outputs of 62 scores, up from 37 under the old
12-million-frame limit. The three additional scores previously
required a 24 kHz run. Structural and written-word coverage were
62 of 62 and MIDI output remained 51 of 62. The 22 remaining
audio blocks were 11 repeat-boundary cases and 11 missing
instrument bindings across both sample policies once the longer
output budget was applied.

An installed-style CLI run with the larger frame budget wrote and
reopened a 40,435,178-byte private historical WAV. Its 20,217,567
frames span about 421.20 seconds at 48 kHz.
The [corpus inventory](../evidence/music-streaming-inventory-20261118.json)
records the bank identities, rate and policy counts.
