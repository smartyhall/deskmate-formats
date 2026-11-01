# Local screen observation OCR research

Held-out field exact match was **44.3% for whole-image Tesseract**, **67.2%
for selected field crops**, and **32.8% for raw Windows OCR**. Critical date/time
fields failed. Local OCR is useful as supplementary evidence extraction on these
fixed layouts, but this benchmark does **not** justify a public observation helper
or replacing routine direct screenshot verification. No helper was implemented.

## Scope and experimental plan

This independent branch starts at main
`6cdb0f29b02ca09110f61358ddae3759064ec9bd`. E19 and Address Book Phase II
worktrees and commits are preserved. This is offline observation of existing
evidence: no guest input, database mutation, emulator reconfiguration, AUTOTYPE
investigation or repeat of the unsuccessful Ctrl+F5 extraction.

The private evidence root is
`DOSLAB/EXPERIMENTS/RESEARCH/screen_observation_ocr`. Proprietary screenshots,
transcripts, manifests with host paths and derived images remain there.

Before implementation, `PLAN.md` specified 27 historical screenshots, a frozen
18/9 calibration/evaluation split, raw Tesseract PSM 3/6 baselines, a bounded
preprocessing matrix and field-based comparisons. Configuration selection uses
calibration exact match, then character error rate. Held-out results must not
change selected parameters. No claim of population accuracy follows from this
small historical convenience sample.

The implementation gate is at least 95% held-out exact match for a useful field
family, no wrong non-abstained critical dates/phones in that family, validated
geometry and explicit uncertainty. Failure means publish findings without a new
automation interface. OCR and pixel checks never authorize saves or edits.

## Inventory and corpus checkpoint

Inventory found 650 existing PNGs. The selected 27 comprise ten Calendar, ten
Address Book and seven controls/dialogs. Dates, schedule headings, appointment
text, scrolling descriptions, names, telephone variants, entry counts, labels,
empty fields, masks, selection, AM/PM controls and save confirmations are included.
No verified checked-alarm positive was found in this selected corpus.

The frozen `manifest.json` SHA-256 is
`316daf56e8ee53cce7989bf3719fd54aef9a27883b9208ed605151f3df0cc1db`.
It records source/hash/dimensions, application/profile, source and viewport
rectangles, expected text, verification status, visual annotations, split and
hashed independent provenance. Reference values come from preserved action
records, input/outcome reports and independent image inspection, before OCR.
The review sheets and `CHECKPOINT_1.md` preserve that checkpoint.

Original capture uses System.Drawing `CopyFromScreen` over the virtual desktop.
Later `capture_observation.ps1` additionally records a `GetWindowRect` crop,
checks PID creation identity, rejects minimized/off-desktop windows and preserves
both images. These existing methods are unchanged; screen occlusion is still a
capture risk. Selected desktop images are 1280×960 with guest origin (320,261);
window images are 656×539 with guest origin (8,51). Both guest viewports are
640×480. Origins and field rectangles were independently inspected before OCR.
Coordinates are half-open source pixels. Those two offsets are evidence for
these captures, not universal profiles for future windows or DPI settings.

Unselected images include duplicate desktop/window pairs, DOS/debugger states,
redundant sequences and less-documented captures. Selection precedes OCR.
Unverified wrapped text and untranscribed menu items are excluded explicitly.
Visible scrolling substrings are distinguished from full stored descriptions.

## Local engines and dependencies

