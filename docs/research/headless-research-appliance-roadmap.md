# Headless, reproducible emulator research appliance — deferred roadmap

**Mission-drift correction — 2026-11-11:**
Per [experimental laboratory posture](experimental-lab-operating-posture.md),
the existing Windows research VM is the accepted initial prototype.
Second-VM isolation, Linux migration and appliance hardening are **not**
prerequisites for a narrowly authorized first S0 canary. Prove a real
supervised turn in the working lab before future migration discussions.

**Status:** Long-term design proposal; no migration or implementation authorized by this document.  
**Recorded:** 2026-11-06.  
**Primary predecessor:** [DeskMate Observatory v2](observatory-v2-spec.md) and [Codex laboratory supervisor](codex-supervisor-design.md).  
**Initial target:** The current Windows 10 / 86Box / Codex research lab; eventual scope extends beyond DeskMate.

## Motivation and sequence

The DeskMate reverse-engineering lab has already produced components with broader uses: a native emulator controller, bounded read-only observation, semantic evidence replay, a browser observatory, and a proposed durable Codex supervisor. If the supervisor owns Codex sessions and all guest operations use the authenticated native automation interface, a logged-in Windows desktop and RDP session should no longer be necessary for normal experiments. That is a **hypothesis to test**, not proof that the current 86Box build runs without any display backend.

The longer-term opportunity is a reproducible **emulation research appliance**: create a disposable emulator instance from a pinned profile, run controlled experiments, preserve independently verifiable evidence, follow progress from a browser, and recover cleanly after process or host failures. Its reusable infrastructure should not assume Tandy, DOS, Calendar, or a single emulator.

**Order matters:** finish and verify the observer and supervisor on the known-working Windows platform first. Do not make Linux migration, containerization, or NixOS prerequisites for Observatory v2, the supervisor, or current DeskMate experiments. Retain the Windows lab and its working checkpoints as the reference and rollback path until a separate replacement passes comparison tests.

## Entry gate: Windows functionality demonstrated

Open the first Linux feasibility investigation only after the following have been exercised **in the real Windows lab**, not solely in mocks:

1. Observatory v2 provides durable normalized events, real Codex activity/approval reporting, immutable emulator snapshots, and a read-only LAN browser view. Browser refreshes and concurrent viewers cause **zero native automation requests and zero guest-time advancement**; owner-side scheduled publication is separately attributable.
2. A supervisor-owned Codex app-server or supported CLI run can start a bounded task, receive genuine structured events, handle an explicitly authorized approval, preserve source milestones, and report completion without a desktop-app session.
3. Service/collector and supervisor recovery is demonstrated after disconnect/restart. Replayed events and task revisions cannot trigger duplicate emulator input, double commits, or repeated job dispatch.
4. An authenticated controller enforces one owner per emulator, approved exact memory ranges and safe held observations. An observer, HTTP viewer, or other agent cannot bypass that boundary.
5. A realistic unattended run can be monitored from another LAN device with RDP disconnected. Guest disks, NVRAM, run logs, hashes and worktrees survive normally and are reconciled after an intentional failure.
6. The actual deployed binaries, dependencies, host resource use, disk/snapshot layout and startup procedure are recorded as a reproducible Windows reference. The operator explicitly authorizes the migration probe.

The intended work corresponds approximately to Observatory v2 milestones M0–M4 (including a useful LAN view), semantic evidence M5 where relevant, and supervisor phases S0–S6. It is a readiness gate rather than a new schedule that supersedes those plans.

## Key technical distinction: headless control versus headless rendering

