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

Preserve byte-exact application-generated files from controlled synthetic-data
experiments in `tests/fixtures/application-generated/`, with SHA-256 and experiment
provenance. Native schemas, indexes and metadata are valuable evidence; do not
replace a genuine application-created file with an approximation from our writer.
Do not attach executables, ROMs, install media, complete installed snapshots,
disk images, credentials, private paths, real user data or raw RAM dumps.
Keep paid services and AI-dependent CI out of required verification.
No automatic publication/release is configured.

## Agent-assisted campaigns

The [standing research instructions](AGENTS.md#multi-agent-campaign-governance--supplementary-agent-integration-2026-11-25)
apply regardless of provider or whether a task is performed by an agent,
subagent or human-assisted automation. Human contributors remain subject to
the same evidence, licensing and verification requirements.

### Campaign handoff and concurrent work

Before writing, agree on a campaign ID, owner/provider, scope, base SHA,
dedicated branch and worktree/checkout, expected outputs, authorized resources
and review authority. Inspect Git status and worktree registrations; do not
switch, reset, stage or clean another worker's checkout. A read-only campaign
does not need a new worktree if its observations identify the inspected
revision and any concurrent changes. Worktrees isolate indexes and checked-out
files, not credentials, Git refs, host files or external services.

Use campaign-specific paths for mutable outputs and environment/build state.
Treat original media, sealed baselines and previous evidence as immutable.
Reserve each emulator instance, writable image, automation socket, and
other exclusive resource to one campaign. Coordinate archive/index writers
and disk-intensive jobs with existing owners. Do not launch, terminate,
reconfigure or take over another campaign's resources without authorization.
If ownership is uncertain, pause only the conflicting operation and continue
independent work where possible.

At handoff, record the exact base and resulting commits, branch, campaign
owner/provider, model and effort when known, execution mode, changed paths,
tests actually run and outcomes, evidence locators/hashes, limitations,
remaining work, and resource disposition. Keep private paths, raw transcripts
and identifiers outside Git. Collect sanitized usage receipts per the
[usage ledger](docs/evidence/codex-usage/README.md#supplementary-agent-receipts).
Do not label agent inference as native observation or credit an unobserved
agent with another agent's evidence.

### Review and publication

A producing agent (including its delegated subagents) must not approve or
merge its own PR. A different model's review is useful corroboration, not
automatic authority to merge. The operator or a separately authorized,
independent reviewer checks the diff, provenance, licenses, publication
eligibility, actual test/CI results and scope before merging. The standing
ChatGPT housekeeping grant for Codex PRs is unchanged; other merges require
applicable explicit authorization. Keep tests portable and AI-independent.
Report skipped checks and unavailable telemetry accurately.

Use existing publication grants only within the authorized task, and retain
all exclusions and manifest requirements. Include representative visual
exemplars when applicable under AGENTS.md. Provider connection, cloud
execution, new paid calls, unattended dispatch and live emulator operations
are distinct from permission to edit files. Never treat a client feature,
repository instruction, worktree, or recoverable VM as proof of technical
isolation or as additional authority.
