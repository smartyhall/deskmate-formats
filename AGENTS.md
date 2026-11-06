# Standing research instructions

- Preserve reproducibility: pin source/ROM/build revisions, machine configuration,
  commands, controlled variables, actual results and SHA-256 hashes. Distinguish
  runtime observations, source findings, synthetic tests and hypotheses.
- Preserve original commercial inputs and private evidence unchanged in the lab.
  Preserve application-generated synthetic-data research files byte-for-byte as
  eligible Git fixtures under `tests/fixtures/application-generated/`, with
  SHA-256 and experimental provenance. Back up config/NVRAM before changes; use
  disposable media. Format only a newly created, explicitly identified disk.
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
  Do not push, merge or change a remote PR without explicit authorization.
