# Contributing

This project documents and independently implements DeskMate formats. Follow
[LICENSING.md](LICENSING.md) for the approved per-file categories.

## Rights and contribution terms

Provide software, CLIs, tests/generators and executable/build tooling under
`GPL-3.0-or-later`. Formal technical specification contributions must be authorized
for `GPL-3.0-or-later OR CC-BY-4.0`: offer **both alternatives** so recipients may
choose either. General documentation contributions must likewise be authorized
for `GPL-3.0-or-later OR CC-BY-SA-4.0`.

Submit only material you have authority to offer on its destination's terms.
A grant under just one alternative does not automatically permit offering both.
Identify third-party material, notices and restrictions for review first. There
is no CLA or copyright assignment: authors retain their rights and attribution.
Preserve existing notices and add accurate notices for new contributions.

Use an adjacent .license sidecar with truthful SPDX-FileCopyrightText and
SPDX-License-Identifier declarations. Copy the format, not another person's
ownership claim. If primary purpose or ownership is uncertain, raise the question
instead of selecting a category arbitrarily. Do not add project copyright notices
to the standard license texts.

## Development and evidence

For development, install `.[dev]`, run REUSE lint and the portable unittest suite,
Ruff's focused correctness checks, content audit and wheel build. Private fixture tests are opt-in
and must never become a requirement for public CI. Keep the original lab regression
coverage intact; do not replace archival byte-equality evidence with a parser-only
check or silently skip missing local fixtures.

For format findings, include application/version, provenance, controlled variable,
before/after hashes, all byte changes and confidence level. Distinguish application
observations from synthetic tests or algorithm hypotheses. Never assume shared
storage between applications. Prefer small evidence-backed additions over empty
frameworks or speculative field names.

Do not attach executables, full snapshots, disk images, credentials, private paths
or personal data to issues/PRs. Provide a minimal independently generated specimen
or a redacted offset table instead. Keep paid services and AI-dependent CI out of
required verification. No automatic publication/release is configured.
