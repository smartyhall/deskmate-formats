# Source findings for Symphony and Command Center

See the [independent requirements](agent-orchestrator-requirements.md). The
observations below come from reading default-branch snapshots. Test descriptions
identify checked-in coverage and were inspected as source. Neither project was
installed or run.

## Symphony

[openai/symphony](https://github.com/openai/symphony/tree/be10a1b79df723d6d7612b5651c8522704dafb2e) at `be10a1b79df723d6d7612b5651c8522704dafb2e`
(2026-09-15), Apache-2.0 with upstream NOTICE. Reference implementation
`symphony_elixir` 0.0.3 uses Elixir 1.19.5 and Erlang/OTP 28 in mise, with
Phoenix/LiveView and Bandit, Bash for local Codex launch and shell hooks,
Codex app-server, and a configured tracker. SSH workers are optional. Its
release workflow targets Linux and macOS only. Native Windows 10 would
require launch, hooks and packaging work plus runtime qualification.
[LICENSE](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/LICENSE), [NOTICE](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/NOTICE), [SPEC.md](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/SPEC.md),
[mise.toml](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/mise.toml), [mix.exs](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/mix.exs),
[release matrix](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/.github/workflows/burrito-release.yml).

- **Dispatch and isolation.** The GenServer polls tracker candidates, sorts
  eligible issues, checks dependency/state/label and capacity rules, revalidates
  a candidate by tracker ID, then launches a supervised task. Claims, worker
  capacity, blocked entries and retry timers are process state. Workspace
  isolation is a normalized, validated per-issue directory with optional
  create/run/remove hooks. The example workflow clones a repo and delegates
  commits, pushes and PRs to agent instructions and skills. The scheduler
  supplies neither a Git worktree lease nor a publication receipt.
  [orchestrator.ex](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/lib/symphony_elixir/orchestrator.ex), [workspace.ex](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/lib/symphony_elixir/workspace.ex), [agent_runner.ex](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/lib/symphony_elixir/agent_runner.ex),
  [example workflow](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/WORKFLOW.md).
- **Owned protocol and approvals.** The runner starts its own app-server,
  initializes and starts a thread, then issues sequential turns on that
  session while the issue is eligible. It closes the session at the end of
  the worker attempt. The inspected runner has no operator follow-up queue
  or exact-turn steering path. Approval handling can stop/block the issue.
  With policy `never` the adapter sets its auto-approval flag and responds
  to supported approval requests, including command and MCP approval
  prompts. Its tracker tools can also issue tracker requests under service
  credentials. These are different authority defaults from S0.
  [agent_runner.ex](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/lib/symphony_elixir/agent_runner.ex), [app_server.ex](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/lib/symphony_elixir/codex/app_server.ex),
  [dynamic_tool.ex](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/lib/symphony_elixir/codex/dynamic_tool.ex),
  [approval and input blocker tests](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/test/symphony_elixir/app_server_test.exs).
- **Visibility.** Status snapshots cover running, blocked and retrying work.
  The Phoenix router includes a POST refresh route that asks the scheduler
  to trigger a poll. The read projection is a useful pattern, but the HTTP
  surface as shipped is coupled to dispatch.
  [router](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/lib/symphony_elixir_web/router.ex),
  [presenter](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/lib/symphony_elixir_web/presenter.ex),
  [HTTP and LiveView tests](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/test/symphony_elixir/extensions_test.exs).

### Failure traces

**A. Lost acknowledgement.** `AppServer.start_turn` sends `turn/start`
before waiting for the matching transport ID. Timeout or port exit yields
an error. The response supplies the turn ID. Notifications encountered
while waiting do not reconcile the mutation. The runner closes the port,
and an ordinary worker failure can enter retry/backoff. On restart the
orchestrator starts with empty claims and refetches active issues. A new
attempt starts a fresh thread in the reusable workspace. If the old turn
already acted and the issue still qualifies, the work can run again.
Tracker issue identity and filesystem artifacts drive rediscovery.
The path has no durable mutation identity or exact history read before
resending work. [app_server.ex](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/lib/symphony_elixir/codex/app_server.ex), [agent_runner.ex](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/lib/symphony_elixir/agent_runner.ex),
[orchestrator.ex](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/lib/symphony_elixir/orchestrator.ex), [restart specification](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/SPEC.md#143-partial-state-recovery-restart),
[worker exit and retry tests](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/test/symphony_elixir/core_test.exs).

**B. Held experimental state.** Startup sweeps terminal workspaces. Removal
can invoke a shell hook and then delete the workspace. Active work can be
stopped and retried after stalling, and a fresh attempt runs before/after hooks
around the reused workspace. No inspected claim or cleanup gate knows about a
held native controller. Symphony itself issues no 86Box command. A workflow
that carries a clone, controller credentials or emulator lifecycle hooks
could delete its files, disturb the hold or start conflicting work.
This is a conditional integration hazard. [orchestrator.ex](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/lib/symphony_elixir/orchestrator.ex),
[workspace.ex](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/lib/symphony_elixir/workspace.ex), [agent_runner.ex](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/lib/symphony_elixir/agent_runner.ex),
[stall and blocked-worker tests](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/test/symphony_elixir/orchestrator_status_test.exs).

**C. Rewritten or duplicated task.** In-memory ID checks suppress another
dispatch while the same issue is claimed. Before dispatch the tracker refresh
returns the current issue record. The prompt renders this issue into the current
workflow template. The workflow store reloads edited local files and keeps
the last good parse. Neither a tracker label nor that parse binds a reviewed
Git object or grants a separate dispatch receipt. An eligible issue edited
after discovery can supply different prompt text at dispatch. Templates that
include issue descriptions expose the agent to instructions from whoever can
edit them. Local workflow writers also control executable shell hooks.
[orchestrator.ex](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/lib/symphony_elixir/orchestrator.ex), [workflow_store.ex](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/lib/symphony_elixir/workflow_store.ex), [prompt_builder.ex](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/lib/symphony_elixir/prompt_builder.ex),
[workspace.ex](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/lib/symphony_elixir/workspace.ex), [candidate revalidation tests](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/test/symphony_elixir/core_test.exs).

## Command Center

[cgeene/commandcenter](https://github.com/cgeene/commandcenter/tree/85f39956976ceb03aec668bd5955e5304ddd5dae) at `85f39956976ceb03aec668bd5955e5304ddd5dae`
(2026-07-29), MIT, version 0.1.0. Node 22+, Hono, better-sqlite3 and node-pty,
tmux, Git and configured Codex or Claude CLI. GitHub CLI is used for PR
operations. The deployment guide covers launchd on macOS and foreground
operation on Linux. POSIX shell, tmux, terminal/process inspection and the
package's postinstall command make native Windows a substantial port.
[LICENSE](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/LICENSE), [package.json](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/package.json), [deployment.md](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/docs/deployment.md),
[architecture.md](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/docs/architecture.md).

- **Queue and lifecycle.** SQLite stores task and agent rows. The scheduler
  separates cron enqueue from auto-spawn with a master switch, windows,
  dependency checks, concurrency and daily budgets. Claim is a conditional
  status update. Worker identity is tracked through tmux target, PID and
  provider hook/session data. Codex uses the interactive CLI or CLI resume
  in a managed pane. Task status, stored provider ID and pane evidence support
  recovery, but none represent a durable app-server request ID.
  [tasks.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/db/tasks.ts), [scheduler.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/daemon/scheduler.ts),
  [spawn.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/daemon/spawn.ts), [worker-resume.test.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/test/worker-resume.test.ts).
- **Git and publication.** Worker worktrees use task branches. New branches
  prefer the fetched origin default, with a logged local HEAD fallback. Review
  worktrees are detached. There is a separate snapshot-first publication mode
  for human review before committing/pushing. Other modes instruct workers to
  commit/push/open a draft PR. PR sync and `prdraft.ts` manage discovered PR
  state, including ready/draft transitions. These are useful separable patterns
  for S3. The inspected worker prompt and PR wrappers do not supply the lab's
  file eligibility audit or an atomic commit/push/PR receipt.
  [worktree.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/daemon/worktree.ts), [reviewsnapshot.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/daemon/reviewsnapshot.ts),
  [spawn.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/daemon/spawn.ts), [prsync.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/daemon/prsync.ts),
  [prdraft.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/daemon/prdraft.ts), [worktree.test.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/test/worktree.test.ts),
  [prdraft.test.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/test/prdraft.test.ts).
- **Browser and approvals.** API supports sending text into a waiting agent
  and terminal WebSockets can write to the PTY. Automated delivery checks for
  pending questions, permission menus and unsubmitted drafts. This protects
  ordinary terminal interaction, while our approval scope requires a typed
  app-server request identity and a separate authenticated decision path.
  The browser API is a control console.
  [api.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/daemon/api.ts), [resume.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/daemon/resume.ts),
  [termws.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/daemon/termws.ts), [agent-send.test.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/test/agent-send.test.ts).

### Failure traces

**A. Lost acknowledgement.** There is no equivalent app-server RPC in the
inspected Codex dispatch path. The closest mutation is submitting a prompt
to Codex in tmux. A direct send accepts agent ID and text, with no idempotency
key. `resumeAgent` sends first and updates local state afterward. For
persisted notifications, the flush deletes pending rows only after delivery
returns. If Enter reaches the pane and the daemon dies before deleting the
row, boot re-adopts pending deliveries and the watchdog can resend when that
pane is again clear and the row remains eligible. A direct HTTP caller
repeating a lost-response send can also duplicate input. The local session ID
and tmux success give no authoritative identity for that submission.
The queue test covers normal boot adoption and pending-row deduplication.
It does not establish exactly-once delivery across the send/delete gap.
[api.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/daemon/api.ts), [resume.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/daemon/resume.ts),
[notifqueue.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/daemon/notifqueue.ts), [index.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/daemon/index.ts),
[delivery-queue.test.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/test/delivery-queue.test.ts).

**B. Held experimental state.** The watchdog checks tmux and avoids a wave of
false worker deaths when observations are unreliable. Confirmed missing
workers or abandoned spawns can requeue once across both causes. The spawn
path can reuse the task's worktree and provider session. This recovers
interactive coding but does not fence a surviving emulator controller.
The watchdog documents an interruption between window creation and recording
the pane target where an unclaimed window cannot be found by that row. If a
held emulator or its credentials were coupled to a worker, requeue could
introduce conflicting custody even with the original worktree preserved.
Cancellation also supports explicit process teardown and worktree removal.
No emulator effect was observed or is built into these paths.
[scheduler.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/daemon/scheduler.ts), [spawn.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/daemon/spawn.ts),
[scheduler.test.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/test/scheduler.test.ts), [cancel.test.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/test/cancel.test.ts).

**C. Rewritten or duplicated task.** The task creation route validates the
body and inserts a row with a numeric ID. The direct task path has no caller
key that would collapse two identical creates into one row. The claim guard
covers a single row. Task edits can invalidate triage, and spawn reads the
task prompt from the current row. This path has no reviewed Git-object
binding. Direct-dispatch eligibility plus the relevant scheduler policy
allows submitted text to enter worker prompts. Authentication, cron open-task
guards and provider profiles address other risks. They supply no S1-style
authorization for the exact text and revision. [api.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/daemon/api.ts),
[tasks.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/db/tasks.ts), [scheduler.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/daemon/scheduler.ts),
[spawn.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/daemon/spawn.ts), [tasks.test.ts](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/test/tasks.test.ts).
