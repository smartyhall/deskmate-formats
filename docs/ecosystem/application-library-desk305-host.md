# DeskMate 3.05 host environment (application library)

This page records the host environment that every application baseline in the
[application library](application-library.md) clones. It is a clean nine-disk
DeskMate 03.05.00 installation made from the TVDog file sets
`dm305dk1.zip`–`dm305dk9.zip`, on Tandy MS-DOS 5.00. The release guides already
describe DeskMate 03.05.00 media generally; this page records the exact
installation used for application qualification.

## Identity

| Item | Value |
| --- | --- |
| Product | Personal DeskMate / DeskMate for DOS, generic 03.05.00 set |
| Media | Nine TVDog file sets, `dm305dk1.zip`–`dm305dk9.zip` |
| Source index | <http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/00_index.txt> |
| Media instructions | <http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm305dsk.txt> |
| Working media | Nine rebuilt 720 KiB FAT12 images, labels `DESKMATE_1`–`DESKMATE_9` |
| Operating system | Tandy MS-DOS 5.00 from `rsx-dos5-pristine-20261104` |
| Destination | `C:\DESKMATE` |
| Baseline | `applib-001-host-desk305-20261128` (private, sealed) |
| Observed version | 03.05.00 |

Installer banner in the guest: "DeskMate / Version: 03.05.00 / Copyright
1984,1990 Tandy Corporation".

## Machine

- 86Box 7.0 automation build, SHA-256
  `e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d`.
- Profile `tandy1000rsx`: i386SX 25 MHz, 4,096 KiB, internal video and sound,
  `fdd_01_type = 35_2hd`, IDE disk of 54,525,952 bytes.
- DOS 5.00 verified in the guest (`VER`) before installation.

## Media

The ZIP sets contain flat files rather than disk images, so each set was turned
into a labelled 720 KiB FAT12 image with
[`tools/experimental/application_library_media.py`](../../tools/experimental/application_library_media.py).
The tool writes both FAT copies, pads the label to eleven bytes, and emits a
per-member receipt; it does not execute anything from the set.

| Disk | Image SHA-256 |
| --- | --- |
| `dm305dk1.img` | `31305d3404c43124f0efa0fd5a628d9e3488e136637db92a2a49595f01995c5e` |
| `dm305dk2.img` | `d799bff522047be092004e493016756a3bbfc583e16cb597cb526554868914b0` |
| `dm305dk3.img` | `a760db22f66df3045014cf741d2ef60352713f32f94ef19b8e5778b5f64558e0` |
| `dm305dk4.img` | `9c413bdc3f95ebe94e23674f6eb443e7561f2dcf4f0fd64b6baf33625bcebe15` |
| `dm305dk5.img` | `dbd4f2ed518d902c577620332885d84786e7cee6247a8db3c22bfec239ee5154` |
| `dm305dk6.img` | `145f112ddf3d5f643ba6bbe5797b8cf3642e5a507587c31c91c6f88be9c58207` |
| `dm305dk7.img` | `e0c5f4911187fc166fd26cb622aeb18edc005b4c7b69ef88b691145fb6716f94` |
| `dm305dk8.img` | `7e32e26ac0bf1b76f848cc62208e599b81b93c1b4ad1b5837cdf1ed305e92c0a` |
| `dm305dk9.img` | `2484a3536da18a6f2816a8c879d1fa779502ff1155ccd6ca7acab7bfff91d3f8` |

These hashes describe disposable reconstructions. SHA-256 values of the
original ZIP sets in the private mirror remain the authoritative media
identity.

## Procedure

1. Boot the verified DOS 5.00 baseline; confirm `VER` reports 5.00.
2. Insert Disk 1, change to `A:`, and run `INSTALL`. Running `INSTALL` from the
   hard disk produces "Please change to the drive containing the DESKMATE 1
   disk before running install."
3. Accept the installer banner and the proposed destination `C:\DESKMATE`.
4. Supply Disks 2 through 5 at the prompts; the installer copies the startup,
   Desktop, Text, communications, Worksheet, Address Book, Calendar, Filer, and
   Form Setup components.
5. During the printer phase the installer requested `DMPDIBMM.ACC` from Disk 6.
6. Answer `ALL` for the remaining re-reads; the installer asked again for
   Disks 7, 8, and 9 and completed.
7. Reset to the hard disk and run `DESK`; the Desktop starts in 640×480 with
   Text, Address, Calendar, PC-Link, Quick Launch, and Teach Me.

## Result

- Installation completed with the installer's own completion screen.
- `C:\DESKMATE` holds 142 files, 2,602,369 bytes.
- DOS 5.00 verified before and after installation, and the Desktop launched
  from the hard disk.
- The session was stopped at 501,766 ms of emulated time and 30,886 frames.

## Sealed baseline

`C:/DeskMateLab/baselines/applib-001-host-desk305-20261128` (private) is
read-only and carries `baseline-manifest.json`. Stopped disk SHA-256:

```
cd530f8f9cbb7fd550d5af69632bdb0480d5eca0a5426c654bcb58d40cb32e41
```

The baseline manifest records the emulator build, machine configuration, BIOS
and ROM identities, configuration and NVRAM hashes, the media hashes above, the
installation record, and the relationship to
`rsx-dos5-pristine-20261104`.

## Use in the library

Each application baseline clones this sealed image, installs its package into
its own directory, and is preserved separately. Do not install applications
into this host baseline, and do not replace its runtime files with those from
an application distribution: several packages carry DeskMate 03.02 or 03.03
runtimes that would change the environment under test.

## Open questions

- Whether the nine-disk set's factory disk labels and layout can be recovered
  from period documentation rather than reconstructed.
- Which of the installed files are required for a minimal environment that
  hosts a single application.
- Whether the 03.05.00 Desktop and bundled Worksheet differ from the
  application modules installed by Lotus Spreadsheet or HomeWord II; see the
  per-application pages.
