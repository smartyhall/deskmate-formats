# Deterministic procedure candidates — 2026-11-26

The Supervisor ships five procedures: `hash-files`, `fixture-compare`,
`portable-tests`, `package-build`, `reuse-lint`, `repository-audit`. This note
records the procedures the rest of the laboratory actually needs, what each one
would have to declare, and the bar for registering it.

**Rule:** a procedure is registered for execution only when its inputs can be
bound by content, its fixed script can be reviewed as a whole, its result is a
bounded deterministic artifact, and its failure states map onto the existing
exit table. Anything that samples a live system, reaches the network or depends
on wall-clock time is not eligible until it says so in its descriptor.

## Ready now

### Archive identification and extraction

- **Inputs:** the archive directory (named paths), never the whole disk.
- **Executes:** `fixed-script` — a Python reader over `zipfile`/`tarfile`, with a
  hard entry count, per-entry and aggregate limits, and no path traversal
  (resolve each member, refuse anything outside the destination).
- **Resources:** `evidence:<canonical dir>` read-only lease; `build:<dir>` write
  lease if extraction produces files.
- **Result:** a manifest of members with CRC32/SHA-256, sizes, and detected
  format by signature; a refusal list for unsafe members.
- **Why it is ready:** it is pure local file reading with a stable archive
  format, and the existing hash/compare scripts already prove the bounded
  streaming pattern it needs.

### Archive integrity verification

A narrower variant of the above: compare member CRCs and the container digest
against a reviewed expected manifest. `fixed-script`, no extraction, no write
lease. This is the procedure our 157-file archive candidate corpus actually
needs.

### Evidence hashing and validation

- **Inputs:** a reviewed manifest of evidence paths plus their expected digests.
- **Executes:** `fixed-script` (`sha256` over bounded streams).
- **Result:** per-file match/mismatch, aggregate digest, and an explicit
  `unreachable` list for files that disappeared.
- **Note:** this is `hash-files` plus an expectation table; it should be a
  procedure variant rather than a new script.

### Laboratory inventory

- **Inputs:** an inventory of paths (private state roots, not the home
  directory), enumerated by the *planner* rather than the child, so the file set
  is frozen in the plan like any other input binding.
- **Executes:** `fixed-script`.
- **Result:** sizes, mtimes, digests, and which private state directories are
  present, absent, or unreadable.
- **Care:** inventory output describes private operator state. It must never be
  published to the rendered Observatory without redaction, and the plan must
  record that it contains private paths.

### Native fixture comparison

Already effectively present as `fixture-compare`. The extension that matters is
a *versioned* expectation file with its own digest, so a reviewer approves the
expected bytes rather than the path that happens to contain them. Small change,
high value.

## Needs qualification first

### Browser and website qualification

- **Inputs:** the built site directory and the qualification script.
- **Executes:** `third-party-tool-over-repository-data` — a headless browser is
  a large external tool with its own update cadence; the plan must record its
  version and binary digest.
- **Resources:** a `preview:<dir>` lease (already modelled), plus a loopback
  port reservation, which the registry does not model yet.
- **Result:** per-route status, console error count, and digests of rendered
  text — never screenshots inside the attempt directory without a manifest.
- **Blocker:** the port reservation is a real gap. Two campaigns qualifying two
  sites on one port would collide with no lease to say so.

### Visual regression comparison

- **Inputs:** two image sets plus a reviewed threshold.
- **Executes:** `fixed-script` if the comparator is ours; the comparison itself
  is deterministic once the images exist.
- **Blocker:** image comparison is only deterministic with a pinned decoder.
  Pillow's version changes pixel handling across releases, so the plan must bind
  the decoder's version and digest, exactly as it binds the interpreter.
- **Policy:** the resulting diff images are temporary review artifacts. They are
  not committed unless a manifest entry, a licence file and a reason exist.

### Ghidra import and structural analysis

- **Inputs:** a reviewed binary plus a reviewed Ghidra project directory.
- **Executes:** `third-party-tool-over-repository-data` with a JVM, a large
  install, and a headless analyzer whose output depends on Ghidra's version.
- **Result contract:** import success, function count, symbol table digest,
  and a decompiled-function manifest. Version-stamped, because a Ghidra upgrade
  changes every number.
- **Blocker:** the tool is hundreds of megabytes and lives outside the
  repository. The plan must bind its install digest, and the procedure must
  refuse when the analyzer's version differs from the reviewed one. This is the
  procedure most likely to produce an unreproducible result, and it should say
  so in its descriptor.

## Not eligible

- Anything that reads the live Desktop application, its token or its state.
- Anything that dispatches a model turn (see the upstream note: that is either
  paid SDK or nothing).
- Anything that samples a running emulator: the result depends on the machine
  state, not on reviewed inputs.

## The bar for registration

A candidate becomes a registered procedure when all of the following are true:

1. Its inputs can be expressed as patterns or named paths and bound by content.
2. Its fixed script is small enough to review in one sitting, and its limits are
   passed in argv so they appear in the plan.
3. It declares `executes` and `network` truthfully.
4. Its resource needs are representable as leases over canonical identities.
5. Every outcome maps onto one of the six existing terminal states, and partial
   output is bounded.
6. A failure is recoverable: the attempt directory can be inspected after the
   fact without re-running anything.
7. At least one harmless, real run has been qualified on the platform where it
   will be used.

None of the "needs qualification" items above meets conditions 4 and 7 today.
The port reservation and the decoder/analyzer version binding are the two
missing pieces that unblock most of them.
