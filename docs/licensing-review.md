# Licensing and provenance review — 2026-10-31

This review applies the owner's approved policy and confirmed default notice:
Copyright (c) 2026 Michael A. Hall. It is not a claim to third-party rights or a
legal determination that every factual or generated element is copyrightable.

## Scope and classification

All existing Python source, CLI, test and generator/tool bytes are preserved.
Individual REUSE .license sidecars apply GPL-3.0-or-later. Build/package/CI/Git
configuration is treated as software. GitHub issue forms and explanatory JSON are
general documentation. There is no catch-all future-file ownership declaration.

Three files are formal technical references, with GPL-3.0-or-later OR CC-BY-4.0:
docs/formats/calendar/CALENDAR_FORMAT.md, docs/containers/README.md and
docs/compatibility.md. The Calendar specification mixes experimental history with
format material, but its primary purpose remains the binary format reference;
it is licensed as a whole under this category. Other notes and reports are general
documentation under GPL-3.0-or-later OR CC-BY-SA-4.0, including parser/writer guides
and Phase III-A's research narrative. These choices preserve structure/results.
New mixed-purpose files need individual review rather than inferred licensing.

## Provenance audit and exclusions

The staged code/docs originate in the independently developed DOSLAB investigation;
source hashes and migration edits are recorded in source-provenance.json. The owner
confirmed the default copyright holder and initial year2026. No OpenAI/Codex
ownership assignment is made. These records support provenance but cannot prove
the legal status of every possible future source or contributor.

No original DeskMate program, media, database, installed snapshot, historical
manual excerpt, third-party source, screenshot or external image is included.
Independently assembled synthetic test-generator source expresses the observed
format; it reads no archived database. Controlled example descriptions and the
fixed internal format signature are not personal records or user credentials.
No credentials, archive access tokens or host-user paths were found in the source
and distribution audit. The original DOSLAB laboratory and archive are untouched.

The only newly incorporated external texts are complete standard licenses from
SPDX's license-list-data repository. They remain byte-for-byte unmodified, with
original Free Software Foundation / Creative Commons notices, no Michael Hall
copyright sidecars, and source URLs/SHA-256 in docs/evidence/license-texts.json.
Root LICENSE exactly duplicates the standard GPL text; later-version permission
comes from project declarations. Standard license texts are exempt metadata
artifacts in REUSE, not independently authored project works.

The previous LICENSE-DECISION.md and earlier verification JSON are retained as
historical evidence of the pre-license checkpoint. Their prior pending state and
MIT recommendation are not current grants. Current README, CONTRIBUTING,
LICENSING.md, package metadata and per-file sidecars agree on the approved policy.
No experiment values, hashes, results or uncertainty classifications were changed.

## Dependencies and third-party compatibility

The package declares no third-party runtime dependencies and uses Python's
standard library. Python itself retains its PSF terms; no interpreter is bundled.
Build/check tooling is executed rather than copied into the project distribution.
The local review reads installed license metadata for build, setuptools, wheel,
Ruff, REUSE and their installed dependencies. Their notices/licenses stay with
their own distributions. No third-party package is relabeled as project-owned.

The build tools build/setuptools/wheel and Ruff identify MIT terms. REUSE identifies
an aggregate metadata expression, Apache-2.0 AND CC0-1.0 AND CC-BY-SA-4.0 AND
GPL-3.0-or-later, for its included components. Its transitive packages include
permissive terms and python-debian GPL-2.0-or-later. Aggregate metadata does not
mean every component has every license; consult original notices if redistributing
the tools. These are development checks, not linked runtime
dependencies or vendored sources. No runtime license conflict was identified.
This is a version-specific metadata review, not a guarantee for future dependency
versions, a license grant from this project, or permission to redistribute private
archives. Recheck dependency terms if code is vendored or packaging changes.

GitHub Actions checkout/setup-python are referenced by pinned upstream revisions;
their implementations are not incorporated in this repository or wheel. Our
independently authored workflow is GPL-3.0-or-later. Action references do not
relicense upstream code. No extra service or publication workflow was introduced.

## Verification and remaining limits

REUSE lint checks SPDX syntax, license-text presence and complete per-file metadata.
Additional checks verify category assignments, standard-text hashes, package SPDX
metadata and included license files/sidecars, unchanged runtime/test/specification
bytes, fixture hashes, portable/private tests and a licensing-only Git diff.
Results are recorded after execution below; local raw logs are ignored by Git.

No included file is currently flagged as having unresolved provenance based on
the available owner confirmation and source record. This does not certify legal
title: if contrary third-party evidence, an omitted contributor, uncertain manual
material or disputed copyrightability emerges, flag it for human review, preserve
the evidence and do not assume the default grants apply. Standard licenses and
external DOSLAB/third-party works remain explicit exceptions.

No CLA, assignment, remote, push, publication or visibility change is introduced.
E15 and other format work were not begun.

## Executed checks

* REUSE6.3.0 lint passed against REUSE Specification3.3: no missing, invalid,
  deprecated or unused license declarations/texts;44/44 files reported covered.
  REUSE automatically exempts license-named files, including historical
  LICENSE-DECISION.md; an independent per-category check verifies all45 authored
  targets and their sidecars, including that historical note.
* SPDX expressions were strictly validated:20software,3formal references and
  22general-documentation files. All use the confirmed holder/year and category.
* Standard-text hashes match their recorded canonical downloads, and root LICENSE
  equals the GPL license-file bytes. No project attribution was put on those texts.
* Portable47tests and private74tests passed on WindowsPython3.13 and3.14.
  All existing runtime/tool/test source and formal specification bytes remain
  unchanged;2,227 watched DOSLAB/evidence/source files and mtimes were unchanged.
* Focused static checks and the source-content audit passed. Package metadata,
  the wheel declares GPL-3.0-or-later and includes all seven declared licensing
  files and sidecars beside all five runtime modules. Packaged standard-license
  bytes match their canonical files. Final archive content and sidecar coverage
  are checked before commit; installed imports and both CLI entry points passed
  on Python3.13 and3.14.

Windows uses REUSE's documented charset-normalizer extra so lint does not depend
on a system libmagic installation; the same extra is declared for development/CI.
charset-normalizer's installed distribution declares MIT terms and is not vendored.
Raw test/lint/dependency outputs are kept in ignored local-results. No license was
assigned to private fixtures, and no experimental result was modified.
