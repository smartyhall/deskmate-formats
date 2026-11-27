# Supplementary agent usage receipts

The [Codex ledger](../codex-usage/README.md), existing receipt schema, collector and historical files
remain unchanged. For authorized non-Codex campaigns use the same collection
cadence (startup, meaningful checkpoints, completion or earliest safe stop)
and privacy/attribution principles. Put reviewed supplemental JSON receipts
in `docs/evidence/agent-usage/` with unique provider/campaign/checkpoint
filenames and accurate REUSE sidecars; do not feed them to the Codex collector
or pretend they conform to its schema. The directory may be created with the
first eligible receipt. Keep provider-specific collection documentation with
its implementation once one exists.

The initial supplemental receipt contract (schema version 1) includes:

- Provider/agent label, opaque campaign ID, checkpoint label, UTC observation
  timestamp, public Git revision if known, and execution mode.
- Model and reasoning setting as observed, or null; distinguish a UI-selected
  model from an independently verified runtime identity.
- Source kind (manual UI observation, documented read-only API, local
  allowlisted collector, or unavailable), source/version if known, coverage,
  attribution limitations and checkpoint status.
- Usage measurements only where actually observed: metric name, value, unit,
  scope (campaign or account), cumulative/incremental/remaining semantics,
  observation time, and reset boundary if known. A missing measurement is
  null or an empty measurement list with an explicit explanation; never zero
  unless observed. Provider allowance hours, tokens, credits and wall-clock
  duration are distinct units. Do not sum across unlike units or infer
  per-campaign consumption from a shared account meter.
- No raw transcripts, private paths, credentials, exact account identifiers,
  unrelated activities or unrestricted provider logs. Retain private source
  evidence separately; review all public receipt fields.

## Receipts

- [Source-bound Supervisor execution](freebuff-source-bound-execution-20261127.json)
  and its [completion receipt](freebuff-source-bound-execution-20261127-completion.json)
  — checkpoint receipt for the
  [source-binding report](../../research/source-bound-execution-20261127.md).
  Usage measurements are unknown and recorded as an empty list; the commit is
  recorded in the pull request rather than guessed.
- [Campaign Python environment review corrections](freebuff-campaign-python-environment-20261127-review-corrections.json)
  — checkpoint receipt for the
  [campaign report](../../research/campaign-python-environment-isolation-20261127.md).
  Usage measurements are unknown and recorded as an empty list.
- [Native emulator startup](freebuff-native-emulator-20261126-startup.json),
  [checkpoint](freebuff-native-emulator-20261126-checkpoint-native.json) and
  [completion](freebuff-native-emulator-20261126-completion.json) — the earlier
  Freebuff campaign.

Freebuff's initial read-only evaluation reported that its agent tools did not
expose model identity, context size or quota. The desktop model selector and
usage UI are possible manual observation sources, but API/collector support,
quota semantics and attribution still require verification. A manual receipt
with explicit gaps is sufficient until a reviewed read-only collector exists.
Do not launch extra turns, connect paid providers, redeem resets, buy credits,
or scrape private logs merely to collect telemetry.

## Follow-up implementation

The initial contract is usable for manually reviewed receipts. A versioned
machine-readable schema, synthetic examples, deterministic validator and
portable tests are planned follow-up work, not prerequisites for an
authorized manual Freebuff campaign. Keep receipt validation independent
of AI services and do not expose private account telemetry. The private
operational campaign registry is distinct from this public usage ledger.
