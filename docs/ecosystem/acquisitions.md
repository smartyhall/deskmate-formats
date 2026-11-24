# Immediate acquisition handoff — next Codex campaign

For current acquisition priorities and edition status, use the
[prioritized gap list](acquisition-gaps.md). The sections below retain the
original leads, later transfer receipts, and experiment-specific plans.

The operator supplied two archives in ChatGPT on 2026-11-19. Their
exact uploaded bytes were hashed here; no transfer to the Windows VM
is claimed. Acquire the same files by an accessible operator-provided
path or the documented distribution source, verify SHA-256, and record
any version differences rather than silently substituting.

| Filename | Bytes | SHA-256 |
| --- | ---: | --- |
| dm305dk9.zip | 86916 | 52befdd828e7065fc2e1fde60c010693d946ca5e4c477703f9c43564086cd883 |
| PFS First Publisher 2.01 for DeskMate.7z | 671052 | b080193f1d05d3db7e6097e1dd08992c73bc3af8d72155a111c27757c94c50a7 |

- First Publisher distribution lead:
  https://winworldpc.com/product/first-publisher/201-for-deskmate
  (also lists a separately available book).
- DeskMate disk 9 distribution lead:
  https://www.dosdays.co.uk/computers/Tandy%201000/download.php
  (verify the exact archive; no direct download link verified here).

Use a private archive directory under C:/DeskMateLab and preserve
the original archives before extraction. Do not put their bytes in Git.
The ChatGPT attachment paths are not Windows VM paths.

DeskMate disk 9 ZIP directory was directly checked: COBB.FF1,
MARIN.FF1, and eight DMVE display RES files for Hercules, MCGA,
Tandy, Tandy 1000, CGA, EGA, VGA and TC16. Compare exact font hashes
against the existing pinned resources and inventory display resources.
Do not assume this disk provides a new face.

First Publisher: prior inspection reported three FAT12 disk images,
MASTER.FNT, EXTRA.FNT, APLASER.FNT, HPLASER.FNT, DESKJET.FNT and
FONTMOVE.EXE. Reproduce and verify that extraction in the VM; record
exact hash/size identities, font record descriptors and the HP-soft-font
conversion path. WinWorld identifies the bundled runtime as 3.02.
Do not overwrite the current 3.05 lab runtime; test in a separate clone
and compare dependencies. Native-format acceptance and any shared
clipboard/font behavior are untested. Record `.PUB` and other candidate
extensions only as measured or explicitly unverified.

For the next Draw/font campaign, stage these archives and make a
bounded inventory. Prioritize FF1 serialization, original synthetic
font creation, modern OpenType/TrueType conversion and native
load/print/round-trip verification over an extensive First Publisher
reverse-engineering diversion. Search for additional FF1 resources,
especially the historical Rockwell reference, and for Express Publisher
and the Q&A Write font-import documentation. Record blocked acquisition
honestly; no paid acquisition or contacts without separate authorization.

## Verified Windows VM acquisition

Dos Days disk 9 and WinWorld's Quebec mirror delivered the exact hashes
and sizes above. The original archives and full per-file receipt are in
the private typography evidence directory. No alternate identity was used.

Cobb and Marin match the [pinned original fonts](../research/draw-fonts-20261119.md).
The eight DMVE entries all begin with DOS MZ headers. Device identities,
sizes and hashes are recorded below. Their roles in System text and
graphical primitives remain unverified by execution tracing.

| Member | Bytes | SHA-256 |
| --- | ---: | --- |
| DMVE1000.RES | 5314 | ce3131cdbf1c1595a9547078c9ff88cb935aa64534ae8657c91be64dbd41df1f |
| DMVECGA.RES | 5378 | b6dd694cec5420e182032678bea3e3b416f8f8f1516e6ebe0b1c86340ee6fac6 |
| DMVEEGA.RES | 5330 | 590243846fe0cfeca35abe44fcee74c4f71ed155f4e6cbac0cd689a457525b4b |
| DMVEHERC.RES | 5378 | 07dbc1e5c3fa947ba9846794f2d6fff80275eb66c3fb479b2ffb10e4e77bf982 |
| DMVEMCGA.RES | 5250 | 8852ec86acdedf476c8fb28127aa9ef4ea9ec7059dd69018d0af0a1f43d41c6f |
| DMVET.RES | 5314 | 4c9468af3f3b9fc6db0d76eb7e859dcd04e5ff0aadebc67833be6d5a24f0ce08 |
| DMVETC16.RES | 5474 | 3b4ab1f0f9bc46a71edde25e13886ffc1ccf2fdbee149cc90a9b7dd1dd3016b1 |
| DMVEVGA.RES | 5426 | 4e582f82dd1727832e92802c86b508f0b0a777b8cfd9c9e94d4edeb780148a09 |

