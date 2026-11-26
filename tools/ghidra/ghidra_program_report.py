"""Programmatic inspection of an owned Ghidra program, with bounded output.

Read modes (``--summary``, ``--functions``, ``--xrefs``, ``--decompile``) open
the stored program read-only and report structural facts: counts, sizes,
addresses and reference types. Decompiled source is proprietary content, so it
is never put in the receipt; ``--text-output`` writes it to a private file and
the receipt records only a digest and a line count.

Write mode (``--annotate``) proves that persistent annotations and transactions
work in a project we own: it writes a plate comment, a bookmark and a label in
one transaction, saves, and reports the result. ``--verify-annotation`` is a
separate invocation that reopens the project and reads them back, because a
reopen inside the writing JVM proves nothing about persistence.

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
import sys
from pathlib import Path

ANNOTATION_PLATE = "campaign probe: %s"
ANNOTATION_LABEL = "probe_label"


def _application_properties() -> dict:
    install = os.environ.get("GHIDRA_INSTALL_DIR")
    if not install:
        return {}
    path = Path(install) / "Ghidra" / "application.properties"
    if not path.is_file():
        return {}
    wanted = {"application.version", "application.release.name",
              "application.build.date", "application.revision.ghidra"}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            if key in wanted:
                values[key] = value
    return values


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
    project = manager.openProject(locator, False, False)
    consumer = Object()
    record: dict = {"program": program_path, "committed": False}
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
                program.save("campaign annotation probe", pyghidra.task_monitor())
                record["saved"] = True
        finally:
            program.release(consumer)
    finally:
        project.close()
    return record


def _verify_annotation(project_dir: Path, name: str, program_path: str) -> dict:
    from ghidra.program.model.listing import CommentType  # noqa: PLC0415

    context, project = _open_readonly(project_dir, name, program_path)
    with context as program:
        start = program.getMinAddress()
        plate = program.getListing().getComment(CommentType.PLATE, start)
        bookmarks = [
            {"type": str(b.getTypeString()), "category": str(b.getCategory()),
             "comment": str(b.getComment())}
            for b in program.getBookmarkManager().getBookmarks(start)
        ]
        symbols = [s.getName() for s in program.getSymbolTable().getSymbols(start)]
    project.close()
    return {
        "address": str(start),
        "plate_comment": plate,
        "bookmarks": bookmarks,
        "symbols": symbols,
        "persisted": bool(plate) and ANNOTATION_LABEL in symbols,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--program", required=True, help="project path, e.g. /DESK.EXE")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--functions", action="store_true")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--xrefs", help="address whose references to list")
    parser.add_argument("--decompile", help="function name or address")
    parser.add_argument("--text-output", help="private file for decompiled source")
    parser.add_argument("--annotate", help="plate comment text to persist")
    parser.add_argument("--verify-annotation", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    project_dir = Path(args.project_dir).resolve()
    program_path = args.program if args.program.startswith("/") else "/" + args.program

    import pyghidra  # noqa: PLC0415

    pyghidra.start()
    record: dict = {
        "schema": "ghidra-program-report/1",
        "tool": "tools/ghidra/ghidra_program_report.py",
        "ghidra": {"install_dir": os.environ.get("GHIDRA_INSTALL_DIR"),
                   "application_properties": _application_properties()},
        "program_path": program_path,
    }

    if args.annotate:
        record["annotation"] = _annotate(project_dir, args.project, program_path,
                                         args.annotate)
    elif args.verify_annotation:
        record["annotation"] = _verify_annotation(project_dir, args.project,
                                                  program_path)
    else:
        context, project = _open_readonly(project_dir, args.project, program_path)
        with context as program:
            if args.summary:
                record["summary"] = _summary(program)
            if args.functions:
                record["functions"] = _functions(program, args.limit)
            if args.xrefs:
                record["xrefs"] = _xrefs(program, args.xrefs)
            if args.decompile:
                record["decompile"] = _decompile(program, args.decompile,
                                                 args.text_output)
            record["requested"] = {
                "summary": args.summary, "functions": args.functions,
                "xrefs": args.xrefs, "decompile": args.decompile,
            }
        project.close()

    text = json.dumps(record, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
