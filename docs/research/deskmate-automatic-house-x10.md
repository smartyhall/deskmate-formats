# Automatic House, Plug 'n Power, and the CP290

**Status (2026-11-22).** Automatic House 01.08 and its three feature programs
launched from the reconstructed RSX hard-disk installation. Radio Shack's
own cross-reference identifies 61-2617 as the CP290. The OEM software
sent CP290 commands at 600 baud, and Scheduler exchanged a synthetic
lamp event with an offline virtual controller.
[RSX installation and control](deskmate-rsx-oem-recovery-20261122.md)

## Why this lead matters

The operator remembers seeing **Information Center** and **Automatic House**
on retail Tandy demonstration machines. The display may have been automated,
and the machine model is uncertain. The Evolution Atlas independently
captured the shortcut on the RSX 03.04.04 floppy desktop. The later
hard-disk run opens the three-part Automatic House navigator from that
shortcut. [Native floppy trial](deskmate-evolution-native-20261121.md#tandy-1000-rsx-oem-030404) · [Evolution Atlas](../ecosystem/deskmate-evolution-atlas.md#machine-specific-deskmate-3)

## Automatic House on the RSX

From Teach Me on the installed desktop, four Right presses and Enter
opened the Automatic House navigator. Three illustrated controls select
Floor Plan, Routine Maker, or Scheduler. The File → About dialog reports
`HOMEAUTO.PDM` version **01.08**, `DESK.EXE` resource version **69.5**,
`DMCSR.RES` **3.125**, `DMDB.RES` **5.0**, and `DMDBRD.RES` **2.11**.
The DeskMate launcher independently reports **03.04.04**.
[OEM media and module identities](deskmate-rsx-oem-recovery-20261122.md#application-media-inventory) · [Native image provenance](../evidence/deskmate-rsx-oem-20261122.json)

## Floor Plan, Routine Maker, and Scheduler

The selected Floor Plan opens a supplied first-floor layout with a yard,
kitchen, bedrooms, and living space. The Room menu offers Add, Remove,
Rename, View room, and Move to top. Escape returns to the navigator.
From Floor Plan on the navigator, Right and Enter open Routine Maker.
It shows a Routines list, a name, a description, and a device/action
table. The Routine menu offers New and Run. Copy, Delete, and Print
were unavailable in the empty state.

Clicking Scheduler from the Routine Maker footer opens
**Scheduler — NORMAL** with File, Event, and Options. On this first
run, **No X-10 Devices** asked the user to enter schedule-capable
devices in Floor Plan. Acknowledging the message opened Floor Plan.
This establishes an application dependency that the desktop tiles
alone could not show. [Native image provenance](../evidence/deskmate-rsx-oem-20261122.json)

## Building a room and a schedule

From Floor Plan, Ctrl+A opened Add Room. Entering `ATLAS LAB` created
a room with resize handles on the first-floor sample. Room → View room
opened a detailed room view with a floor-plan thumbnail. Device → Light
offered ten illustrated lamp types. The default table lamp used a Lamp
Dimmer module at C1. Device → Appliance offered a fan and several
other appliance types. The selected fan used a 2-Prong Appliance Module
at C2. OK added each device to the room.

After adding the devices, the Scheduler footer button opened the device
list and events view. Select the lamp and choose Event → Add. Event Day
offers Everyday, Weekdays, Weekends, and Specific days. Event Time
offers a wall-clock time, sunrise, sunset, and an optional security mode.
Event Action offers on, off, and dim for the lamp. The experiment
selected Everyday, 6:06 am, and On, with security mode clear. The
application also offered to add a corresponding Off event. Declining
left the single On event in the NORMAL schedule.
[Room and Scheduler evidence](../evidence/deskmate-rsx-oem-20261122.json)

## Period software and hardware identification

- Radio Shack's [1992 catalog](https://www.worldradiohistory.com/Archive-Catalogs/Radio-Shack/Radio-Shack-1992.pdf) advertises a **Plug 'n Power Computer Interface** supplied with **DeskMate Automatic House software**, catalog **61-2617**, requiring DeskMate 3.x. Its description specifies a computer serial cable, a 9 V backup battery, 128 scheduled events, control addressing up to 256 modules, and the ability to disconnect the PC after programming. This is period advertising, not a verified measurement of the RSX OEM package.
- The [1993 catalog](https://www.worldradiohistory.com/Archive-Catalogs/Radio-Shack/Radio-Shack-1993.pdf) advertises the same catalog number and DeskMate-based floor-plan scheduling. The [1995 catalog](https://www.worldradiohistory.com/Archive-Catalogs/Radio-Shack/Radio-Shack-1995.pdf) lists **61-2617** with a **Windows-compatible** Automatic House package. **Do not assume those software revisions are byte-identical**, or that the OEM DeskMate shortcut contains the retail package.
- Jill Champion's contemporary [April 1992 *COMPUTE!* review](https://www.atarimagazines.com/compute/issue139/36_The_Radio_Shack_hous.php) identifies the software as **Automatic House Companion** and describes its three functions: **Floor Plan**, **Routine Maker**, and **Schedule Manager**, including a security option varying scheduled times. It says DeskMate 3.0 or later was required and the PC could be disconnected after programming.
- A period [April 1995 comp.home.automation X10 FAQ](https://groups.google.com/g/comp.home.automation/c/8lj9WL27e9E) explicitly cross-references **X10 CP290** with **Radio Shack 61-2617**, and describes the CP290 computer, Macintosh, Apple II, and Commodore 64/128 software/cable packages. This strongly supports the same controller **family/model identification**; it does **not** establish that all cable assemblies, software versions, ROMs, circuit boards, and branded packages are identical.
- X10 engineer Dave Rye's [1999 retrospective interview](https://hometoys.com/dave-rye-x10/) explains a progression from a planned **Mattel Aquarius** interface, through the **Radio Shack Color Computer** interface, to the **CP290**. See also [Matthew Reed's hardware history](https://www.trs-80.org/plug-n-power.html). Distinguish the earlier TRS-80 cassette-port controller **26-1182** (Model I/III/CoCo, host-controlled), the later CoCo serial-controller **26-3142** (standalone scheduling), and the CP290/61-2617. **Shared design lineage is not proof of interchangeable hardware or protocols.**

## CP290 protocol documentation

Radio Shack's own cross-reference lists **CP290** alongside **61-2617**.
Its separate feature sheet lists the bundled Automatic House software and
describes programming a timer that continues to operate when disconnected.
The TVDog mirror copies used here hash to
`6273cb434bc165cb9a390f8994bb429668689669562fbe3525ad223ddb82e0be`
and `21f35e97eceebf0dd44fafe9858433c80219e66c8e3447d27172d221873f0632`,
respectively. These manufacturer records identify the controller sold
under that catalog number. [Radio Shack Faxback 8892](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/08892.txt) · [Radio Shack Faxback 8905](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/08905.txt)

The [X10 FAQ's CP290 programming section](https://groups.google.com/g/comp.home.automation/c/8lj9WL27e9E) cites the *CP290 Home Control Interface Programming Guide for Advanced Programmers* and records:

- Simplified RS-232, **600 baud, 8 data bits, no parity, one stop bit (8N1)**; a suggested 1 ms inter-byte delay.
- **Five-pin DIN** on the CP290; reported pins 2 = host-to-controller data, 3 = signal ground, 4 = controller-to-host data, 1/5 unused (verify orientation before physical wiring).
- Eight host command codes (0–7), framed by 16 bytes of `FF` synchronization, followed by command bytes and checksum where required. Responses use six `FF` sync bytes, status, optional data, and a checksum. **Implement the complete command-specific rules from the original guide before claiming compatibility.**
- Distinguish CP290 serial commands, CP290 local scheduling, and X10 power-line signaling. The last stage must not be inferred from host-side serial bytes alone.

## Observed CP290 serial exchange

The trial connected emulated COM1 and COM2 to the 86Box automation
backend on a disposable RSX clone. Floor Plan → File → Set up interface
box offered COM1–COM4, IRQ2–IRQ5, and a base house code. The defaults were
COM2, IRQ3, and house C, with COM1 marked as a modem. The app left setup
at 2,400 baud until **Test Interface → Yes**. The emulated UART then
reported **600 baud, 8 data bits, no parity, and one stop bit**. Each
port had previously emitted one `00` at 582 ms during boot. The
subsequent command frames appeared only on COM2.
[86Box UART capture](../evidence/deskmate-rsx-oem-20261122.json)

Each measured command below begins with sixteen `FF` bytes, followed
by the listed hex bytes. The interpretations follow the documented
CP290 command formats. [Period CP290 protocol reference](https://groups.google.com/g/comp.home.automation/c/KpeaxXhXZKM)

| Guest action | Frame body | Observed result |
| --- | --- | --- |
| Test Interface for house C | `00 20` | The app waited over nine emulated seconds without a reply. Six `FF` bytes and status `01` returned it to Floor Plan. |
| Table lamp properties → Turn On | `01 02 20 00 80 A2` | Direct On for C1. The checksum is the sum of `02 20 00 80`. After a status packet and completion packet from the virtual endpoint, the app returned to the device dialog. |
| Scheduler → File → Transfer | `04`, then `05` | The app read the virtual clock and base house code, then requested the timer inventory. |
| Transfer with empty timer inventory | `03 00 00 08 7F 06 06 80 00 20 02 35` | The app wrote the recurring C1 On event at 6:06 am to the first slot. The checksum `35` is the low byte of the sum from `08` through `02`. |
| Transfer with the same timer stored | `04`, then `05` | The app reported **No Events Transferred** and said the interface already had the correct schedule. It sent no further timer write in the observed transfer. |

The [offline CP290 model](../../tools/experimental/cp290_replay.py)
replays set-house and direct on/off frames, maintains simulated unit
state, and implements the fixed clock and single timer slot used in
the live Scheduler test. The first run presented an empty timer
inventory. After accepting the write, the model returned the stored
event on the second Transfer. The model's CLI takes complete host
frames as hex arguments and emits decoded operations and generated
replies. The live test used the same Python class and passed its
replies exclusively through the authenticated emulated COM2 endpoint.
The documented direct completion packet was injected through the
same endpoint during the earlier manual trial. Physical signaling,
additional slots, scheduled time progression, and dimming remain
untested. [Exact bytes and time boundaries](../evidence/deskmate-rsx-oem-20261122.json)

## OEM file comparison

The private TVDog mirror search examined 895 ZIP member listings and
6,479 loose text and index files. It identified shared Automatic House
components in the [verified 1000 RLX-HD B file set](../ecosystem/deskmate-evolution-releases.json)
(`1000RLX_HD-B.zip`, SHA-256
`c19e395880113fed55ad50e8a8d1e05b6cdf87ca883f700b0d28dd062882463f`).
The RLX and RSX versions of `HOMEAUTO.PDM`, `FLORPLAN.PDM`,
`ROUTINE.PDM`, `SCHEDULE.PDM`, and the three feature Help files
match byte for byte. `HOMEAUTO.DB`, `HOMEAUTO.TUT`, and
`HOMGREET.PDM` differ. This comparison explains why matching
application modules can coexist with different greetings and sample data.
Tandy's RLX/B feature sheet identifies Automatic House as an included
X10 interface. The sheet describes the bundle as DeskMate 3.5 in one
paragraph and reports 3.04.03 for the distributions in another. The
two labels are preserved as written. The local Faxback copy hashes to
`9d1a309089bcd7a32bda72d172b65e141cd778b41f77de40611d10cca09e2156`.
[Tandy Faxback 1342](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01342.txt)

The search covered ZIP filenames and loose text, so other packaging
or unidentified media might still contain the retail software.
[RSX file identities](deskmate-rsx-oem-recovery-20261122.md#application-media-inventory)

## Next experiments

Define a second timer and observe its actual address before expanding the
one-slot model. Check the failure path with a bounded no-reply wait
and distinguish timeouts from a bad checksum or status. Compare the
OEM tutorial and greeting with a verified retail copy when one is
available. The RSX experiment establishes the application workflow and
host-side protocol for the measured commands. Hardware signaling and
retail equivalence remain separate questions.
