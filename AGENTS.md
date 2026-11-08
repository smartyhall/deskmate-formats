# Standing research instructions

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
