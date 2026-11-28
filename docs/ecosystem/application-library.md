# DeskMate application library

This is the overview for campaign `application-library-001`, an
operator-authorized installation campaign that built reusable historical
DeskMate application environments for future research. It complements the
[ecosystem catalog](README.md) and the
[DeskMate release installation guides](deskmate-installations.md): the release
guides cover DeskMate itself, while this library covers the third-party and
companion applications that ran on it.

The library is a set of reproducible private guest baselines plus published,
independently authored records of how each baseline was produced and what was
observed. Commercial media, installed program trees, protected resources, ROMs,
disk images, and raw capture sequences stay outside Git. Each application has a
machine-readable entry in the
[application library registry](application-library-registry.json); this page
explains the method and the states those entries record.

## What the campaign produced

| Application | Release observed | Architecture | Qualification |
| --- | --- | --- | --- |
| DeskMate host environment | 03.05.00, nine-disk TVDog set | Native DeskMate environment | Installed, sealed baseline |
| Sierra HomeWord II | 1.20 (1990 media) | Native module on a bundled runtime | Installed, smoke-tested, save and cold reopen |
| Lotus Spreadsheet | 1.0 (`LOTUS-DM`, 1989-1990 files) | Native module plus standalone launcher | Installed, smoke-tested, native save |
| Express Publisher | 1.00, runtime 03.05.00 | Standalone distribution with its own DeskMate runtime | Installed, launched, page edited; save blocked by dialog input |
| Quicken 2.0 | Release 4 media (`quicken2.zip`, `Q.PDM` dated 1989-10-19) | Standalone `INSTALL.COM` with runtime 03.02 | Blocked: installer stopped at its splash; archive lacks the program disk 2 that `Q.PDM` requests |

Detailed procedures live on the subordinate pages:

- [DeskMate 3.05 host environment](application-library-desk305-host.md)
- [HomeWord II 1.20](application-library-homeword-ii.md)
- [Lotus Spreadsheet 1.0](application-library-lotus-spreadsheet.md)
- [Express Publisher 1.00](application-library-express-publisher.md)
- [Quicken 2.0, blocked installation](application-library-quicken-2.md)

## Qualification states

The campaign uses the same evidence discipline as the release guides, with
distinctions that matter when a future agent picks an environment. These are
the states the registry records per application:

1. **Verified media** — an archive in the private TVDog mirror matches its
   transfer receipt by size and SHA-256.
2. **Inspected installer** — the installer was listed or run far enough to
   identify its model, choices, and media order.
3. **Installed** — the installer reported completion and the destination
   directory holds the program tree.
4. **Native launch** — the application reached its own interface in a
   disposable guest.
5. **Partial functional testing** — a representative native workflow was
   exercised, but not to a completed artifact.
6. **Native document creation** — the application itself wrote a document from
   fictional data.
7. **Cold reopen** — the application reopened that document after a full
   restart, or the campaign records that this was not verified.
8. **Candidate baseline preserved** — a stopped image, manifest, hashes, and
   installation record exist for review in private storage.
9. **Independent canonical qualification** — a second party reproduced and
   reviewed the environment. **No application in this campaign has reached
   this state.**

A package can stop at any step without invalidating the earlier ones, and the
registry records each state separately rather than as one label. Express
Publisher is installed, launched, and partially tested, but has no native
document; Lotus has a document but no verified cold reopen; HomeWord II reaches
native document creation and cold reopen. None is canonical.

## Host environment and baselines

All installations started from the same verified DOS 5.00 baseline and one
machine profile, so results are comparable:

- Emulator: 86Box 7.0 automation build, SHA-256
  `e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d`,
  controlled only through its authenticated loopback socket.
- Machine: `tandy1000rsx`, i386SX at 25 MHz, 4,096 KiB RAM, internal video and
  sound, `fdd_01_type = 35_2hd`, 54,525,952-byte IDE disk.
