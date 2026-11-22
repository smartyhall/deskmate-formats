# Automatic House, Plug 'n Power, and the CP290: research lead

**Status (2026-11-21):** Historically supported hardware/software identification and protocol lead; **no native Automatic House session or serial trace has yet been reproduced**. This is a deferred research handoff, not an interoperability claim.

## Why this lead matters

The operator remembers seeing the **Information Center** and **Automatic House** icons on retail Tandy demonstration machines, with a particular sense of excitement about home automation. The display may have run an automated demonstration; the operator does not claim to remember an interactive session or a particular machine model. This is **recollection, not historical proof**. The Evolution Atlas independently captured an **Automatic House** desktop shortcut in the RSX OEM DeskMate 03.04.04 floppy startup. Whether that icon launches a complete installed application, a stub, or a demonstration remains untested. [Native RSX trial](deskmate-evolution-native-20261121.md#tandy-1000-rsx-oem-030404) · [Evolution Atlas](../ecosystem/deskmate-evolution-atlas.md#machine-specific-deskmate-3)

## Period software and hardware identification

- Radio Shack's [1992 catalog](https://www.worldradiohistory.com/Archive-Catalogs/Radio-Shack/Radio-Shack-1992.pdf) advertises a **Plug 'n Power Computer Interface** supplied with **DeskMate Automatic House software**, catalog **61-2617**, requiring DeskMate 3.x. Its description specifies a computer serial cable, a 9 V backup battery, 128 scheduled events, control addressing up to 256 modules, and the ability to disconnect the PC after programming. This is period advertising, not a verified measurement of the RSX OEM package.
- The [1993 catalog](https://www.worldradiohistory.com/Archive-Catalogs/Radio-Shack/Radio-Shack-1993.pdf) advertises the same catalog number and DeskMate-based floor-plan scheduling. The [1995 catalog](https://www.worldradiohistory.com/Archive-Catalogs/Radio-Shack/Radio-Shack-1995.pdf) lists **61-2617** with a **Windows-compatible** Automatic House package. **Do not assume those software revisions are byte-identical**, or that the OEM DeskMate shortcut contains the retail package.
- Jill Champion's contemporary [April 1992 *COMPUTE!* review](https://www.atarimagazines.com/compute/issue139/36_The_Radio_Shack_hous.php) identifies the software as **Automatic House Companion** and describes its three functions: **Floor Plan**, **Routine Maker**, and **Schedule Manager**, including a security option varying scheduled times. It says DeskMate 3.0 or later was required and the PC could be disconnected after programming.
- A period [April 1995 comp.home.automation X10 FAQ](https://groups.google.com/g/comp.home.automation/c/8lj9WL27e9E) explicitly cross-references **X10 CP290** with **Radio Shack 61-2617**, and describes the CP290 computer, Macintosh, Apple II, and Commodore 64/128 software/cable packages. This strongly supports the same controller **family/model identification**; it does **not** establish that all cable assemblies, software versions, ROMs, circuit boards, and branded packages are identical.
- X10 engineer Dave Rye's [1999 retrospective interview](https://hometoys.com/dave-rye-x10/) explains a progression from a planned **Mattel Aquarius** interface, through the **Radio Shack Color Computer** interface, to the **CP290**. See also [Matthew Reed's hardware history](https://www.trs-80.org/plug-n-power.html). Distinguish the earlier TRS-80 cassette-port controller **26-1182** (Model I/III/CoCo, host-controlled), the later CoCo serial-controller **26-3142** (standalone scheduling), and the CP290/61-2617. **Shared design lineage is not proof of interchangeable hardware or protocols.**

## Candidate serial protocol, not yet traced from DeskMate

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

**Critical unknown:** The actual Automatic House release being recovered may use CP290 commands, a driver layer, or a different I/O interface. Confirm via the running application or qualified binary analysis rather than treating CP290 compatibility as already measured.

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
The search covered ZIP filenames and loose text, so other packaging
or unidentified media might still contain the retail software.
[RSX file identities](deskmate-rsx-oem-recovery-20261122.md#application-media-inventory)

## Deferred native research: bounded experimental sequence

1. **Identify the program.** From the pristine RSX OEM 03.04.04 Desktop, select Automatic House. Record the precise display state, required disk, executable/module filename, version/copyright, dialogs, and whether this is a working app or demo. Do the same for **Information Center** as a separate icon/application; do not assume it is part of Automatic House. Take contextual native screenshots with ordinary provenance and privacy review.
2. **Locate independent media.** Search the verified TVDog mirror and historical catalogs for `Automatic House`, `Automatic House Companion`, `61-2617`, `CP290`, and related `HOUSE` modules or bundled software. Record hashes, archive paths, commercial licensing status, and software-specific cables; do not publish commercial program bytes.
3. **Inspect without attached hardware.** Exercise Floor Plan, Routine Maker, Schedule Manager, and any demo or sample modes using synthetic household/device names. Capture document/save formats if available. Observe what the program does without a serial interface attached. Record error handling and whether the app can still work offline.
4. **Trace the UART.** Attach a disposable emulated COM port/null-modem or monitored serial backend if supported by the qualified 86Box configuration. Capture raw bidirectional serial traffic, port settings, write timing, checksum, command/reply framing, and the corresponding on-screen action. Avoid private/real home device identifiers.
5. **Build an offline CP290 mock only if the trace matches.** First test known protocol transactions in an isolated simulator, including acknowledgements, time/date, direct control, schedules, error cases, and resets. Compare with published CP290 documentation and, if available, genuine hardware. Maintain separate compatibility claims for original DeskMate and other host packages (e.g., Commodore).
6. **Optional demonstration:** Only after validating the simulator, explore a strictly opt-in bridge to a real CP290, other X10 interface, or Home Assistant. A simulated lamp/floor plan is the default; do not send commands to physical household devices without explicit authorization and safeguards.

## Evidence and stopping criteria

A native run, screenshots, and serial capture are needed before declaring **DeskMate ↔ CP290 wire compatibility**. Keep hardware-model family, historical retail SKU, application software, serial protocol, power-line protocol, and modern bridge implementation as **separate** claims. Preserve captures and commercial material in the private lab; publish only eligible documentary images, synthetic files, and research notes via a reviewed PR.

**Next handoff:** Resume the RSX OEM installation held at Disk 3 ([Atlas continuation](../ecosystem/deskmate-evolution-atlas.md#continuation)), then examine the icon's launch behavior before attempting protocol emulation.
