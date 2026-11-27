"""Read-only, advisory research campaign inventory validation and reporting."""
import argparse
import json
from pathlib import Path, PurePosixPath
import re

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "docs/research/campaign-inventory.json"
FIELDS = set("id domain priority status effort workers resources depends_on sources issues "
             "pull_requests evidence acceptance completion_refs".split())
TOP = {"schema_version", "as_of", "base_revision", "purpose", "campaigns"}
DOMAINS = {"infrastructure", "archive", "native-formats", "ecosystem", "reference", "workbench"}
STATUSES = {"review", "proposed", "blocked", "standing", "completed"}
WORKERS = {"repository-review", "repository-development", "offline-lab", "native-lab", "operator"}
SLUG = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
MAX_BYTES = 256 * 1024


class InventoryError(ValueError):
    """Invalid planning data."""


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InventoryError("duplicate JSON property")
        result[key] = value
    return result


def require(condition, message):
    if not condition:
        raise InventoryError(message)


def string_list(value, label, *, nonempty=False):
    require(type(value) is list and (bool(value) or not nonempty)
            and all(type(x) is str and x.strip() for x in value), f"invalid {label}")
    require(len(set(value)) == len(value), f"duplicate {label}")


def number_list(value, label):
    require(type(value) is list and all(type(x) is int and x > 0 for x in value),
            f"invalid {label}")
    require(len(value) == len(set(value)), f"duplicate {label}")


def source_path(value, root):
    path = PurePosixPath(value)
    require(not path.is_absolute() and "\\" not in value
            and all(part not in ("", ".", "..") for part in value.split("/"))
            and path.as_posix() == value, "invalid source path")
    candidate = root / path
    require(candidate.resolve().is_relative_to(root.resolve()) and candidate.is_file(),
            f"missing or out-of-tree source: {value}")


def validate(data, root=ROOT):
    require(type(data) is dict and set(data) == TOP, "invalid inventory fields")
    require(type(data["schema_version"]) is int and data["schema_version"] == 1,
            "unsupported schema version")
    require(type(data["as_of"]) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}", data["as_of"]),
            "invalid snapshot date")
    require(type(data["base_revision"]) is str and re.fullmatch(r"[0-9a-f]{40}", data["base_revision"]),
            "invalid base revision")
    require(type(data["purpose"]) is str and bool(data["purpose"].strip()), "missing purpose")
    entries = data["campaigns"]
    require(type(entries) is list and 0 < len(entries) <= 500, "invalid campaign list")
    by_id = {}
    for row in entries:
        require(type(row) is dict and set(row) == FIELDS, "invalid campaign fields")
        key = row["id"]
        require(type(key) is str and SLUG.fullmatch(key), "invalid campaign ID")
        require(key not in by_id, f"duplicate campaign ID: {key}")
        by_id[key] = row
        require(type(row["domain"]) is str and row["domain"] in DOMAINS, f"invalid domain: {key}")
        require(type(row["status"]) is str and row["status"] in STATUSES, f"invalid status: {key}")
        require(type(row["priority"]) is int and 1 <= row["priority"] <= 4, f"invalid priority: {key}")
        require(type(row["effort"]) is str and row["effort"] in {"small", "medium", "large"},
                f"invalid effort: {key}")
        for field in ("workers", "resources", "sources", "depends_on", "completion_refs"):
            string_list(row[field], f"{key}.{field}", nonempty=field in {"workers", "resources", "sources"})
        require(set(row["workers"]) <= WORKERS, f"invalid worker role: {key}")
        require(all(SLUG.fullmatch(x) for x in row["resources"]), f"invalid resource: {key}")
        for field in ("evidence", "acceptance"):
            require(type(row[field]) is str and bool(row[field].strip()), f"missing {key}.{field}")
        for field in ("issues", "pull_requests"):
            number_list(row[field], f"{key}.{field}")
        for source in row["sources"]:
            source_path(source, root)
        if row["status"] == "completed":
            require(bool(row["completion_refs"]), f"missing completion evidence: {key}")
        else:
            require(not row["completion_refs"], f"unexpected completion evidence: {key}")
    for key, row in by_id.items():
        for dependency in row["depends_on"]:
            require(dependency in by_id, f"unknown dependency: {key} -> {dependency}")
            require(by_id[dependency]["status"] != "standing",
                    f"standing workstream cannot be a completion dependency: {dependency}")
            if row["status"] == "completed":
                require(by_id[dependency]["status"] == "completed", f"incomplete dependency: {key}")
    visiting, visited = set(), set()

    def visit(key):
        require(key not in visiting, f"dependency cycle at {key}")
        if key in visited:
            return
        visiting.add(key)
        for dependency in by_id[key]["depends_on"]:
            visit(dependency)
        visiting.remove(key)
        visited.add(key)

    for key in by_id:
        visit(key)
    return data


def load(path=DEFAULT, root=ROOT):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES, "inventory exceeds size limit")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise InventoryError("invalid UTF-8 JSON") from error
    return validate(data, root)


def report(data, worker=None):
    by_id = {row["id"]: row for row in data["campaigns"]}
    selected = []
    for row in sorted(by_id.values(), key=lambda item: (item["priority"], item["id"])):
        if worker is not None and worker not in row["workers"]:
            continue
        pending = [key for key in row["depends_on"] if by_id[key]["status"] != "completed"]
        selected.append({**row, "unresolved_dependencies": pending})
    return {"as_of": data["as_of"], "base_revision": data["base_revision"],
            "advisory_only": True, "campaigns": selected}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--inventory", type=Path, default=DEFAULT)
    parser.add_argument("--worker", choices=sorted(WORKERS))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = report(load(args.inventory), args.worker)
    except (InventoryError, OSError) as error:
        parser.exit(2, f"inventory: {error}\n")
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Advisory snapshot {result['as_of']} — not execution authority")
        for row in result["campaigns"]:
            pending = ", ".join(row["unresolved_dependencies"]) or "none recorded"
            print(f"P{row['priority']} {row['id']} [{row['status']}; {row['effort']}] — "
                  f"unresolved internal dependencies: {pending}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
