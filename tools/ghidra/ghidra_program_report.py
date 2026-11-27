"""Programmatic inspection of an owned Ghidra program, with bounded output.

Read modes (``--summary``, ``--functions``, ``--symbols``, ``--xrefs``,
``--disassemble``, ``--pcode``, ``--decompile``) open the stored program
read-only and report structural facts: counts, sizes, addresses, reference
types, instruction text and p-code operations. Decompiled source is
proprietary content, so it is never put in the receipt; ``--text-output``
writes it to a private file and the receipt records only a digest and a line
count.

Write mode (``--annotate``) proves that persistent annotations and transactions
work in a project we own: it writes a plate comment, a bookmark and a label in
one transaction, saves, and reports the exact values it wrote. The plate and the
bookmark comment carry the attempt identifier, so an annotation can be told
apart from an earlier probe left at the same address.

``--verify-annotation`` is a separate invocation that reopens the project and
reads those values back, because a reopen inside the writing JVM proves nothing
about persistence. It is bound to the annotate receipt (``--annotation-receipt``)
and requires that receipt's attempt, project, program, address, plate comment,
bookmark type/category/comment and label to match exactly. A missing, stale,
mismatched or partial annotation is ``not_persisted``; nothing is inferred from
the presence of some comment.

Receipt rules (see docs/research/ghidra-dos-import-receipts.md):

* Every invocation is an *attempt* with a unique identifier, and the receipt
  names the project, the program and the toolchain it actually used.
* A missing project is a failure. This tool never creates one.
* An annotation that was committed but not saved is reported as unsaved, not
  as persisted.
* A verified annotation must match the annotation an annotate receipt names,
  component by component.
* Receipts are published atomically.

Exit codes::

    0  success
    2  usage or validation error
    3  project or program not found
    4  the program could not be opened
    5  the requested operation failed
    6  the operation completed but was not persisted

Example::

    python tools/ghidra/ghidra_program_report.py \\
        --project-dir PRIVATE/projects --project desk --program /DESK.EXE \\
        --summary --functions --limit 25 \\
        --decompile FUN_1000_0000 --text-output PRIVATE/exports/dec.txt \\
        --output PRIVATE/exports/report.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# The plate and the bookmark comment both carry the attempt identifier: an
# annotation that cannot be attributed to one attempt cannot be distinguished
# from a stale probe left at the same address.
ANNOTATION_PLATE = "campaign probe (%s): %s"
ANNOTATION_LABEL = "probe_label"
ANNOTATION_BOOKMARK_TYPE = "Note"
ANNOTATION_BOOKMARK_CATEGORY = "campaign-probe"

RECEIPT_SCHEMA = "ghidra-program-report/3"

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NOT_FOUND = 3
EXIT_OPEN_FAILED = 4
EXIT_OPERATION_FAILED = 5
EXIT_NOT_PERSISTED = 6

OUTCOMES = (
    "succeeded",
    "invalid_request",
    "project_missing",
    "program_missing",
    "open_failed",
    "operation_failed",
    "not_persisted",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def publish_json(path: str | None, payload: dict) -> str:
    """Write ``payload`` atomically, or to stdout; return the digest."""
    text = json.dumps(payload, indent=2) + "\n"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if not path:
        sys.stdout.write(text)
        return digest
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(
        f"{target.name}.tmp-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    )
    # Bytes, not text: platform newline translation would make the published
    # file differ from the digest recorded for it.
    temporary.write_bytes(text.encode("utf-8"))
    os.replace(temporary, target)
    return digest


def _parse_properties(path: Path) -> dict:
    wanted = {
        "application.version",
        "application.release.name",
        "application.build.date",
        "application.java.min",
        "application.revision.ghidra",
    }
    values = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            if key.strip() in wanted:
                values[key.strip()] = value.strip()
    return values


def _application_properties() -> dict:
    install = os.environ.get("GHIDRA_INSTALL_DIR")
    if not install:
        return {}
    path = Path(install) / "Ghidra" / "application.properties"
    if not path.is_file():
        return {}
    return _parse_properties(path)


def _size_histogram(sizes: list[int]) -> dict:
    buckets = {"0": 0, "1-16": 0, "17-64": 0, "65-256": 0, "257-1024": 0, "1025+": 0}
    for size in sizes:
        if size == 0:
            buckets["0"] += 1
        elif size <= 16:
            buckets["1-16"] += 1
        elif size <= 64:
            buckets["17-64"] += 1
        elif size <= 256:
            buckets["65-256"] += 1
        elif size <= 1024:
            buckets["257-1024"] += 1
        else:
            buckets["1025+"] += 1
    return buckets


def _content_sha256(program) -> str:
    """Hash the program's byte content and block geometry.

    A report has to name the bytes it describes. Names and counts can match
    while the stored bytes differ, so this digest is what ties an observation to
    a specific program rather than to a similarly shaped one. Uninitialized
    blocks contribute their geometry only.
    """
    digest = hashlib.sha256()
    for block in program.getMemory().getBlocks():
        digest.update(
            f"{block.getName()}|{block.getStart()}|{block.getEnd()}|"
            f"{block.getSize()}|{int(bool(block.isInitialized()))}|".encode()
        )
        if block.isInitialized():
            data = bytearray(block.getSize())
            program.getMemory().getBytes(block.getStart(), data)
            digest.update(hashlib.sha256(bytes(data)).digest())
        else:
            digest.update(b"uninitialized")
    return digest.hexdigest()


def _project_path(program) -> str | None:
    """The program's path inside its project, if the API will tell us."""
    try:
        return str(program.getDomainFile().getPathname())
    except Exception:  # noqa: BLE001 - identity is best effort, never fatal
        return None


