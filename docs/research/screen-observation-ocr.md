# Local screen observation OCR research

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

This first checkpoint freezes the plan and corpus before calibration selection.
The final comparison and implementation decision follow after evaluation.
