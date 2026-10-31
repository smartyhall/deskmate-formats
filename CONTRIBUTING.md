# Contributing

This repository is local staging; publication and the license decision are pending.
Before accepting outside code, the owner must choose a license and contributor
policy. Do not infer that a recommendation grants redistribution permission.

For development, install `.[dev]`, run the portable unittest suite, Ruff's focused
correctness checks, content audit and wheel build. Private fixture tests are opt-in
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