def _summary(program) -> dict:
    functions = list(program.getFunctionManager().getFunctions(True))
    sizes = []
    thunks = 0
    external = 0
    for function in functions:
        body = function.getBody()
        size = sum(int(r.getLength()) for r in body)
        sizes.append(size)
        if function.isThunk():
            thunks += 1
        if function.isExternal():
            external += 1
    return {
        "name": program.getName(),
        "project_path": _project_path(program),
        "content_sha256": _content_sha256(program),
        "language_id": str(program.getLanguageID()),
        "compiler_spec": str(program.getCompilerSpec().getCompilerSpecID()),
        "image_base": str(program.getImageBase()),
        "min_address": str(program.getMinAddress()),
        "max_address": str(program.getMaxAddress()),
        "instruction_count": int(program.getListing().getNumInstructions()),
        "function_count": len(functions),
        "thunk_count": thunks,
        "external_function_count": external,
        "function_size_histogram": _size_histogram(sizes),
        "symbol_count": int(program.getSymbolTable().getNumSymbols()),
        "data_type_count": int(program.getDataTypeManager().getDataTypeCount(True)),
        "block_count": len(list(program.getMemory().getBlocks())),
        "blocks": [
            {"name": b.getName(), "start": str(b.getStart()), "size": b.getSize(),
             "initialized": bool(b.isInitialized()), "execute": bool(b.isExecute())}
            for b in program.getMemory().getBlocks()
        ],
    }


def _functions(program, limit: int) -> dict:
    rows = []
    for function in program.getFunctionManager().getFunctions(True):
        if len(rows) >= limit:
            break
        rows.append(
            {
                "entry": str(function.getEntryPoint()),
                "name": function.getName(),
                "size": sum(int(r.getLength()) for r in function.getBody()),
                "thunk": bool(function.isThunk()),
                "external": bool(function.isExternal()),
                "calling_convention": str(
                    function.getCallingConventionName()
                    if hasattr(function, "getCallingConventionName")
                    else ""
                ),
            }
        )
    return {
        "returned": len(rows),
        "limit": limit,
        "truncated": len(rows) >= limit,
        "functions": rows,
    }


