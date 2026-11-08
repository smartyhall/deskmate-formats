# Database compatibility campaign

Started 2026-11-07 (America/New_York), from verified `origin/main`
`0d8c9e9cb538c65c382cd4f5478048e4397c6bb7`. This is a new progress record,
not a reconstruction of the absent historical PROJECT_STATUS.md.

## Completed

- M0: clean checkout verified; fetched without resetting; dedicated branch
  `codex/database-generation-campaign` created from main. PRs #65 and #66 are
  both open drafts, unmerged; #66 head matches `ff179bd…`. Neither was changed.
- Windows 10 Pro 19045 x64; Python 3.13.17, Ruff 0.17.3, REUSE 6.3.0,
  build 1.6.1 available. Source imports require `PYTHONPATH=src` because the
  installed package is a separate older copy. No dependencies were changed.
- Local preserved empty ADR matches published SHA-256
  `cb890e6d7ba96fafb5a5d3991e208f4de862bee485f6ce32696e989c97d3394c`.
  Historical DOSLAB E15–E19/A01–A04 trees are not located; their published
  byte observations and existing private tests are available. No private suite
  pass is claimed. Existing three public native Calendar fixtures are available.
- Issue #35 inspected: a readiness timeout is not child exit. No launcher or
  native connection is needed for offline milestones; live reproduction deferred.

## Current work

M1 complete: shared bounded structural reader, retaining opaque bytes and avoiding a
universal next-ID rule (the Filer DBCOLS counterexample is decisive). Six new
portable tests passed; unchanged baseline: 284 tests passed in 130.787 seconds.
See docs/research/database-campaign.md. M1 commit `0158cf8` was pushed and
remote-verified; draft PR [#67](https://github.com/smartyhall/deskmate-formats/pull/67).

M2 partial: explicit SDK profile, multipage reading and a generated 14-day,
29-appointment file are implemented and independently checked offline. Existing
default validation is preserved. 42 Calendar-focused and 37 adversarial tests
passed. Actual output and receipt are durably archived privately; hashes are in
docs/evidence/database-campaign.json. Allocation/full-month output remains blocked.
M2 commit `5067da5` was pushed and remote-verified.

M3 partial: ten-page Address Book reader and empty-to-one writer implemented;
eight portable tests and two focused private tests passed. All four A01–A04
whole-file native hashes reproduced. Generated 25 contacts in 25 separate files,
not a multicontact book. See docs/research/addressbook-codec.md. M4/M5 are next.

## Gates and next steps

- M2: explicit SDK-derived ordinary date/time profile and useful 14-day output;
  existing observed-only APIs must keep their validation. Additional-page reading
  is independent of allocation. Header allocation meanings remain unresolved.
- M3: Address Book schema-aware reader and empty-to-one experimental writer;
  multi-contact ordering needs independent native evidence.
- M4/M5: compatibility report and versioned interchange contract after codecs.
- New native runs, RAM access, guest mutations/saves and infrastructure changes
  lack separate operator authorization. Continue offline. No emulator was
  contacted: requested emulated execution **0 ms**; actual guest-clock delta
  **not measured**. No native acceptance of new outputs is claimed.
- Publication of validated campaign checkpoints and a draft PR is authorized by
  this campaign request; merging and unrelated PR changes are excluded.
