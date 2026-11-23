# Project status — DeskMate formats

## Tandy OEM America Online 1.3 — 2026-11-23

The [RSX AOL campaign](docs/research/rsx-aol13-20261123.md) ran the
original installer under Tandy MS-DOS 5.00 and reproduced launch from
both DOS and the stock DeskMate 03.04.04 shortcut. A one-line GEOS
configuration change bypassed unfinished hardware setup for offline
testing. A synthetic note saved from the DOS launch reopened after
launch from DeskMate. The original `TANDYAOL` media and commercial
installation remain in the lab.

## Corkboard and Home Organizer storage — 2026-11-23

[Native Corkboard trials](docs/research/deskmate-corkboard-20261123.md)
on the RSX, SL/2, and generic 3.05 identify `DMNOTEPD.ACC` as the F10
accessory and `DMCORKBD` as its persistent text buffer. RSX Information
Center 3.61 reads and writes the same buffer from its dashboard. Clear
can leave the prior text recoverable. The separate Financial Notebook
and Collections applications use the common 1 KiB database framing also
seen in Information Center's message database and Filer. The campaign
adds measured read-only inspection, native synthetic fixtures, and
release-by-release evidence.

## Post-merge handoff and current investigation order — 2026-11-22

[PR #164](https://github.com/smartyhall/deskmate-formats/pull/164)
merged after its pull-request test matrix passed. The alternate DeskMate 03.05.00,
SL/2 ROM startup, and related RL/RLX controls are now documented in
[the experiment report](docs/research/deskmate-305-variants-sl2-20261122.md)
with release identities, native captures, and preserved private checkpoints.
The SL/2 needed factory EEPROM initialization before its ROM DOS and ROM
DeskMate startup could be reproduced; exact-machine RL/RLX follow-ups remain open.

**Next bounded native campaign:** [Corkboard #165](https://github.com/smartyhall/deskmate-formats/issues/165)
should locate any genuine Corkboard module and saved specimen in the preserved
DOS releases, then compare its storage with the now-observed Information
Center 3.61 and Filer databases. Do not treat `NOTEBOOK.PDM` as Corkboard
without independent identity evidence, and do not assume format compatibility.

**Queued communications investigations:** [DOS Telecom #167](https://github.com/smartyhall/deskmate-formats/issues/167)
is a controlled two-86Box, virtual-modem and native transfer-protocol study.
[PC-Link #166](https://github.com/smartyhall/deskmate-formats/issues/166)
is a separate, later service-protocol/revival study; compatibility with
Commodore QuantumLink is a hypothesis, not an established feature.
Keep experiments local, synthetic, and version-specific.

**CI efficiency:** [Windows profiling #147](https://github.com/smartyhall/deskmate-formats/issues/147)
now has per-test evidence from the recent PR #164 runs. The same 731-test
portable suite took approximately 78–84 seconds on Ubuntu and 395–531 seconds
on Windows, principally in supervisor/process tests. Instrument this
separately from application archaeology; preserve all safety and
fail-closed assertions.

**Research sequence:** Prioritize the DOS DeskMate family, its release
lineage, runtime, and native formats. Cross-system investigation of
Color Computer DeskMate and comparisons with OS-9 or GEOS are deferred until
the DOS evidence is better established. The historical
[chronology PR #155](https://github.com/smartyhall/deskmate-formats/pull/155)
remains intentionally **draft/unpublished**, with period-image preparation and
source reconciliation still required. The last
[Codex usage completion receipt](docs/evidence/codex-usage/20261122-305-sl2-completion.json)
is a historical checkpoint, not a live account quota reading.

## Alternate 3.05 and SL/2 ROM recovery — 2026-11-22

The [follow-up campaign](docs/research/deskmate-305-variants-sl2-20261122.md)
reproduced the alternate DeskMate 03.05.00 install on the RSX. Its
Desktop 3.69 replaces the raw-media Desktop 3.68's PC-Link shortcut
with Hangman, and the separate Thesaurus works in Text. A controlled
EEPROM comparison recovered both ROM DOS and the SL/2 ROM DeskMate
desktop. Address Book, Calendar, Music, and Sound opened under that
runtime. Related-machine trials opened the RL CookBook on the SL/2
and booted RLX B DOS media on the RSX.

Exact TL, TL/2, 1100 FD, RL/RL-HD, and RLX-HD B profiles remain open
in the pinned lab build. See the [updated release matrix](docs/ecosystem/deskmate-evolution-releases.json)
for qualified media and acquisition leads.

## Historical release survey and RSX home automation — 2026-11-22

The reviewed [DeskMate Evolution Atlas](docs/ecosystem/deskmate-evolution-atlas.md)
(PR [#161](https://github.com/smartyhall/deskmate-formats/pull/161))
catalogs 23 distributions, archive variants, and documentary leads,
11 backed by native desktop or application observations. It separates
original DeskMate and DeskMate II, Personal DeskMate, generic DeskMate 3.x,
and machine-specific OEM distributions; the [release matrix](docs/ecosystem/deskmate-evolution-releases.json)
distinguishes documentary evidence from verified media and successful launches.

The RSX OEM 03.04.04 campaign (merged PR [#162](https://github.com/smartyhall/deskmate-formats/pull/162))
completed the six-disk native hard-disk installation and tested the
distinctive household applications. [Automatic House 01.08](docs/research/deskmate-automatic-house-x10.md)
created a synthetic floor plan, two-device routine, and daily schedule,
then reopened them after a cold boot. DeskMate sent measured **CP290**
serial frames at 600 baud, 8N1 to an **offline simulated controller**:
direct lamp action, timer transfer, and schedule readback were observed.
This is *not* evidence of physical X10 signaling or general CP290
compatibility. [Information Center 3.61](docs/research/deskmate-rsx-oem-recovery-20261122.md#information-center)
saved and reopened synthetic messages; a byte-verified 6,144-byte native
database specimen and representative framebuffer captures are published.

**Current site:** The BOOTSTRA.386-inspired Eleventy reference is built
from [docs/site/page-map.json](docs/site/page-map.json) and deployed
at [deskmate.retroconnect.org](https://deskmate.retroconnect.org/).
The RSX application research and atlas are now linked from the site.
The prior generic 3.02, 3.03.01, and 3.05 comparisons remain available.

**Open historical work:** [installation roadmap #153](https://github.com/smartyhall/deskmate-formats/issues/153)
continues beyond the completed releases. The CP290 model covers
only observed commands; multi-event scheduling, dimming, time progression,
and physical-hardware validation remain separate future work.
[Chronology PR #155](https://github.com/smartyhall/deskmate-formats/pull/155)
is still an **editorial draft** pending verified period-image preparation,
source checking, and reconciliation with the now-completed release atlas.
The [Faxback publication project #154](https://github.com/smartyhall/deskmate-formats/issues/154)
remains staged and requires the prescribed per-document review; do not
confuse archive-mirror completeness with publication completion.

## TVDog archive intelligence — 2026-11-19

The first [mirror verification](docs/ecosystem/tvdog-mirror-verification.md)
rehashes 958 originals and 62 directory listings. The manifest records
9,015 remaining transfers at that checkpoint. The downloader now persists
and honors bounded retry cooldowns. The private
[offline index](tools/archive/intelligence.md) follows committed verified
receipts and reuses extraction and text by content identity.

The [annotated reference catalog](docs/ecosystem/tvdog-reference.md) records
Express Publisher 1.00, Q&A Write 1.00, DM_Music 1.04, SDK materials, and
period community collections. Express Publisher adds the Dingbat2 and
Springer FF1 profiles. Historical files drove bounded Text margin recovery
and opt-in Music sector-padding recovery. The
[demonstrator purchase facts](docs/ecosystem/demonstrator-purchase-facts.md)
pin period prices and source-specific compatibility evidence. See the
[campaign handoff](docs/research/tvdog-intelligence-20261119.md) for
measurements, private locations and remaining native trials.

## Ecosystem preservation and living demonstrator — 2026-11-19

The operator expanded the long-term preservation scope to dedicated
third-party DeskMate applications, companion modules and their native
file formats. The initial [ecosystem catalog](docs/ecosystem/README.md)
and [demonstrator plan](docs/ecosystem/demonstrator.md) distinguish
historical documentation, media acquisition, installation and format
qualification. No new installation or third-party parser is claimed.
The [acquisition handoff](docs/ecosystem/acquisitions.md) pins two
operator-supplied archives for the next Draw/font campaign.

## Draw II typography, raster and browser authoring — 2026-11-19

The shared graphics engine reads the outline command streams in all
672 glyph records of the pinned Cobb, Dixon and Marin resources. It
accepts local FF1s for SVG and experimental RSX raster output. The two
new frozen comparison milestones raise typography foreground overlap
to 43.76% and retain Cedar Lake at 99.91%. Nine isolated oblique grids
match the native RSX pixels. The offline browser can author native FIGs
from a blank canvas, including a grouped four-object control that Draw
opened, moved, saved and reopened. Native Draw flattens the group
during that move. [Draw II evidence](docs/research/draw-ii-20261119.md).

## Draw preservation and native graphics — 2026-11-19

The Draw campaign freezes four original native-resaved figures and
19 diagnostic inputs. Four immutable comparison milestones pair those
exact inputs with genuine RSX framebuffer crops, the PR #120 baseline,
shared quadratic SVGs and two independent raster profiles. A local
browser gallery and offline FIG Workbench provide visual comparison,
inspection, and the first native-validated edits. The 206-figure
historical inventory, explicit arc recovery, Python writing operations
and native Text/Filer transfers are documented in the
[campaign report](docs/research/draw-campaign-20261119.md).

## Independent sampled Music playback — 2026-11-18

The [v1 listening suite](examples/music-listening/README.md) contains
ten native RSX DAC and PR #118 renderer pairs. Five original passages
use three synthetic Sound instruments and five use the original Tandy
Clarinet, Piano, Bells and Cello bank. The frozen score and instrument
specification, capture provenance, and quantitative comparisons accompany
the audio.

The experimental interleaved RSX DAC mode improves aligned waveform
correlation in all ten listening cases. The default Music CLI can
stream longer scores with an explicit frame budget. The historical
comparison now covers 40 of 62 scores at 48 kHz using the established
bank. [Trace and compatibility report](docs/research/music-playback-trace-20261118.md)

The Music CLI and Preservation Workbench render sampled PCM/WAV using an
explicit SND collection. The RSX model uses measured numeric binding,
sample ranges, sustain boundaries, block-quantized tempo and bounded
repeat execution. Native DAC comparisons cover synthetic instruments,
ties, slurs, dynamics, multiple voices and historical scores. Gate and
mixing approximations remain visible in exported metadata.

All 62 historical scores now pass written-word interpretation. MIDI
coverage grew from 15 to 51. The retained instrument bank rendered 37
complete scores at 48 kHz and three additional long scores at 24 kHz.
Remaining execution failures center on repeat cuts and missing instruments.
[Campaign and reproducibility report](docs/research/sampled-music-playback-20261118.md)

## Sound and Music preservation campaign — 2026-11-18

The standalone 3.05.00 distribution lacks the audio modules. The RSX OEM
Sound and Music applications ran on a disposable Tandy 1000 RSX using
the 3.05 runtime and measured OEM resources. Exact native synthetic saves
establish later Sound PCM, native compression and three-voice notation.

The bounded Sound reader recovers unsigned mono PCM from both generations
and both compression modes. The Music reader preserves three voice streams,
conductor instructions and opaque words. The Workbench adds local WAV playback
and MIDI for supported linear scores, including tempo changes and ties. An
emulated DAC capture verifies external SND playback, octave transposition,
and a repeat control in Music. The private collection provides
16 distinct Sound files, 62 distinct Music scores, and 206 Draw comparators.
See the [Sound research](docs/research/sound-native-20261118.md),
[Music research](docs/research/music-native-20261118.md) and
[historical archive report](docs/research/audio-historical-corpus-20261118.md).

## Preservation Workbench Phase I — 2026-11-18

The read-only `deskmate-preserve` command recognizes the measured profiles of
all six principal DeskMate 3.05 families and exports individually verifiable
bundles. Worksheet provides a grid and two CSV views, Text interleaves literal
text with local SVG illustrations, Draw exports SVG with the stored palette,
and Filer combines ordered DATA records with recovered card/report geometry.
Calendar and Address Book provide strict interchange where representable,
with additional iCalendar and vCard projections for the measured fields.
Batch exports include an offline collection index and per-file outcomes.

Portable regression coverage includes all 44 native Worksheet specimens,
native Text picture order and formatting, synthetic Form Setup specimens,
two named Calendars and a native two-contact Address Book. The end-to-end
demo verifies a six-family collection. The manifest documents the profile,
opaque fields, approximations and omissions while preserving the original
bytes. [Workbench guide](docs/preservation-workbench.md)

## Worksheet research checkpoint — 2026-11-17

The dedicated Worksheet branch preserves 44 exact native synthetic WKS
files and a bounded reader for all five cell categories. Controls establish
the packed TOPLIST layout, counted dummies, rebased memory pointers,
one-based grid, NUL string pool and binary64 values. Native formula
copies distinguish relative references from `#` absolute references.
Stored formula results can remain stale across a save and reopen.
See the [native Worksheet report](docs/research/worksheet-native-20261117.md)
and [evidence receipt](docs/evidence/worksheet-native-20261117.json).

The preceding native graphics campaign is integrated by
[PR #112](https://github.com/smartyhall/deskmate-formats/pull/112) at
`a5d3a713e808fd0e73fbc6ae6c09104a90020260`. Its
[native report](docs/research/graphics-native-20261117.md) supersedes the
historical graphics proposal below.

## Manufacturer-derived Appendix A reference layer — 2026-11-17

The [Tandy format crosswalk](docs/reference/tandy-format-crosswalk.md) now indexes [common Page Setup headers](docs/reference/tandy-common-headers.md), [Address Book](docs/reference/tandy-addressbook-format.md), [Calendar](docs/reference/tandy-calendar-format.md), [Draw](docs/reference/tandy-draw-format.md), [Filer/Form Setup](docs/reference/tandy-filer-format.md), [Text](docs/reference/tandy-text-format.md), and [Worksheet](docs/reference/tandy-worksheet-format.md). These are original technical paraphrases from the operator-provided DeskMate Development System 03.05.00 Development Guide, Appendix A, with page references, uncertainties and specific native-test targets. They **do not add new experimental evidence** or expand measured reader/writer support. The proprietary manual is not redistributed.

## Proposed next research — Draw, Filer graphics and Text embedding (2026-11-17)

The next cross-application campaign is documented in [the graphical-format research plan](docs/research/graphics-cross-application-plan-20261117.md). The operator-provided DeskMate Development System 03.05.00 Development Guide, Appendix A, explicitly describes Draw graphics forms, Filer's ASCII-constrained GRAPHICS storage and Draw pictures pasted into Text (length-delimited picture paragraphs). The plan prioritizes a native Draw corpus, early Draw-to-Text embedding controls and separately created Form Setup graphics for three-way comparison. **This is a proposal, not completed native evidence.** [PR #110](https://github.com/smartyhall/deskmate-formats/pull/110) contains the preceding Filer/Text campaign and is now merged into `main` at `eccdf2c85c3c1382096d140c0bec8e9892016c32`; use the integrated Filer/Text reports as the native baseline.

## Latest integrated checkpoint — 2026-11-17, PRs #107 and #108 merged

**Native Calendar index-maintenance trigger and bounded writer:** [PR #107](https://github.com/smartyhall/deskmate-formats/pull/107) merged as `f24fa9bfd91e79af1fee5ebeee177efd7af03ca7`, after all four Windows/Ubuntu Python 3.13/3.14 CI jobs passed. A DOS-only boot and two stop-while-open controls left the disk unchanged, while two independent clean Calendar open/close trials rewrote only the PERSONAL index page on 61-event and 59-event inputs, splitting the first full group `41→20+21` and shifting the existing second group. The observations link the durable write to clean close, **not uniquely to the instant of in-memory restructuring**; the native table-close configuration UPDATE_ROW is the strongest static explanation, not an instrumented runtime trace. Published application-written outputs and independently constructed byte oracles agree. The opt-in `calendar.maintenance` API supports only measured single-PERSONAL 59/61-event eight-page index normalization and same-length printable ASCII description edits. A normalized tool candidate survived native read/detail/cancel unchanged; native edit/save/reopen changed only the intended five description bytes. General balancing, arbitrary counts and multi-calendar mutation are not qualified. See [trigger report](docs/research/calendar-index-trigger-20261117.md) and [writer report](docs/research/calendar-writer-maintenance-20261117.md).

**Address Book two-contact native checkpoint:** [PR #108](https://github.com/smartyhall/deskmate-formats/pull/108) merged as `00c69b6224c47f8d6309dc025e9056a127d34c8b`, after all four CI jobs passed. From the published **tool-reconstructed**, historical-hash A01 starting file (the original A01 archive was unavailable), original DeskMate inserted ZULU ALPHA / 555-0100 and saved an exact 10,240-byte result (SHA-256 `c37c62bf2fb16963f910c4d4c80e395d3a42305b55e954435d30ca0f9d3cdf40`). The new row is physically appended at `0x103D` (ID 17) but sorted ahead of USER A by index; a separate read-only reopen verified both contacts. An initial UI repaint inconsistency cleared on selection, without another edit. The exact native file and independent generated replica match byte-for-byte. New `addressbook.experimental_second` is strictly opt-in and exact-A01 / ALPHA-only; other first names/phones have offline-only tests. Secondary/tied FirstName sorting and general third-contact growth remain unresolved. See [native report](docs/research/addressbook-two-contact-native-20261117.md).

**Release status:** Both PRs were independently reviewed, their published fixture bytes/hashes checked, and their PR-head CI passed before merge. The dated *“Successor campaign proposed — PR #107”* paragraph below records its pre-merge state and is superseded by this checkpoint. Neither campaign used an S3 supervisor model-edit dispatch; native Windows sandbox compatibility remains a separate unverified investigation.

## Successor campaign proposed — 2026-11-17, PR #107

[PR #107](https://github.com/smartyhall/deskmate-formats/pull/107) preserves new
controlled native evidence and proposes a bounded maintenance API; these source
changes await independent review and are not yet merged. DOS-only boot preserves
the whole disk. No-edit Calendar open/close rewrites only index page 5: 61 events
split `[41,21,0,0]` to `[20,21,21,0]`; a 59-event forward-insertion control splits
`[41,19,0,0]` to `[20,21,19,0]`. Two stop-while-open controls preserve the whole
disk, including one matched to the clean-exit trial's elapsed time. The durable
rewrite is associated with clean close; earlier in-memory rebuilding versus
close-time writeback remains unobserved. The source-pinned config-row UPDATE_ROW
on table close supplies the strongest explanation. See
[trigger/timing evidence](docs/research/calendar-index-trigger-20261117.md).

The proposed opt-in API normalizes only the measured single-PERSONAL 59/61-event
structural profiles and performs same-length ASCII description replacements
while preserving row addresses/IDs and unrelated bytes. A new normalized writer
candidate survives native open/detail/cancel unchanged; a separate native
five-byte description save preserves its index and survives read-only reopen.
Exact tool/native files and independent raw-byte oracles are published on the PR.
This is selected-event evidence, not general rebalance or multicontact support.
[API, native acceptance and local validation](docs/research/calendar-writer-maintenance-20261117.md).
The earlier merged checkpoint below remains accurate for its dated scope.

## Current checkpoint — 2026-11-17 (post-merge Calendar campaign)

**Direct interactive development — three PRs merged:** [#103](https://github.com/smartyhall/deskmate-formats/pull/103) adds `Alarm: on/off/<undecoded>` to user-appointment text listings with synthetic regressions, without changing the parser, JSON or internal/control records. [#104](https://github.com/smartyhall/deskmate-formats/pull/104) adds per-index-group routing kind and physical endpoint diagnostics, independently tested against native PERSONAL/SECOND fixtures and synthetic repartitions. The former common-parser rejection at `0x1400` was **already resolved** in [#84](https://github.com/smartyhall/deskmate-formats/pull/84); #104 improves visibility and boundary checks rather than introducing general multicalendar writing. [#105](https://github.com/smartyhall/deskmate-formats/pull/105) preserves the native saved result and reproducible verification of one controlled edit/save/reopen. All four Linux/Windows Python 3.13/3.14 CI jobs passed on the reviewed heads of each PR; all three were independently reviewed and merged.

**Native Calendar save/reopen verified within a narrow scope:** Original DeskMate 03.05.00, in a verified disposable 86Box installation, opened the exact published 8,192-byte 61-appointment/30-date month candidate (SHA-256 `d35b10c8e8f0b04e41cd6d16a27b9825531353b00ab503e94b7abd3a11499106`). One declared same-length description edit for PERSONAL ID 77, `Plan 01 / allocator trial` → `Plan 01 / allocator saved`, was saved; a separate read-only reopen showed the changed detail, unchanged times and alarm off. The exact application-saved 8,192-byte file, SHA-256 `4b59c4f30ba21260df8159ac8758077858f1f516efbfc95365c7a5096ccab970`, is committed as [a native saved synthetic fixture](tests/fixtures/application-generated/calendar/native-30-day-edit-save-20261117.cln). Offline checks establish all 61 appointment semantics with only that substitution; all logical locators and row addresses remain, and only `PERSONAL.CLN` changed among 143 installed files after save. This is **selected-event native edit/save/reopen evidence**, not all-date visual inspection, alarm firing, general writer acceptance or arbitrary multicalendar operations. See [trial report](docs/research/calendar-native-save-20261117.md) and [receipt](docs/evidence/calendar-native-save-20261117.json).

**A new index-repartition clue, not yet a trigger proof:** The native save changed exactly 242 Calendar byte positions: 237 on PERSONAL index page 5 and five description bytes on data page 7. Physical index-group occupancy moved from `[41,21,0,0]` to `[20,21,21,0]`, with the index page matching the earlier native empty-SECOND specimen byte-for-byte. Because no second calendar was created during this trial, multicalendar creation is **not necessary** for that rearrangement. The experiment did not sample the unopened/merely-opened database separately, so **open versus edit/save remains unresolved**. The highest-value next control is a *newly authorized* untouched month-file open/close-without-edit trial, with exact before/after Calendar, installed-tree, configuration and NVRAM evidence. See [issue #71](https://github.com/smartyhall/deskmate-formats/issues/71) and [issue #81](https://github.com/smartyhall/deskmate-formats/issues/81).

**Separate supervisor status:** This campaign used directly authorized interactive Codex development, **not** S1 acceptance or S3 native source editing. The S3 revision-2 alarm-listing task remained unaccepted and undispatched; its earlier revision-1 claim remains permanently consumed. Four separate no-model Windows sandbox compatibility attempts were incomplete before native positive/negative write assertions, and do not verify S3 confined writing or native model `apply_patch`. Resume that investigation only by a separate task and grant. The dated 2026-11-16/earlier snapshots below are retained as historical statements and may describe milestones now superseded.

**S3 implementation proposed (2026-11-16):** the [bounded editing workflow](docs/research/codex-supervisor-s3.md) adds explicit version-2 source-editing tasks, disposable Git clones, actual portable validation and a provenance-bound local checkpoint. All execution validation uses synthetic peers; native editing remains unexecuted and separately gated. The first live S2 text analysis completed in [merged PR #98](docs/research/codex-supervisor-s2-first-live-result-20261116.md). The proposed Calendar alarm-listing task is neither accepted nor dispatched.

**Manual S2 implementation — 2026-11-16:** the
[Git-to-Codex text-analysis path](docs/research/codex-supervisor-s2-live-dispatch.md)
adds frozen task-specific prompts, offline inspection and separate dispatch,
model-use and experimental-lab grants using the proven S0 owner. Validation uses
synthetic peers only. The proposed first task is published for review, not accepted
or dispatched. Real S2 remains unverified; issue #86 stays open pending a separately
authorized real Git-delivered model turn and independent answer review.

**S0 LIVE CANARY PASSED — 2026-11-16 UTC:** the separately authorized second
native experiment used reviewed implementation `fe168c86d650f6e8aa4f3187fc4121cf7910783c`
and the exact prepared plan. One owned Codex 0.166.0 app-server created one
persistent thread and submitted one gpt-6-luna/Low turn. The corrected policy
validator accepted the native reply; `S0_CANARY_OK`, terminal notifications,
full history and the on-disk rollout agreed. Owned-child exit was verified;
CLI exit 0, supervisor completed. [Observed report](docs/research/codex-supervisor-s0-second-live-result-20261116.md)
and [sanitized evidence](docs/evidence/supervisor-s0-second-live-20261116.json).
Raw evidence remains private. No retry, restart, S2 dispatch or emulator use
occurred. Issue #58 remains open for broader native restart/resume scope and
independent review; #86 remains open pending separate real-dispatch authority.
Earlier dated records below retain their historical scope.

**Revised lab operating policy — 2026-11-11:**
[Experimental laboratory posture](docs/research/experimental-lab-operating-posture.md)
accepts ordinary risk inside the existing recoverable Windows 10 VM for one
separately authorized S0 protocol canary. No new VM, restricted principal,
or comprehensive OS filesystem/network/descendant confinement is required
*solely* to remove hypothetical VM-local risk. Historic DeskMate software is
a normal **local** lab input; public Git publication is a different boundary.
Retain snapshots, a brief actual host/share/credential exposure review,
durable receipts, no uncertain-op replay and a precise model-use grant.

**Experimental profile implemented — 2026-11-12:** the explicit
`experimental-lab` profile permits one exact-plan authorized S0 sentinel turn
with a separate lab-risk acknowledgment. Default live remains blocked and S2
remains synthetic-only. The [current runbook](docs/research/codex-supervisor-s0-live-canary.md)
and [validation report](docs/research/codex-supervisor-experimental-lab-validation.md)
distinguish accepted VM permissions from unverified OS confinement.
At that checkpoint no real model invocation had occurred; the authorized
second invocation above now passed. The earlier
`BLOCKED` research record below reflects the **former acceptance gate**;
issue #90's second-VM/restricted-user comparison is no longer the selected
first-canary prerequisite.

**S0 live-readiness completed — 2026-11-11 (America/New_York):**
[PR #89](https://github.com/smartyhall/deskmate-formats/pull/89)
(merged `06b29bd620f0ebe61576083fdc42f1781dccb81e`) completed the
credit-interrupted audit of the S0 operator driver with a real Windows 10
**offline** preflight and stricter synthetic checks. Pinned native Codex
0.166.0 and two 321-file schema inventories match recorded hashes; Codex
reported 387 passed portable tests, and all four final-head GitHub Windows/
Ubuntu CI jobs passed. No actual app-server/model session, guest operation
or auth provisioning was performed.

**Decision: BLOCKED — SPECIFIC REMEDIATION REQUIRED.** The S0 driver now
refuses live execution *before child launch*, irrespective of an operator
plan-digest attestation. Synthetic evidence confirms that environment/cwd
sanitization alone does not contain filesystem or loopback access. Real
OS-enforced file/network/descendant isolation, effective Codex tool/config
restrictions and secure auth provisioning remain unresolved. Do not treat
late event/history checks as containment. [Research report](docs/research/codex-supervisor-s0-readiness.md)
and [structured receipt](docs/evidence/supervisor-readiness-20261111.json).
Next scoped decision [issue #90](https://github.com/smartyhall/deskmate-formats/issues/90)
compares disposable Windows execution environments with low-privilege host
containment and synthetic denial tests; [issue #58](https://github.com/smartyhall/deskmate-formats/issues/58)
retains the real S0 authorization gate and [issue #86](https://github.com/smartyhall/deskmate-formats/issues/86)
retains the subsequent real S2 dispatch gate.

**Earlier merged milestone below — 2026-11-08:** preserved for its dated scope.

**Supervisor merged checkpoint — 2026-11-08 (America/New_York):**
[PR #87](https://github.com/smartyhall/deskmate-formats/pull/87)
(merged `825f9bde92aec087f20fa2a7dcbc82229d532a88`)
added an installable single-use S0 operator driver and **synthetic-only**
S1-accepted-task-to-S2 dispatch bridge. The task's exact Git/queue acceptance
and a separate dispatch grant are checked, with private operation receipts
and read-only Observatory results. The published synthetic demonstration
performed one supervised synthetic thread/turn; no original Codex model,
86Box guest, VM media, paid call, daemon or control listener was used.
Codex reported 375 passing portable tests, including 58 focused supervisor
tests; all four final-head GitHub Windows/Ubuntu CI jobs passed.
[Runbook](docs/research/codex-supervisor-operator-driver.md) and
[evidence receipt](docs/evidence/supervisor-offline-driver-20261108.json).
**Issue #86 remains open:** the first real S0 canary and live S2 task execution
still require separate explicit authorization and effective-isolation review.

**Current merged checkpoint — 2026-11-08 (America/New_York):**
[PR #83](https://github.com/smartyhall/deskmate-formats/pull/83) published
the exact operator-produced, synthetic-data FIRST SECOND appointment fixture
(merged `30e5db48de104c844e935049364174d13ce5050a`).
[PR #84](https://github.com/smartyhall/deskmate-formats/pull/84) implemented
bounded SDK-profile reading of named PERSONAL and SECOND calendars and two
explicitly experimental exact-source writers (merged
`43a6a5734408ef81c010a004c2e4a44ac34f4def`). The reader reports
61 PERSONAL and zero/one SECOND appointments in the two original native
specimens. Both generated whole files reproduce their corresponding original
native file SHA-256 **exactly**, with separately retained native/operator versus
tool-generated provenance. This is released offline-validated source code,
**not** broad writer support, an independently instrumented native save/reopen
or a proven general index balancer. All four GitHub CI jobs passed for #83/#84.
[Campaign and limitations](docs/research/calendar-multicalendar-reader-writer.md).

[PR #80](https://github.com/smartyhall/deskmate-formats/pull/80)
(merged `8b47ab08698ea601308707703e14fe98d342dd8c`) adds the
source-pinned Address Book LastName/FirstName insertion trace and conservative
two-contact byte predictions, **not** a new native two-contact file or writer.
Its four CI jobs passed; issue #70 remains open for actual native verification.

The operator granted standing authority on 2026-11-08 for ChatGPT to merge
ready, passing Codex PRs after independent review. This does not authorize
Codex workers to self-merge or to execute paid Codex turns or native guest actions.
S0 now has an installable operator driver; the S1-to-S0 bridge has a separately
gated synthetic-only demonstration. The authorized real S0 canary above now
passed; real S2 dispatch remains unproven and separately gated.
[Operator driver and next-canary gates](docs/research/codex-supervisor-operator-driver.md).
[Supervisor design and rollout](docs/research/codex-supervisor-design.md).

**Historical snapshot below — 2026-11-07:** preserved for its dated context,
including now-superseded statements about native Calendar display and current
implementation scope.

**Snapshot:** 2026-11-07 (America/New_York), after publication of the
30-day Calendar in [PR #78](https://github.com/smartyhall/deskmate-formats/pull/78),
merged as `0cba552411d96376cce5db3c6d4907cc8e9b4ace` on `main`.
The allocator implementation remains from merged PR #75, and the synthetic-fixture
publication policy from merged PR #77.

**30-day publication on `codex/publish-calendar-30-days` ([merged #78](https://github.com/smartyhall/deskmate-formats/pull/78)):**
the complete [8,192-byte Calendar](tests/fixtures/application-generated/calendar/sdk-30-days-allocator-tool-generated.cln)
has been regenerated and matched byte for byte against the preserved allocator
candidate, SHA-256 `d35b10c8e8f0b04e41cd6d16a27b9825531353b00ab503e94b7abd3a11499106`.
The [61-appointment listing](tests/fixtures/application-generated/calendar/sdk-30-days-allocator-tool-generated.expected.json),
[operator download/inspection guide](docs/research/calendar-30-day-native-acceptance.md)
and [publication receipt](docs/evidence/calendar-30-day-publication.json) prepare
native acceptance across all 30 dates and pages 4, 6 and 7. This is **tool-generated,
independently checked offline, not application-produced or native-accepted**.
No emulator/guest operation or native save occurred. Source E02 and the prior
14-day fixture are unchanged. The exact binary and expected listing are now
published on `main`; **native read/display and persistence acceptance remain open**.

This is a concise, public **capability and handoff snapshot**, not a reconstruction
of an older missing `PROJECT_STATUS.md`, a substitute for private experiment
receipts or a live work monitor. Update after verified merges. A result reported
from a draft PR or current experiment is not a released capability.

The immediate objective is **useful Calendar and Address Book files**, validated
independently in DeskMate. Tests in which our reader accepts our writer's output
do not by themselves establish native compatibility.

**Allocator continuation on `codex/dmdb-page-allocator`
([merged #75](https://github.com/smartyhall/deskmate-formats/pull/75)):** campaign base
`8c1e7aa6f6aac04c3167d141f981e10f1d3b860e`.
[Static DMDB investigation](docs/research/dmdb-page-allocator.md) decoded packed
12-bit page chains and reproduced both published E15/E19 header transitions;
original E15/E19 bytes remain unavailable. A separate E02-only, opt-in new-file
builder now produces an independently checked **61-appointment / 30-date /
eight-page candidate**. Existing six-page append profiles stay unchanged.
This is tool-generated and **native open/save acceptance is pending**. No emulator
or Address Book trial was run. The separate experimental builder is now merged,
while the established six-page writer and native-accepted scope are unchanged.
See the successor report/receipt for exact source, candidate and validation identities.

## Evidence vocabulary

- **Implemented:** checked-in source; only the documented test scopes are claimed.
- **Native observed:** tested through an original DeskMate application in a
  controlled emulator experiment.
- **Operator-reported native display:** human inspection in original DeskMate;
  retain the report's scope separately from hash-pinned controlled experiments.
- **Offline tested:** verified by byte comparisons, fixtures or synthetic tests
  without new application interaction.
- **Proposed / unresolved:** an engineering target or hypothesis, not an observed
  storage rule or completed operation.

Dated experiment reports retain what was known *at their respective checkpoints*.
Use [compatibility](docs/compatibility.md) for current supported profiles and
the [README](README.md) for commands.

## Current capabilities

| Area | Implemented or observed | Remaining limits |
| --- | --- | --- |
| Calendar `PERSONAL.CLN` | [Reader and writer](docs/compatibility.md) retain the measured default and SDK profiles; the operator reports **29 appointments / 14 dates** displayed correctly with alarm states in DeskMate. A **separate opt-in E02-only experimental builder** generates an offline-checked **61-appointment / 30-date** candidate ([allocator report](docs/research/dmdb-page-allocator.md)). | Six-page append profiles are unchanged. The 30-day candidate has **not** been opened or saved in DeskMate; native page traversal, persistence and alarm firing remain unverified. Experimental growth is limited to eight pages and rejects unsupported operations. |
| Calendar page behavior | Static 3.05 reader/writer routines identify **packed 12-bit page chains** and reproduce E15/E19 header deltas; a bounded new-file builder now links pages 4→6→7. E16–E18 remain evidence of retained deletions and append behavior. [Source report](docs/research/dmdb-page-allocator.md). | The original E15/E19 files were unavailable in this run; there is no native test of the new 8-page file, no general allocator, and no deletion/reclamation or index-growth writer. |
| Address Book `PERSONAL.ADR` | [Reader](docs/research/addressbook-codec.md) preserves the ten-page/four-table layout, 16 raw contact fields and opaque tables. Empty-to-one writer reproduces **all four** A01–A04 application-produced whole-file SHA-256 hashes using a pinned source template. | 25 fictional contacts were generated in **25 separate one-contact files**, not one populated book. A second insertion, sort/collation rules, additional pages and broad optional field semantics are unverified. |
| Shared DMDB database structures | [Common structural reader](src/deskmate_formats/database.py) and [cross-application evidence](docs/research/cross-application-db.md) cover page framing, schemas, records and indexes. [Call study](docs/research/database-call-review.md) finds code-backed DMDB binding/call thunks in Calendar, Address Book and Filer. | No universal allocation writer or proven runtime DMDB export binding. Shared call interfaces do not establish identical application policies. |
| Interchange | [Version-1 semantic Python/JSON contract](docs/interoperability.md), explicit loss reports, source-snapshot IDs and example files are implemented. | No general native edit/delete, lossless reconstruction, stable external UID mapping or CalDAV/CardDAV network synchronization. |
| Filer | [Native campaign](docs/research/filer-native-20261117.md) covers empty-to-two records, menu changes, editing, deletion, sort configuration and page growth. A new Form Setup schema and its populated version exercise the [bounded inspector](src/deskmate_formats/filer.py). | Conditional Find remains open. Legacy five-field DBCOLS rows and a stale directory tail after Sort fall outside the reader's profile. |
| Text | [Native corpus and extractor](docs/research/text-native-20261117.md) cover plain and default-header formatted streams, mixed bold/underline, centering, soft wrap and a multi-cluster document. | Pictures, other layout controls and alternate headers remain open. |
| 86Box and Observatory | Native authenticated loopback client, held DOS guest evidence, and [Observatory M0/M1](docs/research/observatory-v2-m0-m1.md) read-only publication with [M2](docs/research/observatory-v2-m2.md) opt-in Codex telemetry. Scoped held-canary verification recorded 0 ms guest advance. | No proven unattended service/old-browser acceptance; launcher startup timeout still warrants safe reconciliation [#35](https://github.com/smartyhall/deskmate-formats/issues/35). |
| Supervisor | [S0](docs/research/codex-supervisor-s0.md) owned protocol/receipts and [installable driver](docs/research/codex-supervisor-operator-driver.md); [real single-turn S0 canary passed](docs/research/codex-supervisor-s0-second-live-result-20261116.md); [S1](docs/research/codex-supervisor-s1.md) trusted Git intake; synthetic-only S2 bridge. | Native restart/resume and real S2 dispatch remain unverified. A queued task is not execution authority; further live operations require separate authorization. |
| Windows lab | Existing Windows 10 Pro research VM and [source-only provisioning work](deployment/windows10/INTEGRATION-STATUS.md). | Fresh full ISO/OOBE and recovery validation incomplete; system modifications need explicit review [#32](https://github.com/smartyhall/deskmate-formats/issues/32). |

Worksheet and Draw remain outside implemented application codecs. See
[format inventory](docs/inventory.md).

## Database campaign checkpoints

The [database implementation report](docs/research/database-campaign.md)
contains details, limitations, private-evidence boundaries and reproducibility
instructions. Milestones were checkpointed on a dedicated Codex branch:

| Milestone | Result | Original checkpoint |
| --- | --- | --- |
| M0 | Windows/Python preflight; offline work avoided the uncertain 86Box startup path. | [Campaign report](docs/research/database-campaign.md) |
| M1 | Bounded common directory/column/index/record reader. | `0158cf8e9086d0292ae43c5aab30470163418a71` |
| M2 | SDK Calendar codec; 29 events over 14 days; page-reader extensions. | `5067da55c5ec3ac97f4d855cddec297e0e022376` |
| M3 | Address Book reader and one-contact writer; four independent native hash matches. | `ca06dd9a5ec5c648940c0981760c6e4bfd5e4fb3` |
| M4–M5 | Independent fixed-profile output checker, strict JSON interchange and loss accounting. | `4f761f9a43163dd90e89f03d910925772a43ecdf` |

The 30-day attempt stopped safely after **39 additions / 40 total events**
with **12 free record bytes**. Its incomplete prefix was archived privately; a
full-month deliverable is not claimed. The 14-day result is 6,144 bytes with
SHA-256 `85ad05d6bf58540e32349bbb559301d36aced164741b03b09b30d63f22d636ac`.
See the [public hashes and provenance](docs/evidence/database-campaign.json).

Phase II from `codex/database-phase-ii`, [merged PR #73](https://github.com/smartyhall/deskmate-formats/pull/73):
[source findings, independent diagnostic and operator runbooks](docs/research/database-phase-ii.md)
are prepared for #70/#71. SDK source documents LastName/FirstName ordering;
native second-contact insertion remains unmeasured. The diagnostic checks E15/E19
published hash/delta predictions without treating synthetic controls as originals.
No multicontact writer or page allocator was enabled; no new Calendar generated.
Current validation: **321 portable tests passed (135.970 s)** and **2 focused
private oracle tests passed (0.059 s)**. Seven diagnostic tests were rerun after
making their synthetic header vectors independent of the diagnostic's constants;
all passed (0.100 s). Ruff, REUSE, repository audit and wheel/sdist build passed.
See the [Phase II receipt](docs/evidence/database-phase-ii.json). This run requested
**0 ms** of emulated execution; actual guest-clock delta was **not measured**.

Reported campaign validation: **313 portable tests passed**, **two private
pinned-baseline hash-oracle tests passed**, plus independent output checks, Ruff,
REUSE, repository audit and isolated wheel smoke tests. The original E15–E19
private specimen archives were not available for that run. No new native
database acceptance test occurred during that earlier campaign; no real
guest-clock delta was measured. The later operator-reported native display
milestone is recorded separately below; it does not establish save persistence.

## Next practical gates

1. **Calendar display milestone achieved; controlled persistence remains open:**
   the operator reviewed all 29 appointments and displayed alarm states in native
   DeskMate. [Issue #69](https://github.com/smartyhall/deskmate-formats/issues/69)
   remains open for hash-pinned installed-file identity, manifests and a separately
   authorized controlled save. No-op OK does not establish an actual rewrite.
2. **Second Address Book contact:** a controlled, freshly cloned A01 scenario
   must establish index ordering/counters/physical append before a multi-contact
   writer is generalized. [Discriminating trial](docs/research/addressbook-codec.md).
3. **Calendar native multipage acceptance:** verify the hash-pinned 61-appointment,
   30-date candidate on a separately authorized disposable DeskMate installation,
   including records on pages 4, 6 and 7. Distinguish display/read traversal from
   an independently approved one-edit/save persistence test. [Download and checklist](docs/research/calendar-30-day-native-acceptance.md).
   A tool-generated full month exists; **native compatibility is not yet established**.
4. **Future sync semantics:** preserve high-precision original CalDAV times when
   the native projected representation is unchanged; interpret confirmed changes
   at the supported quarter-hour granularity, with conflict and tied-start
   handling. This is a **design requirement, not implemented sync**. See
   [operator UI evidence](docs/research/calendar-ui-time-normalization.md)
   and [interop policy](docs/interoperability.md).
5. **Infrastructure only when blocking:** unresolved DMDB binding [#25](https://github.com/smartyhall/deskmate-formats/issues/25),
   launcher safety [#35](https://github.com/smartyhall/deskmate-formats/issues/35),
   Filer enablement [#54](https://github.com/smartyhall/deskmate-formats/issues/54)
   and real supervisor canary [#58](https://github.com/smartyhall/deskmate-formats/issues/58)
   remain separate tracks.

Earlier [readiness research](docs/research/next-codex-campaign-readiness.md)
is a dated pre-campaign audit; [S0 live-canary documentation](docs/research/codex-supervisor-s0-live-canary.md)
is a runbook, not evidence of a paid live test.

## Research and publication safeguards

Follow [AGENTS.md](AGENTS.md) and [LICENSING.md](LICENSING.md). Original
commercial media, ROMs, installed trees, raw memory/screenshots, real user data
and credentials remain outside public Git; controlled synthetic records may
be retained with byte-exact provenance and licensing. Never replay an uncertain
guest-changing operation or mutating Codex request. Identify the owned process,
instance, operation, source/fixture hash and evidence scope; record unknowns
explicitly. The browser is read-only and cannot authorize native operations.

**Maintenance:** Update this dated status only after verifying new source and
experimental receipts. Preserve historical reports as written; amend a current
index or add a dated successor note instead of changing what an earlier
experiment claimed to know.
