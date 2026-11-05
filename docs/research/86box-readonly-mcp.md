# Read-only 86Box MCP server

The server uses the [official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
over stdio and the repository's native authenticated 86Box client over IPv4
loopback. It opens one serialized native connection on the first observation
request per configured instance. Up to eight instances can use separate native
ports and machine directories. Each instance has its own connection lock. The
browser listener is optional and runs in the same process.

## Install and configure

Install in a dedicated Python 3.13+ environment from the repository root.

```powershell
python -m pip install '.[mcp]'
```

Keep the JSON config and machine directory outside the repository and restrict
access to the operator. Use the actual machine and version strings from native
`info`. Set `ram_regions` to `{}` until an operator has verified a RAM mapping.
This example uses placeholder paths and identities.

```json
{
  "instances": {
    "rsx-lab": {
      "machine_directory": "C:/Lab/private/rsx-working-copy",
      "port": 8765,
      "expected_machine": "REPLACE_WITH_NATIVE_MACHINE",
      "expected_version": "REPLACE_WITH_NATIVE_VERSION",
      "ram_regions": {}
    }
  }
}
```

Launch a writable clone separately using the [86Box launcher](86box-observer-design.md)
and use the default `automation.token` for that launch. Close the native setup
client before requesting MCP observations. Start the MCP subprocess with
`deskmate-86box-mcp --config C:/Lab/private/86box-mcp.json` or use the module
form below. A terminal launch waits for MCP messages on stdin.

For a fresh Codex session, add a server to the local configuration using the
[Codex MCP settings](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).
Use the Python executable from the environment where you installed the extra.

```toml
[mcp_servers.86box_readonly]
command = 'C:\Lab\mcp-venv\Scripts\python.exe'
args = ['-m', 'deskmate_formats.automation.mcp_server', '--config', 'C:\Lab\private\86box-mcp.json']
```

The equivalent CLI registration is `codex mcp add 86box_readonly -- <python-executable> -m deskmate_formats.automation.mcp_server --config <private-config>`.

## Enable browser publication

Add `"observer": {"port": 8086}` at the top level of the private JSON config.
The server prints the IPv4 loopback URL on stderr. Port 0 selects an ephemeral
port. Omit the observer field for an MCP-only process. Instance IDs used in
browser URLs must start with a lowercase ASCII letter or digit and contain up
to 32 lowercase ASCII letters, digits and hyphens. Install
`deskmate-formats[mcp,observer]` when approving images.

With the listener enabled, native reads also publish the instance ID,
execution flags and sampled emulated clock. The browser starts with an empty
stream and receives no guest display by default. To approve an exact display,
hold the guest under exclusive operator control and review its full screen
transcript and native PNG privately. In the relevant instance config, add
`display_approval` with these fields:

| Field | Value from the reviewed checkpoint |
| --- | --- |
| `ms`, `frames` | Exact integers from native status |
| `hard_resets`, `soft_resets`, `last_reset_ms` | Exact integers from native info |
| `token_sha256` | SHA-256 of the decoded 32-byte launch token, as for RAM approval |
| `screen_sha256` | Optional SHA-256 of UTF-8 encoded `decode_cp437(line.encode("cp437") for line in native_lines)`. Keep full rows and spaces, with LF separators and no added final LF. |
| `framebuffer_sha256` | Optional SHA-256 of the native PNG bytes, before browser conversion |

Use lowercase hexadecimal digests and supply one or both display hashes. For
RAM and display approval in the same instance, both sections must pin the same
launch credential. Close the setup client before starting MCP. An explicit
MCP text or framebuffer read then supplies the candidate for its corresponding
publication. A held `observe_machine` call can supply both in one bracket.
Unapproved display remains available to the trusted MCP client under the
existing held-read policy. Only loopback browser readers get the approved
projection. Any observed checkpoint change, lost hold, inconsistency,
disconnect or identity failure retires display approval for that process.
Restart with a newly reviewed private configuration to approve again.

## Tools and consistency

| Tool | Arguments and result |
| --- | --- |
| `list_instances` | `{}` returns configured IDs, connection state, last error code and region sizes. It performs no native I/O. |
| `get_instance_status` | `{"instance_id":"rsx-lab"}` returns held/paused state, emulated milliseconds, frame count, dimensions, machine/version and reset metadata. It also works while the guest runs. |
| `get_cpu_registers` | Instance ID returns native registers and held-state metadata. |
| `get_screen_text` | Instance ID returns decoded CP437 text for supported text modes. |
| `get_framebuffer` | Instance ID returns bounded PNG image content and metadata. It is the latest rendered frame. |
| `read_memory` | Instance ID, `region_id`, `offset`, `length`, `expected_session` and `expected_generation` return bytes as hex. |
| `observe_machine` | Instance ID returns a bracketed register and text observation. Set `include_text` false to omit text or `include_framebuffer` true to add the PNG. Optional `memory` entries take `region_id`, `offset` and `length`, plus the approval fields at the top level. |

All tools except listing and status require a guest that is already held and
unpaused. The server sends only native `status`, `info`, `regs`, `text`, `memr`
and `screenshot` after authentication. It never establishes hold, resumes, steps,
resets, injects keys or changes media. Held observations compare samples around
reads. This detects sampled changes and cannot provide an atomic CPU snapshot
or an instruction breakpoint. Free-running status and identity are sampled
separately. `server_session`, `generation` and `connection_generation` describe
local continuity. Session values used for RAM approval are scoped to the
instance. Successful observations include the UTC host `observed_at_ms`;
framebuffer results also include host `captured_at_ms`. The native protocol
has no process UUID or frame render timestamp.

### Approve RAM only for one held checkpoint

1. Under exclusive operator control, verify the process, held and unpaused
   status, and the intended ordinary RAM addresses. The [guest canary report](86box-guest-canary.md)
   shows how to derive addresses from observed registers. Keep the guest held
   throughout setup and use.
2. Set `ram_regions` to a map such as `{"canary-data":{"start":18048,"length":32}}`
   only if the current mapping was verified. `start` is a decimal physical address.
   Add `ram_checkpoint` to the same instance with exact integers `ms` and `frames`
   from native `status`, and `hard_resets`, `soft_resets` and `last_reset_ms` from
   native `info`. Set `token_sha256` to the lowercase SHA-256 of the **decoded
   32 token bytes**. The following command prints only that fingerprint. Keep
   the fingerprint in the private config.

   ```powershell
   python -c "from pathlib import Path; import hashlib,sys; print(hashlib.sha256(bytes.fromhex(Path(sys.argv[1]).read_text(encoding='ascii').strip())).hexdigest())" C:/Lab/private/rsx-working-copy/automation.token
   ```

3. Close the setup client. Call `get_instance_status` through MCP and check
   `memory_mapping_valid`. Copy `server_session` and `generation` to
   `expected_session` and `expected_generation` for each memory request.

Approval is tied to the verified launch credential and native counters. Observed
time or state changes, reset, lost hold, disconnect, and identity mismatch
permanently invalidate RAM approval for that server process. A newer generation
does not grant new access. To authorize a new checkpoint, stop the server,
reverify the process and addresses, update the private config and start a fresh
server. The native protocol cannot detect a release and rehold that changes no
sampled state, or make a read and its checks atomic. Keep other controllers and
host UI actions out of the observation session. If identity or custody is
uncertain, stop and reverify before granting access.

Only named spans in conventional RAM `[0x500, 0xA0000)` can be approved. The
operator is responsible for confirming that those addresses are ordinary RAM on
the configured machine. Regions are limited to 4,096 bytes. One call can read up
to four spans with at most 512 bytes per span and 1,024 bytes total, using the
native normal physical byte view. PNG output is limited to 1 MiB and 2,048 ×
1,536 pixels in total. Native requests have finite timeouts and reply limits.

## Ownership and validation

Use a trusted local MCP client. Status and errors omit token contents, token
fingerprints and private paths. Guest text, pixels and approved RAM can still
contain sensitive guest data. No native journal is written by this server. A
transport failure closes the connection and returns a fixed error code. A later
explicit call can reconnect for observations, with RAM approval invalidated.
Stdio shutdown closes the socket and leaves the emulator alone.

Tests use an authenticated synthetic native peer and the real SDK client over
subprocess stdio. They exercise initialization, discovery, structured results,
image content, native errors, EOF, stderr separation and embedded HTTP
publication. See the [controlled canary procedure](86box-observatory-canary.md)
for Codex registration and the separately authorized live validation.