Tesseract was absent from PATH and normal installation locations. The isolated
Windows executable is `v5.5.3.20260724`, Leptonica 1.87.0. The binary came from
the [UB Mannheim distribution](https://github.com/UB-Mannheim/tesseract/wiki)
linked by the [Tesseract installation documentation](https://tesseract-ocr.github.io/tessdoc/Installation.html).
The installer was extracted using the existing 7-Zip; it was never executed.
There were no registry, PATH or system installation changes. Only the standard
English Tesseract recognition data was supplied from the upstream
`tessdata_fast` 4.1.0 tag; no large OCR framework or extra runtime was introduced.

| Artifact | SHA-256 |
|---|---|
| Windows installer | `bee9e3434bd94fd65387d9be28cd467a41f61b1275383b55b0f59a1331270ae4` |
| tesseract.exe | `c66f0f12ed76f6aa455dac97684bbc86756d6a732380bee09122454cfda3f420` |
| eng.traineddata | `7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2` |

The existing Codex runtime provides Python 3.12.14 and Pillow 12.3.0 for private
image analysis; existing project Python 3.13 environments provide portable tests,
Ruff and REUSE. No Python package was installed. Windows PowerShell's existing
WinRT bridge exposes Windows.Media.Ocr and the installed en-US recognizer.
An elevated capability inventory was unavailable; no elevation was attempted.

The [documented Tesseract CLI](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html)
provides text/TSV output and page segmentation. All runs retain complete TSV
page/block/paragraph/line/word boxes, word confidence, stderr and exact parameters.
Confidence values are engine scores, not calibrated correctness probabilities.

## Evaluation definitions

Field exact match collapses whitespace only; case and punctuation remain
significant. CER is total Levenshtein edits divided by nonempty reference
characters. Missing means no recognized text in a nonempty field. False positives
mean recognized text in an independently verified empty field. This is a field
false-positive rate, not an invented-text rate for a completely transcribed
screen. Whole-screen extraction assigns words by their source-coordinate centers;
it never searches for expected answers in the output.

Processing measurements separate individual fresh-process latency from batched
throughput. Every result remains independently unverified. Manual-review rates
must not be inferred from Tesseract confidence alone. No token usage, API charges
or credit savings are measured by this experiment.

The first committed checkpoint froze the plan and corpus before calibration
selection. The completed comparison follows.


## Bounded calibration and frozen selection

There are **172 verified fields**: 111 calibration and 61 held-out, including
29 verified-empty fields. Calibration images divide 7 Calendar / 6 Address Book /
5 controls; evaluation divides 3 / 4 / 2. Held-out groups include the final E19
segment and A02/A04 form sequences. A04's save prompt is calibration while A04's
form images are evaluation: shared-session exposure is an explicit limitation.
Fixtures, fonts and layout are shared across splits. This is a frame holdout,
not an independent application-version, font, resolution or unfamiliar-value test.

Ten whole-screen recipes and five field recipes were compared. Except raw and
raw-viewport controls, preprocessing uses 2× nearest-neighbor scaling. Gray means
Pillow grayscale; threshold means grayscale >=128; contrast factor is 2; invert
means RGB inversion. The guest-viewport controls were added during calibration
after observing host-text contamination, before parameter selection or held-out
Tesseract runs. Failed original-image results were retained. There was no further
search, border removal, whitelist, spell correction or post-evaluation tuning.

| Calibration recipe | Exact / 111 | CER | False positives / 21 blanks |
|---|---:|---:|---:|
| roi_gray_psm6 | 76 | 0.1171 | 0 |
| roi_invert_psm7 | 59 | 0.1517 | 19 |
| roi_nearest_psm7 | 62 | 0.1504 | 16 |
| roi_raw_psm7 | 61 | 0.1258 | 16 |
| roi_threshold_psm7 | 63 | 0.1504 | 13 |
| whole_contrast_psm6 | 30 | 0.7657 | 0 |
| whole_gray_psm6 | 32 | 0.5869 | 0 |
| whole_invert_psm6 | 34 | 0.5758 | 1 |
| whole_nearest_psm11 | 40 | 0.5832 | 0 |
| whole_nearest_psm6 | 33 | 0.7645 | 2 |
| whole_raw_psm3 | 50 | 0.3847 | 0 |
| whole_raw_psm6 | 45 | 0.4797 | 1 |
| whole_threshold_psm6 | 37 | 0.5253 | 1 |
| whole_viewport_psm3 | 40 | 0.6276 | 0 |
| whole_viewport_psm6 | 40 | 0.6979 | 2 |

Selection by exact match, then CER, chose raw original-image **PSM 3** and
grayscale 2× field crops **PSM 6**, both English OEM 1. Their configuration was
frozen before the nine held-out Tesseract images were run once. Raw PSM 6 is
retained as the second baseline: evaluation 12/61 exact, CER 0.9085, 46/53 missing,
0/8 empty-field false positives. Windows OCR was a separate fixed raw baseline,
with no parameter tuning. It supplies word rectangles but no confidence values.
The Windows.Media.Ocr DLL version is **10.0.26100.9278** on Windows 11 build 26300,
using the installed en-US recognizer; the recognizer-data revision is not exposed.

Reproduction uses the documented CLI, with a file list for batch runs:

```text
tesseract <source.png-or-input-list.txt> <private-output-base> -l eng --oem 1 --psm 3 txt tsv
tesseract <preprocessed-crop-list.txt> <private-output-base> -l eng --oem 1 --psm 6 txt tsv
```

Every crop is mapped back to its original source coordinates. No expected value
is passed to the OCR engine. All outputs, complete TSV hierarchy, text, stderr,
transformed images, commands and failures remain in private evidence. Windows
raw JSON retains full text, lines and word rectangles with null confidence.

## Exact results by application and screen category

The cells below report exact fields, CER, missing/nonempty fields and
false-positive/empty fields. A dash means no verified empty field in that group.
All percentages use the stated field counts, not a claim of full-screen accuracy.

| Split / method | Category | Exact match | CER | Missing | Empty-field FP |
|---|---|---:|---:|---:|---:|
| calibration / whole | all | 50/111 (45.0%) | 0.3847 | 37/90 | 0/21 |
| calibration / whole | calendar | 10/40 (25.0%) | 0.3542 | 11/37 | 0/3 |
| calibration / whole | addressbook | 37/50 (74.0%) | 0.3036 | 10/32 | 0/18 |
| calibration / whole | controls | 3/21 (14.3%) | 0.5000 | 16/21 | — |
| calibration / regions | all | 76/111 (68.5%) | 0.1171 | 2/90 | 0/21 |
| calibration / regions | calendar | 17/40 (42.5%) | 0.1566 | 2/37 | 0/3 |
| calibration / regions | addressbook | 44/50 (88.0%) | 0.0595 | 0/32 | 0/18 |
| calibration / regions | controls | 15/21 (71.4%) | 0.0877 | 0/21 | — |
| calibration / Windows raw | all | 31/111 (27.9%) | 0.3835 | 36/90 | 0/21 |
| calibration / Windows raw | calendar | 5/40 (12.5%) | 0.3904 | 14/37 | 0/3 |
| calibration / Windows raw | addressbook | 20/50 (40.0%) | 0.5476 | 12/32 | 0/18 |
| calibration / Windows raw | controls | 6/21 (28.6%) | 0.2500 | 10/21 | — |
| evaluation / whole | all | 27/61 (44.3%) | 0.3249 | 17/53 | 0/8 |
| evaluation / whole | calendar | 4/17 (23.5%) | 0.2884 | 3/17 | — |
| evaluation / whole | addressbook | 21/34 (61.8%) | 0.3038 | 11/26 | 0/8 |
| evaluation / whole | controls | 2/10 (20.0%) | 0.5000 | 3/10 | — |
| evaluation / regions | all | 41/61 (67.2%) | 0.1098 | 0/53 | 0/8 |
| evaluation / regions | calendar | 5/17 (29.4%) | 0.1349 | 0/17 | — |
| evaluation / regions | addressbook | 30/34 (88.2%) | 0.0380 | 0/26 | 0/8 |
| evaluation / regions | controls | 6/10 (60.0%) | 0.2031 | 0/10 | — |
| evaluation / Windows raw | all | 20/61 (32.8%) | 0.3547 | 18/53 | 0/8 |
| evaluation / Windows raw | calendar | 2/17 (11.8%) | 0.3302 | 6/17 | — |
| evaluation / Windows raw | addressbook | 12/34 (35.3%) | 0.4367 | 9/26 | 0/8 |
| evaluation / Windows raw | controls | 6/10 (60.0%) | 0.2344 | 3/10 | — |

For the selected region method, calibration CER is **95/811 edits/characters**;
held-out CER is **48/437**. Held-out whole-image CER is **142/437** and Windows
raw CER is **155/437**. On nonempty evaluation fields alone, regions match
**33/53 (62.3%)**; the eight correctly empty fields increase overall exact match.
Region missing rate is 0/53 and empty-field FP rate 0/8 on evaluation. Those zeros
do not mean the recognized values were right: 20/61 fields still differed.

| Selected-region field family | Calibration exact | Evaluation exact |
|---|---:|---:|
| Calendar date heading | 3/3 | 1/1 |
| Add Event date | 0/4 | 0/2 |
| Find Date value | 0/2 | 0/2 |
| Start time | 0/4 | 0/2 |
| End time | 0/4 | 0/2 |
| Visible description / empty description | 5/7 | 0/2 |
| First Name | 6/6 | 4/4 |
| Last Name | 6/6 | 4/4 |
| City | 6/6 (all empty) | 4/4 (two populated) |
| Work Phone | 6/6 (four populated) | 4/4 (three populated) |
| Entry count | 2/6 | 2/4 |
| Selected contact label | 0/2 | 0/2 |
| Dialog title | 0/8 | 0/4 |

Successful cases include schedule headings, names, the fictional phone values,
City and several button/field labels. The three populated held-out phone fields
repeat one value already represented in calibration; this cannot establish
general telephone recognition reliability. All ten Title fields were empty.

Failures include a zero count rendered as `Qo`, `11/14/2026` recognized as
`1114/2026`, a leading `j` on `11:00`, and `12:00` recognized as `te Oe`.
Long descriptions gained border-like prefix characters and digit substitutions.
Window borders/dither patterns caused extra characters on every tested dialog
title. Selected contact labels gained a space after the comma: a strict exact
failure with a different practical consequence from losing a date slash.
No post-hoc normalization was added to improve the score. A full-screen
hallucination or duplication rate is not measurable from a partial transcript;
host text, inserted characters and the blank-field failures above are retained
as observed examples, not an exhaustive invented-text census.

## Deterministic visual-state checks

The 27-image corpus plus **two separately hashed DOS negative controls** were
tested. DOS captures have a 720×540 interior in a 736×599 window: the detector
examines its upper-left 640×480 from checked origin (8,51), without resizing.
This supplies negative coverage, not positive cross-resolution validation.
Templates come only from calibration images. Fixed source-relative
viewport anchors use mean absolute RGB difference /255, accepted at <=0.04.
Find Date highlight uses the fraction of red pixels (R>80,G<40,B<40) in
[300,212,388,230], accepted at >=0.45. AM selection uses yellow-pixel fraction
(R>120,G>120,B<80), accepted at >=0.10 in start [360,190,384,204] or end
[360,230,384,244]. All rectangles are half-open guest-viewport pixels.

Template anchors: application header [210,8,400,26], Find Date title
[280,174,368,194], Add Event title [272,118,368,136], save-confirmation title
[216,164,432,184]. These checks depend on the verified 640×480 layout, palette
and viewport origin. They do not localize an arbitrary window or infer focus.

| Detector | Calibration TP / TN / FP / FN | Evaluation TP / TN / FP / FN |
|---|---:|---:|
| calendar | 9 / 10 / 0 / 0 | 5 / 5 / 0 / 0 |
| addressbook | 9 / 10 / 0 / 0 | 4 / 6 / 0 / 0 |
| find_date | 2 / 17 / 0 / 0 | 2 / 8 / 0 / 0 |
| add_event | 4 / 15 / 0 / 0 | 2 / 8 / 0 / 0 |
| save_confirmation | 2 / 17 / 0 / 0 | 0 / 10 / 0 / 0 |
| whole_highlight | 1 / 1 / 0 / 0 | 1 / 1 / 0 / 0 |
| start_am | 4 / 0 / 0 / 0 | 2 / 0 / 0 / 0 |
| end_am | 1 / 3 / 0 / 0 | 0 / 2 / 0 / 0 |

No false positives occurred on these tested images. Highlight evaluation is only
one highlighted and one nonhighlighted field. Start-AM has no negative example;
held-out end-AM has no positive; save confirmation has no held-out positive.
**Checked versus unchecked checkbox detection is unknown**, because all verified
alarm examples are unchecked. Recognizing a familiar application header cannot
prove an unobscured or safe application state. Known menus/overlays and unseen
layouts still need direct vision. Templates do not supply general focus detection.
Mean image-loading plus deterministic-check time was 0.0563 seconds per image.

## Processing time, payload and practical usefulness

| Method | Calibration seconds / image | Evaluation seconds / image | Evaluation result bytes |
|---|---:|---:|---:|
| Tesseract whole | 5.106 | 1.822 | 72,625 |
| Tesseract regions | 0.622 | 0.597 | 18,348 |
| Windows raw | 0.943 | 0.529 | 465,503 |

Timing methods differ. Raw Tesseract calibration is 18 individual fresh-process
calls (91.902 seconds total), including image writing and OCR startup/execution,
excluding subsequent TSV/JSON parsing. Other Tesseract results amortize one
file-list batch across its inputs plus measured preprocessing. Evaluation region
OCR took 4.773 seconds for 61 crops; complete private batch
artifact generation took 6.252 seconds, or
0.695 seconds per screenshot. Whole-image evaluation
OCR took 15.351 seconds for nine images. Per-category
batch timings are allocated by input-page count, not measured individual latency.
Windows keeps one engine alive: its first image took 5.595 seconds including
warmup, while later images were faster. These are single-run measurements on a
shared VM, not isolated latency distributions or an end-to-end workflow speedup.

Result bytes are UTF-8 JSON text/word/coordinate/parameter representations, summed
across nine evaluation images; Windows numbers use its pretty-printed JSON and
line records, so payload size is not an engine-intrinsic comparison. Evaluation
source PNGs total 2,285,584 bytes. Region outputs total 18,348 bytes, but were not
used to replace screenshot verification. No token consumption or purchased-credit
reduction was measured. No new acceptance rule was validated.

The VM reports six logical processors and approximately 16 GiB RAM. Tesseract
runs requested `OMP_THREAD_LIMIT=1`. One sampled process had a 97.7 MiB lifetime
peak working set at observation; this is not a full-benchmark peak or a Windows
OCR memory measurement. Setup added an isolated 26,573,224-byte binary archive
and standard English data, used existing Pillow/WinRT/7-Zip, and required explicit
viewport/field annotations. This manual geometry and evidence work is operational
overhead and prevents extrapolating local runtime into time or monetary savings.

**All 27 screenshots (100%) still require direct inspection for application-state
verification. Zero routine direct screenshot inspections were demonstrated as
replaceable.** Exact reference matches numbered 76/111 calibration and 41/61
evaluation fields for regions; those are benchmark comparisons, not live verified
application state. There were no engine execution failures in the completed
matrix. Operationally the proposed automation decision abstains on every screen;
that 100% abstention is separate from the measured OCR missing-field rate.

## Decision, integration and next priorities

No reusable public helper, profile API or production dependency was introduced.
The overall implementation gate failed. Perfect scores on repeated names/phones
and empty fields are too narrow to establish reliability, while critical dates
and times demonstrably fail. The recommended role is **supplementary evidence
extraction on independently verified fixed regions**, with direct vision retained.

For offline research, preserve and hash an existing capture; independently verify
its viewport and intended field rectangle; use the frozen grayscale/2×/PSM6
recipe; retain original text/TSV and source-coordinate boxes; compare against
independent experiment evidence. Mark every recognized value unverified, and
missing/ambiguous observations unknown. Confidence never proves correctness.
Inspect dates, times, counts, long descriptions, focus/selection, confirmation
dialogs, unexpected screens and every consequential edit/save/delete decision
directly. A matching pixel template or OCR value never authorizes submission.

The next useful engineering work is a separate, bounded calibration study of
frame-free interior crops for masked dates/times and a larger independently
documented set of unfamiliar names/phones. Keep fresh session groups wholly held
out, include checked alarms and both radio states, changed geometry/DPI, overlays
and deliberately incorrect screens. Do not strip suspected border characters or
normalize dates without new independent evaluation. Reconsider a narrow helper
only if those critical fields meet the gate; do not expand GUI automation.

## Private reproducibility and publication checks

`inventory.py` / `image_inventory.json` inventory the historical PNGs;
`build_manifest.py`, `freeze_manifest.py`, review sheets and `CHECKPOINT_1.md`
record independent ground truth and exclusions. `benchmark.py` preserves the raw
baseline; `batch_benchmark.py` runs the bounded matrix. `windows_ocr.ps1` uses the
already installed WinRT recognizer. `summarize.py freeze` selects configuration;
`final_analysis.py` produces the comparisons, error audit, integrity record and
no-go decision. Commands use the existing private runtime, not project production
dependencies. `runs/`, `batches/`, `windows_raw/`, `visual_results.json`,
`field_families.json`, `efficiency.json`, `source_integrity.json` and
`CHECKPOINT_2.json` retain all results. Two source-negative hashes are in visual
results. All 27 source screenshot hashes were reverified unchanged afterward.

| Checkpoint artifact | SHA-256 |
|---|---|
| Frozen configuration | `e419a121520d99ceeb6f3d8cf2ea4492fbf4a9c443d1f2426e584b6093a8ecb1` |
| Summary JSON | `c5b2945752b5e2d354b4fb6ab6e087723518a2e461e34b05371222cafd9d4875` |

Five private synthetic scoring tests and **65 portable repository tests** passed
under existing Python 3.13. Ruff passed; REUSE passed **72/72** declarations;
the source privacy/content audit passed **150 files**, including a subsequent
audit of built archives. Wheel and sdist builds passed without installation into
the laboratory environments. Source images and the existing E19/Address Book
Phase II worktrees were preserved; exact checks are in the private publication
checkpoint. Work is published only on `research/screen-observation-ocr`.
No private screenshots, derived images, databases,
OCR binaries or host paths are distributed in this branch.
