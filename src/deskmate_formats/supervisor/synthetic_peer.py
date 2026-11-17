"""Synthetic app-server child. Its only inputs are stdio and disposable test state."""

import json
import os
from pathlib import Path
import sys
import tomllib
from uuid import uuid4
from time import sleep

from .task_execution import CONTEXT_PREFIX, MAX_RESPONSE_BYTES

POLICY_OVERRIDES = {
    "readonly-implicit": {"sandbox": {"type": "readOnly"}},
    "network-enabled": {"sandbox": {"type": "readOnly", "networkAccess": True}},
    "network-string": {"sandbox": {"type": "readOnly", "networkAccess": "false"}},
    "network-zero": {"sandbox": {"type": "readOnly", "networkAccess": 0}},
    "network-one": {"sandbox": {"type": "readOnly", "networkAccess": 1}},
    "network-null": {"sandbox": {"type": "readOnly", "networkAccess": None}},
    "sandbox-other": {"sandbox": {"type": "dangerFullAccess"}},
    "sandbox-extra": {"sandbox": {"type": "readOnly", "networkAccess": False, "unexpected": False}},
    "unsafe-model": {"model": "different-model"},
    "unsafe-provider": {"modelProvider": "different-provider"},
}

MODES = ("success", "lost-ack", "delayed-ack", "approval", "driver-approval", "unknown-request", "mismatch",
         "duplicate", "eof", "normal", "failed", "stale-turn", "history-only", "unsafe-policy", "wrong-version",
         "unsafe-effort", "unsafe-reviewer", "web-tool", "image-tool", "hook-item", "terminal-tool",
         "history-tool", "history-sentinel", "history-not-loaded", "history-extra-turn", "history-cursor",
         "malformed", "oversized", "partial", "duplicate-terminal", "restart-terminal", "bad-sentinel", "thread-lost-ack",
         "unsafe-cwd", "ephemeral-thread", "nonempty-thread", *POLICY_OVERRIDES)
TASK_MODES = ("empty-answer", "oversize-answer", "history-input", "history-response", "terminal-response", "terminal-empty-items")
EDIT_MODES = ("s3-unauthorized", "s3-test-fail", "s3-audit-fail")
MODES += TASK_MODES + EDIT_MODES
SUCCESS_MODES = {"success", "stale-turn", "history-only", "web-tool", "image-tool", "hook-item",
                 "terminal-tool", "history-tool", "history-sentinel", "history-not-loaded",
                 "history-extra-turn", "history-cursor", "duplicate-terminal", "restart-terminal", "bad-sentinel",
                 "readonly-implicit"}
SUCCESS_MODES.update(TASK_MODES + EDIT_MODES)

PRIVATE = "private-canary-command-and-result"


def task_answer(prompt):
    """Deterministic context processing, not a model or factual-analysis oracle."""
    context = json.loads(prompt.removeprefix(CONTEXT_PREFIX))
    manifest = json.loads(context["manifest_utf8"])
    lines = [f"Synthetic context analysis: {manifest['id']} revision {manifest['revision']}.",
             manifest["title"], manifest["description"]]
    for document in context["documents"]:
        lines.append(f"{document['path']}: {len(document['text'].splitlines())} lines; "
                     f"SHA-256 {document['sha256']}; excerpt: {document['text'][:160]}")
    return "\n".join(lines)


def emit(message):
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def notify(method, params):
    emit({"method": method, "params": params})


def turn_status(turn, status):
    turn["status"] = status
    notify("turn/completed", {"threadId": "test-thread", "turn": turn})


