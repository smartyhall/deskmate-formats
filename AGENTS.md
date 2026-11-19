# Standing research instructions

## Accepted experimental laboratory risk — operator decision 2026-11-11

**Read [experimental laboratory posture](docs/research/experimental-lab-operating-posture.md)
when planning supervisor/86Box/Codex tasks.** The current Windows 10 VM is
a recoverable research lab, not a production vault. DeskMate binaries,
historical commercial media and other *local* lab resources are normal
research inputs, not inherently secret. Do not invent additional-VM,
restricted-user, blanket filesystem/network or exhaustive tool-isolation
prerequisites for the **separately authorized single-turn S0 canary** just
to avoid speculative, recoverable VM-local risks.

Prefer a snapshot/rollback, bounded check for actual host/external exposure,
one owned process, durable receipts, exact operator approval and measured
progress. Differentiate local software use from **public redistribution**
(existing commercial-binary Git exclusions remain), and risk acceptance
from **proved isolation**. Historical negative findings remain valid.
Existing production `LIVE_BLOCKERS` require a reviewed code change before
any live launch. This policy is not model-use or emulator authorization.
Challenge scope drift: evidence, consequence, rollback, minimum control.

- Preserve reproducibility: pin source/ROM/build revisions, machine configuration,
  commands, controlled variables, actual results and SHA-256 hashes. Distinguish
  runtime observations, source findings, synthetic tests and hypotheses.
- Preserve original commercial inputs and private evidence unchanged in the lab.
  Preserve application-generated synthetic-data research files byte-for-byte as
  eligible Git fixtures under `tests/fixtures/application-generated/`, with
  SHA-256 and experimental provenance. Back up config/NVRAM before changes; use
  disposable media. Format only a newly created, explicitly identified disk.
- Standing publication permission (granted by the operator 2026-11-08):
  eligible nonproprietary synthetic research files generated during this project,
  including newly supplied operator-produced native-format files containing
  synthetic test records, may be published to this repository without asking
  separately for each file. Check every candidate's actual bytes and provenance
  first. This grant does NOT cover real personal data, commercial software or
  media, credentials, private screenshots/memory, unreviewed third-party
  content, or other restricted/confidential inputs. Use a review PR.
  On 2026-11-08, the operator separately authorized ChatGPT as an independent
  reviewer to merge completed Codex PRs after scope review and passing checks
  during routine post-run housekeeping. This does NOT authorize Codex workers
  to merge their own PRs, bypass tests, operate a VM, spend model quota or
  publish private/commercial inputs.
- When a user requests publication of an eligible synthetic-data sample or
  native-acceptance candidate, commit and push the **actual independently checked
  binary bytes**, not just a private archive, SHA-256 digest or semantic JSON.
  Put an approved tool-generated candidate under
  `tests/fixtures/application-generated/<application>/`, clearly marked
  **tool-generated, not application-produced or native-accepted** until tested.
  Add the exact size/hash, source hash, generator command, evidence limits,
  expected semantic contents and accurate REUSE sidecar to the manifest/docs;
  test the committed bytes and ensure binary fixtures remain excluded from
  wheel/sdist. For authorized publication, push a dedicated branch and open a
  PR for independent review; the 2026-11-08 standing housekeeping grant
  allows ChatGPT to merge a reviewed, passing PR, but not the producing Codex
  worker to auto-merge. If publication is not authorized or is unsafe, keep
  the artifact private and report the precise blocker rather than silently
  substituting hashes for a usable file.
- Never commit commercial installers, ROMs, executables, complete installed
  trees, real user databases, private RAM, credentials, or personal information.
  Embedded native schema, indexes, and metadata in application-created test
  documents are not reasons to reject those files. Archive private screenshots
  and guest images outside Git.
- Interact with 86Box through its authenticated loopback automation socket.
  Avoid emulator-display clicks and host keyboard/mouse injection. Keep tokens
  out of logs; use bounded requests and never replay uncertain mutations.
- For interactive demonstrations, launch 86Box with a visible window by
  default, but continue guest control exclusively over the native socket.
  Never invoke Computer Use or inject host mouse/keyboard input to inspect
  the emulator over RDP without the user's explicit approval. Previous use
  disrupted the Windows remote session. Prefer subprocess/Win32 inspection;
  keep background/headless execution an explicit option.
- Keep reusable automation separate from experiment scripts. Portable tests may
  use committed application-generated synthetic-data fixtures but must not need
  ROMs, DeskMate executables, or a live emulator. Preserve experiment outputs
  in Git or a durable private archive before marking research complete.
  Report exact elapsed emulated time and observation limits.
- Put persistent conventions here and experiment details in research documents.
  Follow LICENSING.md and add accurate per-file REUSE sidecars.
