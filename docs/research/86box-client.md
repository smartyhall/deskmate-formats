# Native 86Box research client

The independently authored [client](../../tools/86box_client.py) connects to
an explicitly selected machine's default token file over loopback TCP. It uses
only Python's standard library. This is a local research tool, not an MCP server
or a DeskMate semantic interface. Its first live validation is described in the
[RSX DOS baseline report](rsx-dos5-baseline.md).

## Launch and identify

Verify that the designated emulator is stopped and the port is free. Back up
the machine's configuration and NVRAM. Launch the automation-enabled executable
with the UCRT64 runtime on PATH. For example, in PowerShell:

```powershell
$machine = 'C:\DeskMateLab\machines\rsx-dos5-experiment'
$python = (Get-Command python.exe).Source
$env:PATH = 'C:\msys64\ucrt64\bin;' + $env:PATH
Start-Process -FilePath C:\DeskMateLab\builds\86box-automation\src\86Box.exe -ArgumentList "--vmpath $machine --automation tcp:127.0.0.1:8765 --automation-hold --automation-seed 1" -WorkingDirectory $machine -WindowStyle Hidden -PassThru
# Wait for this launch's default token and loopback listener before connecting.
& $python tools/86box_client.py --machine $machine status
& $python tools/86box_client.py --machine $machine info
```

The example path has no spaces. Quote individual launch arguments when using
other paths. Keep a private launch receipt with PID, process command line,
executable/source/ROM/configuration hashes and start time. Check the PID and
endpoint against that receipt; a matching `info` reply alone does not identify
a particular process. The token is per launch and must never be copied into a
command, report, terminal output or Git. Do not supply `--automation-token-file`:
the working launch uses the default file in the selected machine directory.

## Supported operations

Use `python tools/86box_client.py --help` and the subcommand help. The CLI
supports `status`, `info`, `hold`, `registers`, `memory ADDRESS LENGTH`, `text`,
`capture PREFIX`, `step MS`, `tap SCANCODE`, `type TEXT`, `floppy DRIVE [PATH]`,
`reset hard|cad`, and `quit`. All are explicit actions; no resets or media
changes occur as error recovery. Omitting the floppy path ejects that drive.

`--journal` selects a **private external** JSONL destination. Each request has
a connection ID, sequence, wall time, response or uncertain-delivery marker.
Authentication is excluded; PNG base64 is omitted from journals. Guest text,
registers, memory, media paths and typed commands can still contain sensitive
evidence, so journals never belong in public Git. They are not sanitized reports.

`capture` holds the machine and saves JSON plus a native PNG under a new prefix.
Existing evidence is never overwritten. The JSON includes a PNG SHA-256.
The Python `Client.observe(spans, framebuffer=True)` API can add bounded memory
spans; spans must be independently approved ordinary RAM ranges for that machine.
Device-mapped reads can have side effects. Addresses are guest addresses, not
offsets in an executable file. The default memory view is explicitly `normal`,
width one; `bus`, `cpu` and `linear` are also selectable through the Python API.

```python
# Import tools/86box_client.py using importlib, or add tools to sys.path.
from pathlib import Path
from importlib import import_module

box = import_module('86box_client')
machine = Path('C:/DeskMateLab/machines/rsx-dos5-experiment')
with box.Client(machine / 'automation.token') as client:
    client.hold()
    actual = client.step(1000)  # actual_delta_ms must equal 1000
    equipment = client.memory(0x410, 2)
    observation, png = client.observe([(0x413, 2)], framebuffer=True)
```

`step` requires held, unpaused execution and a quantum-aligned duration in
1..1000 ms. It brackets status and rejects an actual delta different from the
requested duration. Longer installation waits use repeated explicit steps.
Keyboard events consume emulated time too. Set-1 codes use `0x100` for E0:
Enter `0x1c`, F1 `0x3b`, F2 `0x3c`, Up `0x148`, Down `0x150`.
The `type_ascii` API validates the entire string before sending US-keyboard
scancodes. It supports ASCII punctuation, newline, tab, backspace and Escape.
It cannot infer menu focus or prove that an application accepted typed input;
check the resulting screen before continuing.

## Integrity and limits

- Authentication is mandatory. Only numeric loopback addresses are accepted.
  Connections have finite timeouts, serialized requests and bounded replies.
- Fragmented/coalesced JSON is framed by newline. Malformed, oversized, fatal,
  truncated and disconnected replies invalidate and close the transport.
  There is no automatic replay, reconnect or release on disconnect. If a
  mutation loses its reply, delivery is uncertain, including key-down state.
- Command rejection is distinct from transport failure. PNG signatures,
  dimensions, chunk CRCs and end markers are checked. Full image decoding is
  left to the viewer; captures are visually inspected as experimental evidence.
- A held observation brackets status and machine/reset metadata around reads.
  Changed time, frame count, mode, dimensions or reset state rejects the group.
  The framebuffer is the latest rendered frame; it may predate the held CPU.
  The group is not an atomic instruction-level snapshot or an execution breakpoint.
- Each connection is a new session. This client does not implement the older
  preflight's proposed lease/epoch MCP security contract. Callers must invalidate
  application address mappings across resets/reconnects and coordinate exclusive
  access. It supplies no application layout decoder, Ghidra mapping or debugger.

Thirteen ROM-free tests exercise real loopback authentication, framing,
rejection, disconnect ambiguity, injection/bounds, CP437, memory completeness,
PNG integrity, observed time and reset consistency:

```powershell
python -m unittest discover -s tests/portable -p test_86box_client.py -v
```

These are transport/policy tests, independent of proprietary guest software.
Live DOS observations validate a different layer; neither establishes DeskMate
UI semantics. Keep installation-specific actions in experiment scripts or
runbooks, separate from this transport implementation.