- **Codex CLI/app-server, Python MCP and HTTP services, Git, build/test tools and Ghidra's batch analyzer** are candidates for unattended non-GUI operation. Verify the exact installed release and required runtime/toolchain; do not assume a desktop conversation can be attached to a new app-server process.
- **86Box's native automation endpoint** can operate the guest without desktop keyboard/mouse injection. However, the native screenshot route returns the last rendered framebuffer, and the installed 86Box build may still require a windowing/rendering backend. A held frame is not an instruction-synchronous screen.
- Distinguish **no logged-in user session**, **no desktop/window manager**, **a virtual display server only**, and **no display server/backend at all**. These are progressively stronger claims. Validate each in a clean process environment, not through a still-running interactive desktop.
- First prototype: minimal Linux with a virtual display (for example Xvfb) if required by the verified Linux 86Box build. Do not assume SDL dummy drivers, a no-Qt build or an alternate backend necessarily deliver correct native screenshots.
- A true framebuffer-only or server-only 86Box variant, including a possible upstreamable backend, is optional research after the virtual-display solution works. Treat UNIX-domain native sockets as an option to verify against the actual selected source revision; maintain authenticated exclusive ownership regardless of transport.

## Candidate host strategies

| Strategy | Primary value | Main tradeoff | Decision |
| --- | --- | --- | --- |
| Minimal Debian-class Linux VM, systemd, optional Xvfb | Small, mature compatibility baseline; low-risk port of existing tools | Linux 86Box dependencies, renderer and timing must be qualified | **First feasibility prototype** |
| Alpine Linux | Compact image and musl-based userspace | Binary/runtime availability, C/C++ media libraries, Ghidra/JDK and 86Box packaging may cost more time than they save | Compare only after functional Linux baseline |
| OCI/rootless containers | Per-worker dependencies, bounded filesystem/network access, immutable images | Emulator display, socket ownership, process lifecycle, disk volumes and access to shared tools complicate isolation | Containerize stateless analysis first; emulator only after tests |
| Nix-managed environment or NixOS | Declarative host/services, pinned derivations, rollback, machine recreation | Initial build/packaging complexity, nonfree inputs and secrets must stay outside the store | Long-term option after Linux parity |
| Custom display-independent 86Box build | Truly no window/display stack | Upstream maintenance and newly introduced emulator risk | Optional, conditional on measurable benefit |

A smaller distro is not automatically a faster emulator. Measure memory, CPU, boot-to-ready time, image size, sample throughput, guest-time accuracy, artifact hashes and maintenance cost against the Windows baseline.

## Proposed milestones (relative sequence, not committed dates)

| Stage | Work and deliverable | Acceptance gate |
| --- | --- | --- |
| **H0 — Reference capture** | Record Windows versions, 86Box patch/build flags, Codex integration version, Python/Ghidra/JDK dependencies, ROM/disk/NVRAM identity, automation protocol, reference traces, journals and failure-recovery outcomes. | A repeatable disposable Windows reference run and complete hash manifest. |
| **H1 — Linux emulator probe** | Fresh minimal Linux VM without a desktop environment; compile the pinned automation-enabled 86Box and try its supported rendering backends, initially with a virtual display if necessary. Boot a *copied* RSX fixture. | Authenticated one-owner connection; stable hold/step/key/regs/approved RAM/frame capture; matching visual and guest-state checkpoints; complete shutdown and disk integrity. |
| **H2 — Headless toolchain parity** | Install/provision Codex CLI/app-server, Git, Python, MCP/observer, Java and Ghidra headless; run the portable/deployment suites and a static analysis sample. | Supervised Codex task and source events without a logged-in GUI; tests and analyzer match the supported baseline, with documented platform differences. |
| **H3 — Unattended Linux services** | Use dedicated unprivileged service accounts, private launch receipts, bounded sockets, systemd lifecycle, append-only journals, immutable baselines and disposable writable disk copies. | Reboot, disconnect, crash and restart tests never silently reset, release, advance or re-run an emulator; stale state demands reconciliation. |
| **H4 — Container boundary trial** | Isolate stateless analyzers, tests and event-processing workers first; consider rootless emulator containers separately. | Identical evidence and lifecycle contracts; no control-socket exposure from browser, container network or untrusted workers. Keep native 86Box if containment worsens reliability. |
| **H5 — Nix/NixOS prototype** | Pin toolchain and build inputs, describe users/services/dependencies declaratively, keep external ROMs/media/secrets in a private, hash-verified store; construct a second fresh VM. | Build inputs, service configuration and artifact identities are reproducible; rollback works. Document nondeterministic factors explicitly. |
| **H6 — Reusable appliance** | Define emulator-neutral profiles, task/experiment envelopes, artifact manifests, permissions, portable runner adapters and optional multiple isolated workers. | A second independent emulator or application can use the same orchestration/observer infrastructure without DeskMate-specific assumptions. |