### First Publisher 2.01

7-Zip 26.05 and the independent
[typography inventory](../../tools/experimental/typography_acquisitions.py)
agree byte for byte on the files on all three 737,280-byte FAT12 images.

| Image | SHA-256 |
| --- | --- |
| FPDISK1.IMG | e762608bc736a6786b99b4062fdf462081398e19578e89a7b5dff10eb140c339 |
| FPDISK2.IMG | 5c3604401d224446b9a6f6a081c29a8b657b01838d9cf35226ca23bc8526d45f |
| FPDISK3.IMG | 8901b0779a0cb61e03ff5332d0baf4a3050eb42ca145352a4741555101e22af5 |

The five libraries use a big-endian Macintosh-style map with one FONT type.
Its 12-byte references contain a resource ID, a Pascal-string name offset,
an attribute byte, a 24-bit payload offset and a handle field. Names carry
family, point size, style and display-name metadata. Payloads begin with a
big-endian length. The glyph payload grammar remains opaque.

| Library | Entries | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| MASTER.FNT | 36 | 166766 | abcfddb2274b6e77a46afe21d178add9448a384fb1791f348a8cda7e83aaf20e |
| EXTRA.FNT | 26 | 102856 | 3cff5594b1d731ff8c54413006501a44f276f07fc115ead30400d2f11a3dba1f |
| APLASER.FNT | 54 | 349901 | 79f4848e7ce347853b89a072f85ad0aee002890e9ec1004d5e29d5d244c91b15 |
| HPLASER.FNT | 7 | 16034 | 7d8bce1e19367de7b0a65af6db43b80251083f4f0cac9a096a8b6034a7d1cc6a |
| DESKJET.FNT | 36 | 85928 | ab13520c21f1238719238b4ba24f07e925b2a00ba7402f0be2795934cd09d82c |

FONTMOVE.EXE is a 55,664-byte MZ program
(SHA-256 ec4c97f5ea09139ba1921008d2f9cea400bd629eec5fbb240997295856719167).
Its UI describes copying, erasing and importing portrait HP soft fonts,
with outputs in an FNT library and FONTSLJS.DIC/FONTSLJS.WID.
FONTSLJ.DIC and FONTSDJ.DIC contain PCL escape sequences. LASERDEF.PS
and FONTSLW.DIC accompany the Apple LaserWriter support. The distribution
has FP.HLP and 16 PUB examples with signature AA AA AA 01.

FP.EXE, FPSTART.PDM, FP.PDM and FP.OVL are candidate application components.
FPVID.EXE and FPVID.PDM ship with DMVD*.RRS display resources and
DMCSR/DMCSRHX/DMGUF resources. The disks contain zero FF1s. Native
installation and shared runtime calls remain open.
The FP.EXE string table identifies the bundled DeskMate runtime as
03.02.00. FP.PDM contains references to MASTER.FNT, DMCSR.RRS and
DMVDA.RRS. The latter two identify dependencies in that runtime path.

### Rockwell and additional leads

The sole Rockwell reference is in RSX disk 4, DOCUMENT/ILLSTRTN/COOKWARE.FIG
(SHA-256 20c70a4486e631c5c01511b53457a77e852c6c5f981da6a3fbd7dd787e83d499).
Its Uf starts at file offset 992. The attributes are 01 FF 00 00 00 00,
with an ASCII Rockwell field padded to 30 bytes, point size 5, width 81,
and six label bytes. Descriptor bytes 56–95 are
05005100000000000c00ff00000000000000000000000000007d005400c4000900d303d7025566d303.
The attribute bytes match the known external outline profile. The record
does not establish the historical resource, import path or printer behavior.

