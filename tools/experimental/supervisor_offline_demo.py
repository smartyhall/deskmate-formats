"""Reproduce one synthetic Git task through installed public CLIs and read-only HTTP.

All runtime artifacts stay in a fresh private root outside Git. No Codex/native
emulator executable is selected, and no model or guest is contacted.
"""

import argparse
from hashlib import sha256
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Thread

from deskmate_formats.observer._private_storage import storage_directory
from deskmate_formats.observer.agent_feed import AgentJournalFeed
from deskmate_formats.observer.events import encode_json
from deskmate_formats.observer.http import ObserverServer
from deskmate_formats.observer.publication import Machine, ObservationRegistry
from deskmate_formats.supervisor.driver import digest, read_record, write_record


def demonstrate(root):
    root = Path(root).absolute()
    if root.exists():
        raise ValueError("demonstration requires a fresh private root")
    storage_directory(root, create=True)
    git_dir = root / "synthetic-git"
    storage_directory(git_dir, create=True)
    commands = []
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_AUTHOR_NAME="Synthetic Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
               GIT_COMMITTER_NAME="Synthetic Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid",
               GIT_AUTHOR_DATE="2026-01-01T00:00:00Z", GIT_COMMITTER_DATE="2026-01-01T00:00:00Z")

    def command(argv, *, data=None, cwd=None):
        result = subprocess.run(argv, input=data, cwd=cwd, env=env, capture_output=True, timeout=30)
        commands.append({"argv": argv, "cwd": str(cwd) if cwd else None,
                         "returncode": result.returncode,
                         "stdout": result.stdout.decode("utf-8"), "stderr": result.stderr.decode("utf-8")})
        write_record(root / f"command-{len(commands):02d}.json", commands[-1])
        if result.returncode:
            raise RuntimeError("demonstration command failed; inspect private command receipt")
        return result.stdout

    def git(*args, data=None):
        return command(["git", *args], data=data, cwd=git_dir).decode("ascii").strip()

    git("init", "-q", "-b", "main", "--object-format=sha1")
    git("config", "core.autocrlf", "false")
    git("config", "commit.gpgsign", "false")
    git("remote", "add", "origin", "https://example.invalid/lab/synthetic.git")
    git("commit", "-q", "--allow-empty", "-m", "Synthetic trust anchor")
    anchor = git("rev-parse", "HEAD")
    manifest = {"schema_version": 1, "id": "s2-demo", "revision": 1, "idempotency_key": "s2-demo-1",
                "title": "Synthetic S2 demonstration", "description": "Inspect synthetic metadata only.",
                "category": "verification", "profile": "offline", "resources": ["synthetic-fixtures"],
                "dependencies": []}
    raw = encode_json(manifest) + b"\n"
    blob = git("hash-object", "-w", "--stdin", data=raw)
    git("update-index", "--add", "--cacheinfo", f"100644,{blob},ops/tasks/s2-demo.json")
    git("commit", "-q", "-m", "Synthetic task revision")
    commit = git("rev-parse", "HEAD")

    def task(*args, data=None):
        return command([sys.executable, "-I", "-m", "deskmate_formats.supervisor.task_cli",
                        "--queue", str(root / "queue"), *args], data=data)

    task("init", "--checkout", str(git_dir), "--repository", "https://example.invalid/lab/synthetic.git",
         "--branch", "main", "--anchor", anchor)
    discovered = json.loads(task("discover", commit, "ops/tasks/s2-demo.json"))
    accepted = json.loads(task("accept", commit, "ops/tasks/s2-demo.json", "--review-token",
                              discovered["review_token"], "--reason-stdin", data=b"Explicit synthetic review\n"))
    assert accepted["state"] == "accepted"
    assert not (root / "bridge").exists()

    def bridge(*args):
        return json.loads(command([sys.executable, "-I", "-m", "deskmate_formats.supervisor.bridge_cli",
                                   "--state", str(root / "bridge"), *args]))

    granted = bridge("prepare-synthetic", "--queue", str(root / "queue"), "s2-demo", "1",
                     "--accepted-review-token", discovered["review_token"])
    prepared = bridge("inspect", granted["claim"])
    assert not prepared["attempted"] and prepared["operations"] == []
    outcome = bridge("dispatch-synthetic", "--queue", str(root / "queue"), granted["claim"],
                     "--authorize-dispatch", granted["dispatch_token"])
    assert outcome["state"] == "completed"
    durable = bridge("inspect", granted["claim"])
    assert durable["outcome"] == outcome
    run_dir = root / "bridge" / granted["claim"]
    files = [root / "queue" / "task-queue.sqlite3", run_dir / "receipts" / "operations.sqlite3",
             run_dir / "outcome.json", run_dir / "evidence" / "peer.json"]
    before = [digest(path) for path in files]
    registry = ObservationRegistry((Machine("synthetic", "Synthetic only"),))
    replies = []
    with AgentJournalFeed(run_dir / "spool") as feed:
        with ObserverServer(registry, port=0, agent_publication=feed.publication) as server:
            thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02})
            thread.start()
            try:
                for path, method, expected in (("/api/v1/events", "GET", 200),
                                                ("/api/v1/agents", "GET", 200),
                                                ("/api/v1/events", "POST", 405),
                                                ("/api/v1/dispatch", "GET", 404),
                                                ("/api/v1/operations", "GET", 404)):
                    conn = HTTPConnection("127.0.0.1", server.port, timeout=5)
                    try:
                        conn.request(method, path)
                        response = conn.getresponse()
                        body = response.read()
                        assert response.status == expected
                        if path == "/api/v1/events" and method == "GET":
                            assert b"Synthetic dispatch completed" in body
                            for secret in (b"S0_CANARY_OK", b"test-thread", str(root).encode()):
                                assert secret not in body
                        replies.append({"path": path, "method": method, "status": response.status,
                                        "body_sha256": sha256(body).hexdigest()})
                        write_record(root / f"http-{len(replies)}.json", {"body": body.decode(), **replies[-1]})
                    finally:
                        conn.close()
            finally:
                server.shutdown()
                thread.join(timeout=5)
                assert not thread.is_alive()
    assert before == [digest(path) for path in files]
    peer = read_record(run_dir / "evidence" / "peer.json")
    assert len(peer["turns"]) == 1
    summary = {
        "schema_version": 1, "experiment": "S2 offline synthetic-only",
        "git_anchor": anchor, "git_commit": commit, "git_blob": blob,
        "manifest_size": len(raw), "manifest_sha256": sha256(raw).hexdigest(), "manifest": manifest,
        "acceptance_state": accepted["state"], "prepared_dispatched": prepared["attempted"],
        "dispatch_plan_sha256": granted["dispatch_token"], "dispatch_state": outcome["state"],
        "child_status": outcome["child_status"], "operation_states": [r["state"] for r in outcome["operations"]],
        "mutation_methods": [r["method"] for r in outcome["operations"]], "synthetic_turn_count": len(peer["turns"]),
        "elapsed_host_seconds": outcome["elapsed_host_seconds"], "http_checks": replies,
        "browser_preserved_private_hashes": True,
        "private_artifact_sha256": dict(zip(("s1_queue", "s0_ledger", "outcome", "synthetic_peer"), before)),
        "real_model_turns": 0, "native_emulator_connections": 0,
        "emulated_time": "not measured; no emulator launched or connected",
    }
    write_record(root / "summary.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(demonstrate(args.private_root), sort_keys=True, indent=2))