def _symbols(program, limit: int) -> dict:
    """Enumerate symbols: names, addresses and kinds, not their contents."""
    table = program.getSymbolTable()
    total = int(table.getNumSymbols())
    rows = []
    for symbol in table.getAllSymbols(True):
        if len(rows) >= limit:
            break
        rows.append(
            {
                "address": str(symbol.getAddress()),
                "name": symbol.getName(),
                "type": str(symbol.getSymbolType()),
                "namespace": str(symbol.getParentNamespace().getName()),
                "primary": bool(symbol.isPrimary()),
                "source": str(symbol.getSource()),
            }
        )
    return {
        "total": total,
        "returned": len(rows),
        "limit": limit,
        "truncated": len(rows) >= limit,
        "symbols": rows,
    }


def _xrefs(program, target: str) -> dict:
    address = program.getAddressFactory().getAddress(target)
    if address is None:
        raise ValueError(f"unparseable address: {target}")
    references = list(program.getReferenceManager().getReferencesTo(address))
    return {
        "target": str(address),
        "count": len(references),
        "references": [
            {
                "from": str(reference.getFromAddress()),
                "type": str(reference.getReferenceType()),
                "source": str(reference.getSource()),
            }
            for reference in references[:200]
        ],
        "truncated": len(references) > 200,
    }


def _resolve_function(program, selector: str):
    if selector.startswith(("0x", "0X")) or selector[:1].isdigit():
        address = program.getAddressFactory().getAddress(selector)
        if address is not None:
            function = program.getFunctionManager().getFunctionAt(address)
            if function is not None:
                return function
    for function in program.getFunctionManager().getFunctions(True):
        if function.getName() == selector:
            return function
    return None


def _disassemble(program, selector: str, limit: int) -> dict:
    """Bounded listing from a function entry; follows no branches."""
    function = _resolve_function(program, selector)
    if function is None:
        return {"selector": selector, "found": False}
    listing = program.getListing()
    rows = []
    address = function.getEntryPoint()
    while address is not None and len(rows) < limit:
        instruction = listing.getInstructionAt(address)
        if instruction is None:
            break
        rows.append(
            {
                "address": str(instruction.getAddress()),
                "bytes": bytes(
                    (int(b) & 0xFF)
                    for b in instruction.getBytes()
                ).hex(),
                "mnemonic": instruction.getMnemonicString(),
                "operands": instruction.toString().split(None, 1)[1]
                if len(instruction.toString().split(None, 1)) > 1
                else "",
                "flow_type": str(instruction.getFlowType()),
            }
        )
        address = instruction.getFallThrough()
    return {
        "selector": selector,
        "found": True,
        "entry": str(function.getEntryPoint()),
        "function": function.getName(),
        "returned": len(rows),
        "limit": limit,
        "truncated": len(rows) >= limit,
        "instructions": rows,
        "scope": (
            "fall-through listing only: no branch following and no p-code "
            "evaluation, so a linear sweep is not a control-flow claim"
        ),
    }


def _varnode_text(varnode) -> str | None:
    """Describe a p-code varnode by space, offset and size.

    ``getHigh()`` is only populated after decompilation; using it alone leaves
    every operand blank, which would make two different operations look the
    same. The raw varnode identity is what the bytes actually reference.
    """
    if varnode is None:
        return None
    return (
        f"{varnode.getAddress().getAddressSpace().getName()}:"
        f"{varnode.getAddress().getOffset():#x}:{varnode.getSize()}"
    )


def _pcode(program, selector: str, limit: int) -> dict:
    """P-code operations for a function's instructions, bounded."""
    function = _resolve_function(program, selector)
    if function is None:
        return {"selector": selector, "found": False}
    listing = program.getListing()
    exact = int(function.getBody().getNumAddresses())
    rows = []
    address = function.getEntryPoint()
    while address is not None and len(rows) < limit:
        instruction = listing.getInstructionAt(address)
        if instruction is None:
            break
        for op in instruction.getPcode():
            if len(rows) >= limit:
                break
            rows.append(
                {
                    "address": str(instruction.getAddress()),
                    "sequence": int(op.getSeqnum().getTime()),
                    "mnemonic": str(op.getMnemonic()),
                    "output": _varnode_text(op.getOutput()),
                    "inputs": [
                        _varnode_text(op.getInput(index))
                        for index in range(int(op.getNumInputs()))
                        if op.getInput(index) is not None
                    ],
                }
            )
        address = instruction.getFallThrough()
    return {
        "selector": selector,
        "found": True,
        "entry": str(function.getEntryPoint()),
        "function": function.getName(),
        "body_addresses": exact,
        "returned": len(rows),
        "limit": limit,
        "truncated": len(rows) >= limit,
        "operations": rows,
        "scope": (
            "raw p-code operations with varnode identities but no simplified "
            "form; equal operation sequences are byte-level evidence, not a "
            "claim about runtime behaviour"
        ),
    }


