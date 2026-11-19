# Immediate acquisition handoff — next Codex campaign

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
Write disk, original DMQNAFNT.TXT, DM_PROGS.TXT, or Rockwell FF1.
[Historical Tandy Files Listing](https://groups.google.com/g/comp.sys.tandy/c/hlUY-62ApTM)
· [Q&A Write 1.x catalog](https://winworldpc.com/product/qa-write/1x)
