# Codex research usage ledger

The historical utility qualification campaign recorded [startup](20261127-historical-utility-startup.json),
[known-good DBrepair](20261127-historical-utility-known-good-usage.json), and
[publication checkpoint](20261127-historical-utility-checkpoint.json) receipts.

The [TVDog descriptive index review](../../ecosystem/tvdog-directory-index-review.md)
recorded [startup](20261123-tvdog-directory-index-startup.json),
[reconciliation](20261123-tvdog-directory-index-reconciled.json), and
[completion](20261123-tvdog-directory-index-completion.json).
The publication handoff recorded
[startup](20261123-tvdog-catalog-publication-startup.json),
[media review](20261123-tvdog-catalog-publication-reviewed.json), and
[publication checkpoint](20261123-tvdog-catalog-publication-checkpoint.json).

The [RSX Print Companion campaign](../../research/print-companion-20261123.md)
recorded [startup](20261123-print-companion-startup.json),
[native survey](20261123-print-companion-native-survey.json),
[cold controls](20261123-print-companion-cold-controls.json), and
[completion](20261123-print-companion-completion.json).

The [RSX AOL 1.3 campaign](../../research/rsx-aol13-20261123.md) recorded
[startup](20261123-rsx-aol13-startup.json),
[installation](20261123-rsx-aol13-installed.json), and
[offline validation](20261123-rsx-aol13-offline.json), followed by
[completion](20261123-rsx-aol13-completion.json).

The [DeskMate installation reference](../../ecosystem/deskmate-installations.md)
records [startup](20261121-installation-startup.json),
[inventory review](20261121-installation-inventory.json), and
[completion](20261121-installation-completion.json).

The TVDog campaign recorded [startup](20261119-tvdog-startup.json),
[mirror verification](20261119-tvdog-mirror.json),
[retry changes](20261119-tvdog-retry.json),
[indexing](20261119-tvdog-index.json),
[discoveries](20261119-tvdog-discoveries.json), and
[completion](20261119-tvdog-completion.json).

The [recovered Draw campaign tail](20261119-draw-pr122-recovered-tail.json)
contains observations after PR #122's published completion receipt
through the interrupted turn's last recorded event.

Draw II receipts cover [startup](20261119-draw-ii-startup.json),
[outline decoding](20261119-draw-ii-outlines.json),
[native FF1 trials](20261119-draw-ii-native-ff1.json),
[FF1 comparison](20261119-draw-ii-ff1-gallery.json),
[pen recovery](20261119-draw-ii-pen.json),
[browser authoring](20261119-draw-ii-authoring.json), and
[completion](20261119-draw-ii-completion.json).

**Established:** 2026-11-18, by operator request.
**Scope:** DeskMate research campaigns; sanitized, reproducible usage receipts
only. This directory is the central tracked destination, not a dump of the
operator's account history.

## Supplementary agent receipts

See the [provider-neutral usage ledger](../agent-usage/README.md) for
non-Codex campaigns. The existing Codex collector and schema are unchanged.

## Collection and publication contract

- At campaign start, each useful checkpoint, and completion (or an early stop),
  record available measurements. Prefer a reusable non-model collector which
  can also run after model exhaustion; do not spend inference on polling.
- For historical backfill, inspect the actual local Codex home
  (`CODEX_HOME` when set, otherwise normally `~/.codex`), including the
  `sessions/` and, if present, archived session stores. Local rollout JSONL
  may contain `event_msg` records with `payload.type == "token_count"`,
  token totals/deltas and optional `rate_limits`. Determine available fields
  and relevant project cwd/repo from local metadata without copying raw content.
  Inspect schema variants and use project-attributable records only; quarantine
  uncertain or unrelated records privately. Never modify source logs.
- For current limits, verify the installed app-server version and generated
  schema before using documented read-only `account/rateLimits/read` and
  `account/rateLimits/updated` or `thread/tokenUsage/updated` where supported.
  No added model turn is required just to query usage. If starting a separate
  read-only client is unsupported or would interfere with a live session, use
  the local logs or a manual observation and label it honestly.
- Do not access or export authentication files or tokens. Never publish raw
  rollout records, prompts, tool outputs, conversations, absolute paths,
  account/email/plan identifiers, raw thread/session IDs, or unrelated work.
  Exact banked-reset inventory and expirations remain in private account
  telemetry; no reset redemption or purchases are authorized by this ledger.
- Use reviewed, allowlisted aggregate/project data only. Retain source receipts
  and the stable mapping of local session/event identities in a private lab
  directory. Use a stable private pseudonym or opaque campaign/run label for
  published attribution. Do not confuse a public receipt with a complete
  account-wide usage history.

## Suggested v1 layout

