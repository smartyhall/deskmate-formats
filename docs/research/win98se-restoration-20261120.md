# Windows 98 SE restoration and hardware evidence

The sealed retail checkpoint was restored to a new working directory and
booted with 86Box 7.0 on TCP loopback port 8767. The inventory verifier
matched all 18 source files before and after the trial. Restore copied the
configuration, both NVRAM files and the 4,294,950,912-byte hard disk.
The clone disk was initially SHA-256
`304d2aa76b1780837cad8ec6564e78044daf9e2f59be00e7a4de60dcd281a156`.
The original machine's relative CD path was rebased to the independently
verified external ISO. No private answer floppy was needed for the boot.
Authenticated `info` confirmed the clone disk path and mounted install CD.

The confirmed machine profile was ASUS P/I-P55T2P4 (Intel 430HX), Pentium
MMX at 200 MHz, 128 MiB, PCI S3 ViRGE with the Diamond Stealth3D 2000 BIOS,
and Sound Blaster 16 PnP. Both floppy drives were configured as 1.44 MB,
and all four configured network links were down. The IDE geometry was
8322 cylinders, 16 heads and 63 sectors. System Properties reported
Windows 98 Second Edition 4.10.2222 A. The first observed Welcome screen
was at 40,065 emulated ms. The guest Shut Down command reached the
safe-to-turn-off screen by 121,261 ms. The emulator acknowledged its
native quit at 131,261 ms. These are observation times on the first
restored boot.

The first launcher invocation received an early read-only transport
failure. A fresh authenticated status request identified the same
listener, held at zero. The launcher now retries read-only startup
probes within its readiness timeout. A second visible launch passed
readiness using the same clone after guest shutdown. Native release,
verified hold and STOP acknowledgement were exercised on the first
boot, and paced input produced a usable guest registry export.

## Hardware enumeration

| Guest evidence | Interpretation |
| --- | --- |
| PCI 8086:1250 | Intel 82439HX host bridge, enumerated |
| PCI 8086:7000 and 8086:7010 | Intel 82371SB ISA bridge and Bus Master IDE, enumerated |
| PCI 5333:5631 | S3 ViRGE PCI (325), bound to Display/0000, 640×480 desktop observed |
| ISAPNP CTL0025_DEV0000, CTL0031 | Creative Sound Blaster 16 Plug and Play, bound to MEDIA/0000 |
| ISAPNP CTL0025_DEV0001, PNPFFFF | Unsupported Device, optional IDE logical slot on a non-IDE SB16 profile |
| ISAPNP CTL0025_DEV0002, PNPFFFF | Unsupported Device, reserved logical slot on this SB16 profile |
| ISAPNP CTL0025_DEV0003, CTL7001 | Gameport Joystick, bound to MEDIA/0001 |

The identities come from the guest's `HKLM\Enum` export to a
disposable FAT12 disk. The optional and reserved interpretations come
from the emulator's `sb_16_pnp_config_changed` and
`SB_16_PNP_NOIDE` initialization in `src/sound/snd_sb.c` at source
revision `855258da966f1594f568350be59e8e1eca082ed1`. That source
only configures logical device 1 on models with IDE. Logical device 2
only configures a wavetable on AWE32-class hardware. These findings
support retaining the stock sound profile while qualifying audio output
separately. No driver-qualified checkpoint is claimed here.

The executable SHA-256 was
`e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d`.
The three profile ROMs identified from pinned source, with their locally
measured SHA-256 values, were:

| ROM | SHA-256 |
| --- | --- |
| `machines/p55t2p4/0207_j2.bin` | `3cdabde2f4abbed74887ec714c2c87d565dc76a0fc8ee7b681c9bd82add20ecd` |
| `video/s3virge/s3virge.bin` | `74db5870591f60e36b5be403442bced1cf91b98446a6deB9de8b33f4b8086760` |
| `sound/creative/CT2941 PnP.BIN` | `6abaf06dab04a14a1d86d4ad9697b29bccef6b28f5ea85a9c864cf4211e2fa6f` |

## Checkpoint tool

Run `python tools/86box_checkpoint.py MACHINE verify INVENTORY.csv`
to check sizes and SHA-256 before boot. Use
`MACHINE restore INVENTORY.csv CLONE --original FORMER_MACHINE --port PORT
--media-inventory EXTERNAL.csv` for a new writable clone. The private
inventory has CSV columns `Path,Bytes,SHA256`. Absolute internal disk
paths are relocated. External CD images must match the separately
supplied inventory. Unrecognized absolute paths and writable external
media are rejected. The port is checked for availability at restore
time and again by the launcher.

