# TVDog archive mirror and research index

Operator decision: 2026-11-19.

Source root: http://ftp.oldskool.org/pub/tvdog/

The objective is a complete local preservation copy of every publicly
accessible, permitted file beneath this root, including non-DeskMate
material. This is a private research mirror, not a redistribution
license or an installation mandate. The prior selective acquisition
instructions are superseded for this subtree only. The separate
[software catalog](catalog.json) and [acquisition priorities](acquisitions.md)
remain the guide to DeskMate-specific analysis.

## 1. Plan and preflight

- Check the source site's published mirror guidance, robots directives,
  rate limits and any redistribution or download restrictions. Honor
  them, including a prohibition on bulk mirroring. Do not bypass
  restrictions, authentication, throttling or blocked paths. If bulk
  permission is unclear, begin with conservative permitted requests
  and stop if the host indicates that mirroring is unwelcome.
- Prefer an expressly documented bulk archive or mirror mechanism when
  offered; otherwise use the public directory listing protocol.
  Do not test several protocols concurrently or repeatedly switch
  protocols to evade server restrictions.
- Verify destination free space and reserve headroom for the existing
  research lab. Inventory existing local downloads first, including
  the historical Oldskool references already in the lab. Use local
  verified identical copies where an exact source identity is
  established; record the verification basis and any uncertainty.
- Proposed private destination:
  C:/DeskMateLab/references/oldskool/tvdog-mirror/
  (or a documented larger dedicated volume if necessary). Separate
  originals, listings, transfer state and extracted/indexed derivatives.
  Never write into the repository or overwrite a native research disk.
- Preserve source relative names, case, dates where advertised, and
  directory structure, including empty directories. On Windows handle
  reserved filenames, case collisions and unrepresentable paths with
  a reversible local-name map; do not silently rename or overwrite.
- Explicitly constrain URL traversal to the canonical source subtree.
  Normalize and validate decoded paths; do not follow parent links,
  unrelated query variants, directory cycles or external redirects.
  A canonical HTTP-to-HTTPS upgrade is acceptable if it stays within
  scope and obeys the source's policy. Do not guess hidden paths.

## 2. Server-friendly acquisition

Use a deterministic resumable downloader rather than model-mediated
requests or a high-concurrency crawler. A standard mirror utility
is acceptable if its behavior is verified; otherwise implement a
small reusable tool. Save its configuration and test with a local
mock server before beginning wide traversal.

Conservative starting limits, not targets to maximize:

- One active HTTP/FTP request or file transfer at a time for the
  entire source host, including listings and retries.
- At least 2 seconds between completed requests and the next request,
  or longer if the source asks for it. Begin at 128 KiB/s aggregate
  download bandwidth (about 1 Mbit/s). A lower source limit overrides
  this ceiling. Do not increase without an explicit published mirror
  policy or separate operator approval.
- Identify the downloader honestly with a descriptive user agent.
  Respect robots rules and Retry-After. Never impersonate another client
  or use multiple IPs or parallel workers to increase throughput.
- Use generous connection/read timeouts. For transient failures, use
  exponential backoff with jitter (e.g. 60 seconds, 5 minutes,
  15 minutes), a small retry limit and a persistent deferred queue.
  If repeated 429/503/5xx responses or prolonged instability occurs,
  pause the entire host rather than merely retrying individual files.
  Treat 401/403, explicit denial, and robots exclusions as blocked,
  not as invitations to retry via a different path.
- Save and reuse directory listings to avoid needless requests.
  Do not HEAD every file already described in a listing.
  Resume partial transfers with verified Range support and validators
  where available; do not append incompatible versions. Write to
  temporary files and atomically finalize after validation. Do not
  repeatedly redownload successful files for hashing or testing.
- Check advertised lengths, response types, and transfer integrity.
  Never mistake an error page for a disk image or ZIP. Record server
  checksums when available, but do not invent them.
- Keep every completed original immutable. A changed remote identity
  creates an explicitly versioned new observation/copy; never delete
  prior material solely because it disappears remotely.
- Checkpoint the queue, file manifest and transfer counters throughout.
  Use an ordinary operator-supervised or explicitly authorized local
  process, not extra Codex calls for each transfer. If the session
  ends or the storage/health limits are reached, stop safely and
  resume under the same controls later. Do not redeem usage resets.
  Do not leave an unapproved unattended downloader running.

Prioritize directory discovery, Express Publisher, the documentation
leads and other native DeskMate packages, then drain the entire permitted
queue. The scope includes all descendants, not only tandy1000/wares.
Full completion may span multiple campaigns. The server's health
takes precedence over speed and completeness.

## 3. Private manifests and completeness

Use machine-readable, durable state (e.g. SQLite plus exportable JSONL).
Retain dated raw listings and an exact source-relative path inventory
separately from downloaded files. For each entry record:

- Exact source URL and relative path, entry kind, parent directory,
  advertised size and modification date when supplied.
