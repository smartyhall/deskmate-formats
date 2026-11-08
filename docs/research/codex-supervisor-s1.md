# Supervisor S1 trusted task intake

The [offline S2 bridge](codex-supervisor-operator-driver.md) now consumes an exact
accepted receipt through a separate synthetic dispatch grant. S1 itself remains
an intake/review queue; acceptance and Git changes never launch a worker.

S1 implements the Git intake and private queue in
[issue 60](https://github.com/smartyhall/deskmate-formats/issues/60). A discovered
candidate has a Git provenance receipt and no queue decision. An acceptance
admits one exact revision to the queue. Any future dispatch requires separate
authorization and an implementation that can reconcile it against the
[S0 operation ledger](codex-supervisor-s0.md). S1 stops at operator review.

## Configure a trusted source

Use a standalone, full local Git checkout maintained by the operator. Protect
the checkout's Git metadata, the installed Git executable and the private queue
from other writers. Set the origin's fetch URL to a single canonical lowercase
HTTPS URL of the form `https://host/owner/repository.git`. The queue binds the
absolute checkout path, exact origin, local branch name and full trust-anchor
commit at initialization. Choose the anchor independently from reviewed
repository history. Use a dedicated private directory with an existing parent
on a local filesystem outside Git. The tool creates it with the same access
restrictions as the Observatory spool. The local account that can access this
private directory is the operator trust boundary.

```powershell
deskmate-supervisor-task --queue $queue init --checkout $checkout --repository https://example.invalid/lab/research.git --branch main --anchor $trustedCommit
deskmate-supervisor-task --queue $queue discover $reviewedTip ops/tasks/calendar-baseline.json
```

Supply the full hash of the exact local branch tip. Git object reads use the
configured direct `refs/heads/<branch>`. The candidate must descend from the
anchor and, once a decision intent exists, from the latest recorded commit.
The branch is checked before and after reading. A stale commit, rewrite below
the recorded point, symbolic branch, duplicate origin URL, alternate object
store, linked worktree, shallow history or included Git configuration is
refused. Git replacements, inherited Git overrides, lazy fetches and network
transports are disabled in the reader. The tool reads tracked blobs by object
ID and ignores working tree edits.

The trust check covers the local reference as observed during each command.
The remote origin URL is a configured label checked against local Git metadata.
Fetch, remote branch protection, signature verification and maintaining the
local trusted branch belong to the operator. A rewritten history that still
descends from the last recorded point needs to be identified during review.
The Git ref check and SQLite decision are separate operations. The stored
receipt identifies the exact checked bytes even if the ref moves afterward.

## Version 1 manifest

Use UTF-8 JSON for a small, deterministic standard-library parser. JSON object
key order and whitespace can vary on input. Canonical serialization sorts keys
and uses UTF-8 with compact separators. The Git blob and SHA-256 are calculated
from the original bytes. Even a whitespace edit at a recorded task revision is
a conflict.

```json
{
  "schema_version": 1,
  "id": "calendar-baseline",
  "revision": 1,
  "idempotency_key": "calendar-baseline-1",
  "title": "Check a synthetic calendar baseline",
  "description": "Inspect the metadata in the reviewed portable fixture.",
  "category": "verification",
  "profile": "offline",
  "resources": ["source-read", "synthetic-fixtures"],
  "dependencies": []
}
```

Store this example at `ops/tasks/calendar-baseline.json`. Each of the example
fields is required. The only optional fields are `expires_at` and
`instructions`.

| Field | Version 1 contract |
| --- | --- |
| `schema_version` | Integer `1`. Unknown and duplicate JSON members are refused throughout. The whole input is limited to 8 KiB. |
| `id`, `idempotency_key` | Lowercase ASCII letters, digits and hyphens, 1–64 characters, starting with a letter or digit. Use an identifier suitable for display if publishing to Observatory. The ID determines the canonical path. A key identifies exactly one revision in the queue. |
| `revision` | Positive integer up to 2,147,483,647. Recorded revisions begin at 1 and increment by 1, including rejected and abandoned revisions. |
| `title`, `description` | Nonblank printable text, up to 120 and 2,048 characters respectively. Description also permits LF. Treat both as plain review text. |
| `category`, `profile` | `research` or `verification`, with profile `offline`. These are request labels. |
| `resources` | Nonempty distinct subset of `source-read`, `synthetic-fixtures` and `portable-tests`. These requests confer no privileges. |
| `dependencies` | Up to 16 objects with exactly `id` and `revision`, each referring to a different task ID. An acceptance requires prior acceptance of every referenced revision. This ordering precludes cycles among accepted revisions. |
| `expires_at` | Optional UTC timestamp with seconds, such as `2027-01-01T00:00:00Z`. The gate rejects new acceptance at or after expiry. Existing decisions are retained. |
| `instructions` | Up to four objects with exactly `path` and lowercase hex `sha256`. Each refers to a distinct Markdown blob under `docs/` at the same commit, up to 128 KiB. The operator reviews these separately. Intake verifies the bytes and keeps the references without interpreting the documents. |

The path grammar allows lowercase ASCII letters, digits, dots, underscores and
hyphens within slash-separated segments. Each segment begins with a letter or
digit. Paths with dot segments, trailing dots, Windows reserved device names,
drive prefixes or streams are refused. The exact manifest and any referenced
documents must be tracked as regular, non-executable Git blobs.

The source envelope is supplied by Git discovery. It includes the configured
repository and branch, full commit ID, canonical path, tracked blob ID and
SHA-256. This keeps the commit ID out of the blob that the commit hashes.
The review token is a deterministic SHA-256 of this envelope. It pins the
review target. Access to the local queue and an explicit decision supply
authority. Schema fields for commands, executable expressions, environment
overrides or approval policy are unsupported.

## Review and decide

Discovery prints the validated manifest and provenance to the local terminal
without creating a receipt. Use `validate` to check UTF-8 JSON on stdin without
Git or queue access. This is a schema check, while `discover` also verifies
source provenance. Review the candidate and any referenced documents at the
same commit. Copy the displayed token for the decision.

```powershell
'Reviewed the manifest and referenced fixture' | deskmate-supervisor-task --queue $queue accept $reviewedTip ops/tasks/calendar-baseline.json --review-token $reviewToken --reason-stdin
deskmate-supervisor-task --queue $queue list
deskmate-supervisor-task --queue $queue inspect calendar-baseline 1
```

Use `reject` with the same arguments to record a decline instead. The required
UTF-8 reason is 1–512 printable characters with an optional terminal line break.
The decision re-runs Git verification and requires the exact token. Re-delivery
of identical manifest bytes with the same decision returns the original
receipt, timestamp, commit and reason, with `created: false`. Changed bytes,
reused keys or a different decision for the same revision are refused. A later
revision has its own receipt and preserves the earlier history.

| Exit | Meaning |
| --- | --- |
| 0 | Command succeeded, including an identical decision or publication replay. |
| 2 | Usage, manifest, source or decision refused. |
| 3 | Requested receipt absent during inspection. |
| 4 | Queue unavailable, busy, or local I/O failure. A busy diagnostic means the decision was never attempted. |
| 5 | Decision outcome requires inspection or an unresolved intent already exists. |
| 6 | Observatory publication failed. Inspect the private journal or replay only the publication. |
| 130 | Console interruption outside the decision transactions. Inspect before resubmitting a decision. |

## Durability and retention

The store is a dedicated SQLite database separate from the S0 ledger and event
journal. It holds the source binding, exact manifest bytes and original decision
intent, as well as the final outcome and time. A cooperating OS lock serializes
queue commands across processes. SQLite uses rollback journaling, integrity
checks, `synchronous=EXTRA` and uniqueness constraints for the task revision
and idempotency key. One transaction records the unresolved intent. A second
transaction finalizes acceptance or rejection. The store permits one unresolved
intent at a time.

After a write error, process exit or missing acknowledgement, reopen and inspect
the exact ID and revision.

- An absent receipt means no decision is recorded in the recovered database.
  Review the current trusted tip before trying again.
- An `unresolved` receipt preserves the requested decision, reason, preparation
  time and provenance. Further decisions stop at this gate. Use
  `abandon <id> <revision> --review-token <saved-token> --reason-stdin` to record
  the recovery decision. The abandoned revision is retained. Submit the next
  revision for a new review.
- An `accepted` or `rejected` receipt is the committed outcome, even if the
  caller never saw it. An identical re-delivery does not create a second row.

Capacity defaults to 1,000 receipts, including rejected and abandoned ones.
Initialization can choose a smaller cap. SQLite uses 4 KiB pages with a
32 MiB main database limit. No row expires or is evicted. Preserve the complete
queue directory in a private backup with all queue commands stopped, including
the rollback journal if present. Preserve the same history on restore. A new
empty queue or a stale backup cannot deduplicate decisions missing from it.
If the queue fills, stop intake and preserve it pending a reviewed migration
that carries forward identity and history. Filesystem or disk-cache failure,
hostile edits by principals with write access and multi-host access fall
outside the demonstrated recovery guarantees.

## Read-only Observatory reports

Publication is a separate local action. Only use task IDs cleared for browser
display. Choose a separate dedicated private Observatory spool and use its
configured retention limits.

```powershell
deskmate-supervisor-task --queue $queue publish calendar-baseline 1 --journal $spool
```

Publication reads the durable final receipt, then appends a sanitized
`task.accepted` or `task.rejected` event using the existing journal publisher.
The task ID and revision, decision UTC time and counts at that decision are
shown in the dashboard timeline and in
`GET /api/v1/events?category=task`. The browser also displays the ingestion
timestamp. The report carries no body, title, decision reason, key, path, Git
commit or referenced instructions. These timeline entries create no agent run.
Replay of the same report in the same healthy journal returns the previous
cursor. A journal failure leaves the queue decision intact. The queue never
reads the journal. A browser refresh reads the published event snapshot.

## Reproduction

The baseline was `1a428dfa6d3d6f835dedb792e63eb448d0a347eb`. Tests used Windows
10 build 19045, Python 3.13.17, SQLite 3.50.4 and Git 2.56.0.windows.4. Each test
creates a disposable repository and uses deterministic Git author/committer
dates, explicit SHA-1 object format and no credential or native emulator inputs.
For the unmodified `manifest()` in `tests/portable/task_fixture.py`, the recorded
anchor was `d7b89a38b670b71df6d75e0a70781b1006418b29`, task commit
`5f1e9f1c385ad46eca13b8c63d6f2882423f0df2`, blob
`7f9ad2bbfcbcf4de6fe302f641d4c13eba6271fc` and content SHA-256
`51522255fc9a281b45ccb2263e4903928b0e65e5966a3f15861bbc6aa8878e71`.

```console
python -m unittest discover -s tests/portable -p "test_supervisor_task*.py" -v
python -m unittest discover -s tests/portable -v
python -m unittest discover -s deployment/windows10/tests -v
python -m ruff check src tests/portable tools
python -m reuse lint
python -m build
python tools/check_install.py
python tools/audit_repository.py
```

The HTTP integration test restarts the event collector and issues 320 GET/HEAD
requests. It checks zero Git or SQLite connections during requests, unchanged
queue database SHA-256, and zero synthetic native connections, authentications
or commands. Synthetic guest time remained exactly 1,000 ms (delta 0 ms), with
one frame and one reset. No real guest time was observed. The crash tests cover
process exit during the final transaction and after commit before a CLI reply.
Power loss and a production supervisor dispatch were outside this experiment.
