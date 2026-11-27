"""Inspect the listing text and p-code of x86 segment-register MOV forms.

The probe imports a small payload into a disposable owned project, disassembles
each requested offset, and reports two independent things:

* the **listing text** Ghidra prints for the instruction, which is a display
  template from the processor language; and
* the **p-code** it generates, which is the semantics the decompiler consumes.

Keeping those separate is the point. A listing can read ``MOV AX,DS`` while
the p-code writes ``DS``; only the p-code and the original bytes say what the
instruction means. Reported text is Ghidra's interpretation, not program
structure.

Example::

    python tools/ghidra/segment_forms_probe.py --payload PAYLOAD.bin \\
        --project-dir PRIVATE/projects --project segforms \\
        --offsets 0,2,4,6,8,10,12,14,16,20,24,27,30,32 \\
        --output PRIVATE/exports/segforms.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DEFAULT_LANGUAGE = "x86:LE:16:Real Mode"


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


def _varnode(program, varnode) -> dict:
    record = {"size": varnode.getSize()}
    if varnode.isRegister():
        register = program.getRegister(varnode)
        record["kind"] = "register"
        record["name"] = register.getName() if register is not None else None
    elif varnode.isConstant():
        record["kind"] = "constant"
        record["value"] = varnode.getOffset()
    elif varnode.isAddress():
        record["kind"] = "address"
        record["value"] = str(varnode.getAddress())
    elif varnode.isUnique():
        record["kind"] = "unique"
    else:
        record["kind"] = "other"
    return record


def _pcode(program, instruction) -> list[dict]:
    ops = []
    for op in instruction.getPcode():
        output = op.getOutput()  # a single Varnode or None, unlike getInputs()
        ops.append(
            {
                "opcode": str(op.getMnemonic()),
                "output": [] if output is None else [_varnode(program, output)],
                "inputs": [_varnode(program, v) for v in op.getInputs()],
            }
        )
    return ops


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", required=True)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--language", default=DEFAULT_LANGUAGE)
    parser.add_argument("--offsets", required=True, help="comma-separated offsets")
    parser.add_argument("--base", type=lambda s: int(s, 0), default=0)
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    offsets = [int(value, 0) for value in args.offsets.split(",")]
    payload = Path(args.payload).resolve()
    project_dir = Path(args.project_dir).resolve()
    project_dir.mkdir(parents=True, exist_ok=True)

    import pyghidra  # noqa: PLC0415

    pyghidra.start()
    from ghidra.app.cmd.disassemble import DisassembleCommand  # noqa: PLC0415
    from ghidra.program.model.address import AddressSet  # noqa: PLC0415
    from ghidra.program.model.lang import LanguageID  # noqa: PLC0415
    from ghidra.program.util import DefaultLanguageService  # noqa: PLC0415
    from java.io import File  # noqa: PLC0415
    from java.lang import Object  # noqa: PLC0415

    language = DefaultLanguageService.getLanguageService().getLanguage(
        LanguageID(args.language)
    )
    from ghidra.framework.model import ProjectLocator  # noqa: PLC0415
    from ghidra.pyghidra import PyGhidraProjectManager  # noqa: PLC0415

    project = PyGhidraProjectManager().createProject(
        ProjectLocator(str(project_dir), args.project), None, False
    )

    result: dict = {
        "schema": "ghidra-segment-forms-probe/1",
        "tool": "tools/ghidra/segment_forms_probe.py",
        "payload": {"name": payload.name, "size": payload.stat().st_size},
        "language_requested": args.language,
        "ghidra": {"install_dir": os.environ.get("GHIDRA_INSTALL_DIR"),
                   "application_properties": _application_properties()},
        "instructions": [],
    }
    try:
        builder = pyghidra.program_loader()
        builder.source(File(str(payload)))
        builder.project(project)
        builder.projectFolderPath("/")
        builder.language(language)
        results = builder.load()
        consumer = Object()
        program = results.getPrimaryDomainObject(consumer)
        result["language_resolved"] = {
            "language_id": str(program.getLanguageID()),
            "compiler_spec": str(program.getCompilerSpec().getCompilerSpecID()),
        }
        pyghidra.analyze(program)

        space = program.getAddressFactory().getDefaultAddressSpace()
        for offset in offsets:
            address = space.getAddress(args.base + offset)
            instruction = program.getListing().getInstructionAt(address)
            if instruction is None:
                transaction = program.startTransaction("disassemble probe")
                try:
                    DisassembleCommand(address, AddressSet(address, address), True).applyTo(
                        program, pyghidra.task_monitor()
                    )
                finally:
                    program.endTransaction(transaction, True)
                instruction = program.getListing().getInstructionAt(address)
            if instruction is None:
                result["instructions"].append(
                    {"offset": offset, "address": str(address), "decoded": False}
                )
                continue
            result["instructions"].append(
                {
                    "offset": offset,
                    "address": str(instruction.getAddress()),
                    "decoded": True,
                    "bytes": bytes(instruction.getBytes()).hex(),
                    "length": instruction.getLength(),
                    "text": instruction.toString(),
                    "mnemonic": instruction.getMnemonicString(),
                    "pcode": _pcode(program, instruction),
                }
            )
        results.save(pyghidra.task_monitor())
        results.release(consumer)
    finally:
        try:
            project.save()
            project.close()
        except Exception:  # noqa: BLE001
            pass

    text = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