def _decompile(program, selector: str, text_output: str | None) -> dict:
    from ghidra.app.decompiler import DecompInterface  # noqa: PLC0415

    function = _resolve_function(program, selector)
    if function is None:
        return {"selector": selector, "found": False}
    import time  # noqa: PLC0415

    interface = DecompInterface()
    interface.openProgram(program)
    try:
        started = time.time()
        result = interface.decompileFunction(function, 120, None)
        elapsed_ms = int((time.time() - started) * 1000)
        if not result.decompileCompleted():
            return {
                "selector": selector,
                "found": True,
                "decompile_completed": False,
                "error": str(result.getErrorMessage()),
            }
        decompiled = result.getDecompiledFunction()
        text = decompiled.getC()
        record = {
            "selector": selector,
            "found": True,
            "decompile_completed": True,
            "entry": str(function.getEntryPoint()),
            "name": function.getName(),
            "line_count": len(text.splitlines()),
            "character_count": len(text),
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "signature": str(decompiled.getSignature()),
            "time_ms": elapsed_ms,
            "text_written": False,
        }
        if text_output:
            Path(text_output).write_text(text, encoding="utf-8")
            record["text_written"] = True
        return record
    finally:
        interface.dispose()


def _open_readonly(project_dir: Path, name: str, program_path: str):
    import pyghidra  # noqa: PLC0415

    from ghidra.framework.model import ProjectLocator  # noqa: PLC0415
    from ghidra.pyghidra import PyGhidraProjectManager  # noqa: PLC0415

    manager = PyGhidraProjectManager()
    locator = ProjectLocator(str(project_dir), name)
    if not locator.exists():
        raise FileNotFoundError(f"project {name} does not exist in {project_dir}")
    project = manager.openProject(locator, False, False)
    return pyghidra.program_context(project, program_path), project


def _annotate(
    project_dir: Path, name: str, program_path: str, text: str, attempt_id: str
) -> dict:
    import pyghidra  # noqa: PLC0415

    from ghidra.framework.model import ProjectLocator  # noqa: PLC0415
    from ghidra.program.model.listing import CommentType  # noqa: PLC0415
    from ghidra.program.model.symbol import SourceType  # noqa: PLC0415
    from ghidra.pyghidra import PyGhidraProjectManager  # noqa: PLC0415
    from java.lang import Object  # noqa: PLC0415

    manager = PyGhidraProjectManager()
    locator = ProjectLocator(str(project_dir), name)
    if not locator.exists():
        raise FileNotFoundError(f"project {name} does not exist in {project_dir}")
    project = manager.openProject(locator, False, False)
    consumer = Object()
    plate = ANNOTATION_PLATE % (attempt_id, text)
    record: dict = {
        "program": program_path,
        "plate": plate,
        "bookmark": {
            "type": ANNOTATION_BOOKMARK_TYPE,
            "category": ANNOTATION_BOOKMARK_CATEGORY,
            "comment": plate,
        },
        "label": ANNOTATION_LABEL,
        "committed": False,
        "saved": False,
        "persisted": False,
    }
    try:
        domain_file = project.getProjectData().getFile(program_path)
        if domain_file is None:
            raise FileNotFoundError(f"{program_path} is not in project {name}")
        program = domain_file.getDomainObject(
            consumer, False, False, pyghidra.task_monitor()
        )
        try:
            start = program.getMinAddress()
            record["address"] = str(start)
            listing = program.getListing()
            transaction = program.startTransaction("campaign annotation probe")
            committed = False
            try:
                listing.setComment(start, CommentType.PLATE, plate)
                program.getBookmarkManager().setBookmark(
                    start,
                    ANNOTATION_BOOKMARK_TYPE,
                    ANNOTATION_BOOKMARK_CATEGORY,
                    plate,
                )
                program.getSymbolTable().createLabel(
                    start, ANNOTATION_LABEL, SourceType.USER_DEFINED
                )
                committed = True
            finally:
                program.endTransaction(transaction, committed)
            record["committed"] = committed
            if committed:
                try:
                    program.save("campaign annotation probe", pyghidra.task_monitor())
                    record["saved"] = True
                except Exception as exc:  # noqa: BLE001 - unsaved is a result
                    record["save_error"] = f"{type(exc).__name__}: {exc}"
        finally:
            program.release(consumer)
    finally:
        try:
            project.close()
            record["closed"] = True
        except Exception as exc:  # noqa: BLE001
            record["closed"] = False
            record["close_error"] = f"{type(exc).__name__}: {exc}"
    # A committed annotation that was not saved is not persisted, and the
    # project must also have closed cleanly for the save to be trusted.
    record["persisted"] = bool(record.get("saved")) and bool(record.get("closed"))
    return record