- Parent baseline: `rsx-dos5-pristine-20261104` (Tandy MS-DOS 5.00).
- Campaign host: DeskMate 03.05.00 installed from the nine-disk TVDog set and
  sealed as `applib-001-host-desk305-20261128`, disk SHA-256
  `cd530f8f9cbb7fd550d5af69632bdb0480d5eca0a5426c654bcb58d40cb32e41`.

Each application machine is a clone of the sealed host, so the DeskMate 3.05
research environment is never overwritten with a bundled 3.02 or 3.03 runtime.
Where a distribution carries its own runtime, that runtime is installed into
the application directory and preserved there; see
[Express Publisher](application-library-express-publisher.md).

Stable baseline identifiers follow
`applib-001-<product>-<release>-<profile>`; the registry records the matching
private directory name. Private baselines live under the campaign's private
laboratory storage, not in this repository.

## Installation architectures observed

The queue is not homogeneous, and the differences decide which procedure a
future agent needs:

- **Native module on an existing DeskMate runtime.** Lotus Spreadsheet installs
  a `.PDM` module and resources that the DeskMate runtime loads.
- **Distribution with a bundled runtime.** Express Publisher installs a
  complete DeskMate 03.05.00 runtime plus its own `.PDM`, launcher, and fonts
  into `C:\EXPRESS`, and runs without an existing DeskMate installation.
- **Standalone installer expecting application-specific media.** Quicken 2.0
  ships `INSTALL.COM` for runtime 03.02 and expects a program disk that the
  preserved archive does not contain.
- **File-set distribution without a factory disk layout.** HomeWord II arrived
  as a 7-Zip set of extracted 5.25-inch 360 KiB disks; the working media were
  rebuilt from the same file contents.

## Media reconstruction

Two packages needed new media before an original installer could run:

- The nine-disk DeskMate 03.05 set was distributed as flat file sets. The
  campaign built nine labelled 720 KiB FAT12 images with
  [`tools/experimental/application_library_media.py`](../../tools/experimental/application_library_media.py),
  which shares its FAT12 writer with the release media tool and adds directory
  sources, explicit geometry, and a hash receipt.
- HomeWord II's original 360 KiB images could not be mounted after the drive
  geometry changed: the BIOS reported invalid configuration information and the
  machine looped on floppy boot. The original images remain the media identity
  of record, and the working 720 KiB images were rebuilt from their exact file
  contents, not from a different distribution.

Rebuilt media are disposable inputs, not preservation copies. The original
archive bytes and their hashes stay authoritative.

## Runtime configuration findings

Express Publisher's runtime refuses to load unless `CONFIG.SYS` contains a
`FILES=20` statement. A larger value such as `FILES=30` still failed, and the
runtime did not accept the same statement when it followed device drivers. The
working configuration placed `FILES=20` first. The exact test is recorded on
the [Express Publisher page](application-library-express-publisher.md); treat
it as an observed runtime requirement rather than documented behavior.

## Input limits in the native dialogs

Guest control uses only the emulator's automation socket. Two observation
limits follow from that and are recorded honestly rather than worked around:

- DeskMate file dialogs generally ignore socket key events that reach the
  application's document area. HomeWord II's Save As and Open dialogs accepted
  typed filenames after the list received focus; Lotus's Open dialog selected
  the highlighted list entry instead of a typed name; Express Publisher's Save
  As dialog ignored all socket keys.
- Consequently the Lotus and Express smoke tests stopped short of a native
  reopen of the newly saved document. HomeWord II completed the full cycle.

These limits are about the input path, not about the applications.

## Relationship to the Installation Atlas