Use `MACHINE save CHECKPOINT --include 86box.cfg --include disk.img
--include nvr/board.nvr` with a powered-off source and its actual
configuration, disk and NVRAM names. Preserve drive/media and ROM identity
receipts alongside the verified payload. Add `--seven-zip PATH` for a
second representation written privately as an incomplete archive until
explicit format testing, re-extraction and member-by-member hash validation
succeed. An interrupted run leaves a separately named staging directory.
A verified or restored receipt describes bytes and copying. Boot evidence
and a guest-initiated shutdown qualify the restored machine.

## Provisioning and maintenance

The installed provisioner already verifies the disposable disk and
mounted inputs before resumptions, includes a paced DOS prompt echo check,
reads BOM-bearing configuration and uses a private answer floppy. The
confirmed installation recipe uses a writable startup copy containing
FORMAT.COM and SYS.COM when they are absent, recognizes the Award CMOS
setup state, disables Quick POST, enables floppy seek, selects a 1.44 MB
second drive and orders floppy before IDE during installation. The DOS
Setup system check requires Enter. GUI license acceptance is a separate
step. The original Setup-rejected key was correctly populated from the
answer file. Fresh installer qualification still requires an independently
supplied valid key and a complete GUI run.

For the maintenance series, keep separate inventories by product,
architecture, locale, prerequisite, package digest and install result.
The restored Windows Update v4 catalog is a discovery source. Compatibility
with its service is distinct from the provenance of each package.
Microsoft ended support for Windows 98 SE on July 11, 2006. The
February 2004 security disc has a separately documented payload in
Microsoft KB 836570. Treat the February 2004 disc and end-of-support
coverage as separate targets. Keep media and package installers private
and test installation with guest networking disabled.

