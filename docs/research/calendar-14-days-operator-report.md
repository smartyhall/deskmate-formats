# Calendar 14-day candidate: operator-reported native display

Recorded 2026-11-07 (America/New_York), from the operator's continuation request.
This successor note updates current evidence; the earlier campaign report and
generation receipts retain their historical offline-only results.

The operator reports opening and reviewing the synthetic Calendar in **DeskMate
3.05**, with all **29 appointments over 14 dates** appearing as expected,
including their **displayed alarm states**. This was human-operated native
application inspection, not our parser reading our writer's output. This run
does not repeat that inspection or connect to an emulator.

## Published candidate identity

- File: [sdk-14-days-tool-generated.cln](../../tests/fixtures/application-generated/calendar/sdk-14-days-tool-generated.cln)
- Bytes: **6,144**; SHA-256
  `85ad05d6bf58540e32349bbb559301d36aced164741b03b09b30d63f22d636ac`.
- Appointments: **29**, October 23 through November 5, 2026; **30 PERSONAL
  rows/index entries** including the nonappointment configuration row.
- Source: [committed E02](../../tests/fixtures/application-generated/calendar/e02-86box-historical-match.cln),
  SHA-256 `0af0896163c24c992fa515ddca8c45a31496250d6ba84c9f08e28020a07fe0d9`.
- Expected semantic export: [version-1 JSON](../../examples/calendar-14-days.v1.json).
- Publication: [PR #72](https://github.com/smartyhall/deskmate-formats/pull/72),
  merge `6c742800f88a63551cb5cd5ba9dc9991bc9a7ead`.

The file remains **tool-generated**, despite residing beside native-generated
fixtures. Its generation, source-byte preservation and hash provenance are
unchanged. The report associates the inspection with this candidate; it does
not independently prove the guest-loaded bytes had that hash.

## Scope and limits

Successful native display/read inspection is **operator-reported**. No private
screenshots, machine/build configuration, installation manifest, action ledger,
post-load hash or before/after native save specimen was supplied with the report.
Inspection time and elapsed emulated time are **unknown**, not zero. This offline
reconciliation requests **0 ms** of emulated execution; actual guest-clock delta
is **not measured**. The report does not specify the emulator used.

This establishes neither edit/rewrite persistence nor alarm firing. Unsupported
encodings, arbitrary times, 30-day capacity, allocations, editing/deletion and
other record lifecycle operations remain unvalidated. No codec boundary changes
follow from the report. The strict codec and future sync precision-preservation
policy remain as documented in [interoperability](../interoperability.md).

[Issue #69](https://github.com/smartyhall/deskmate-formats/issues/69) remains open:
the display milestone is achieved, while its broader hash-pinned identity and
controlled-save acceptance criteria remain unmet. A follow-up would pin the
disposable installation and loaded hash, preserve whole-tree before/after
manifests and specify exactly one approved edit/save. That is a proposed
experiment requiring separate authorization, not an action executed here.
