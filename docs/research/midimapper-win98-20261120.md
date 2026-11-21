# MidiMapper 6.38 on Windows 98 SE

## Acquisition

The operator-provided private accession has the original filename
`MidiMapper.zip`, size 440,568 bytes and SHA-256
`323a06e1ae757de09ac25721d94a29ac7bbb1d4038d91cd74cdcdaee2dad798b`.
The modern Windows host downloaded and verified those bytes before
extraction. The original archive, acquisition receipt and extracted
members are retained under the private lab's
`downloads/intake/midimapper-20261120` directory.

The ZIP contains the VB6 setup bootstrap, setup list, PAD XML and a
376,253-byte cabinet. 7-Zip 26.05 extracted 46 cabinet members. They
include the setup engine and uninstaller, VB6 setup toolkit DLL, the
MidiMapper executable, `midifl32.ocx`, the HTML manual, three GIFs,
two BMPs, the `Guitar.frt` and `15-14B.dlc` instrument-definition
files, and 33 HDS files including a guitar tuning control. The full
per-member names, byte counts and SHA-256 values are retained privately
in `private-evidence/midimapper-20261120/distribution-inventory.json`.

The application PE version resource reports 6.38. The setup list
still declares version 6.25.0.0 for that file. The PAD lists 6.12. The MIDI control's
resource reports 1.10.005 and the setup list specifies self-registration
under the Windows system directory. The manual describes the Visual
Basic runtime (SP5 at the time of writing) and the File menu's HDS
to MIDI export.

The source score and the DM_Music control export are documented in
the [DM_Music research notes](dm-music-hds-20261120.md). The
[Windows 98 restoration](win98se-restoration-20261120.md) documents
the offline VB6 SP6 checkpoint.
