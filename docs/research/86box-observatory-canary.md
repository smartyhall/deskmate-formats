# Held RSX/DOS 5.00 canary through MCP and the observatory

This procedure extends the [original canary experiment](86box-guest-canary.md).
The native checkpoint was verified in that earlier experiment. Issue #39
adds the MCP and browser comparison, which still requires a live run.

## Before live authorization

1. Use the pristine sealed RSX/DOS 5.00 baseline from the original experiment.
   Verify the manifest, disk, config and NVRAM against the published hashes
   and file sizes. Verify the same clean 86Box and ROM revisions and the
   executable hash. Record these with the integration revision, Python, MCP
   SDK and Pillow versions in a new private evidence directory.
2. Copy only the three manifest-listed files into a new private machine
   directory. Keep their relative paths, make the copies writable and hash
   them. Save independent backups of the clone's config and NVRAM. Leave the
   sealed directory and manifest intact. Generate the canary floppy separately
   and check its hash against the original experiment.

   ```powershell
   python tools/experimental/guest_canary.py "$machine/media"
   python -m pip install ".[mcp,observer]"
   ```

3. Use a test configuration with a fictional target and no token file to
   verify the stdio launcher in a fresh Codex session. Use the
   [Codex registration instructions](86box-readonly-mcp.md#install-and-configure)
   or pass the equivalent `mcp_servers.<name>.command` and `.args`
   overrides for that invocation. Discover the seven tools and call
   `list_instances`. It should report `not_connected`. The SDK subprocess
   test also verifies real initialization and discovery with an authenticated
   synthetic peer and its own loopback browser listener.

## Live authorization and checkpoint

Obtain operator authorization to launch the identified clone, advance it over
the native socket, mount the generated data floppy, and type the canary command.
Agree whether to quit the clone after the comparison or leave it held. Review
and explicitly approve the exact transcript and PNG separately before adding
their hashes to the browser configuration.

1. In the interactive Windows session, run the normal visible launcher with
   native port 8765 and seed 1. Confirm that the private launch receipt says
   ready, held and unpaused at 0 ms. Record the PID, process start time, session
   ID, native machine/version and reset counters. Keep the emulator display and
   host input untouched.

   ```powershell
   python tools/86box_launch.py --machine $machine --mode visible --port 8765 --seed 1
   ```

2. Use one authenticated setup client with a private journal. The following
   excerpt uses the existing experiment helpers. Set `$env:CANARY_MACHINE`
   to the clone and `$env:CANARY_EVIDENCE` to the new evidence directory
   before running it from the repository root.

   ```powershell
   @'
   import os
   from pathlib import Path
   import sys

   sys.path.insert(0, str(Path("tools/experimental").resolve()))
   from run_guest_canary import Client, advance, capture, save

   machine = Path(os.environ["CANARY_MACHINE"])
   evidence = Path(os.environ["CANARY_EVIDENCE"])
   with Client(machine / "automation.token", port=8765,
               journal=evidence / "native-setup.jsonl") as client:
       start = client.status()
       assert (start["ms"], start["held"], start["paused"]) == (0, True, False)
       advance(client, 12000)
       boot = capture(client, evidence, "boot")
       assert "C:\\>" in "\n".join(boot["text"]["lines"])
       client.floppy(0, machine / "media" / "canary-data.img")
       client.type_ascii("a:\\canary\n")
       advance(client, 3000)
       checkpoint = capture(client, evidence, "checkpoint", checkpoint=True)
       save(evidence / "native-checkpoint-summary.json", checkpoint)
   '@ | python -
   ```

   The helper validates the self-loop, eight registers, segments, 98 code
   bytes, 32 data bytes and source-defined screen pattern. The earlier run
   measured 15,044 emulated ms, including 44 ms of scheduled key delivery.
   Record the new run's actual status. Stop on an unexpected result and
   preserve the evidence before any further action.
3. Review `checkpoint.json` and `checkpoint.png` privately. Use the exact
   status/reset counters, launch token fingerprint and the approved display
   hashes in the [private config](86box-readonly-mcp.md#enable-browser-publication).
   For the RAM checkpoint, approve two regions named `canary-code` and
   `canary-data`, with starts from the validated `locations.code` and
   `locations.data` and lengths 98 and 32. Set the instance ID to `rsx-lab`
   and browser port to 8086. Keep the guest held and maintain exclusive
   custody after the setup client closes.

## Compare one MCP observation with the published views

1. Record socket attempts from the actual Python MCP owner. Save this wrapper
   as `audit-owner.py` in the new private evidence directory and use it as
   the stdio launcher's script in place of
   `-m deskmate_formats.automation.mcp_server`. Pass the same `--config`.

   ```python
   import os
   from pathlib import Path
   import sys
   from time import time_ns

   from deskmate_formats.automation.mcp_server import main

   with Path(__file__).with_name("native-connects.txt").open("x", encoding="ascii") as log:
       def record(event, args):
           if event == "socket.connect" and args[1] == ("127.0.0.1", 8765):
               print(time_ns(), os.getpid(), file=log, flush=True)

       sys.addaudithook(record)
       main()
   ```

   Expect exactly one attempt after the first MCP status call as a positive
   control. This counts attempts by the Python owner, including its HTTP
   workers. For independent host-wide evidence an elevated operator can
   start an IPv4 TCP metadata trace with
   `logman start DeskMateIssue39Live -p Microsoft-Windows-Kernel-Network 0x10 4 -o "$evidence/native-tcp.etl" -ets`.
   If used, check that the trace records the initial connection. Match the
   loopback addresses and native port in IPv4 connect, accept, reconnect and
   disconnect events (IDs 12, 15, 16 and 13), accounting for network byte
   order in port fields. Keep the trace private.
2. Use one MCP stdio subprocess for the entire comparison, with the approved
   config. The [SDK test](../../tests/portable/test_mcp_stdio.py) shows the
   `StdioServerParameters` / `stdio_client` / `ClientSession` sequence.
   Initialize and list tools, then call `get_instance_status` with
   `{"instance_id":"rsx-lab"}`. Save the reply privately. Check the held
   state, reset identity, clock, `memory_mapping_valid` and initial
   `connection_generation`. Read `get_cpu_registers` and verify the
   checkpoint with `guest_canary.locations()`. Use either Codex or the SDK
   as the MCP client for the live comparison so one stdio owner is active.
3. Call `observe_machine` once. Set `include_text` and
   `include_framebuffer` to true. Set `expected_session` and
   `expected_generation` from status and `memory` to the following array.

   ```json
   [
     {"region_id":"canary-code","offset":0,"length":98},
     {"region_id":"canary-data","offset":0,"length":32}
   ]
   ```

   Save the structured result and base64-decoded image privately. Confirm
   that the code/data hex, registers and display match the setup checkpoint.
   Compare the PNG SHA-256 to the exact approval digest. The embedded
   listener publishes the approved projection of this call.
4. With the MCP session still open and no other observation in progress,
   retrieve `/i/rsx-lab/api/status`. Check the instance, generation,
   `observed_at_ms`, held flags and emulated clock against the same MCP
   result. Compare the full `screen` to the canonical CP437 transcript.
   Assert the absence of registers, RAM, native replies, paths and token
   material. Check the capture timestamp against the MCP image metadata.
   Expect `latest_rendered` true, both render times null and `age_basis`
   equal to `capture`.
5. Use the returned frame key to GET `/i/rsx-lab/frame.png?frame=<key>`
   and `/i/rsx-lab/frame.gif?frame=<key>`. Decode them locally. Compare
   PNG dimensions and RGB pixels with the approved native PNG composited
   onto black. Compare the single GIF still with the approved PNG resized
   by nearest neighbor within 640 × 480 and quantized to at most 64 colors
   without dithering. Use `observer.presentation.ascii_display()` to
   compare the transcript in `/i/rsx-lab/status.txt`; check that
   `/i/rsx-lab/legacy/` references the same GIF key.
6. Record a refresh interval with no MCP calls. Retrieve those five routes
   repeatedly and load or refresh the modern and classic browser pages.
   Save the first and last browser observation sequence, generation, frame
   key and guest clock. All four must be unchanged. The view can become
   stale after ten seconds and the frame age can grow. Finish with another
   `get_instance_status`. Verify unchanged guest ms (delta **0 ms**),
   frames, held state, reset identity, server session and connection
   generation. Expect **zero** new entries in the owner's socket-attempt
   log and the same established native endpoint before and after. If the
   optional trace was used, stop it with
   `logman stop DeskMateIssue39Live -ets` and count native connections during
   the refresh interval. The browser's own TCP connections use port 8086.
7. Close the MCP session and confirm its native socket and listener close.
   If authorized to quit, use a sequential native cleanup client and verify
   the recorded 86Box PID exits. After exit, hash the clone disk, config,
   NVRAM and canary floppy. Rehash the sealed baseline and manifest. Keep
   raw receipts, native replies, images and traces outside Git. Report the
   exact measured guest-time delta, socket count and observation limits in
   a separate sanitized validation record.

Framebuffer evidence describes the latest render at capture. The native
brackets detect sampled changes and cannot resolve an unobserved release and
rehold or give an instruction-precise render timestamp. The browser comparison
does not establish historical browser compatibility.