- Acquisition timestamp UTC, response/transfer status, final byte
  length, SHA-256, server validator/checksum where applicable.
- Local path mapping, original vs derived role, duplicate hash
  references, and earlier versions if present.
- Status such as discovered, partial, verified, deferred, unavailable,
  forbidden, excluded by policy, invalid response, or unresolved.
  Record error detail, retry count and last attempted observation.

Deduplicate offline processing by hash, while preserving every original
path and reference. Compare prior snapshots and do not erase an
unavailable listing or overwrite a known-good copy. Record directories
whose enumeration failed and any unknown descendants. Report exact
counts, verified/downloaded bytes, blocked paths, remaining queue,
and observation dates. Claim a complete mirror only relative to a
successfully enumerated, dated tree and verified allowed files; list
policy exclusions and failures separately. Do not infer that an
unreachable directory is empty. No live server totals are established
at protocol creation.

## 4. Offline analysis

Once the mirror is acquired, parse the local copy without additional
source requests. Partial indexes may be generated earlier, explicitly
labeled incomplete. Preserve originals and extract to a separate
private directory. Use bounded parsers and sandboxed extraction:
reject path traversal, absolute paths, unsafe symlinks/hardlinks,
device entries and resource-exhaustion/archive-bomb patterns.
Set depth, expanded-size and member-count budgets; retain unsupported,
encrypted or suspicious archives as opaque originals. Never execute
archived binaries/scripts merely to index them; native execution
belongs in disposable isolated emulated systems with separate
authorization and evidence. Hash original members and keep their
containing archive/member chains. Do not send the collection to
external indexing or OCR services.

Build a private searchable SQLite full-text index (or equivalent)
of extracted text, documentation titles, descriptions, release notes,
catalog data, archive and disk-image members, format signatures and
identification results, with local page/message/line locators.
Use local PDF text extraction first and local OCR only where useful;
flag uncertain OCR. Support relevant legacy encodings and formats
(ZIP, ARC, LZH, ARJ and disk images, etc.) using available safe tools;
record failures rather than claiming successful extraction. Mine
period listings, manuals, catalogs and messages for DeskMate names,
version, SDK, Tandy hardware, FF1/Atech/Rockwell, printing, native
formats and interoperability. Independently verify technical claims
before treating them as established. Keep historical personal
correspondence and sensitive data private.

## 5. Public annotated reference index

Produce a browsable Markdown overview plus a deterministic
machine-readable catalog (JSON or JSONL, split by category when
large) in docs/ecosystem/ or a documented dedicated reference
subdirectory. Publish reviewed bibliographic/structural facts and
independently authored annotations, not the downloaded directory
pages, full texts, OCR, media or unreviewed private database.
Preserve author/publisher attribution, source location, and historical
dates, distinguish original source claims from modern verification.
For relevant entries include:

- Stable archive item ID, exact original source URL, parent/containing
  archive and internal member locator, source date/version, size,
  SHA-256 where verified and verification status.
- Independently written description, category and relevance to
  specific project investigations; known and uncertain identifications.
- Product IDs from catalog.json, exact edition/runtime, format and
  extension/signature links, related technical reports and relevant
  specification sections; cross-reference alternative releases and
  duplicate media by hash without merging distinct editions.
- For documents: title/author/date where evidenced, relevant page
  or message locator, topics, catalog numbers and historic prices
  where available. Provide source links for every factual annotation.
- Flag missing and ambiguous resources, mismatched editions,
  OCR-derived uncertainty and source-specific evidence limitations.

Keep the broad archive manifest separately from curated DeskMate
annotations. A public broad path/hash index is acceptable where
reviewed, rights-compatible and non-sensitive; otherwise publish
coverage totals/categories and curated entries. Do not reproduce
personal contact details, licenses/serials, original source code,
proprietary font data, commercial disk contents, or adult-content
archives' sensitive member details. No blanket license claim over
third-party materials. Use the repository's normal REUSE sidecars
for original tools and authored metadata; preserve source notices.
Validate links from the saved listing and provenance without
repeated bulk network checks. Validate index schema, unique IDs,
references to real catalog entries, path containment, stable ordering
and duplicate handling. Test offline on synthetic fixtures; keep
research originals and searchable private database out of the
repository, wheel and sdist. Run the usual publication audit and CI.

## 6. Campaign handoff

In the next Codex prompt, begin mirror preflight and queue construction
early, preserve useful acquisitions in private storage, and prioritize
the Express Publisher/font research leads while transfers proceed
within approved process limits. Do not spend model tokens waiting
on network pacing. Continue technical research with already available
local resources. Following completion of the mirror, undertake
the comprehensive offline index and cross-reference campaign.
If blocked or unfinished, commit the safe tooling, metadata and
exact resumable handoff without implying all files were obtained.
Record usage at standard checkpoints; do not redeem the banked reset.
