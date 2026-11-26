# Greptile Starter advisory-review qualification

Operator direction: 2026-11-26. Campaign: GRS-20261126; owner: ChatGPT
(GPT-6.2, GitHub connector, isolated remote branch). Base: `3d3f78471ec8832f944baa4d12102fe1ed508305`.
The operator installed Greptile and granted repository access; this change
does not authorize additional repos, private inputs, paid use, or new
execution environments. Existing AGENTS.md and CONTRIBUTING.md govern.

## Review policy

Greptile supplements CodeRabbit; neither is a required check, approver,
producer or merge authority. CodeRabbit's configuration is unchanged.
Its qualification reported that automatic reviews were unavailable below
ten stars; verify actual review completion rather than assuming coverage.

Root .greptile/config.json selects Base, manual-only triggers, no automatic
approval, actionable logic/syntax findings, inline comments, no PR body
rewrite and no AI fix prompts. No blanket file exclusions: specifications,
tests, provenance, licenses, workflows and documentation may be consequential.
No automatic tier escalation or directory-specific tier overrides are intended.
The scoped rules and context references are advisory and must be qualified
against the installed Starter entitlement.

Prioritize binary writers and readers, format claims, native evidence,
publication/audit logic, emulator automation and supervisor authority,
shared state, cross-component changes, and substantive site/evidence changes.
Ordinary editorial corrections, asset-only updates, dependency churn and
intermediate checkpoints are normally lower priority, not categorically exempt.

## Credit budget (50 per month)

Suggested planning envelope, not an enforced quota or a spending grant:
30 Base reviews (30 credits), up to four Plus reviews (12 credits), and
eight credits held for rechecks or unexpected work. Use Base for the initial
comparison; Plus only for especially consequential or ambiguous changes.
Apex costs ten credits and requires operator approval and a revised allocation.
Do not assume higher tiers are entitled on Starter. Do not use Auto, TREX
(three extra credits/run), local CLI review (not included in Starter), or
automatic recharge. Do not purchase credits, create a trial, connect MCP,
or enable autonomous repair. Existing separate authorization requirements
remain unchanged.

Operator, or agent specifically authorized to request a review within the
remaining allocation, posts a single GitHub PR comment with @greptileai.
The vendor also documents "@greptileai effort: plus" for deliberate escalation.
Avoid repeated mentions, gratuitous follow-up questions, review loops and
automatic re-review on each push. Check current balance and existing results
first; reserve a re-review for consequential corrections. If balance is
unknown, obtain confirmation before an agent triggers a review. When credits
run out, use normal independent review and CI; never block on the bot.

Record review PR, exact head SHA, date, tier, expected/actual credits when
available, effective settings, finding disposition and verification in the
campaign handoff or qualification record. Do not invent billing telemetry.
Keep account identifiers, API tokens, raw receipts and private evidence out
of Git. For the first 10–15 substantive reviewed PRs, compare with actual
CodeRabbit/independent findings: valid unique issues, duplicates, false
positives, missed known issues and time to resolve. Treat scores as advisory.

## Dashboard checks by the account owner

Before relying on this configuration, inspect:
- Settings > Code Review > Greptile Review Configuration:
  default tier Base; remove higher/Auto tier rules; turn automatic reviews
  (open, push, rebase and draft) off; disable auto-approval. The tier resolver
  can select a higher dashboard/rule tier despite the repository Base setting.
- Settings > Billing and Usage: Starter, remaining balance, automatic
  recharge off. Do not add payment methods or buy credits for qualification.
- Confirm the repository is enabled and other repositories/private lab
  resources are not connected. Leave TREX, additional review products
  or integrations off unless separately authorized.
- Confirm custom rules/context are actually honored on Starter: pricing
  explicitly advertises custom review rules for Pro, so availability and
  effective behavior on Starter are unverified. If unavailable, retain the
  repository files for future use and rely on manual scoped review requests.
- Confirm Greptile is not a required merge check and never auto-approves.
  Do not change branch protection to make it required.

Repository settings are read from the PR source branch for normal reviews;
older branches may not contain this configuration. Dashboard manual-only
settings are therefore important immediately, and before qualifying older
PRs. Auto-approval policy is read from the base branch. Review configuration
changes independently and do not assume configuration loading from a green
status. For qualification, choose a substantive, current PR containing the
configuration, confirm the expected Base review and compare the findings
with source/evidence. Do not use a synthetic defect canary or extra review
credits without separate approval.

## Sources and limitations

Vendor documentation checked 2026-11-26:
- https://www.greptile.com/docs/code-review/greptile-config-reference
- https://www.greptile.com/docs/code-review/greptile-config
- https://www.greptile.com/docs/code-review/review-tiers
- https://www.greptile.com/docs/code-review/developer-essentials
- https://www.greptile.com/docs/account/billing-seats
- https://www.greptile.com/pricing

Configuration and referenced paths checked against the published schema and
repository tree; actual app settings, entitlement, credit balance, review
execution and local portable CI are not verified by this connector campaign.
No review requested by this campaign; automatic app behavior before the
settings are effective is unknown. No local worktree, emulator or lab
resources used. Usage telemetry unavailable. Independent review and CI
remain required before merge. Visual exemplars: not applicable (configuration
and documentation only).
