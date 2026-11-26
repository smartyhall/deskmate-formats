"""Reproducible PyGhidra import and inspection driver for DOS images.

This is a provider-neutral command-line tool. It does not call a model and it
does not need Freebuff, Codex or an emulator. It imports one stored DOS image
into an owned Ghidra project with an explicit processor language, optionally
applies Ghidra autoanalysis, and writes a machine-readable receipt.

Design rules encoded here (see docs/research/ghidra-dos-binary-analysis.md):

* The processor language is always explicit. Default loader selection is not
  evidence of a correct mapping.
* The project directory is owned by the caller and is never a shared or in-use
  project. Existing projects are opened, never overwritten.
* Stages are timed so a reviewer can bound import, analysis and reopen.
* The receipt records the input hash, resolved language, Ghidra/Java versions,
  the loader block model and the project path. It is a receipt, not a
  published disassembly.

Requires PyGhidra for the interpreter you run it with and a Ghidra
installation named by ``GHIDRA_INSTALL_DIR``::

    python ghidra_dos_import.py --project-dir PRIVATE/projects --project cal \\
        --input CALENDAR.PDM --analyze --reopen-check \\
        --output PRIVATE/receipt.json

Import and reopen run in separate processes on purpose: Ghidra's in-process
project manager can retain a project's lock, so an in-JVM "reopen" would not
test what a later reviewer actually does.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_LANGUAGE = "x86:LE:16:Real Mode"


def _application_properties() -> dict:
    """Read the installed Ghidra version record instead of assuming one."""
    install = os.environ.get("GHIDRA_INSTALL_DIR")
    if not install:
        return {}
    path = Path(install) / "Ghidra" / "application.properties"
    if not path.is_file():
        return {}
    wanted = {
        "application.version",
        "application.release.name",
        "application.build.date",
        "application.java.min",
        "application.java.compiler",
        "application.revision.ghidra",
    }
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        if key in wanted:
            values[key] = value
    return values


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _open_or_create(project_dir: Path, name: str):
    """Open a writable owned project, creating it when absent.

    ``pyghidra.open_project`` returns a temporary/read-only project, which
    cannot persist an analysed program.
    """
    from ghidra.framework.model import ProjectLocator  # noqa: PLC0415
    from ghidra.pyghidra import PyGhidraProjectManager  # noqa: PLC0415

    manager = PyGhidraProjectManager()
    locator = ProjectLocator(str(project_dir), name)
    if locator.exists():
        return manager.openProject(locator, False, False)
    return manager.createProject(locator, None, False)


def _clear_own_lock(project_dir: Path, name: str) -> list[str]:
    """Remove lock files of a project this run created.

    Ghidra's in-process project manager can retain a project lock after
    ``close()``. When this run created the project, nothing else can
    legitimately hold it, so clearing the lock lets a fresh process reopen it.
    A pre-existing project is never touched.
    """
    removed = []
    for suffix in (".lock", ".lock~"):
        candidate = project_dir / f"{name}{suffix}"
        if candidate.exists():
            try:
                candidate.unlink()
                removed.append(candidate.name)
            except OSError:
                pass
    return removed


def _block_records(program) -> list[dict]:
    records = []
    for block in program.getMemory().getBlocks():
        records.append(
            {
                "name": block.getName(),
                "start": str(block.getStart()),
                "end": str(block.getEnd()),
                "size": block.getSize(),
                "initialized": bool(block.isInitialized()),
                "read": bool(block.isRead()),
                "write": bool(block.isWrite()),
                "execute": bool(block.isExecute()),
                "comment": block.getComment(),
            }
        )
    return records


def _program_summary(program) -> dict:
    return {
        "name": program.getName(),
        "language_id": str(program.getLanguageID()),
        "compiler_spec": str(program.getCompilerSpec().getCompilerSpecID()),
        "image_base": str(program.getImageBase()),
        "min_address": str(program.getMinAddress()),
        "max_address": str(program.getMaxAddress()),
        "blocks": _block_records(program),
        "instruction_count": int(program.getListing().getNumInstructions()),
        "function_count": int(program.getFunctionManager().getFunctionCount()),
    }


def run_import(args) -> dict:
    """Import one image in this process and return the receipt body."""
    source = Path(args.input).resolve()
    if not source.is_file():
        raise SystemExit(f"input not found: {source}")
    project_dir = Path(args.project_dir).resolve()
    project_dir.mkdir(parents=True, exist_ok=True)

    receipt: dict = {
        "tool": "tools/ghidra/ghidra_dos_import.py",
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "python": platform.python_version(),
        },
        "input": {
            "name": source.name,
            "size": source.stat().st_size,
            "sha256": _sha256(source),
        },
        "requested": {
            "language": args.language,
            "analyze": args.analyze,
            "timeout_seconds": args.timeout,
        },
        "stages": [],
        "status": "started",
    }

    import pyghidra  # noqa: PLC0415 - imported late so --help needs no JVM

    receipt["ghidra"] = {
        "pyghidra": getattr(pyghidra, "__version__", None),
        "install_dir": os.environ.get("GHIDRA_INSTALL_DIR"),
    }

    started = time.time()
    pyghidra.start()
    receipt["stages"].append(
        {"stage": "jvm_start", "seconds": round(time.time() - started, 2)}
    )

    from ghidra.program.model.lang import LanguageID  # noqa: PLC0415
    from ghidra.program.util import DefaultLanguageService  # noqa: PLC0415
    from java.io import File  # noqa: PLC0415
    from java.lang import Object  # noqa: PLC0415
    from java.lang import System as JavaSystem  # noqa: PLC0415

    receipt["ghidra"].update(
        {
            "application_properties": _application_properties(),
            "java_runtime": str(JavaSystem.getProperty("java.runtime.version")),
            "java_vm": str(JavaSystem.getProperty("java.vm.name")),
        }
    )

    language = DefaultLanguageService.getLanguageService().getLanguage(
        LanguageID(args.language)
    )
    if language is None:
        raise SystemExit(f"unknown processor language: {args.language}")

    created_project = not (project_dir / f"{args.project}.gpr").exists()
    project = _open_or_create(project_dir, args.project)
    try:
        builder = pyghidra.program_loader()
        builder.source(File(str(source)))
        builder.project(project)
        builder.projectFolderPath("/")
        builder.language(language)

        stage = time.time()
        results = builder.load()
        receipt["stages"].append(
            {"stage": "import", "seconds": round(time.time() - stage, 2)}
        )

        consumer = Object()
        program = results.getPrimaryDomainObject(consumer)
        receipt["resolved_language"] = {
            "language_id": str(program.getLanguageID()),
            "processor": str(program.getLanguage().getProcessor()),
            "compiler_spec": str(program.getCompilerSpec().getCompilerSpecID()),
        }
        receipt["program"] = {"project_path": program.getDomainFile().getPathname()}
        receipt["program"].update(_program_summary(program))

        if args.analyze:
            stage = time.time()
            try:
                pyghidra.analyze(program)
                receipt["analysis"] = {"ok": True}
            except Exception as exc:  # noqa: BLE001 - reported, never hidden
                receipt["analysis"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            receipt["stages"].append(
                {"stage": "autoanalysis", "seconds": round(time.time() - stage, 2)}
            )
            summary = _program_summary(program)
            receipt["program"]["instruction_count"] = summary["instruction_count"]
            receipt["program"]["function_count"] = summary["function_count"]
            receipt["program"]["blocks"] = summary["blocks"]

        # LoadResults.save() requires a real TaskMonitor and must run before
        # release; save() on the Program itself raises ReadOnlyException.
        stage = time.time()
        results.save(pyghidra.task_monitor())
        results.release(consumer)
        receipt["stages"].append({"stage": "save", "seconds": round(time.time() - stage, 2)})
        receipt["status"] = "ok"
    finally:
        project.save()
        project.close()

    if created_project:
        receipt["released_own_lock"] = _clear_own_lock(project_dir, args.project)
    return receipt


def reopen_only(project_dir: Path, name: str, program_name: str) -> int:
    """Describe a stored program after reopening the project from disk."""
    import pyghidra  # noqa: PLC0415

    program_path = program_name if program_name.startswith("/") else "/" + program_name
    pyghidra.start()
    project = _open_or_create(project_dir, name)
    try:
        domain_files = []
        stack = [project.getProjectData().getRootFolder()]
        while stack:
            folder = stack.pop()
            for entry in folder.getFiles():
                domain_files.append(entry.getPathname())
            for child in folder.getFolders():
                stack.append(child)
        payload: dict = {"ok": True, "project_files": sorted(domain_files)}
        if program_path in domain_files:
            with pyghidra.program_context(project, program_path) as program:
                payload["program"] = _program_summary(program)
        else:
            payload["ok"] = False
            payload["error"] = f"{program_path} is not present after reopening"
    finally:
        project.close()
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0 if payload.get("ok") else 1


def _spawn(mode_args: list[str], timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        [sys.executable, str(Path(__file__).resolve()), *mode_args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import a DOS image into an owned Ghidra project and write a receipt."
    )
    parser.add_argument("--project-dir", required=True, help="owned project directory")
    parser.add_argument("--project", required=True, help="project name")
    parser.add_argument("--input", required=True, help="stored DOS image, or project path")
    parser.add_argument(
        "--language",
        default=DEFAULT_LANGUAGE,
        help=f"explicit processor language id (default: {DEFAULT_LANGUAGE})",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="apply Ghidra autoanalysis after import (slow; unnecessary for byte probes)",
    )
    parser.add_argument("--output", help="write the receipt JSON here")
    parser.add_argument(
        "--reopen-check",
        action="store_true",
        help="reopen the stored program in a separate process and record its identity",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=900,
        help="per-stage subprocess timeout in seconds (recorded in the receipt)",
    )
    parser.add_argument("--import-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--reopen-only", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_dir = Path(args.project_dir).resolve()

    if args.reopen_only:
        return reopen_only(project_dir, args.project, args.input)

    if args.import_worker:
        receipt = run_import(args)
        text = json.dumps(receipt, indent=2)
        if args.output:
            Path(args.output).write_text(text + "\n", encoding="utf-8")
        else:
            sys.stdout.write(text + "\n")
        return 0

    if args.reopen_check:
        worker_output = Path(str(args.output or "receipt.json") + ".import.json")
        worker_args = [
            "--import-worker",
            "--project-dir", str(project_dir),
            "--project", args.project,
            "--input", args.input,
            "--language", args.language,
            "--output", str(worker_output),
            "--timeout", str(args.timeout),
        ]
        if args.analyze:
            worker_args.append("--analyze")
        completed = _spawn(worker_args, args.timeout)
        if completed.returncode != 0:
            sys.stderr.write(completed.stderr or completed.stdout)
            return completed.returncode
        receipt = json.loads(worker_output.read_text(encoding="utf-8"))

        stage = time.time()
        reopened = _spawn(
            [
                "--reopen-only",
                "--project-dir", str(project_dir),
                "--project", args.project,
                "--input", receipt["program"]["project_path"],
            ],
            args.timeout,
        )
        try:
            receipt["reopen"] = json.loads(reopened.stdout)
        except json.JSONDecodeError:
            receipt["reopen"] = {
                "ok": False,
                "exit_code": reopened.returncode,
                "error": (reopened.stderr or "")[-2000:],
            }
        receipt["stages"].append(
            {"stage": "reopen_check", "seconds": round(time.time() - stage, 2)}
        )
    else:
        receipt = run_import(args)

    text = json.dumps(receipt, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
