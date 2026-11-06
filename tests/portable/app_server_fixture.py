"""Synthetic app-server child. Its only inputs are stdio and disposable test state."""

import json
from pathlib import Path
import sys
from uuid import uuid4

PRIVATE = "private-canary-command-and-result"


def emit(message):
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def notify(method, params):
    emit({"method": method, "params": params})


def turn_status(turn, status):
    turn["status"] = status
    notify("turn/completed", {"threadId": "test-thread", "turn": turn})


def main(state_path, mode):
    path = Path(state_path)
    thread = json.loads(path.read_bytes()) if path.exists() else None
    initialized = False
    ready = False
    pending = None

    def save():
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(thread), encoding="utf-8")
        temp.replace(path)

    for line in sys.stdin:
        message = json.loads(line)
        identifier = message.get("id")
        method = message.get("method")
        params = message.get("params", {})
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
                    "cliVersion": "0.166.0", "createdAt": 1, "updatedAt": 1, "cwd": str(path.parent),
                    "ephemeral": False, "modelProvider": "synthetic", "preview": PRIVATE,
                    "source": "appServer", "status": {"type": "idle"}, "turns": [],
                }
                save()
                notify("thread/started", {"thread": thread})
            if method in ("thread/start", "thread/resume"):
                assert params.get("threadId", thread["id"]) == thread["id"]
                result = {
                    "thread": thread, "model": "synthetic", "modelProvider": "synthetic",
                    "cwd": thread["cwd"], "approvalPolicy": "on-request", "approvalsReviewer": "user",
                    "sandbox": {"type": "readOnly"},
                }
            elif method == "thread/read":
                assert params["threadId"] == thread["id"]
                result = {"thread": thread if params.get("includeTurns") else thread | {"turns": []}}
            elif method == "thread/turns/list":
                assert params["threadId"] == thread["id"]
                result = {"data": thread["turns"]}
            elif method == "turn/start":
                assert params["threadId"] == thread["id"]
                turn = {"id": str(uuid4()), "status": "inProgress", "items": []}
                thread["turns"].append(turn)
                save()
                if mode == "lost-ack":
                    # The mutation reached durable synthetic state before stdout vanished.
                    return
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
                if mode != "out-of-order":
                    notify("item/started", activity | {"startedAtMs": 1})
                if mode in ("approval", "string-approval", "file-approval", "stale-approval"):
                    # Collide with an outstanding client ID in the numeric case.
                    pending = str(identifier) if mode == "string-approval" else identifier
                    approval = {"threadId": thread["id"], "turnId": turn["id"],
                                "itemId": item["id"], "startedAtMs": 1}
                    kind = "fileChange" if mode == "file-approval" else "commandExecution"
                    emit({"id": pending, "method": f"item/{kind}/requestApproval", "params": approval})
                    if mode == "stale-approval":
                        notify("serverRequest/resolved", {"threadId": thread["id"], "requestId": pending})
                        pending = None
                if mode in ("out-of-order", "failed"):
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
