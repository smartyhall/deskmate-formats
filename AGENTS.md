# Standing research instructions

- Preserve reproducibility: pin source/ROM/build revisions, machine configuration,
  commands, controlled variables, actual results and SHA-256 hashes. Distinguish
  runtime observations, source findings, synthetic tests and hypotheses.
- Preserve original evidence unchanged outside Git under the laboratory root.
  Back up configuration and NVRAM before changes; use disposable working media.
  Partition/format only a newly created, explicitly identified emulated disk.
- Never commit proprietary media, ROMs, executables, original documentation,
  private databases, raw memory/screenshots, credentials or personal information.
  Public reports contain sanitized independently authored findings only.
- Interact with 86Box through its authenticated loopback automation socket.
  Avoid emulator-display clicks and host keyboard/mouse injection. Keep tokens
  out of logs; use bounded requests and never replay uncertain mutations.
- For interactive demonstrations, launch 86Box with a visible window by
  default, but continue guest control exclusively over the native socket.
  Never invoke Computer Use or inject host mouse/keyboard input to inspect
  the emulator over RDP without the user's explicit approval. Previous use
  disrupted the Windows remote session. Prefer subprocess/Win32 inspection;
  keep background/headless execution an explicit option.
- Keep reusable automation separate from experiment scripts. Test transport and
  validation with synthetic fixtures; do not require ROMs or proprietary software
  for portable tests. Report exact elapsed emulated time and observation limits.
- Put persistent conventions here and experiment details in research documents.
  Follow LICENSING.md and add accurate per-file REUSE sidecars.
- Inspect status/diffs, preserve local changes, fetch without resetting, and work
  on a dedicated branch. Run applicable portable checks before local commits.
  Do not push, merge or change a remote PR without explicit authorization.