The bounded search found no matching Express Publisher or DeskMate Q&A
Write disk or Rockwell FF1. The Q&A Write 1.02 download listing is
for the DOS product and does not identify a DeskMate edition.
[Historical Tandy Files Listing](https://groups.google.com/g/comp.sys.tandy/c/hlUY-62ApTM)
· [Q&A Write 1.x catalog](https://winworldpc.com/product/qa-write/1x)

Two historical text files are preserved privately. The 15,962-byte
DM_PROGS.TXT copy from the laboratory's Oldskool archive is dated
1994-09-20 internally and has SHA-256
4699f28b2ae9d699c767e212b38f547805b3a1a96579ced524dc6b8f0c56c68a.
It identifies Express Publisher as using DeskMate 3.05 Atech fonts.
This is a contemporary lead for shared outline resources.
[DM_PROGS.TXT](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm_progs.txt)

The 6,013-byte DMQNAFNT.TXT download has SHA-256
50f613d3c1b3d76ece1e5ef7e74440870de4d39eaee8326c13b95aed4f1ae8e5.
Its example modifies IBM ProPrinter font-selection descriptions,
control sequences and spacing fields in Q&A Write's IBMPRO.FNT.
It documents printer definitions and provides no FF1 outline grammar.
[DMQNAFNT.TXT](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dmqnafnt.txt)

### Isolated First Publisher launch

The follow-up RSX clone copied all three 720 KiB images into a separate
DOS directory, C:\FP201. The three final copy summaries accounted for
21, 32 and 16 files. After setting DMCONFIG to that directory,
launching FP from DOS reached the First Pub editor with a new PUB
document and the native font menu. The 3.02 runtime stayed in the
private test directory. No production or established 3.05 files were
replaced by the First Publisher runtime. Shared runtime and clipboard
calls remain open. See the
[typography laboratory report](../research/typography-lab-20261119.md)
for the stopped disk and emulated time.

## Express Publisher — operator-supplied acquisition lead

The TVDog campaign acquired and validated all three Express Publisher
disk sets and the manual. It also located DeskMate Q&A Write 1.00.
The [archive reference catalog](tvdog-reference.md) supersedes the
acquisition status in the original leads below.

After the typography laboratory campaign, the operator identified this
specific archive directory:

http://ftp.oldskool.org/pub/tvdog/tandy1000/wares/Express-Publisher-for-DeskMate/

HTTP and HTTPS retrieval from ChatGPT failed. Do not infer the directory
contents, exact version, or successful acquisition from the URL alone.
The next Codex native campaign should retrieve its listing and relevant
media from the VM (try the original HTTP URL, HTTPS or the archival FTP
service if available), preserve original bytes privately, inventory and
hash every acquired file, and verify edition and media integrity. Install
in a disposable isolated clone, without replacing the verified 3.05
baseline. Inspect FF1 resources and internal family/variant names against
Cobb, Dixon and Marin, especially the OEM Rockwell reference, plus shared
DMFONT resources, example documents and print drivers. Test actual font
selection, native saves and printing where practical. Update the catalog
with measured results; if acquisition remains blocked, record the failure
rather than substituting an unrelated DOS/Windows edition. No commercial
media or extracted proprietary font resources belong in Git.

## Broader commercial software inventory

The [descriptive index review](tvdog-directory-index-review.md)
reconciles the completed preserved tree with the searchable archive. It
identifies additional application, companion, and utility packages and
records the claims still awaiting version or hardware checks.

The operator also identified the parent archive directory as containing
numerous DeskMate software packages:

http://ftp.oldskool.org/pub/tvdog/tandy1000/wares/

Treat this as a priority acquisition source for the ecosystem catalog.
HTTP and HTTPS listing requests from ChatGPT returned 502. Retrieve the
actual listing in the Windows lab; retain a dated private copy, enumerate
relevant child directories and files, and cross-reference the results
with DM_PROGS.TXT, the existing catalog and period advertisements.
Separate native DeskMate applications and bundled runtimes from ordinary
DOS software and other platforms. Record exact names, editions, publisher,
catalog numbers where evidenced, archive URLs, acquisition status and
verification method. Do not infer contents from directory names alone.
Prioritize DeskMate editions and resources relevant to shared fonts,
printing, word processing, database and graphics. Acquire relevant media
privately with SHA-256 receipts, preserving originals and deduplicating
identical files. Use a bounded, polite download process; if the archive
is unavailable, retain the lead and report the error. Identify missing
catalog titles and newly discovered candidates. The subsequent operator decision authorizes a full private mirror of
/pub/tvdog/ under [the archive protocol](archive-mirror.md), superseding
this earlier selective acquisition limit. No public rehosting of original
media or bulk installation in the core research image. Extensive per-title
reverse engineering belongs to later campaigns; the next typography
campaign should undertake the inventory and useful adjacent acquisitions
without displacing its primary research objectives.

## Historical documentation and community archive

The operator supplied the [TVDog documentation index](http://www.oldskool.org/guides/tvdog/documents.html)
and its pasted listing. The listed filenames and descriptions were
inspected, not the underlying downloads. Check existing private archives
first. Retain a dated listing and acquire relevant files from
http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/ .

| Priority | Listed files | Research purpose |
| --- | --- | --- |
| Immediate | aoldesk.zip | AOL DeskMate forum: search FF1, Atech, Rockwell, font installation, hinting, variants, printing, layout, undocumented formats, SDK and third-party titles |
| Immediate | videomem.zip | Historical DeskMate Text document; inventory and test reader privately |
| Immediate | cblmgc.zip | Two Print Magic documents; identify edition and format, preserve privately |
| High | mm.zip, cistanne.zip | Radio Shack newsletters and monthly memos, official CompuServe announcements; release dates, catalog numbers and product changes |
| High | expsoft.zip, rscat87.zip, rscat89.zip, rscat90.zip, rscat91.zip, rscat92.zip, rssoft86.zip, rssoft87.zip, tccat85.zip, tccat87.zip, tccat88.zip, edulist.zip | Software and hardware catalogs; dated sales offerings, editions, prices, compatibility |
| High | direct.txt | 1992 factory-direct price list |
| High | cistanfo.zip, aoltan.txt, delfor88.zip through delfor94.zip, tandy.zip, turp2_2.txt, julynl.txt | Community discussions and leads |
| As needed | dmp120.txt, 2100cod.txt, 26-1255.zip, 26-1280.zip, 26-1280a.zip, 26-2839.zip, dmp240.txt | Printer codes and device profiles |
| As needed | 1kprog.zip, 1ktech.zip, tltech.zip, sltech.zip, whichvid.txt, tandymap.txt, 1ktech-1.zip, 1ktech-2.zip | Hardware/video/I/O/audio context; verify model applicability |
| Later | 1kguide.zip, pdmquik.zip, sxquik.zip, practsl.zip, practtl.zip, tl3user.zip, rlinst.zip, rlxuser.zip, rlxauser.zip | Early application workflows and machine-specific references |
| Later | meetpcl.zip, tandy2.txt, tandy7.txt, sensman.zip | PC-Link, SchoolMate, WinMate context; distinct platform/service research, no live legacy service connection |

Record URL, acquisition date, hashes, archive members, document date/title,
and page or message locators. Build a searchable private text/OCR index
where useful, with uncertain OCR flagged. Distinguish community reports
from independently reproduced behavior. Keep original archives, scans,
forum messages, personal contact details and historical documents private.
Publish independent findings, citations, metadata and eligible synthetic
fixtures only. Retain dated price and product evidence for the future
demonstrator's internally consistent purchase records. Do not invent the
family canon. Use the prioritized list to order the initial transfers within the full
private mirror; all permitted in-scope files remain eventual targets.
See the [archive protocol](archive-mirror.md).

## Complete TVDog archive — operator decision

The operator expanded the acquisition scope to the entire publicly
accessible subtree at http://ftp.oldskool.org/pub/tvdog/ . The
[archive mirror protocol](archive-mirror.md) governs server-friendly
acquisition, persistent verification, offline indexing and publication
of annotated source references. This replaces earlier selective-only
acquisition instructions within this subtree; it does not expand the
scope to other hosts or parent directories. Prioritize the existing
DeskMate leads first within the mirror queue. No mirror is yet claimed.

## DM_Music, MidiMapper and the Tandy1000 group archive

[PR #129](https://github.com/smartyhall/deskmate-formats/pull/129)
documents the Tandy1000 Yahoo Groups lead and separates Baldwin and
Hayes's SNG-to-HDS converter from the companion Windows player. The
[DM_Music ZIP](http://ftp.oldskool.org/pub/tvdog/tandy1000/sound/dm_music.zip)
acquired for this campaign matches the earlier private ZIP. Its two
members are the VB6 converter and its readme. The executable reports
file and product version 1.04. The differing version spellings in the
[author's discussion](https://groups.google.com/g/comp.sys.tandy/c/fq1OO44yLtI)
remain historical references.

PR #129 records the operator-supplied MidiMapper ZIP as 440,568 bytes
with SHA-256 `323a06e1ae757de09ac25721d94a29ac7bbb1d4038d91cd74cdcdaee2dad798b`.
Its CAB contains HDS examples and the player readme. SETUP.LST reports
player version 6.25.0.0 and its PAD XML reports 6.12. These are two
metadata observations. Record the actual PE resource after obtaining the
exact ZIP in the Windows lab. The samples may include manual changes or
different arrangements, so raw HDS from an observed converter run is
the differential comparison input. The author discussion and the
Tandy1000 archive remain leads for distinct releases and more
contemporary Music documentation.

## Tandy1000 Yahoo! Groups — community archive lead

The operator identified this Wayback snapshot (2006-08-15 14:01:02 UTC):

https://web.archive.org/web/20060815140102/http://groups.yahoo.com/group/Tandy1000/

Replay retrieval in ChatGPT failed; message and attachment coverage
remain unverified. This is separate from the authorized TVDog mirror.
Prioritize existing downloadable public archive packages over replay-page
crawling. Investigate:

- Archive Team collection: https://archive.org/details/archiveteam_yahoogroups
- Group metadata: https://archive.org/details/Yahoo_Groups_Metadata
- Search: https://archive.org/search?query=subject%3A%22yahoo%20groups%22%20Tandy1000
- Retrieval guide: https://datahorde.org/how-to-recover-your-yahoo-groups-from-the-internet-archive/

Verify the exact group name in metadata (master_T.csv), then look for
group-specific WARC or other public export packages. Do not download
unrelated multi-group batches indiscriminately. If no package is found,
make a bounded Wayback CDX inventory of the original group's public URLs
and capture dates, including message, topic, file and link paths and
the later /neo/groups/Tandy1000/ URL family. Respect archive service
policies and rate limits; do not infer missing captures or bypass access
restrictions. No bulk Wayback crawling is authorized by the TVDog mirror
decision. Preserve original packages and provenance privately when
separately approved, decode WARC/JSON or message exports offline, and
deduplicate by message identity and hashes while retaining capture
provenance. Distinguish user-reported technical claims from verified
native behavior. Search relevant messages for DeskMate SDK, formats,
fonts, Atech/Rockwell, Express Publisher, utilities, printer drivers,
Tandy hardware, and links to otherwise missing software. Public
repository output should be curated technical summaries and source
references, not raw messages, member details or attachments.

## DM_Music and MidiMapper — independent SNG interpretation

Operator-supplied author page:
https://web.archive.org/web/20120204044413/http://members.fortunecity.com/whb11/Midi/MyMidiPlayer.htm

Replay retrieval here failed; recover the page and linked README(s) in the
lab if accessible. Independently located primary discussion:
https://groups.google.com/g/comp.sys.tandy/c/fq1OO44yLtI

On 2006-12-14 WB announced the Windows 32-bit SNG-to-HDS text converter,
co-developed with TVDog. The 2007-02-05 post describes conversion of
instrument dynamics in converter version 1.4 or later, and a default
of mf in DeskMate versus p in the author's player. The 2007-03-08 post
calls DM_Music version 1.05 and reports manual adjustments to distributed
MIDI examples. Preserve the version spelling discrepancy; do not assume
1.05 sorts before or after 1.4 without the actual release files/readme.
The 2014-06-14 post gives the moved author site and converted MIDI page;
the 2015-08-19 post names MidiMapper 6.49. A 2017-12-20 reply reports
failure to find backed-up applications, not proof they are unavailable.

Acquisition leads (not verified live downloads):
- http://whb.comli.com/Midi/MyMidiPlayer.htm#DM_Music
- http://whb.comli.com/Midi/MyPDM2toMidi.htm
- http://my.voyager.net/~wb/misc/MidiMapper.zip (player/docs, not proven converter)
- TVDog mirror private inventory and Tandy1000 Yahoo Groups file archives.
- Bounded Wayback CDX lookup for the original and moved page directories,
  then exact linked executable/ZIP and readme URLs; avoid indiscriminate crawl.

The same thread contains first-person posts from DeskMate Music project
manager Kevin Michael Vail (2006-12-15), describing sampled-note
interpolation, the shared mouse/audio converter, and RTC-assisted buffer
servicing; and Frank Durda IV (2006-12-19), describing earlier PSSJ recording
limitations, the TL/3-era hardware revision and SND header changes to
identify recording hardware. Treat these as historical hypotheses for
native timing/recording experiments, not offsets or exact algorithms.
Preserve links and dates, not wholesale copies of the posts.

After acquiring and hashing an exact converter release and docs privately,
run it in a disposable isolated Windows guest (no network; not the core
research VM). Use fresh original synthetic controls and private historical
SNGs with unresolved semantics. Compare untouched HDS output against the
independent parser event stream and original DeskMate native evidence.
Vary one field at a time: initial/changed dynamics for each voice, instrument
slots and names, tempo, meter/key, accidentals, ties/rests/dots, repeat
boundaries and crossings, missing slots and unsupported records. Include
same-note timing and duration controls, and test absent versus explicit
metadata. Record byte offsets, exact input hash, converter version/hash,
raw HDS hash, normalized differences, warnings and omissions. Compare
HDS before MIDI, and distinguish converter behavior from player defaults,
manual edits, articulation and MIDI channel mapping. A plausible HDS result
is an independent hypothesis, not proof of original DeskMate semantics;
confirm discrepancies with native UI/save/playback and static evidence.
Keep third-party binaries and historical arrangements private; publish
only original synthetic eligible data, independent findings and provenance.
This is a bounded follow-up to sampled Music/SNG research, not a reason
to abandon the next typography/Express Publisher campaign.

### Operator clarification and supplied MidiMapper archive

The operator identified **DM_Music.zip** as the expected separate
converter package in TVDog. Locate it case-insensitively in the local
mirror's manifest, directory listings and nested archives before making
further requests. Pin the observed exact original URL and hash; do not
guess a direct link. MidiMapper.zip is the companion player, not a
substitute for DM_Music. The author independently distinguishes these
programs in the December 2006 Usenet discussion.

The operator supplied MidiMapper.zip (440,568 bytes; SHA-256
323a06e1ae757de09ac25721d94a29ac7bbb1d4038d91cd74cdcdaee2dad798b).
Its four ZIP entries are MidiMapper.CAB, pad_file.xml, setup.exe and
SETUP.LST. The manifest identifies MidiMapper.exe 6.25.0.0, dated
2007-03-24, while the included PAD XML declares 6.12 (2007-01-28).
Preserve both metadata observations; verify actual PE resources in the lab.
The PAD identifies W. H. Baldwin / Horizon Software and freeware status,
not a source-code license. The CAB was independently read in memory
using libarchive without executing or installing any component; 46
members include 33 HDS files, MidiMapper.exe, a MIDI OCX, setup support
and Midi_ReadMe.htm. No DM_Music executable is listed. CAB SHA-256:
85ca490767cc0882d0aaa7a37e6f1b4debcecb73c195dfa6c5f3d68741324b4e.
The extracted readme was 31,955 bytes (manifest advertises 35,166;
reverify extraction and possible version mismatch), SHA-256
10fda8778e0b89459541faf0eb1eb434337f4f592c1d9fa2255fe17342a71835.

Readme sections describe [Song] and [Notes], PolyDur=True, PolyPhony,
slash-separated voices with different durations, dotted durations,
per-voice dynamics (pp through ff), velocity scaling, raw MIDI events,
and annotations for key, meter, bars and score markers. Some annotations
are ignored by the player. Treat these as documented HDS semantics,
not established SNG field meanings. The bundled Canon, Sonatina and
Bach arrangement candidates may correlate with the native SNG corpus;
manual edits and new voices/instrument assignments are possible. Compare
new converter output before using bundled HDS as historical controls.

Use privately archived bytes and readme for the offline investigation.
The uploaded file is not automatically available on the Windows VM;
acquire the exact package through an operator-provided local copy or
verified original archive URL. No installer execution, server download,
or transfer to the VM was performed in this ChatGPT turn. Do not
publish third-party binaries, historical arrangements, full readme or
contact information in Git.
