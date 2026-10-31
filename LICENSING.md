# Licensing policy

Approved 2026-10-31. Default independently authored project attribution:
**Copyright (c) 2026 Michael A. Hall**, confirmed by the project owner.
Retain accurate notices for other contributors. This policy assigns no copyright
to OpenAI, Codex or any other party.

## Per-file categories

| Category | SPDX expression | Files |
|---|---|---|
| Software and executable/build tooling | `GPL-3.0-or-later` | All Python libraries, CLIs, tests, synthetic generators and tools; pyproject.toml, MANIFEST.in, CI workflow, .gitignore and .gitattributes |
| Formal technical specifications | `GPL-3.0-or-later OR CC-BY-4.0` | docs/formats/calendar/CALENDAR_FORMAT.md, docs/containers/README.md, docs/compatibility.md |
| General documentation and explanatory metadata | `GPL-3.0-or-later OR CC-BY-SA-4.0` | Other authored Markdown, evidence/provenance JSON and GitHub issue templates/configuration |
| Standard license texts | Original notices/permissions, unmodified | LICENSE and LICENSES/*.txt |

Each independently authored file has an adjacent REUSE-compatible `.license`
sidecar with its copyright and exact SPDX expression. It applies to that file
alone, not dependencies or private evidence. Retain the sidecar when redistributing
the source. No project copyright notice is applied to standard license texts.

Classification follows primary purpose. The Calendar reference is a formal
specification despite historical experiment narratives: it primarily describes
binary structures/encodings. The container reference and compatibility requirements
are formal references too. Phase III-A's report, usage guides, inventory,
architecture, methodology and verification records are general documentation even
where they contain technical tables. No experiment or result was changed to force
these classifications. See [licensing review](docs/licensing-review.md).

## OR means a choice

For a dual-licensed file, each recipient may choose **either** offered license;
they need not comply with both simultaneously. Software has only the GPL offer.
Contributors to a dual-licensed destination must authorize offering **both
alternatives**, preserving the recipient's choice. A GPL-only or CC-only grant
does not automatically authorize that dual offer.

`GPL-3.0-or-later` means GNU GPL version 3 or, at the recipient's option, a later
version published by the Free Software Foundation. LICENSE and its LICENSES copy
contain the complete unmodified standard GPLv3 text. Project declarations and
sidecars supply the **or later** designation.

Under the CC-BY-4.0 option, licensed specification expression may be quoted,
reproduced, translated, incorporated or adapted in academic, archival, commercial
and independent implementation works, subject to that license's conditions. This
option imposes no ShareAlike requirement. The CC-BY-SA-4.0 option for general
documentation has its own ShareAlike conditions for adaptations. Choosing the GPL
alternative means following its applicable conditions. No extra restriction is
added by this explanation.

## Attribution, changes and factual discoveries

Preserve supplied author/copyright, license and applicable disclaimer notices.
When sharing under a CC option, identify the author and supplied source information
where reasonably practicable, identify the chosen license with its text/link, and
indicate changes while retaining prior modification notices, as required by that
license. A citation can identify Michael A. Hall, document title, repository
revision/file, chosen license and modifications. No particular citation format or
endorsement is imposed. Under the GPL option, follow the GPL's notice/source/other
requirements rather than adding CC conditions.

These grants cover copyrightable explanatory expression and rights the licensor
can grant. They do not claim ownership of facts, file layouts, encodings,
mathematical relationships, discoveries or independently developed implementations
as such. Copyrightability and exceptions depend on applicable law. Where legal
permission is unnecessary, this policy creates no new permission or attribution
requirement; scholarly citation remains good practice, not ownership of facts.

## Third-party material and dependencies

No project license grants rights to Tandy DeskMate executables, media, databases,
manuals, assets, trademarks, external images or other third-party works. Require
a documented rights basis before incorporating them. Preserve their original
notices/terms rather than substituting the project attribution. Flag uncertainty
for human review before incorporation or redistribution.

Standard license texts retain their Free Software Foundation / Creative Commons
notices. Exact sources and hashes are in docs/evidence/license-texts.json. DOSLAB
is external, unchanged and not relicensed. Independently assembled synthetic
fixture-generator code is software; no archived database is bundled.

There are no third-party runtime package dependencies; Python's standard library
is used. Development/build/check tools and referenced GitHub Actions retain their
own terms and are not vendored. Their execution is distinct from redistribution.
The licensing review records this distinction and dependency metadata.

## Contributions and checks

See CONTRIBUTING.md. Authors retain copyright and attribution; there is no CLA or
copyright assignment. Add accurate notices for contributions without removing
existing contributor notices. New files need a reviewed category and sidecar:
there is no blanket rule assigning future or third-party material to the default holder.

Run `python -m reuse lint` and the checks in the licensing review. Package metadata
identifies its software as GPL-3.0-or-later; documentation's per-file alternatives
remain intact. Earlier pending-license records are historical repository-preparation
evidence, superseded by this approved policy.
