"""Reproduce the S0 shape profile from a private stable Codex schema export."""

import argparse
from hashlib import sha256
import json
from pathlib import Path


METHODS = {
    "initialize": ("v1/InitializeParams", "v1/InitializeResponse"),
    "thread/start": ("v2/ThreadStartParams", "v2/ThreadStartResponse"),
    "thread/resume": ("v2/ThreadResumeParams", "v2/ThreadResumeResponse"),
    "thread/read": ("v2/ThreadReadParams", "v2/ThreadReadResponse"),
    "thread/turns/list": ("v2/ThreadTurnsListParams", "v2/ThreadTurnsListResponse"),
    "turn/start": ("v2/TurnStartParams", "v2/TurnStartResponse"),
    "turn/steer": ("v2/TurnSteerParams", "v2/TurnSteerResponse"),
    "turn/interrupt": ("v2/TurnInterruptParams", "v2/TurnInterruptResponse"),
    "item/commandExecution/requestApproval": (
        "CommandExecutionRequestApprovalParams", "CommandExecutionRequestApprovalResponse",
    ),
    "item/fileChange/requestApproval": (
        "FileChangeRequestApprovalParams", "FileChangeRequestApprovalResponse",
    ),
}
NOTIFICATIONS = {
    "thread/started": "v2/ThreadStartedNotification",
    "turn/started": "v2/TurnStartedNotification",
    "turn/completed": "v2/TurnCompletedNotification",
    "item/started": "v2/ItemStartedNotification",
    "item/completed": "v2/ItemCompletedNotification",
    "serverRequest/resolved": "v2/ServerRequestResolvedNotification",
}
ANNOTATIONS = {"description", "title", "default", "$schema", "examples"}


def shape(schema):
    if type(schema) is bool:
        return schema
    return {
        key: (
            {name: shape(value) for name, value in child.items()}
            if key in {"properties", "patternProperties", "definitions"}
            else shape(child) if type(child) is dict
            else [shape(value) if type(value) is dict else value for value in child]
            if type(child) is list else child
        )
        for key, child in schema.items()
        if key not in ANNOTATIONS
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schema_directory", type=Path)
    parser.add_argument("profile", type=Path)
    parser.add_argument("inventory", type=Path)
    args = parser.parse_args()
    files = {
        path.relative_to(args.schema_directory).as_posix(): path.read_bytes()
        for path in sorted(args.schema_directory.rglob("*.json"))
    }
    names = sorted({
        *NOTIFICATIONS.values(), *(name for pair in METHODS.values() for name in pair),
        "ClientNotification", "JSONRPCError", "RequestId",
    })
    definitions = {}
    for name in names:
        schema = shape(json.loads(files[name + ".json"]))
        for key, value in schema.pop("definitions", {}).items():
            if definitions.setdefault(key, value) != value:
                raise ValueError(f"conflicting schema definition {key}")
        if definitions.setdefault(name, schema) != schema:
            raise ValueError(f"conflicting schema definition {name}")
    profile = {
        "methods": METHODS,
        "notifications": NOTIFICATIONS,
        "definitions": definitions,
    }
    # Keep each machine-generated definition on its own line.
    encode = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"))
    lines = [f'  "{key}": {encode(profile[key])},' for key in ("methods", "notifications")]
    definitions = ",\n".join(f"    {encode(key)}: {encode(value)}" for key, value in sorted(definitions.items()))
    profile_bytes = ("{\n" + "\n".join(lines) + '\n  "definitions": {\n' + definitions + "\n  }\n}\n").encode()
    args.profile.write_bytes(profile_bytes)
    inventory = {
        "codex_cli": "0.166.0",
        "schema_command": "codex app-server generate-json-schema --out <private-directory>",
        "profile_sha256": sha256(profile_bytes).hexdigest(),
        "sha256_by_path": {name: sha256(data).hexdigest() for name, data in files.items()},
    }
    args.inventory.write_bytes((json.dumps(inventory, indent=2, sort_keys=True) + "\n").encode())


if __name__ == "__main__":
    main()
