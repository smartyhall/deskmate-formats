# S3 Windows workspace-write downgrade: pinned-source diagnosis

The first real S3 experiment stopped before turn/start. The original plan,
staged config, native thread result, read-only SQLite operation ledger and blocked
outcome were inspected privately. All original receipts and the S1 queue remain
unchanged. The consumed claim is
`883aa0e5db4fbc586a788caff894273fae0deb24ce144163ed8de290bc8bade5`.
No native app-server, model turn, setup helper or emulator was launched in this
investigation. No existing native installation or Windows permissions were changed. Packaging
checks use a separate private Python virtual environment.

## Cause established at pinned source level

Upstream revision is `6ff1e1ca3b30fc8b914720681fcf5fe62e95f856`, Codex 0.166.0.
Downloaded source bytes were checked against that revision's Git tree blob IDs;
the private inspection inventory also retains SHA-256 hashes. Relevant functions:

- [config_toml.rs: effective_sandbox_mode](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/config/src/config_toml.rs):
  Windows + Disabled level + WorkspaceWrite yields ReadOnly, before construction
  of the permission profile. The workspace-write options are consequently absent.
- [windows_sandbox.rs: resolve_windows_sandbox_mode and WindowsSandboxLevelExt](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/core/src/windows_sandbox.rs):
  explicit windows.sandbox takes precedence; unelevated selects RestrictedToken,
  elevated selects Elevated, otherwise legacy feature flags select the level.
- [features/src/lib.rs](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/features/src/lib.rs):
  experimental_windows_sandbox and elevated_windows_sandbox both default false
  (removed-stage compatibility flags). Enabling arbitrary tools is unnecessary.

The original config had workspace-write plus both tmp exclusions, no windows table
and neither legacy flag. Native returned exactly readOnly/networkAccess false.
This deterministic source path explains that observation, including missing tmp
fields. It is a source-derived diagnosis consistent with the retained runtime
receipt, not a new native reproduction or proof that no other native config layer
could influence the result.

## Small correction and boundaries

S3 prepare-live now requires `--windows-sandbox unelevated` and rejects absent or
unsupported selections before reserving a workspace. The driver independently
checks the selection, writes the Windows table only for live editing, and freezes
windows_sandbox plus the config hash in the canonical plan. Offline preflight and
prelaunch validation refuse a missing/mismatched backend. Existing config hashing,
installed-code pins, exact-plan grants and workspace provenance remain in force.
The native effective-policy verifier is unchanged: it still refuses read-only,
extra writable roots, network, approvals or reviewer drift before turn/start.

No shell, JS, MCP, web, subagent or Git capability is enabled. S0/S2 retain their
existing read-only config and reject this S3-only option. Synthetic tests cover
selection, immutable configuration/digest, fallback before turn submission and
permanent attempt fencing. The original attempted state is never upgraded or
rewritten; changed implementation pins cannot authorize an old plan.

## Windows compatibility and setup limits

| Backend | Pinned selection/setup path | Decision |
| --- | --- | --- |
| Disabled | Default without explicit mode/legacy flags; workspace-write downgrades | Refuse for S3 |
| Unelevated | windows.sandbox=unelevated; RestrictedToken; legacy capability-SID token/ACL path | Only offered S3 backend; operational verification outstanding |
| Elevated | Elevated level; prepare_elevated_sandbox invokes elevated setup if incomplete, then setup refresh | Not offered; provisioning/elevation requires separate operator action |
| MXC | Separate sandbox implementation/availability selection, not the legacy level; explicit Mxc maps to Disabled in from_config | Not offered or assumed available in this Windows 10 lab |

In [windows-sandbox-rs/src/lib.rs](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/windows-sandbox-rs/src/lib.rs),
run_windows_sandbox_legacy_preflight resolves permission roots, creates home state,
obtains root capability SIDs and calls apply_legacy_session_acl_rules. Runtime
capture constructs a restricted token; it rejects restricted read/deny-read modes
requiring the elevated backend. Our profile retains ordinary full-disk read
semantics; it does not add deny-read policy.

[spawn_prep.rs](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/windows-sandbox-rs/src/spawn_prep.rs)
persists capability state, grants write ACEs on allowed roots, adds deny-write ACEs
on protected paths, and protects workspace .codex/.agents directories. Several ACL
helper errors are intentionally ignored upstream. Therefore even a successful
setup return or reported policy cannot establish actual writes or confinement.
The Windows account/filesystem must permit these operations on the exact roots;
a filesystem/ACL incompatibility is a blocker, not permission to elevate silently.

The elevated [setup.rs](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/windows-sandbox-rs/src/setup.rs)
path uses setup/runtime helpers and sandbox-user state; provisioning can involve
administrative account, ACL and firewall changes. None were performed. No
alternative VM or new security framework is proposed.

## Fresh experiment prerequisites

The next task manifest proposes revision 2, a new idempotency key, and reviewed
main at the start of this correction as its source parent (the exact SHA is in
ops/tasks/calendar-listing-alarm.json). That parent already contains the unchanged
Calendar source and the first failure report. The task commit independently binds
this updated proposal and corrected installed worker; source_revision need not be
the implementation merge itself. Review ancestry and both exact file blobs after
merge. No acceptance, preparation or dispatch has occurred.

Before any fresh plan: review/merge/install this correction independently; obtain
separate approval for the bounded native setup/write verification described in the
S3 runbook; establish operational compatibility for the exact disposable roots;
then independently discover/review/accept revision 2 and prepare a new immutable
plan. Recheck model, effective policy, tool restrictions, staged auth, 300-second
observation, 10-second RPC and 1800-second portable validation. Obtain fresh
exact-plan dispatch, model-use, lab-risk and conditional-checkpoint grants.

The previous claim, tokens and digest are permanently unusable. This correction
removes the known disabled-backend configuration error; native apply_patch and
operational write access remain explicitly unverified until separately authorized
experiments produce evidence. A fallback still stops before a model turn.
