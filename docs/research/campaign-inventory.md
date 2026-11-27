# Research campaign inventory

Snapshot: 2026-11-27, based on integrated revision `7dee5fa25eb1b02b2724bdd87759ce53fcb3256b` and the separately
identified pending PRs. Campaign `chatgpt/research-campaign-inventory-20261127`; repository-only planning.

The [machine-readable inventory](campaign-inventory.json) joins research
questions to existing evidence, candidate work, prerequisites, possible worker
roles, and observable closeout criteria. It is an **advisory** planning layer,
not a live queue or the private campaign registry. No worker is assigned,
no resource is reserved, no task is accepted, and no execution is authorized.

## Authority and maintenance

- The [project status](../../PROJECT_STATUS.md), [format inventory](../inventory.md),
  [compatibility profiles](../compatibility.md), [archive backlog](../archive-format-backlog.json),
  [release atlas](../ecosystem/deskmate-evolution-atlas.md), and research reports
  remain canonical in their respective scopes. A planning row is not a support
  claim. Pending PR references are candidate evidence only.
- GitHub issues/PRs own their current state. Refresh this snapshot after
  independent integration and record completion evidence before changing
  a milestone to completed. Never mark a campaign complete solely because
  a producing agent reports success or CI passed.
- `priority` 1–4 is a proposed relative order (1 highest), not operator
  authorization. `effort` is a rough ordinal scope band (small, medium, large),
  not a duration, token/credit estimate, or availability meter.
- `depends_on` names hard planning milestones whose completion is required
  for this particular package. Source links and related issues are not
  dependency edges. A standing workstream has no one-time completion;
  split a finite prerequisite out as a separate milestone if needed.
- `workers` are possible roles, not actual worker capabilities; `resources`
  are abstract requirements, not private identifiers, path names, actual leases
  or available capacity. Live native work and external actions remain subject
  to existing operator gates. `completed` requires explicit evidence references.
- `review` means proposed work in review, `proposed` means candidate scope,
  `blocked` means a stated missing prerequisite, `standing` means recurring
  candidate work, and `completed` means recorded closeout evidence. The `evidence` field names the blocker for a `blocked` row; version 1 has no separate structured blocker field.
  Even a proposed package with completed dependencies is only a candidate
  for human selection. Unstated dependencies (specimens, authorization, worker
  health, capacity) must still be checked.
- `sources` are repository-relative evidence pointers checked for existence;
  issue and PR numbers are separate tracking references, not asserted live status.
  Each `evidence` statement is scoped and each `acceptance` describes an observable
  result or documented blocker. Private media, paths, approval tokens, and raw
  measurements do not belong here.

## Proposed first sequence

Integrate the current stacks independently; isolate campaign environments;
qualify the single deterministic hash task in issue #204. The quiet integrated
performance baseline in #147 precedes optimization but is not a dependency
of the hash canary. Coordinate #191/#199 shared fixture and configuration changes as merge-order concerns, not hard functional dependencies. Existing native socket procedures can support Corkboard follow-up independently of the candidate input improvements. Resume the highest-value native work when resources and
authority are available. Preserve the archive backlog rather than copying
its individual formats into this inventory.

## Inspect and validate

```sh
python tools/research_campaigns.py
python tools/research_campaigns.py --worker repository-development
python tools/research_campaigns.py --json
```

The default report lists the snapshot's campaigns by priority and unresolved
internal dependencies. It never returns "ready to dispatch." The optional
worker filter selects a planning role only; it does not remove dependency
checks. JSON output exposes the same advisory information for eventual use by
a read-only planner. No external API, model, network, or lab access is used.

Portable tests cover strict shape, duplicate IDs/JSON keys, unknown or
cyclic dependencies, completion evidence, source paths and deterministic
ordering. The validator checks structure (including revision spelling, not Git object existence or ancestry), not scientific correctness,
current remote state or the truth of closeout references.

## Existing recovery capabilities

The [Workbench capability crosswalk](workbench-capability-crosswalk-20261127.md)
maps integrated reader and converter entry points, separate archive tooling,
and the proposed offline interface boundary to campaign IDs. It deliberately
excludes unmerged capabilities and does not duplicate the maintained support
matrix.

## Future integration

Only after the inventory has been reviewed and maintained through several
real handoffs should a read-only adapter connect its IDs to the Supervisor
or Observatory. Keep task identity, accepted manifests, approvals, live
worker capability, actual leases and outcomes in their existing stores.
A later workbench capability map can reference these IDs but must cite
actual implementation entry points and exact profile limits.
