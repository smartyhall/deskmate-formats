# Application library 001 evidence

Sanitized receipts for campaign `application-library-001`. The campaign
installed and qualified historical DeskMate applications in disposable guest
machines; see the [application library overview](../../ecosystem/application-library.md)
for the narrative and the
[registry](../../ecosystem/application-library-registry.json) for the
machine-readable selection guide.

Nothing in this directory reproduces commercial software. The receipts record
archive and media hashes, machine configuration, observed installer behavior,
stopped-disk hashes, installed file counts, and smoke-test outcomes. Original
media, installed program trees, disk images, ROMs, and raw capture sequences
remain in private laboratory storage.

## Files

- [`qualification-receipts.json`](qualification-receipts.json) — one receipt per
  host environment or application attempt, with hashes, observations, and
  capture inventory counts.

## Method summary

- Every guest was created by cloning the sealed DOS baseline
  `rsx-dos5-pristine-20261104`; application machines clone the sealed DeskMate
  03.05.00 host `applib-001-host-desk305-20261128`.
- Emulator control used only 86Box's authenticated loopback automation socket;
  no host keyboard or mouse input was injected.
- One emulator ran at a time.
- Captures are numbered framebuffer PNGs with matching text dumps; only
  selected frames were reviewed for publication.
- Within one session the host elapsed time and emulated guest time are reported
  separately; no usage telemetry source was available for this campaign.

## Publication status

- Published: authored documentation, registry, receipts, the media builder
  helper and its test, and a small set of documentary screenshots listed in
  `website/reference-images.json`.
- Private: original ZIP/7z archives, rebuilt media images, transient and sealed
  disk images, installed trees, synthetic native documents, raw capture
  sequences, transcripts, driver scripts, and the baseline manifests.
