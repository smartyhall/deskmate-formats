# Synthetic Codex CLI JSONL

Hand-authored from OpenAI Codex CLI 0.166.0 at
[`6ff1e1ca3b30fc8b914720681fcf5fe62e95f856`](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/exec/src/exec_events.rs).
These are fabricated streams. The commands and tool requests are data and the
test child only writes these bytes. No model or guest produced any fixture.

- `success.jsonl` has an overlapping command and MCP call, completion-only
  file change, plan updates, an agent message and a private reasoning item.
- `failure.jsonl` has a command exit code, a declined command, and explicit
  stream and turn errors.
- `anomalies.jsonl` deliberately violates ordering and syntax. It includes
  an explicit approval-shaped record from outside the pinned exec contract,
  a JSON-RPC request, and a duplicate-key web search shape for rejection.
- `open-turn.jsonl` ends with an outstanding command. The same source bytes
  model quiet, missing-outcome and interrupted runs with different host
  process observations.
