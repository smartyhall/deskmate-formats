# DeskMate SDK source and module identities

This is the provenance record for the offline Calendar and DMCSR crosswalk.
The repository baseline was `9c7ac46d64b5255ca7477a6e63a1004fd6b7a85d`.
The comparison used the private Oldskool collection and two already archived
DeskMate installation trees. Guest advancement in this investigation was
**0 ms**. Every runtime observation cited by the crosswalk predates this work.

## Reference collection

Read the handoff, suggested next prompt, run manifest, source acquisition
list, inventory and SHA-256 manifest under the lab's `references/oldskool`.
The SHA-256 manifest is
`2ed1ff33111fb0638da01c8e1fe5d0db968558159a92f5dc0b9c886933bc2d9a`.
The CSV inventory is
`536dd2a0d070c82388c8e008ed2470a796b8dbca62950c3ddff1beae5b8cf39f`.
Rehashing all 32 originals and 474 extracted files matched both lists and
the recorded lengths. The run summary's zero archive extractions describes
the staging run, while 474 extracted files were already present. Reading
all five original SDK ZIP central directories and comparing the 83
non-directory members to the staged files confirmed that subset directly.
The locally pinned SDK originals and the acquired retail archives have
different provenance. Digest agreement identifies bytes.

Paths in this table are relative to `references/oldskool`. Header pairs are
independent C and assembler descriptions of the same public records.

| Input | SHA-256 |
| --- | --- |
| `originals/sdk-3.03/DeskMate-Technical-Reference.pdf` | `c4ce5457339234071ef46ac0ec021b7e2674b77cb869103389193ce2bed1352a` |
| `originals/sdk-3.03/DeskMate-Development-Guide.pdf` | `8081d5cd34305982844ab3598ebfbdf8887e7e369d1174a88a7631cba08439e0` |
| `extracted/sdk-3.03/Development-Disk-1/CSRCMPS.H` | `6d8a02bdb5e8128c011eeffe3cbeb251e0a210068a8b8d87de6e6b24e28733d7` |
| Same disk, `CSRCMPS.INC` | `b5ccd54499bfd0da2ebec84199922587ca53389bf845f939a43d501e57598687` |
| Same disk, `CSRBASE.H` | `2bed5f27da5fbbcf44025b6a62494b0c591d13fdd2fce5b32cb1d6a285ce062a` |
| Same disk, `CSRBASE.INC` | `fce3542874c363cb15e5caf3f334139f2247ee0c470f4b59d6ebe92ab5289360` |
| Same disk, `DMDECL.H` | `c0c3faea0bc947a534fbc181d97a51664935d07554c1ce2c94c0557e01e8473d` |
| Same disk, `DMEXEC.H` | `429061518c39dcf92379f1452cb7e4e81d58bf3e323c23ae05bba32192305b91` |
| Same disk, `DMEXEC.INC` | `d3290c8cf68b0be9eee4370c363cf367e779bf202c0fd67e6704dc735f9cda49` |
| Same disk, `DMDB.H` | `47c2ff4638d8ab1bcc12aeab3e2dd5b51ccfeef9bbddb1a014912c831df4d5aa` |
| Same disk, `DMDB.INC` | `2ea33422d68ab2402ca2b83a1c1f5d7fee80db9c36000a8609d42712ce299a29` |
| `extracted/sdk-3.03/Development-Disk-2/DM.LIB` | `4aba9fff22fc5e519550a227a805f4a58a3bfbcacb3b0c80e313f9d0dbf7ad28` |
| Same disk, `DMMED.LIB` | `1772dca9a10acfb2007f86eb3a03bbf6fcda8b07b1f651ca01787677f5bb8f42` |
| Same disk, `DESK.MAP` | `fdf06903d497ebafcffc0c0a1911f8ffdd0365390f94764d0b06c6c0f7471b00` |
| `extracted/sdk-3.03/Runtime-Disk-3/RUNTIME.MAP` | `f9750c498914c27a6bdb34f6d16e225ac0967324d92529ad4b77ef3668011e13` |

## Runtime comparison