def main(state_path, mode, live_policy=None):
    path = Path(state_path)
    thread = json.loads(path.read_bytes()) if path.exists() else None
    initialized = False
    ready = False
    pending = None
    policy = {}
    methods = []
    if live_policy == "--live-policy":
        # Test adapter only: report the driver's requested live model/provider.
        # There is still no model, credential reader, tool or network client.
        policy = tomllib.loads((Path(os.environ["CODEX_HOME"]) / "config.toml").read_text(encoding="utf-8"))

    def save():
        temp = path.with_suffix(".tmp")
        descriptor = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(thread))
            stream.flush()
            os.fsync(stream.fileno())
        temp.replace(path)

    for line in sys.stdin:
        message = json.loads(line)
        identifier = message.get("id")
        method = message.get("method")
        params = message.get("params", {})
        if live_policy:
            methods.append(method)
            request_path = path.with_suffix(".requests.json")
            descriptor = os.open(request_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(json.dumps(methods))
                stream.flush()
                os.fsync(stream.fileno())
        if method is None:
            assert pending is not None and type(identifier) is type(pending) and identifier == pending
            assert message == {"id": pending, "result": {"decision": "decline"}}
            notify("serverRequest/resolved", {"threadId": thread["id"], "requestId": pending})
            pending = None
            turn_status(thread["turns"][-1], "completed")
            save()
            continue
        if method == "initialized":
            assert initialized and not ready and identifier is None
            ready = True
            continue
        if method == "initialize":
            assert not initialized and params["capabilities"] == {"experimentalApi": False}
            initialized = True
            version = "0.167.0" if mode == "wrong-version" else "0.166.0"
            result = {
                "userAgent": f"deskmate_supervisor/{version} (Synthetic)",
                "codexHome": str(path.parent), "platformFamily": "test", "platformOs": "test",
            }
        else:
            assert ready
            if mode == "malformed":
                sys.stdout.buffer.write(b'{"method":"x","method":"y"}\n')
                sys.stdout.buffer.flush()
                continue
            if mode == "oversized":
                sys.stdout.write(" " * (256 * 1024) + "\n")
                sys.stdout.flush()
                continue
            if mode == "partial":
                sys.stdout.write('{"id":')
                return
            if mode == "unknown-request":
                emit({"method": "attestation/generate", "id": 2, "params": {}})
                continue
            if mode == "eof":
                return
            if mode == "remote-error" or thread is None and method != "thread/start":
                emit({"id": identifier, "error": {"code": -32602, "message": PRIVATE}})
                continue
            if method == "thread/start":
                thread = {
                    "id": "test-thread", "sessionId": str(uuid4()), "projectId": "test-project",
                    "cliVersion": "0.166.0", "createdAt": 1, "updatedAt": 1,
                    "cwd": os.getcwd() if mode in MODES else str(path.parent),
                    "ephemeral": False, "modelProvider": "synthetic", "preview": PRIVATE,
                    "source": "appServer", "status": {"type": "idle"}, "turns": [],
                }
                save()
                if mode == "thread-lost-ack":
                    return
                notify("thread/started", {"thread": thread})
            if method in ("thread/start", "thread/resume"):
                assert params.get("threadId", thread["id"]) == thread["id"]
                result = {
                    "thread": thread, "model": policy.get("model", "synthetic"), "modelProvider": policy.get("model_provider", "synthetic"),
                    "cwd": thread["cwd"], "approvalPolicy": "on-request" if mode == "unsafe-policy" else "never", "approvalsReviewer": "user",
                    # Sanitized policy shape observed in the first native S0 run.
                    "sandbox": {"type": "readOnly", "networkAccess": False},
                    "reasoningEffort": "high" if mode == "unsafe-effort" else policy.get("model_reasoning_effort", "low"),
                }
                if mode == "unsafe-reviewer":
                    result["approvalsReviewer"] = "auto_review"
                instructions = params.get("developerInstructions", "")
                if "source-edit-v1" in instructions:
                    result["sandbox"] = {"type": "workspaceWrite", "writableRoots": [], "networkAccess": False,
                                         "excludeTmpdirEnvVar": True, "excludeSlashTmp": True}
                result.update(POLICY_OVERRIDES.get(mode, {}))
                if mode == "unsafe-cwd":
                    result["cwd"] = str(path.parent)
                elif mode == "ephemeral-thread":
                    result["thread"] = thread | {"ephemeral": True}
                elif mode == "nonempty-thread":
                    result["thread"] = thread | {"turns": [{"id": "pre-existing", "status": "completed", "items": []}]}
            elif method == "thread/read":
                assert params["threadId"] == thread["id"]
                result = {"thread": thread if params.get("includeTurns") else thread | {"turns": []}}
            elif method == "thread/turns/list":
                assert params["threadId"] == thread["id"]
                result = {"data": thread["turns"]}
                if mode == "history-tool":
                    result["data"][0]["items"].append({"id": "hidden-tool", "type": "webSearch", "query": PRIVATE})
                elif mode == "history-sentinel":
                    result["data"][0]["items"] = []
                elif mode == "history-not-loaded":
                    result["data"][0]["itemsView"] = "notLoaded"
                elif mode == "history-extra-turn":
                    result["data"].append(thread["turns"][0] | {"id": "extra"})
                elif mode == "history-cursor":
                    result["nextCursor"] = "more"
                elif mode == "history-input":
                    result["data"][0]["items"][0]["content"][0]["text"] = "different task"
                elif mode == "history-response":
                    result["data"][0]["items"][-1]["text"] = "different answer"
            elif method == "turn/start":
                assert params["threadId"] == thread["id"]
                prompt = params["input"][0]["text"]
                task = prompt.startswith(CONTEXT_PREFIX)
                editing = task and json.loads(prompt.removeprefix(CONTEXT_PREFIX)).get("class") == "source-edit-v1"
                edit_item = None
                user = {"id": "synthetic-input", "type": "userMessage", "content": params["input"]}
                turn = {"id": str(uuid4()), "status": "inProgress", "items": [user] if task else []}
                thread["turns"].append(turn)
                save()
                if mode == "lost-ack":
                    # The mutation reached durable synthetic state before stdout vanished.
                    return
                if mode == "delayed-ack":
                    sleep(6)  # Longer than the driver's five-second test RPC bound.
                if mode == "lost-ack-live":
                    # Break protocol after the mutation but stay alive until stdin closes.
                    sys.stdout.write("not-json\n")
                    sys.stdout.flush()
                    continue
                lifecycle = {"threadId": thread["id"], "turn": turn}
                item = {"id": "synthetic-tool", "type": "commandExecution", "command": PRIVATE,
                        "cwd": thread["cwd"], "commandActions": [], "status": "inProgress"}
                if mode == "file-approval":
                    item = {"id": item["id"], "type": "fileChange", "changes": [], "status": "inProgress"}
                activity = {"threadId": thread["id"], "turnId": turn["id"], "item": item}
                notify("synthetic/ignored", {"secret": PRIVATE})
                if mode == "out-of-order":
                    notify("item/completed", activity | {
                        "completedAtMs": 2, "item": item | {"status": "completed", "aggregatedOutput": PRIVATE},
                    })
                notify("turn/started", lifecycle)
                if mode not in SUCCESS_MODES | {"out-of-order", "driver-approval"}:
                    notify("item/started", activity | {"startedAtMs": 1})
                extra = {"web-tool": {"type": "webSearch", "query": PRIVATE},
                         "image-tool": {"type": "imageView", "path": PRIVATE},
                         "hook-item": {"type": "hookPrompt", "fragments": []}}.get(mode)
                if extra:
                    notify("item/completed", activity | {"item": {"id": "extra", **extra}, "completedAtMs": 2})
                if mode in ("approval", "driver-approval", "string-approval", "file-approval", "stale-approval"):
                    # Collide with an outstanding client ID in the numeric case.
                    pending = str(identifier) if mode == "string-approval" else identifier
                    approval = {"threadId": thread["id"], "turnId": turn["id"],
                                "itemId": item["id"], "startedAtMs": 1}
                    kind = "fileChange" if mode == "file-approval" else "commandExecution"
                    emit({"id": pending, "method": f"item/{kind}/requestApproval", "params": approval})
                    if mode == "stale-approval":
                        notify("serverRequest/resolved", {"threadId": thread["id"], "requestId": pending})
                        pending = None
                if editing and mode in SUCCESS_MODES:
                    # Fixed synthetic fixture edit. Never evaluates commands or code from task prose.
                    edits = {"src/sample.py": "def answer():\n    return 2\n",
                             "tests/portable/test_s3_sample.py":
                             "import unittest\nfrom src.sample import answer\nclass Sample(unittest.TestCase):\n"
                             "    def test_answer(self):\n        self.assertEqual(answer(), 2)\n"}
                    if mode == "s3-test-fail":
                        edits["src/sample.py"] = "def answer():\n    return 3\n"
                    if mode == "s3-audit-fail":
                        edits["src/sample.py"] += "# " + "sk-" + "A" * 30 + "\n"
                    for name, text in edits.items():
                        Path(name).write_text(text, encoding="utf-8", newline="\n")
                    if mode == "s3-unauthorized":
                        Path("unexpected.txt").write_text("synthetic unexpected file", encoding="utf-8")
                    edit_item = {"id": "synthetic-edit", "type": "fileChange", "status": "completed",
                                 "changes": [{"path": str(Path(name).absolute()), "kind": {"type": "update"},
                                              "diff": "synthetic change; inspect actual Git bytes"} for name in edits]}
                    notify("item/completed", {"threadId": thread["id"], "turnId": turn["id"],
                                              "item": edit_item, "completedAtMs": 2})
                if mode in SUCCESS_MODES:
                    agent = {"id": "synthetic-answer", "type": "agentMessage",
                             "text": "WRONG" if mode == "bad-sentinel" else task_answer(prompt) if task else "S0_CANARY_OK"}
                    if mode == "empty-answer":
                        agent["text"] = " \n"
                    elif mode == "oversize-answer":
                        agent["text"] = "x" * (MAX_RESPONSE_BYTES + 1)
                    notify("item/completed", {"threadId": thread["id"], "turnId": turn["id"], "item": agent, "completedAtMs": 2})
                    turn["items"] = ([user] + ([edit_item] if edit_item else []) + [agent]) if task else [agent]
                    turn["itemsView"] = "full"
                    if mode == "terminal-tool":
                        turn["items"].append({"id": "hidden-tool", "type": "webSearch", "query": PRIVATE})
                    if mode == "stale-turn":
                        notify("turn/completed", {"threadId": thread["id"], "turn": turn | {"id": "stale", "status": "completed"}})
                    elif mode == "history-only":
                        turn["status"] = "completed"
                    else:
                        if mode in ("terminal-response", "terminal-empty-items"):
                            turn["status"] = "completed"
                            items = [agent | {"text": "different terminal answer"}] if mode == "terminal-response" else []
                            notify("turn/completed", {"threadId": "test-thread", "turn": turn | {"items": items}})
                        else:
                            turn_status(turn, "completed")
                        if mode == "duplicate-terminal":
                            notify("turn/completed", {"threadId": thread["id"], "turn": turn | {"status": "failed"}})
                        elif mode == "restart-terminal":
                            notify("turn/started", {"threadId": thread["id"], "turn": turn | {"status": "inProgress"}})
                    save()
                    result = {"turn": turn | {"status": "inProgress"}}
                elif mode in ("out-of-order", "failed"):
                    turn_status(turn, "failed" if mode == "failed" else "completed")
                    save()
                    result = {"turn": turn | {"status": "inProgress"}}
                else:
                    result = {"turn": turn}
            elif method == "turn/steer":
                assert params["expectedTurnId"] == thread["turns"][-1]["id"]
                result = {"turnId": params["expectedTurnId"]}
            elif method == "turn/interrupt":
                turn = thread["turns"][-1]
                assert params["turnId"] == turn["id"]
                turn_status(turn, "interrupted")
                save()
                result = {}
            else:
                raise AssertionError("unsupported fixture method")
        response_id = str(identifier) if mode == "mismatch" and ready else identifier
        emit({"id": response_id, "result": result})
        if mode == "duplicate" and ready:
            emit({"id": identifier, "result": result})


if __name__ == "__main__":
    main(*sys.argv[1:])
