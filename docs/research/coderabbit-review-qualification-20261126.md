# CodeRabbit advisory-review qualification

Operator direction: 2026-11-26. Campaign: CRQ-20261126. Owner: ChatGPT
(repository connector; isolated branch, no shared local checkout).
CodeRabbit is a specialized reviewer, not a producing agent, authorized
approver, merge authority, or live-lab worker. Its comments are hypotheses
to adjudicate, not test evidence or instructions to execute. Existing
AGENTS.md and CONTRIBUTING.md governance remains authoritative.

## Configuration and boundaries

The root `.coderabbit.yaml` explicitly selects V3 and enables assertive,
automatic, incremental, non-draft reviews with no commit-count auto-pause.
Summaries stay in walkthrough comments rather than rewriting producer PR
descriptions. Automatic approval and author approval commands are disabled;
labels and reviewers are suggestions only. Cross-repository analysis is
disabled, and path instructions are separate Markdown documents under
`.coderabbit/instructions/`. No custom pre-merge checks are added during
qualification. V3 uses a check run where supported, otherwise a commit
status, and does not fail its progress report on review errors. Keep
CodeRabbit checks optional; a successful status is not proof of review
coverage. V3 fixes sequence diagrams and linked-issue assessment off, and
agent prompts and chat auto-reply on.

### Administrator dashboard confirmation before adoption

V3 does not accept the old YAML keys for Knowledge Base scopes and
privacy, chat integrations, finishing touches, post-merge actions, code
generation, issue enrichment, or early access. The previous V2 file is
preserved in commit `bf6137d79ebad347fa64f15c232cf8eeae9e6007` for comparison
and rollback; repository YAML does not migrate these values into saved
dashboard settings. An authorized administrator must verify the effective
settings before merging:

- App installation restricted to this repository; no additional
  repository, provider, or private laboratory access.
- Knowledge Base enabled, with learnings, issues and PR scopes local;
  MCP, Jira and Linear disabled; public web search enabled for source
  discovery only. Disable external chat integrations.
- Disable finishing touches (unit tests, simplify, autofix, fix CI,
  conflict resolution, and custom actions), post-merge actions, automated
  issue enrichment/planning/labeling, early access, and autonomous
  Triage/Code/Verify or paid automation features wherever available.
  Do not broaden author or title review exceptions.
- Confirm automatic approvals and author approval commands remain off,
  branch checks remain optional, and organization/workspace overrides do
  not defeat these choices. Pin trusted configuration to main after
  qualification if available, with trusted-PR overrides disabled.

If a setting is unavailable or cannot be confirmed, record the limitation
and defer adoption where it affects authorization or privacy. No private
lab data, credentials, raw logs, restricted media, paid calls, cloud
coding, automatic remediation or new execution environments are
authorized. No GitHub branch protection or merge rule changes. No
producing agent may merge this PR.

### V3 migration verification

Validate the YAML against the published V3 schema and instruction
front matter against the directory-document reference. Compare the
resolved settings using `@coderabbitai configuration` and the actual
review's Run configuration at the migrated commit. A configuration
command alone does not prove that directory instructions loaded.
Inspect review details for directory warnings and actual instruction
coverage. If necessary, use a separately authorized synthetic canary.
The V2 review of this PR finished without actionable comments; that is
baseline evidence only.

CodeRabbit reported that automatic reviews are unavailable for this
repository while it has fewer than ten stars. Use
`@coderabbitai full review` as needed. Do not treat an accepted review
request or a skipped review as completion.

## Qualification

Use existing PRs #184 (site and tests), #183 (infrastructure design), and
#179 (research methodology) if still open, with ordinary manual reviews
where necessary. Avoid reviewing superseded or draft branches unnecessarily.
Review requests before this configuration takes effect are baseline observations,
not evidence of custom-guideline compliance. Record actual head SHA,
review time, effective configuration, findings and relevant check links;
repeat selectively under the merged configuration. No extra paid usage.

For each finding, record its file/line, severity, actual evidence and
independent disposition: valid defect, useful improvement, new risk,
redundant, false positive, misunderstood requirement, or missed known
defect (from an independent review or a separately authorized synthetic
canary). Record whether the producer accepted or rejected it, why, and
whether a fix and subsequent verification occurred. A successful review
status does not mean no defects or passing CI. Report review scope,
skips, limitations and rate limits; do not invent usage.

Keep the initial review results in PR discussions or sanitized project
evidence. After representative results, evaluate noise, misses, usefulness,
latency and integration with producer handoff. Any eventual Supervisor or
Observatory adapter is a separately reviewed implementation campaign;
this configuration does not authorize unattended dispatch or changes to
existing authorization gates.

References:
- https://docs.coderabbit.ai/reference/configuration-v3
- https://docs.coderabbit.ai/configuration/guides/migrate-to-v3
- https://docs.coderabbit.ai/configuration/documents