Retail disk names below refer to directories in `extracted/deskmate`.
Every 3.05 row also matched the corresponding file in both the already
extracted E02 closed installation and the final geometry run's archived
installation. The Calendar, DMCSR, DESK and DMDB hashes agree with the
[prior activation](calendar-dialog-activation.md) and
[binding](calendar-binding-25.md) reports. Address Book, Filer and the
3.05 database resource hashes agree with the F00
[inventory](cross-application-evidence.json). Matching disk files establish
which static offsets to compare. Prior anchors and register evidence still
supply the loaded mappings.

| Distribution | File | SHA-256 |
| --- | --- | --- |
| SDK Runtime Disk 1, macros, f2ddos | DMCSR.R89 | `8139d20e151647cae75fdcd3476c497deb87cd1f2f3be38492311147961100f8` |
| dm303dk1 | DMCSR.R89 | `b756c00bf3c9320819a8ae763bb6866cdaf4f2e902e1fd50aa0c17c2e44580a9` |
| dm305dk1 | DMCSR.R89 | `085edb2f2c67ae323343d9efedd7c731778f5fbb8dc59ed8bd6560006b45da75` |
| dm303dk1 | DESK.EXE | `702a5f6237695793a773a327b2b9bedc706cce3d16a52360aa90c4f13f67066a` |
| dm305dk1 | DESK.EXE | `0f2a40243c997276904d2555a117c60eedf0016dde073285e8d63c8345a2eba3` |
| SDK Runtime Disk 1 | RUNTIME.EXE | `56fb39c09d3a5eca7a3a3c8ab06b68cff9a5d8d0d78009a02b6c5ec55aae9ce2` |
| dm303dk1 | CALENDAR.PDM | `53f780566d0966317db0693e6e0932052aa637a1146fe4999aefc25b905ce8ee` |
| dm305dk4 | CALENDAR.PDM | `819df5658b663aa69b15584abf805062679e97f587f3404738f6e82876e4bd23` |
| dm303dk3 | ADDRESS.PDM | `127bf102fdd2371c0a020beb99e1a59f1122d83b8c4e1d47f7dff2ecbd324ff1` |
| dm305dk4 | ADDRESS.PDM | `ef685b20e259f0932378668d9b120882468dc0da157a015e2df95d4ce61a60fb` |
| dm303dk3 | FILER.PDM | `aef8682eb18a829013a0fb7c8e4e42617c784d07e74a77d4f523d277d6e1c425` |
| dm305dk5 | FILER.PDM | `5c62bfcf9676153003753046b223467136659a23ad0883ba56fb312e55b96005` |
| SDK Runtime Disk 1, dm303dk1–4 | DMDB.R89 | `5051e8d298e9a282430fa2bb21897880cc891d1d983847b5d28894d05c33e6a5` |
| dm305dk4/5 | DMDB.R89 | `799444bb8c04632d261f61498ba269f9352e5528718f2e0a89512bf6ef7b808f` |
| SDK Runtime Disk 1, dm303dk1/3 | DBBUILD.RES | `c44ffb66d4b2c7e9cf11caf9c162fb1e794cd2bda410a43a0d4f5a720ef0385a` |
| SDK Runtime Disk 1, dm303dk1–4 | DBREAD.RES | `008727eda24d3d698dd4095be94b5b384a63f477face8a53a353ad9dfa66dc30` |
| SDK Runtime Disk 1, dm303dk1/3 | DBUPDATE.RES | `e9e7e3e3813d21e7b20bacda555a138f759f7a9be2a6a2a7decb33180c9eacaf` |
| dm305dk5 | DMDBBLD.RES | `91ada27c026de823aef6a9aae541bafcb6a312552cc5bd612ec8b0e90e53aeed` |
| dm305dk4/5 | DMDBRD.RES | `c4bc9f5699bfaf1ac5adb57a011b04dcec00a2ae75edb2baf603c8001fa99cee` |
| dm305dk4/5 | DMDBUPD.RES | `9e77a2081ebb3a9549903f5d337580c65d6e0a3f603185064d4c82e16327cf4f` |

Reproduce the identity check with Python 3.13 `hashlib.sha256` over the
unmodified files and `zipfile.ZipFile.read` for the SDK members. Compare
the installation files in the private Calendar archive's
`disk-E02-closed/files/DESKMATE` and
`geometry-research/disk-geo-add-C/files/DESKMATE`.
The offline probe and complete results are in the lab's
`private-evidence/sdk-crosswalk-20261106`.
