# Experimental lab operating posture and scope control

**Operator decision: 2026-11-11.** Standing guidance for the single-user
Windows 10, DeskMate, 86Box and Codex research laboratory. Read with
[AGENTS.md](../../AGENTS.md), the [supervisor design](codex-supervisor-design.md)
and [project status](../../PROJECT_STATUS.md).

## Operating objective and accepted risk

Prioritize **working, observable, reproducible and recoverable experiments**
over speculative or production-grade hardening. The operator expressly accepts
ordinary **VM-local experimental risk** in the existing Windows 10 lab VM.
Historical commercial DeskMate executables and installation media, ROMs,
synthetic files, and other lab inputs are **not automatically sensitive**
because they are proprietary, old, or outside a dedicated scratch folder.
Reading and using local copies to study native formats is routine research.

For the **first narrowly scoped, separately authorized S0 app-server canary**,
the project does **not** require a second VM, a restricted Windows user, full
filesystem/network confinement, prevention of every possible Codex tool, or a
general security architecture simply to eliminate recoverable VM-local risks.
Use the known working lab, a snapshot or credible rollback path, one owned
process/turn, durable receipts, and a brief check for real outside-VM exposure.

**Risk acceptance is not a claim of technical isolation.** The 2026-11-11 S0
audit accurately observed that a sanitized environment and cwd alone do not
stop a process from reading/writing other accessible VM files or reaching
loopback endpoints. Preserve those facts. What changed is the operator's
**acceptance criterion for a minimal protocol experiment**, not the evidence.

## Distinct boundaries

**Local research:** Authorized tasks may inspect locally installed historical
commercial software, reverse engineer it, work with synthetic fixtures, and
eventually operate 86Box through the native controller. Avoid emulator use
*during the first S0 canary* to isolate the protocol test, **not** because
DeskMate files require extraordinary protection. Take snapshots or use
disposable media for consequential guest mutations.

**Host and external effects:** VM-local risk acceptance does not automatically
extend to writable host shares, hypervisor management, unrelated LAN systems,
credentials for other accounts, or external services. Before the initial
canary, inventory concrete host/share/credential exposure relevant to the
run and resolve specific high-consequence paths proportionately. Do not
transform that bounded inventory into another unrelated security campaign.

**Public publication:** Local possession, analysis and use do not inherently
confer permission to redistribute third-party installers, ROMs or executables.
Retain the existing public Git publication rules, provenance, synthetic
fixture policy, licensing and exclusions for personal data/credentials.
This **distribution boundary is distinct from local experimental access**.

**Authorization:** Agreeing to this operating posture is not authorization
for an actual paid model call, arbitrary host changes, a specific emulator
mutation, unattended dispatch or Codex self-merging. Require ordinary explicit
approval for the specific live invocation and any consequential external
action.

## Minimum initial S0 canary and implementation

A reviewed, named **experimental-lab** launch profile may deliberately accept
the VM's normal permissions instead of claiming a stronger OS sandbox.
The [experimental profile implementation](codex-supervisor-s0-live-canary.md)
now replaces the former unconditional gate only for explicitly selected
`experimental-lab` plans with two exact-plan confirmations. Default live modes
retain `LIVE_BLOCKERS`. Review/merge of that implementation and separate model-use
authorization are required; never bypass it through private reflection.

For the first real canary, use a pinned Codex version/schema, one newly owned
app-server child, one exact approved model/effort, one short harmless turn,
stable request identities, durable intent/response receipts, no automatic
replay on ambiguous acknowledgements, finite observation, terminal/history
verification, and direct-child cleanup. If descendant behavior is unverified,
record the limitation; do not claim full process-tree containment.
The fixed no-tools sentinel prompt is a **behavioral test, not an OS control**.
Record unexpected activity honestly. The first canary should be small, not
an exhaustive demonstration that no unwanted tool could ever run.

## Mission-drift test for every proposed blocker

Before adding a new prerequisite, say:

1. Which boundary is affected: recoverable VM-local files, evidence integrity,
   host/external effects, public redistribution, or model usage?
2. Is there a measured failure, a version-pinned source finding, or merely a
   hypothetical failure mode?
3. What could actually be lost or changed, and what is the shortest rollback?
4. What **smallest** control permits the next informative experiment?

Do not repeatedly turn speculative VM-local concerns into mandatory long
projects or condition a short protocol smoke test on building a production
enclave. Preserve evidence quality and distinguish verified limits from
claims of impossibility. A prior `BLOCKED` conclusion may remain accurate
**under its old chosen criteria** while the operator subsequently **accepts
the VM-local risk and revises those criteria**.

## Sequence and historical audit

First prove one supervisor-owned real S0 turn in the existing VM, **after**
review of the experimental launch profile and exact operator authorization.
Then prove one Git-driven S2 task and, later, task-scoped emulator control.
A second VM, extensive Windows confinement, daemonization and Linux/NixOS
migration are not dependencies for the S0 handshake.

The [2026-11-11 readiness report](codex-supervisor-s0-readiness.md) remains
a faithful record of experiments and the requirements applied *at that time*.
This later **operator policy** supersedes its recommendation to prove a new
OS-level/second-VM isolation boundary before a narrow S0 canary, but does not
retract any empirical observation or itself authorize model usage.