def _text_key(value) -> str:
    """Compare recorded text (a path, an address) by value, not by spelling."""
    return str(value or "").strip().lower()


def _path_key(value) -> str:
    """Compare paths by the file they name, not by how they were written."""
    return os.path.normcase(os.path.realpath(os.path.abspath(str(value or "."))))


def _annotation_expectations(
    receipt_path: str, project: str, project_dir: Path, program_path: str
) -> tuple[dict | None, list[str]]:
    """Resolve the annotation a verify run must find, from the annotate receipt.

    A verify run is only meaningful against a named annotation, so every part of
    the expectation comes from the receipt the annotate run published: the
    attempt, the project, the program, the address, the plate comment, the
    bookmark and the label. Nothing is taken from whatever the program happens
    to contain, because a comment written by an earlier probe at the same
    address would otherwise pass as evidence of this one.
    """
    problems: list[str] = []
    try:
        data = Path(receipt_path).read_bytes()
    except OSError as exc:
        return None, [f"annotation receipt {receipt_path} is unreadable: {exc}"]
    try:
        receipt = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, [f"annotation receipt {receipt_path} is not JSON: {exc}"]
    if not isinstance(receipt, dict):
        return None, [
            f"annotation receipt is {type(receipt).__name__}, not a JSON object"
        ]
    digest = hashlib.sha256(data).hexdigest()

    if receipt.get("schema") != RECEIPT_SCHEMA:
        problems.append(
            f"annotation receipt schema is {receipt.get('schema')!r}, "
            f"not {RECEIPT_SCHEMA}"
        )
    if receipt.get("tool") != "tools/ghidra/ghidra_program_report.py":
        problems.append("annotation receipt was not written by this tool")
    if receipt.get("outcome") != "succeeded":
        problems.append(
            f"annotation receipt outcome is {receipt.get('outcome')!r}, "
            "not 'succeeded'"
        )
    attempt = receipt.get("attempt")
    attempt_id = attempt.get("id") if isinstance(attempt, dict) else None
    if not isinstance(attempt_id, str) or not attempt_id:
        problems.append("annotation receipt names no attempt")
        attempt_id = None

    annotation = receipt.get("annotation")
    if not isinstance(annotation, dict):
        problems.append("annotation receipt has no annotation record")
        annotation = {}
    if annotation.get("persisted") is not True:
        problems.append("annotation receipt does not claim persisted annotations")

    requested = receipt.get("requested")
    if not isinstance(requested, dict):
        problems.append("annotation receipt has no requested section")
        requested = {}
    if requested.get("project") != project:
        problems.append(
            f"annotation receipt names project {requested.get('project')!r}, "
            f"not {project!r}"
        )
    if _text_key(requested.get("program_path")) != _text_key(program_path):
        problems.append(
            f"annotation receipt names program {requested.get('program_path')!r}, "
            f"not {program_path!r}"
        )
    if _path_key(requested.get("project_dir")) != _path_key(project_dir):
        problems.append(
            "annotation receipt names project directory "
            f"{requested.get('project_dir')!r}, not {str(project_dir)!r}"
        )

    address = annotation.get("address")
    if not isinstance(address, str) or not address.strip():
        problems.append("annotation record names no address")
        address = None
    plate = annotation.get("plate")
    if not isinstance(plate, str) or not plate.strip():
        problems.append("annotation record names no plate comment")
        plate = None
    elif attempt_id is None or attempt_id not in plate:
        problems.append(
            "annotation plate does not carry the attempt identifier, so a stale "
            "annotation at the same address cannot be excluded"
        )
    bookmark = annotation.get("bookmark")
    if not isinstance(bookmark, dict):
        problems.append("annotation record names no bookmark")
        bookmark = {}
    else:
        if bookmark.get("type") != ANNOTATION_BOOKMARK_TYPE:
            problems.append(
                f"annotation bookmark type is {bookmark.get('type')!r}, "
                f"not {ANNOTATION_BOOKMARK_TYPE!r}"
            )
        if bookmark.get("category") != ANNOTATION_BOOKMARK_CATEGORY:
            problems.append(
                f"annotation bookmark category is {bookmark.get('category')!r}, "
                f"not {ANNOTATION_BOOKMARK_CATEGORY!r}"
            )
        if plate is not None and bookmark.get("comment") != plate:
            problems.append(
                "annotation bookmark comment is not the plate the receipt names"
            )
    if annotation.get("label") != ANNOTATION_LABEL:
        problems.append(
            f"annotation label is {annotation.get('label')!r}, "
            f"not {ANNOTATION_LABEL!r}"
        )

    if problems:
        return None, problems
    return {
        "receipt": str(receipt_path),
        "receipt_sha256": digest,
        "attempt_id": attempt_id,
        "project": project,
        "project_dir": str(project_dir),
        "program_path": program_path,
        "address": address,
        "plate": plate,
        "bookmark": {
            "type": bookmark["type"],
            "category": bookmark["category"],
            "comment": bookmark["comment"],
        },
        "label": annotation["label"],
    }, []


