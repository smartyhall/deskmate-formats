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
one transaction, saves, and reports the result. ``--verify-annotation`` is a
separate invocation that reopens the project and reads them back, because a
reopen inside the writing JVM proves nothing about persistence.

Receipt rules (see docs/research/ghidra-dos-import-receipts.md):

* Every invocation is an *attempt* with a unique identifier, and the receipt
  names the project, the program and the toolchain it actually used.
* A missing project is a failure. This tool never creates one.
* An annotation that was committed but not saved is reported as unsaved, not
  as persisted.
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

ANNOTATION_PLATE = "campaign probe: %s"
ANNOTATION_LABEL = "probe_label"

RECEIPT_SCHEMA = "ghidra-program-report/2"

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


def _annotate(project_dir: Path, name: str, program_path: str, text: str) -> dict:
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
    record: dict = {
        "program": program_path,
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
            listing = program.getListing()
            transaction = program.startTransaction("campaign annotation probe")
            committed = False
            try:
                listing.setComment(start, CommentType.PLATE, text)
                program.getBookmarkManager().setBookmark(
                    start, "Note", "campaign-probe", text
                )
                program.getSymbolTable().createLabel(
                    start, ANNOTATION_LABEL, SourceType.USER_DEFINED
                )
                committed = True
            finally:
                program.endTransaction(transaction, committed)
            record["committed"] = committed
            record["address"] = str(start)
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


def _verify_annotation(project_dir: Path, name: str, program_path: str) -> dict:
    from ghidra.program.model.listing import CommentType  # noqa: PLC0415

    context, project = _open_readonly(project_dir, name, program_path)
    try:
        with context as program:
            start = program.getMinAddress()
            plate = program.getListing().getComment(CommentType.PLATE, start)
            bookmarks = [
                {"type": str(b.getTypeString()), "category": str(b.getCategory()),
                 "comment": str(b.getComment())}
                for b in program.getBookmarkManager().getBookmarks(start)
            ]
            symbols = [s.getName() for s in program.getSymbolTable().getSymbols(start)]
    finally:
        project.close()
    return {
        "address": str(start),
        "plate_comment": plate,
        "bookmarks": bookmarks,
        "symbols": symbols,
        "persisted": bool(plate) and ANNOTATION_LABEL in symbols,
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
                project_dir, args.project, program_path, args.annotate
            )
            record["outcome"] = (
                "succeeded"
                if record["annotation"]["persisted"]
                else "not_persisted"
            )
        elif args.verify_annotation:
            record["annotation"] = _verify_annotation(
                project_dir, args.project, program_path
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
