# Reusable archive mirror

A standalone, standard-library Python 3.11+ tool with a Windows PowerShell
5.1/7 launcher. Archives public HTTP(S) directory indexes (Apache/nginx-style
HTML); not a general web crawler, FTP client, WARC capture tool or continuous
synchronizer. The original operator's Mirror-TVDog.ps1 database schema,
root identity, local-name mapping, lock file and partial naming are retained.
Existing completed files are not rehashed or downloaded by default.
The exact existing mirror must be offline before first adoption. Keep a
backup of its state and do not run two versions against the same destination.

## Configuration

Copy mirror-targets.example.toml to a private editable file outside Git.
Set each named table's root, destination and per-site limits. Relative local
paths are based on the configuration file's location. The TVDog example
uses the existing VM destination and the operator's requested 256 KiB/s,
one-second delay; generic engine defaults are 128 KiB/s and two seconds.
The configurable ceiling of 1024 KiB/s is not a recommendation or permission;
use only rates compatible with the source's policies. Review robots.txt and
published mirroring guidance before passing the policy confirmation flag.
The engine also checks robots directives and source cooldowns.
Run only one process per source host, even when configured with multiple
destinations. Select one named target at a time.

From the checkout root on Windows:

    powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/archive/Mirror-Archive.ps1 -Config C:\DeskMateLab\mirror-targets.toml -Target tvdog -PolicyChecked

Portable direct invocation:

    python tools/archive/archive_mirror.py --config /path/to/targets.toml --target tvdog --policy-checked

## Stop, status, resume

From a second PowerShell window, with the same config and target:

    powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/archive/Mirror-Archive.ps1 -Config C:\DeskMateLab\mirror-targets.toml -Target tvdog -Stop

Or create the destination's STOP file directly:

    New-Item -ItemType File -Force C:\DeskMateLab\references\oldskool\tvdog-mirror\STOP

The engine checks the sentinel between transfers, before requests, between
read chunks and during pacing and cooldown waits. A blocked network read, connection,
disk operation or hash may delay stopping; the default socket timeout is 60
seconds, not a hard overall deadline. The legacy embedded script does not
understand the sentinel. Wait for the active process to exit. The sentinel is
persistent and never cleared automatically.

    powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/archive/Mirror-Archive.ps1 -Config C:\DeskMateLab\mirror-targets.toml -Target tvdog -Status
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/archive/Mirror-Archive.ps1 -Config C:\DeskMateLab\mirror-targets.toml -Target tvdog -ClearStop

Then use the ordinary start command again. Status reads SQLite without
claiming the writer lock or sending network requests. ClearStop refuses to
operate while the destination is locked. The direct Python equivalents are
`--status`, `--stop` and `--clear-stop`. `--max-items` bounds the number of
processed entries in a trial. A transient retry still belongs to the same
entry. `--retry-unavailable` requeues invalid or unavailable entries and
respects recorded robots and access-denied blocks.

### Transient failures

A connection error, incomplete response, HTTP 408 or 429, or HTTP 5xx pauses
all requests to the source. The downloader persists the host cooldown,
consecutive failure count, error, and any partial transfer before waiting.
It resumes the same queue automatically after waits of at least 1, 5 and 15
minutes, with a small additive jitter. A valid `Retry-After` delta or HTTP
date can lengthen any wait. The fourth consecutive failure saves a cooldown
of at least one hour and exits with status `2` for operator review. A later
manual restart waits out any remaining cooldown before issuing even a robots
request and retains the failure count until a queued entry succeeds. Status
reports `host_not_before_epoch`, `host_consecutive_failures`, and
`host_last_error` without taking the download lock.

Explicit HTTP access denials stop the run immediately. Paths excluded by
robots are recorded as blocked without requesting them. During a transient
interruption, a partial can resume with a verified byte range and matching
validator. An operator stop preserves the pending cooldown for a later run.

## Scope and limits

The engine retains directory listings, JSONL receipts, SQLite state, original
files and partials in the original layout. It refuses unrelated redirects,
uses a single sequential request stream and validates range responses and lengths. It only
supports recognizable UTF-8 HTML directory indexes and direct child links;
unrecognized listings, other encodings and unsupported response framing are
reported rather than guessed. It does not extract or execute downloaded files.
A complete discovered tree is not proof that the server listed every file.
No automatic refresh, timestamped remote-version history, non-HTTP transport,
arbitrary linked-page traversal or cross-process per-host pacing is claimed.
The destination is a trusted local research directory, not a security sandbox
for hostile local filesystem changes. Keep it and real target configurations
outside Git. The local-only tests require no live archive server.

See docs/ecosystem/archive-mirror.md for the TVDog-specific preservation and
publication policy.
