# Source findings for Codex Monitor and Gas Town

See the [independent requirements](agent-orchestrator-requirements.md).
These are source findings. The upstream tests cited below were read without
running them.

## Codex Monitor

[Dimillian/CodexMonitor](https://github.com/Dimillian/CodexMonitor/tree/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5) at `dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5`
(2026-03-26), MIT, version 0.7.68. Desktop stack is Tauri 2, Rust, React/Vite
and Node/npm, with Codex CLI and Git. GitHub CLI is optional for GitHub
integration. Source builds use CMake and Windows uses LLVM/Clang for bindgen.
The repository has opt-in Windows packaging and Windows CI. It also has a
standalone Rust daemon, which avoids the desktop frontend but introduces a
separate control service. Windows CI is evidence of build intent, with lab
Windows 10 operation still unverified. [LICENSE](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/LICENSE), [README.md](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/README.md),
[package.json](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/package.json), [CI matrix](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/.github/workflows/ci.yml),
[Windows build job](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/.github/workflows/release.yml).

- **Owned sessions and steering.** The backend launches app-server in the
  workspace with piped stdio, initializes it, and tracks request IDs and
  workspace/thread routing in memory. Shared protocol code implements
  thread start/resume/read, turn start and steer with `expectedTurnId`.
  This is the closest analogue to S2's protocol surface. It enables
  experimental API in initialization. Retain S0's version and schema gate.
  The process helper has Windows executable lookup, cmd-shim handling and
  process-tree teardown. That is useful for launch qualification. Its
  PID-based teardown should never run against a saved PID without ownership
  proof. [app_server.rs](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/src-tauri/src/backend/app_server.rs),
  [codex_core.rs](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/src-tauri/src/shared/codex_core.rs),
  [process_core.rs](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/src-tauri/src/shared/process_core.rs).
- **Follow-up queue and loss.** The composer queue and in-flight state are
  per-thread React state. The active idle thread drains one item at a time
  and waits for a processing transition before advancing. The transport
  removes pending entries on timeout. The messaging hook can classify a
  thrown steer error as `steer_failed`, which the queue hook can convert into
  a later fresh send. The queue also prepends an item when its send callback
  throws. Those are distinct paths. An ordinary start error can instead be
  surfaced as blocked. If the server applied a steer before its reply was
  lost, a later queued turn can deliver the same intent again. A UI restart
  loses this queue, and thread resume/read gives no durable operation
  reconciliation by itself. Use the one-at-a-time and exact-turn behavior
  as reference. Preserve separate definite-rejection and uncertain-send
  states in our implementation. [useThreadMessaging.ts](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/src/features/threads/hooks/useThreadMessaging.ts),
  [useQueuedSend.ts](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/src/features/threads/hooks/useQueuedSend.ts),
  [queue and fallback tests](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/src/features/threads/hooks/useQueuedSend.test.tsx),
  [app_server.rs](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/src-tauri/src/backend/app_server.rs).
- **Approvals and visibility.** The UI passes workspace ID and request ID to
  the backend. The response core forwards that ID and result to the workspace
  session. The UI can remember a command prefix rule. Neither this forwarding
  path nor the daemon's shared TCP token supplies S0's one-shot authorization
  scoped to generation/thread/turn/item. The remote daemon supports session
  mutation and approval replies. Its event-to-view separation is useful,
  while its authenticated control surface belongs outside our Observatory.
  [useThreadApprovals.ts](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/src/features/threads/hooks/useThreadApprovals.ts),
  [useThreadApprovalEvents.test.tsx](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/src/features/threads/hooks/useThreadApprovalEvents.test.tsx),
  [codex_core.rs](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/src-tauri/src/shared/codex_core.rs),
  [codex_monitor_daemon.rs](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/src-tauri/src/bin/codex_monitor_daemon.rs),
  [Codex RPC handlers](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/src-tauri/src/bin/codex_monitor_daemon/rpc/codex.rs).
- **Git and scheduler scope.** Shared Git code creates named worktrees and
  supports commit/push actions. Workspace setup can be configured separately
  with a marker. These are operator tools. The inspected paths supply no
  durable trusted task intake, per-resource fencing, audited milestone
  publication transaction or restart scheduler. [worktree.rs](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/src-tauri/src/shared/workspaces_core/worktree.rs),
  [commands.rs](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/src-tauri/src/shared/git_ui_core/commands.rs),
  [useWorktreeOps.ts](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/src/features/workspaces/hooks/useWorktreeOps.ts).

## Gas Town

[gastownhall/gastown](https://github.com/gastownhall/gastown/tree/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476) at `466aa41c83ee73b1fa0eb79eb9d172fb1eca9476`
(2026-10-28), MIT. Go module minimum 1.26.2, toolchain 1.26.10. Full operation
uses Git, Beads (`bd`), Dolt, tmux and configured agent CLI(s).
Go/MSYS2 ICU/CGO Windows CI builds and vets the code. Upstream documents
native Windows as a minimal CLI path and WSL/Linux for tmux-backed roles.
Minimal mode leaves runtime instances manually managed. Full deployment
would add a separate database and service topology beyond the native lab.
[LICENSE](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/LICENSE), [go.mod](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/go.mod), [README.md](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/README.md),
[Windows smoke workflow](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/.github/workflows/windows-ci.yml).

- **Dispatch and resource ownership.** `gt sling` serializes dispatch for a
  bead. The dispatch path reads the current bead, checks status, uses an
  assignee lock around hook assignment, persists the work-to-agent link and
  then starts the session. Tests cover lock contention and release. These
  mechanisms cover duplicate concurrent dispatch and worker assignment. The
  app-server mutation boundary is outside their scope. The polecat lease formula tracks worker
  lifecycle and liveness. Neither the lock nor the lifecycle formula fences
  a separate native emulator. The Codex runtime preset invokes the CLI and
  includes `--dangerously-bypass-approvals-and-sandbox` by default, with
  configurable execution settings. This preset is unsuitable for the lab.
  [sling.go](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/cmd/sling.go), [sling_dispatch.go](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/cmd/sling_dispatch.go),
  [sling_dispatch_lock_test.go](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/cmd/sling_dispatch_lock_test.go),
  [polecat lease formula](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/formula/formulas/mol-polecat-lease.formula.toml),
  [agents.go](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/config/agents.go), [agents_test.go](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/config/agents_test.go),
  [Codex launcher](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/wrappers/scripts/gt-codex).
- **Recovery and task identity.** A dead assignee can trigger auto-force
  for an existing hook, while deferred tasks still need explicit force.
  The Witness can report recovered work and the Deacon's redispatch helper
  checks bead status and applies persisted cooldowns and attempt limits
  before using `gt sling`. The attempts track work recovery, without an
  app-server operation identity. A durable bead ID and live assignment
  checks do not pin the reviewed Git bytes or supply a separate lab
  dispatch grant. Treat automatic redispatch as incompatible for any worker
  with unresolved mutation or held resources. [sling_dispatch.go](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/cmd/sling_dispatch.go),
  [handlers.go](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/witness/handlers.go), [redispatch.go](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/deacon/redispatch.go),
  [redispatch_test.go](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/deacon/redispatch_test.go).
- **Worktrees and checkpoints.** The polecat manager can create a worktree
  from a start ref or attach a resumed branch. The integrity helper
  distinguishes proven structural damage from generic probe failure.
  Separate checkpoint code records branch and commit identity. A daemon
  checkpoint patrol actually stages all changes, unstages known runtime
  artifacts and attempts to exclude deletions before a WIP commit. Tests
  cover nested runtime artifacts. This is broader staging than R6 permits.
  Learn from structural classification and source-progress receipts while
  retaining our allowlist, checkpoint barrier and durable publication.
  The Refinery can process and land merge requests, with direct merge and
  auto-push defaults, beyond S3's draft publication authority.
  [manager.go](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/polecat/manager.go), [worktree.go](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/polecat/worktree.go),
  [worktree_test.go](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/polecat/worktree_test.go), [checkpoint.go](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/checkpoint/checkpoint.go),
  [checkpoint_dog.go](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/daemon/checkpoint_dog.go), [checkpoint_dog_test.go](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/daemon/checkpoint_dog_test.go),
  [engineer.go](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/refinery/engineer.go).
- **Browser surface.** The dashboard API supports POST operations such as
  running commands, sending mail and creating/updating issues. The CSRF
  mechanism protects a privileged console. Lab viewers must remain on the
  immutable Observatory projection. [api.go](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/web/api.go),
  [api_test.go](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/web/api_test.go).