- Inspect status/diffs, preserve local changes, fetch without resetting, and work
  on a dedicated branch. Run applicable portable checks before local commits.
  Push and open eligible synthetic research PRs only under the standing
  publication grant or other explicit authorization. Codex must not merge
  its own PRs; ChatGPT may independently merge ready PRs under the operator's
  2026-11-08 post-run housekeeping grant. Do not infer approval for unrelated
  repository mutations, unattended dispatch, emulator control or paid calls.

## Codex usage receipts — operator decision 2026-11-18

For every Codex research campaign, record available usage telemetry at startup,
each meaningful Git checkpoint, and completion/earliest safe stop in the
[central usage ledger](docs/evidence/codex-usage/README.md). Use a deterministic,
read-only collector rather than repeated model-driven monitoring. Capture what
the installed version actually exposes: model/effort, token counters, and
account quota windows identified by duration and reset epoch. If a source is
unavailable, record the gap; do not invent values. Import recoverable
project-attributable historical telemetry incrementally and deduplicate it.

Only allowlisted, sanitized project usage receipts belong in Git. Raw rollout
logs, prompts, responses, account/session identifiers, authentication material,
unrelated projects and exact banked-reset inventory stay private. Preserve
the receipt with each publishable checkpoint, especially near exhaustion.
When little quota remains, checkpoint earlier and stop at a coherent boundary;
do not wait for an additional model turn to preserve existing work. Never
redeem a usage reset, purchase credits, or launch extra model turns merely to
measure quota without separate operator authorization. This policy does not
authorize unattended dispatch or expand existing live-launch gates.

## Sampled Music listening references — operator decision 2026-11-18

Maintain the [fixed synthetic listening suite](examples/music-listening/README.md).
At each major sampled-renderer fidelity milestone, regenerate the same
musical controls in native DeskMate and with the independent renderer;
publish the actual matched, eligible WAV files, provenance and quantitative
comparisons in a review PR. Preserve earlier milestones and immutable native
score/instrument identities. Label capture path and remaining approximations.
Use original test music with both independently synthesized instruments
and the actual Tandy-provided musical instrument bank. On 2026-11-18 the
operator explicitly authorized publishing rendered performances of original
test compositions using Tandy's supplied musical instruments, based on
their intended use in user compositions. Record that basis and source
provenance; do not claim a verified express vendor license or ownership of
underlying samples. Review any applicable contrary terms before publication.
Do not publish OEM SND files, extracted PCM, isolated sample dumps, historical
compositions or other third-party material under this grant. See LICENSING.md
and the listening suite for the distinction. Implement a manifest-verified,
path-specific WAV exception
to the publication audit with regression coverage; do not relax the general
audio embargo or package research binaries in wheel/sdist. Record a blocked
native re-capture honestly rather than substituting renderer output or
mislabeling a prior reference as fresh.

## Draw visual references and Classic UI — operator decision 2026-11-19

Maintain the [Draw comparison library](examples/draw-comparison/README.md).
Use its four original featured drawings (primitive/style chart, technical
plan, compound illustration and typography) and existing pinned native
diagnostics. Establish an immutable baseline before major renderer changes;
at each major shared-graphics interpreter or rendering milestone regenerate
the same genuine native and independent visual comparisons, publish actual
eligible images and provenance/metrics, and retain earlier outputs.
Extend the existing audit narrowly for manifest-listed comparison imagery;
keep raw framebuffer captures, original historical art and proprietary
resources private. Distinguish exact native pixels from scalable vector
approximations. Do not claim a missing native comparison was captured.

The [Draw Workbench](examples/draw-workbench/README.md) must reproduce the
actual original Draw UI and workflows as closely as practical, using
independently authored assets and native behavioral evidence. Integrate
modern QoL in the same visual language. The offline browser viewer/editor
must treat native forms as authoritative and enable only validated edits;
verify browser-written FIGs in original DeskMate. Preserve unsupported
records or reject affected operations. The illustrative AROS concept is
not a compatibility claim or authoritative UI specification.

## DeskMate ecosystem preservation — operator decision 2026-11-19

Maintain the [ecosystem catalog](docs/ecosystem/README.md) as a secondary
research track: identify commercial and community DeskMate software,
acquire media privately, inventory native file formats and eventually
extend the independent recovery suite to those formats. Distinguish
documented products from acquired and installed copies and distinguish
native/runtime applications from DOS launcher entries. Preserve exact
editions and provenance. Use the [enthusiast demonstrator](docs/ecosystem/demonstrator.md)
as a separate, richly populated living-system target and native fixture
laboratory; do not modify verified core research baselines to build it.
Do not publish commercial media or a preinstalled commercial disk
image. The [acquisition handoff](docs/ecosystem/acquisitions.md) pins
the two operator-provided archives for the next campaign. In the near
term prioritize core Draw/font reconstruction and independent font
conversion, with bounded adjacent acquisitions and inventory.