Store one small JSON file per campaign or backfill batch in this directory,
using a unique filename such as `20261118-audio-native.json` or
`20261118-historical-backfill-01.json`, with an accurate REUSE sidecar.
Update existing campaign receipts at checkpoints, or use separate immutable
batch files if concurrent writers would conflict. Keep a versioned schema and
document any revisions. Initial suggested fields:

- `schema_version`, campaign/run label, source kind, collector version, and
  relevant Git commit/checkpoint where known.
- Measurement UTC timestamp; model and reasoning effort if actually known;
  token counters (input, cached input, output, reasoning output, total) labeled
  as cumulative or incremental, with explicit nulls for unknowns.
- Quota window entries with duration in minutes, observed used percentage and
  reset timestamp when retained for analysis; distinguish used from remaining
  (do not assume primary means five hours). Record missing/stale observations.
- Coverage/limitations: source record count, deduplicated count, current versus
  historical source, gaps, attribution quality, and whether a checkpoint was
  completed. Optional milestone labels or public commit references.

Normalize and validate types/ranges; preserve source semantics. Do not sum
cumulative counts across events, double count reasoning or cached tokens, or
attribute a shared account's quota change to one worker without evidence.
Deduplicate using private stable source/event identities; ensure re-running the
import does not inflate totals. Distinguish quota decreases due to resets or
source changes from negative consumption. Do not invent an accounting ratio,
guess missing model names, or extrapolate a precise cost from rounded meters.

The first implementation should include deterministic extraction and synthetic
tests (null fields, differing schemas, repeated cumulative totals, duplicate
records, mixed projects, malformed/truncated input and a reset boundary).
Build an incremental backfill with a private input index and small reviewed
public receipts, and summarize coverage by date/campaign/model/effort when
available. Avoid reading private conversation text into model context.

See also the [standing research instructions](../../../AGENTS.md) and
[supervisor design](../../research/codex-supervisor-design.md), which treats
usage as an input to future dispatch and early checkpoint policy.

## Local collector and receipt schema v1

Run from the checkout with Python 3.13 or newer. Review the receipt before
publication and choose a new filename for each milestone.

```powershell
python tools/experimental/codex_usage.py --root . --private-dir $private --label campaign-slug --checkpoint milestone-slug --output $receipt
```

Repeat `--root` for known project worktrees and repeat `--home` to include
multiple known homes. Omit `--checkpoint` for event history. Reuse the same private directory
to retain opaque session labels. Merge histories by session and observation
contents or regenerate the batch from source. `--at` is an inclusive ISO
timestamp cutoff with timezone. Attach a known public Git SHA with `--commit`.
The campaign checkpoints use the already committed HEAD at collection.

`--compact-history` declares positional row fields in `history.columns`. Each
session label maps to its ordered rows. Token and window arrays use
`token_columns` and `window_columns`, respectively. Compaction rows end after
the event type. Each batch regenerates deterministically for fixed inputs,
cutoff and key.

[Historical batch 01](20261118-historical-backfill-01.json) covers
2026-11-11 23:12:27 to 2026-11-18 17:45:23 UTC, with 2,457 token observations
across 21 sessions. The default home contributed 19 historical sessions.
Its archive directory had no rollouts. Two reviewed supervisor homes
under private evidence contributed one session each. The cutoff excluded the
active campaign. Attribution comes from the project checkout or the documented
supervisor run directories. Public milestone attribution requires separate
evidence because the starting checkout can still be on an earlier campaign's
branch.

[Historical batch 02](20261118-historical-backfill-02.json) covers
25 additional project sessions with missing rollout files in the desktop
state index, from 2026-11-05 01:48:57 to 2026-11-08 18:40:06 UTC.
Run the collector with `--state-index` and an explicitly selected
`state_5.sqlite` to reproduce. The database is opened read-only. For 20
indexed project sessions with readable rollouts, the indexed total exactly
matched the last rollout total in every session. The second batch keeps the
indexed field separate from the rollout counters. It has no per-request
usage fields or meter observations. A zero index value is recorded as null
because an empty/default value cannot be distinguished from a measured zero.
The created and updated timestamps are session metadata. Existing rollout
files and matching rollout identities in the selected stores are excluded.

Token observations include UTC time, reviewed model and effort from turn
context, cumulative counters, the reported last increment, and counter state.
Repeated totals can carry the same last increment. A decreased total indicates
a discontinuity. Compaction observations carry only a timestamp and event type.

Window keys are durations in minutes. Each carries used percent, reset epoch
in Unix seconds, and an observation status. Missing values are null. A window
whose epoch has passed is expired. The latest rollout checkpoint becomes stale
after 900 seconds or when its epoch has passed. An advanced epoch marks a meter
boundary and can reflect a rolling window. Regressed epochs or percentage
decreases are recorded as discontinuities. Account meter movement can include
other work.