def _compare_annotation(expected: dict, observed: dict) -> dict:
    """Check every component of the named annotation; none of them is implied."""
    symbols = observed.get("symbols") or []
    bookmarks = observed.get("bookmarks") or []
    want_bookmark = expected["bookmark"]
    checks = {
        "address": {
            "expected": expected["address"],
            "observed": observed.get("address"),
            "ok": observed.get("address") is not None
            and _text_key(observed["address"]) == _text_key(expected["address"]),
        },
        "plate_comment": {
            "expected": expected["plate"],
            "observed": observed.get("plate_comment"),
            "ok": observed.get("plate_comment") == expected["plate"],
        },
        "bookmark": {
            "expected": want_bookmark,
            "observed": bookmarks,
            "ok": any(
                row.get("type") == want_bookmark["type"]
                and row.get("category") == want_bookmark["category"]
                and row.get("comment") == want_bookmark["comment"]
                for row in bookmarks
            ),
        },
        "label": {
            "expected": expected["label"],
            "observed": symbols,
            "ok": expected["label"] in symbols,
        },
    }
    return {"checks": checks, "persisted": all(c["ok"] for c in checks.values())}


def _verify_annotation(
    project_dir: Path, name: str, program_path: str, expected: dict
) -> dict:
    from ghidra.program.model.listing import CommentType  # noqa: PLC0415

    observed: dict = {
        "address": None,
        "plate_comment": None,
        "bookmarks": [],
        "symbols": [],
    }
    context, project = _open_readonly(project_dir, name, program_path)
    try:
        with context as program:
            try:
                target = program.getAddressFactory().getAddress(expected["address"])
            except Exception:  # noqa: BLE001 - unresolvable is a failed check
                target = None
            if target is not None:
                observed["address"] = str(target)
                plate = program.getListing().getComment(CommentType.PLATE, target)
                observed["plate_comment"] = str(plate) if plate else None
                observed["bookmarks"] = [
                    {
                        "type": str(row.getTypeString()),
                        "category": str(row.getCategory()),
                        "comment": str(row.getComment()),
                    }
                    for row in program.getBookmarkManager().getBookmarks(target)
                ]
                observed["symbols"] = [
                    str(symbol.getName())
                    for symbol in program.getSymbolTable().getSymbols(target)
                ]
    finally:
        project.close()
    comparison = _compare_annotation(expected, observed)
    return {
        "address": observed["address"],
        "observed": observed,
        "checks": comparison["checks"],
        "persisted": comparison["persisted"],
    }