Each stage is a separate opt-in effort. Stop after any stage that meets the operator's practical goals; a working Debian/Xvfb service is a valid final outcome.

## Safety, provenance and reproducibility boundaries

- Keep the browser observatory **read-only**, with no hidden control routes. Codex/supervisor control and operator approvals use a separately authenticated channel. No public native automation endpoints.
- Never couple viewer demand to live emulator reads. Immutable owner-published snapshots and event records remain the only browser data source.
- Do not equate process liveness, event transport health or last real Codex activity. Do not fabricate agent progress during silence.
- Guest state is not Git state. Pin and preserve the emulator source and executable, build settings, ROMs, machine configuration, NVRAM, original disk hash, writable overlay, guest clock, resets, frame ages, tool versions, authorized memory spans, outputs and run journals.
- Do not store original DeskMate binaries, ROMs, private RAM, commercial media, passwords, tokens, personal data, or raw guest captures in the public repo or in world-readable Nix derivations/container layers. Keep encrypted/private stores and external hash manifests. Secrets may not be embedded in a Nix store path.
- Container or Nix reproducibility of a host build does **not** prove identical emulator timing, screenshots, asynchronous event ordering or guest application output. Validate these experimentally. Pin Nix flake inputs or equivalent immutable references and capture derivation/output hashes.
- Avoid retrying uncertain guest mutations, replaying actions after connection loss, or auto-starting/resetting a held guest during supervisor restart. Strong instance IDs, exclusive resource leases, durable idempotency keys and explicit operator intervention on ambiguity remain required.
- Preserve the Windows VM until two independently provisioned Linux disposable runs match the agreed behavioral/evidence controls and the operator approves cutover. Maintain a documented reverse migration and export of all private artifacts.

## Questions to resolve at H1/H2

1. Does the selected Linux 86Box source/build require Qt, SDL, X11, Wayland, Xvfb or another renderer for **fresh** native screenshots? What is the least expensive stable configuration?
2. How do authenticated automation endpoint ownership, launch tokens, guest holds and process exit behave under systemd and, later, containers?
3. Which Codex CLI/app-server distribution, Java/Ghidra release and C/C++ dependencies are actually supported on the target libc/architecture?
4. Do audio/video/input backends have hidden assumptions about an active host user session? Are guest rendering and key delivery equivalent to Windows?
5. What measurements justify Alpine, containers or NixOS beyond aesthetic preference for minimalism? Which dependencies and build outputs can truly be pinned?
6. Can the broader appliance support another emulator or application with only an adapter and profile, while preserving the same evidence/authorization contract?

## Future kickoff prompt (not executable work)

After the Windows gate passes, scope one **offline-first feasibility PR**: inventory the verified Windows baseline and Linux 86Box build requirements; create a disposable minimal-Linux prototype; demonstrate native framebuffer and automation parity on a synthetic canary before using private DeskMate media. Report exact commands, digests, limitations, resource use and a recommendation for the next stage. Do not migrate active checkpoints, shut down the Windows lab, or start container/NixOS work in that first PR.

**Decision checkpoint:** Revisit this roadmap when the Windows Observatory v2 and supervisor have completed their real-lab acceptance tests, or if a newly discovered Windows-specific limitation makes migration necessary sooner.