CLI 0.166.0 rollout collection was verified locally. The installed generated
app-server schema includes `account/rateLimits/read`, `account/rateLimits/updated`
and `thread/tokenUsage/updated`. The read returned a startup snapshot through
an owned stdio client. The notifications were schema-verified only. The
supervisor's pinned profile excludes these methods.
`--account-snapshot` attaches a separately measured, sanitized read response
with `measured_at` and a `windows` list of at most two entries
(`windowDurationMins`, `usedPercent`, `resetsAt`).

References for the installed release:
[Codex App Server](https://learn.chatgpt.com/docs/app-server);
[Codex upstream discussion on rollout rate-limit snapshots](https://github.com/openai/codex/discussions/56932).

The [typography laboratory](../../research/typography-lab-20261119.md)
records [startup](20261119-typography-startup.json),
[acquisitions](20261119-typography-acquisitions.json),
[outline interchange](20261119-typography-outlines.json),
[native rendering](20261119-typography-native-interchange.json),
[additive installation](20261119-typography-installation.json), and
[fixture publication](20261119-typography-fixtures.json).

The [typography completion receipt](20261119-typography-completion.json)
records the final research checkpoint.

MidiMapper receipts cover [startup](20261120-midimapper-startup.json),
[verified acquisition](20261120-midimapper-acquisition.json), and
[native playback and export completion](20261120-midimapper-completion.json).

The November 20 native-semantics campaign preserved
[startup](20261120-native-semantics-startup.json),
[MidiMapper fixture qualification](20261120-native-semantics-midi.json),
and [safe-stop](20261120-native-semantics-completion.json) receipts.
Its [handoff](../../research/native-semantics-campaign-handoff-20261120.md)
links the four review branches.

The November 21 generic DeskMate installation campaign preserved
[startup](20261121-deskmate-303-startup.json),
[3.03.01 installed](20261121-deskmate-303-installed.json),
[native comparison](20261121-deskmate-303-native-comparison.json),
[evidence commit](20261121-deskmate-303-evidence-commit.json), and
[completion](20261121-deskmate-303-completion.json) receipts.
[Campaign report](../../research/deskmate-303-305-comparison.md)

The Evolution Atlas survey recorded [startup](20261121-evolution-startup.json),
[generic 3.00](20261121-evolution-300-usage.json),
[resumed work](20261121-evolution-resume-usage.json),
[DeskMate II](20261121-evolution-dmii.json),
[Personal DeskMate](20261121-evolution-personal.json),
[OEM progress](20261121-evolution-oem-usage.json), and
[held Disk 3 stop](20261121-evolution-completion.json).
[Survey and native records](../../ecosystem/deskmate-evolution-atlas.md)

The November 22 RSX OEM recovery recorded
[startup](20261122-rsx-oem-startup.json),
[the transition to Disk 4](20261122-rsx-oem-disk4.json),
[the Disk 6 reset and hard-disk boot](20261122-rsx-oem-installed.json),
[the first application launches](20261122-rsx-oem-applications.json),
[the CP290 timer round trip](20261122-rsx-oem-serial.json),
[the application data and OEM sweep](20261122-rsx-oem-fixtures.json), and
[safe stop and validation](20261122-rsx-oem-completion.json).
[Recovery record](../../research/deskmate-rsx-oem-recovery-20261122.md)

The alternate 3.05 and SL/2 OEM campaign recorded
[startup](20261122-305-sl2-startup.json),
[alternate installation](20261122-305-sl2-installed.json),
[matched 3.05 comparison](20261122-305-sl2-comparison.json),
[SL/2 ROM and EEPROM controls](20261122-305-sl2-rom-control.json),
[RL CookBook compatibility](20261122-305-sl2-rl.json), and
[completion](20261122-305-sl2-completion.json).
[Campaign report](../../research/deskmate-305-variants-sl2-20261122.md)

The November 23 Corkboard and Home Organizer campaign recorded
[startup](20261123-corkboard-startup.json),
[first native database and note evidence](20261123-corkboard-native.json),
[database and release comparisons](20261123-corkboard-comparative.json),
[message removal](20261123-corkboard-message-removal.json), and
[completion](20261123-corkboard-completion.json).
[Campaign report](../../research/deskmate-corkboard-20261123.md)

The November 23 laboratory storage audit recorded
[startup](20261123-lab-storage-startup.json),
[inventory and tooling](20261123-lab-storage-inventory.json), and
[completion](20261123-lab-storage-completion.json).
[Campaign report](../../research/lab-storage-audit-20261123.md)
