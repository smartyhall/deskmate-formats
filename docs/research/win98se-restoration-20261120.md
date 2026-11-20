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