- [Windows Update Restored v4](https://windowsupdaterestored.com/en/windows-update-v4.htm)
- [Microsoft KB 836570 archive](https://www.betaarchive.com/wiki/index.php/Microsoft_KB_Archive/836570)
- [Microsoft lifecycle announcement](https://www.microsoft.com/en-us/msrc/blog/2006/06/windows-98-98se-and-me-information-about-support-lifecycle-and-ms06-015)

## Compressed round trip

A second representation of the sealed stock checkpoint completed
explicit 7z testing, extraction and SHA-256 comparison for all 18
inventory files. The resulting archive is 206,548,904 bytes with SHA-256
`884ec9d6cf295402891d05b188aa5de4c6f591e34e51216fe7782b9363384845`.
The preserved baseline remains authoritative. The original incomplete
184 MiB artifact was retained for provenance.

## DM_Music compatibility

The unmodified stock software environment reached the converter's loader
error because `MSVBVM60.DLL` was absent. The archived Microsoft Visual Basic
6.0 SP6 runtime wrapper matched the Download Center snapshot's SHA-1.
The current Windows host validated its Microsoft Authenticode signature.
The wrapper SHA-256 is
`467b5a10c369865f2021d379fc0933cb382146b702bbca4bcb703fc86f4322bb`.
After offline wrapper extraction, redistributable installation and
guest restart, `DM_Music` opened. The pinned application SHA-256 is
`b84f1a9a9dab3252c6c85127a7c9d25f68c0cde53a572ede80a4674230a02150`.

The third-party converter produced an HDS file from the published
synthetic major-scale SNG, at octave offset +0. Independent SNG
projection yields a quarter-note tempo of 100, instrument slot 9, a
15-note scale with MIDI pitches 60 through 72, a final half-note tonic
and a quarter rest. The recovered 383-byte HDS preserves the note and
duration sequence, slot and mp-to-mf dynamic labels. It writes the
low C as `C3` and the upper tonic literally as `C+2`. A standalone HDS
player check would be needed to assign an exact absolute MIDI mapping to
those labels. The exact CRLF export is a Git-only synthetic fixture,
with provenance in the fixture manifest.

Five decoded framebuffer observations from the held converter used
intervals of 0, 237, 431, 659 and 929 ms. They had zero changed pixels
between observations after excluding a documented pointer rectangle.
Pixel comparisons are advisory. The boot and installation
experiments used state and affirmative UI observations to decide when
to move.

- [Archived Microsoft VB6 SP6 runtime metadata](https://legacyupdate.net/download-center/download/24417/service-pack-6-for-visual-basic-6.0-run-time-redistribution-pack-vbrun60sp6.exe)

The three-file DM_Music directory conversion also generated byte-exact
duration/tempo, accidental and alternate-ending controls. The tempo file
has a default `Pace=100` header and an explicit quarter-note tempo of
140, which agrees with independent SNG decoding. The accidental file
spells the measured F, F sharp, F, E sequence. The repeat file retains
the repeat count, first ending, second ending and repeat terminator
in the order projected by the parser. That repeat input is tool-generated.
The observation qualifies its interpretation by DM_Music 1.04.
The three outputs are individually hash-pinned in the fixture manifest.

## Native Award BIOS controls and provisioning handoff

On a second independent stock restore, the authenticated automation
client found the Award main menu at 2,040 emulated ms. Standard CMOS
Setup used attribute 0x4f on its highlighted label. The neighboring
unselected BIOS Features and Chipset Features labels used 0x1e.
Entering the displayed selection confirmed two 1.44 MB floppy drives.
The BIOS Features page showed Quick Power On Self Test disabled, boot
sequence A,C and Boot Up Floppy Seek enabled. The guest exited Setup
through the affirmative Quit Without Saving prompt.

Use `tools/86box_award_setup.py` with a named, held machine at the
beginning of POST. Its optional highlighted action checks the label
and raw CP437/VGA attribute cells before sending Enter, then requires
the named submenu. The receipt records observed bytes and emulated
time. The native framebuffer tool separately supports nonuniform
sampling, optional rectangular exclusion and decoded-pixel differences.

The lab keeps an independently named revision of its Windows 98
provisioner. It uses reusable paced typing, held-state verification and
a self-removing STOP marker for Setup advancement. It adds an explicit
resume mode gated on the named DOS routine check, the expected
provisioning phase and the working disk identity. The original and the
revised tool passed their host-only self-tests. The revised script's
SHA-256 is
`249ef757249f98eb35b3259457977e07eb2a6bb7ffd8367726cb78a6fb067238`.
Fresh end-to-end retail Setup remains pending a valid key for that
installation. Automatic Setup captures are disabled in the revised
script to keep the answer state private.

## Driver and audio controls

The stock Windows driver class export ties the displayed S3 ViRGE
adapter to `DXS3.INF` section S3V and the Intel IDE controller to
`MSHDC.INF` section DUAL_GOOD_IDE. The recognized Sound Blaster
function is `SB16AWE.INF` section CTL0031_Device, with mmdevldr.vxd
and sb16snd.drv for wave output. These inbox entries report April
23, 1999. Stock IDE boot and file transfer worked. The separate 2004
test clone retained 800×600 at 16-bit color during the update.

The 06 runtime clone reproduced a synthetic 440 Hz WAV through
Windows Media Player. In its native 48 kHz main stream the strongest
250 ms window measured 440 positive-going crossings per second and
−33.19 dBFS RMS. The independently restored stock-driver trial
showed an unavailable audio device at cold boot and after a Windows
restart with the same control. Its captured sound did not establish
successful playback. The differential warrants a separate
driver-qualified classification only after a reproducible positive
result. The 06 runtime clone shut down normally at or before the
278,984 ms observation and was copied to a verified four-file private
checkpoint.

Creative lists the period SDR-95UPD-1-US release 16 for Windows 95/98.
The archived package digest is
`9c78b6ddb5de1647927af105b046c7cef9899c137a4282e877341006c273fa6e`.
The vendor's update utility was run on the driver trial clone after
the documented whole-package staging step. Its result requires
post-restart comparison. The disabled logical-device functions of the
non-IDE SB16 profile remain distinct from the wave playback result.

- [Creative release 16 package registration](https://support.creative.com/downloads/download.aspx?nDownloadId=417)

## February 2004 official-media trial

The private archived ZIP is 469,938,862 bytes and its validated
`Security9_enu_15.iso` member is 476,715,008 bytes. The ISO SHA-256 is
`83ce5d3244ee3e3dbb723391bbced6f5edbd5918b77a8950c954880b8e10020f`.
The modern host validated the Microsoft signatures of both
`Autorun.exe` and `W9XSetup.exe`. The 98 SE finish INF sets the
subversion letter to B. This metadata identifies the intended path.
A B suffix alone cannot establish the installed component inventory.

A second independent restored stock clone entered the Security Update
CD wizard with all configured network links down. The 640×480 prompt
required raising the display to 800×600. The IE6 component install
reached its automatic restart prompt at 421,844 emulated ms. The
first post-reboot Windows Setup frame showed Updating System Settings
at 473,844 ms. Further verification is required to qualify the 04
checkpoint. There is no separate early maintenance, IE6-only or
end-of-support environment in this checkpoint.

- [Archived February 2004 disc catalog entry](https://www.vogonsdrivers.com/getfile.php?fileid=873&menustate=50,0)