The nine-disk DeskMate host here is a separate installation identity from the
one in the unmerged Release Installation Atlas 001 (PR #225). The two runs
reconstructed nine byte-identical working images from the same TVDog sets and
followed the same installer sequence, but their stopped disk hashes differ. The
[host guide](application-library-desk305-host.md#comparison-with-the-installation-atlas)
records what was independently reproduced and what was not, including the
140-directory-file versus 142-aggregate-file reporting difference.

Both campaigns also produced the same installer-banner frame. This PR withdrew
its duplicate and publishes a distinct installation-complete frame instead.

## Registry

[`application-library-registry.json`](application-library-registry.json)
records, for each application and release: a stable identifier, product and
publisher, observed release, category, source archive identities, installation
architecture, runtime dependencies, compatible machine profiles, qualification
state, guide link, private baseline identifier, smoke-test result, native file
types, existing research, remaining opportunities, and blockers.

The registry is separate from the Desktop release registry being developed in
PR #225 and does not modify it. A future agent should read the registry first,
then open only the guide for the environment it needs.

## Evidence

Sanitized qualification receipts are in
[`docs/evidence/application-library-001/`](../evidence/application-library-001/README.md).
They record media hashes, stopped-disk hashes, installed file counts, smoke-test
observations, and capture inventories without publishing any commercial bytes.

Documentary screenshots from these sessions are published under the project's
standing documentary-image authorization. They show the applications running
with fictional data only; interface artwork remains the property of its
publishers.

## Remaining queue

Verified media awaiting qualification in the private archive, in the order the
campaign ranked them:

- Music Studio 3 for DeskMate.
- Q&A Write 1.00 for DeskMate, including the `DMQNAFNT.TXT` font-import note.
- Print Magic 1.1.
- Form Finisher 1.01.
- Business Graphs.
- First Publisher 2.01 for DeskMate.
- MemoryMate 1.0 and Outliner.
- RightWriter 3.2 for DeskMate.
- Personal Financial Assistant and the Retail Home Organizer components.
- Workgroup, Macro, and Thesaurus companions.
- Mavis Beacon Teaches Typing 1.31T, Alge-Blaster Plus 1.3, StudyWare Physics,
  GRE, and SAT variants.
- filePro for DeskMate.
- Quicken 2.0 Release 3 (`QDM.zip`), which was never attempted and remains a
  separate identity from the blocked Release 4 attempt.

Historically documented titles without acquired media stay in the
[ecosystem catalog](README.md) and are deliberately not part of this
installation queue.

## Research opportunities

The campaigns that follow should use these environments rather than rebuild
them. The most promising comparisons are listed per application; the common
threads are:

- Native document interchange between DeskMate Text, HomeWord II, Q&A Write,
  and RightWriter.
- Shared runtime and resource use: which `.RES`, `.R89`, `.FF1`, and `.PDM`
  files are application-specific, and which come from the bundled runtime.
- Standalone-versus-integrated behavior for Lotus Spreadsheet, Express
  Publisher, and Quicken, including whether files written in one mode reopen
  in the other.
- Printer driver and font resources shared between Print Magic, Print
  Companion, First Publisher, and Express Publisher.

## Sources

- TVDog DeskMate archive index and file-set listings:
  <http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/00_index.txt> and
  <http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm305dsk.txt>. The
  nine-disk DeskMate 03.05.00 set is `dm305dk1.zip`–`dm305dk9.zip`.
- DeskMate 03.05.00 installer banner, observed in the guest: "DeskMate /
  Version: 03.05.00 / Copyright 1984,1990 Tandy Corporation".
- Express Publisher 1.00 installer and runtime, observed in the guest:
  "(c) 1991, Power Up! Software Corporation" and "DeskMate Runtime /
  Version: 03.05.00".
- HomeWord II 1.20 media identity: `HomeWord II 1.20 (1990) (5.25-360k).7z`
  in the private TVDog mirror, archive SHA-256
  `8de88e3d08f355b7b0e09e77452b714e0132afba56c6b70f40582c01f2a8c2cf`.
- Lotus Spreadsheet program files dated 1989-09-28 and 1990-09-26 in
  `Lotus-Spreadsheet-for-DeskMate/123disk1.zip`.
- TVDog reference library and acquisition records:
  [tvdog-reference.md](tvdog-reference.md), [acquisitions.md](acquisitions.md).