def _validate(args) -> list[str]:
    errors = []
    if args.limit <= 0:
        errors.append("--limit must be a positive number")
    if args.max_instructions <= 0:
        errors.append("--max-instructions must be a positive number")
    modes = [
        args.summary,
        args.functions,
        args.symbols,
        bool(args.xrefs),
        bool(args.disassemble),
        bool(args.pcode),
        bool(args.decompile),
        bool(args.annotate),
        args.verify_annotation,
    ]
    if not any(modes):
        errors.append("request at least one read or write mode")
    if args.annotate and args.verify_annotation:
        errors.append("--annotate and --verify-annotation are separate invocations")
    if args.verify_annotation and not args.annotation_receipt:
        errors.append(
            "--verify-annotation needs --annotation-receipt from the annotate run"
        )
    if args.annotation_receipt and not args.verify_annotation:
        errors.append("--annotation-receipt is only read with --verify-annotation")
    if args.text_output and not args.decompile:
        errors.append("--text-output needs --decompile")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--program", required=True, help="project path, e.g. /DESK.EXE")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--functions", action="store_true")
    parser.add_argument("--symbols", action="store_true")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--xrefs", help="address whose references to list")
    parser.add_argument("--disassemble", help="function name or address to disassemble")
    parser.add_argument("--pcode", help="function name or address to lift to p-code")
    parser.add_argument("--max-instructions", type=int, default=256)
    parser.add_argument("--decompile", help="function name or address")
    parser.add_argument("--text-output", help="private file for decompiled source")
    parser.add_argument("--annotate", help="plate comment text to persist")
    parser.add_argument("--verify-annotation", action="store_true")
    parser.add_argument(
        "--annotation-receipt",
        help="receipt published by the --annotate run whose annotation is verified",
    )
    parser.add_argument(
        "--attempt-id",
        default=None,
        help="correlate this receipt with a caller's attempt identifier",
    )
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    project_dir = Path(args.project_dir).resolve()
    program_path = args.program if args.program.startswith("/") else "/" + args.program
    attempt_id = args.attempt_id or uuid.uuid4().hex
    record: dict = {
        "schema": RECEIPT_SCHEMA,
        "tool": "tools/ghidra/ghidra_program_report.py",
        "attempt": {"id": attempt_id, "started_utc": _utc_now()},
        "python": {
            "executable": sys.executable,
            "version": platform.python_version(),
        },
        "requested": {
            "project": args.project,
            "project_dir": str(project_dir),
            "program_path": program_path,
            "modes": {
                "summary": args.summary,
                "functions": args.functions,
                "symbols": args.symbols,
                "xrefs": args.xrefs,
                "disassemble": args.disassemble,
                "pcode": args.pcode,
                "decompile": args.decompile,
                "annotate": bool(args.annotate),
                "verify_annotation": args.verify_annotation,
            },
        },
        "outcome": "operation_failed",
    }
    record["project"] = {"name": args.project, "dir": str(project_dir)}

    problems = _validate(args)
    if problems:
        record["errors"] = problems
        record["outcome"] = "invalid_request"
        publish_json(args.output, record)
        sys.stderr.write("\n".join(problems) + "\n")
        return EXIT_USAGE

    # The annotation to verify is resolved from the annotate receipt before any
    # JVM starts, so a receipt for another attempt, project or program is a
    # request error rather than an inconclusive run.
    expectation = None
    if args.verify_annotation:
        expectation, receipt_problems = _annotation_expectations(
            args.annotation_receipt, args.project, project_dir, program_path
        )
        if receipt_problems:
            record["outcome"] = "invalid_request"
            record["errors"] = receipt_problems
            publish_json(args.output, record)
            sys.stderr.write("\n".join(receipt_problems) + "\n")
            return EXIT_USAGE
        record["annotation_expectation"] = expectation

    project_file = project_dir / f"{args.project}.gpr"
    if not project_file.exists():
        record["outcome"] = "project_missing"
        record["error"] = (
            f"{project_file} does not exist; this tool never creates a project"
        )
        publish_json(args.output, record)
        return EXIT_NOT_FOUND

    try:
        import pyghidra  # noqa: PLC0415
    except ImportError as exc:
        record["outcome"] = "open_failed"
        record["error"] = f"PyGhidra is not importable: {exc}"
        publish_json(args.output, record)
        return EXIT_OPEN_FAILED

    pyghidra.start()
    from java.lang import System as JavaSystem  # noqa: PLC0415

    record["toolchain"] = {
        "requested": {
            "ghidra_install_dir": os.environ.get("GHIDRA_INSTALL_DIR"),
            "python": sys.executable,
        },
        "resolved": {
            "application_properties": _application_properties(),
            "pyghidra": getattr(pyghidra, "__version__", None),
            "java_runtime": str(JavaSystem.getProperty("java.runtime.version")),
            "java_vm": str(JavaSystem.getProperty("java.vm.name")),
        },
    }

    try:
        if args.annotate:
            record["annotation"] = _annotate(
                project_dir, args.project, program_path, args.annotate, attempt_id
            )
            record["outcome"] = (
                "succeeded"
                if record["annotation"]["persisted"]
                else "not_persisted"
            )
        elif args.verify_annotation:
            record["annotation"] = _verify_annotation(
                project_dir, args.project, program_path, expectation
            )
            record["outcome"] = (
                "succeeded" if record["annotation"]["persisted"] else "not_persisted"
            )
        else:
            context, project = _open_readonly(
                project_dir, args.project, program_path
            )
            try:
                with context as program:
                    if args.summary:
                        record["summary"] = _summary(program)
                    if args.functions:
                        record["functions"] = _functions(program, args.limit)
                    if args.symbols:
                        record["symbols"] = _symbols(program, args.limit)
                    if args.xrefs:
                        record["xrefs"] = _xrefs(program, args.xrefs)
                    if args.disassemble:
                        record["disassembly"] = _disassemble(
                            program, args.disassemble, args.max_instructions
                        )
                    if args.pcode:
                        record["pcode"] = _pcode(
                            program, args.pcode, args.max_instructions
                        )
                    if args.decompile:
                        record["decompile"] = _decompile(
                            program, args.decompile, args.text_output
                        )
            finally:
                try:
                    project.close()
                    record["closed"] = True
                except Exception as exc:  # noqa: BLE001
                    record["closed"] = False
                    record["close_error"] = f"{type(exc).__name__}: {exc}"
            record["outcome"] = "succeeded"
    except FileNotFoundError as exc:
        record["outcome"] = "program_missing"
        record["error"] = str(exc)
        publish_json(args.output, record)
        return EXIT_NOT_FOUND
    except Exception as exc:  # noqa: BLE001 - a failed read is a result
        record["outcome"] = "operation_failed"
        record["error"] = f"{type(exc).__name__}: {exc}"
        publish_json(args.output, record)
        return EXIT_OPERATION_FAILED

    publish_json(args.output, record)
    if record["outcome"] == "succeeded":
        return EXIT_OK
    if record["outcome"] == "not_persisted":
        return EXIT_NOT_PERSISTED
    return EXIT_OPERATION_FAILED


if __name__ == "__main__":
    raise SystemExit(main())
