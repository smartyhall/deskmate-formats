"""Compare one Ghidra build's reading of the x86 segment-register forms.

For each requested offset the probe records what a build reports through four
independent surfaces:

* **listing text** — what a human transcribes;
* **operand indexing** — what a script sees at operand 0 and 1;
* **p-code** — the semantics the decompiler consumes;
* **assembly round-trip** — whether the listing text assembles back to the
  original bytes.

The round-trip is the important one. A build that prints ``MOV AX,DS`` for
``8E D8`` will assemble that text to ``8C D8``, so a listing a human would
trust does not survive its own assembler. The probe also assembles an explicit
list of statements, so a direction that cannot be written can be distinguished
from one that is merely printed wrongly.

Run it once per installation, with ``GHIDRA_INSTALL_DIR`` pointing at that
installation, and diff the two JSON files.

Example::

    python tools/ghidra/ghidra_x86_segment_compare.py --payload PAYLOAD.bin \\
        --project-dir PRIVATE/projects-v122 --project segcmp \\
        --language "x86:LE:16:Real Mode" \\
        --offsets 0,2,4,6,8,10,12,14,16,20,24,27,30,32 \\
        --assemble "MOV DS,AX;MOV ES,AX;MOV AX,DS;MOV ES,DI" \\
        --output PRIVATE/exports/segcmp-12.2.json
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
    wanted = {"application.version", "application.build.date",
              "application.revision.ghidra", "application.java.min"}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            if key in wanted:
                values[key] = value
    return values


def _object_name(obj) -> dict:
    from ghidra.program.model.address import Address  # noqa: PLC0415
    from ghidra.program.model.lang import Register  # noqa: PLC0415
    from ghidra.program.model.scalar import Scalar  # noqa: PLC0415

    if isinstance(obj, Register):
        return {"kind": "register", "name": obj.getName()}
    if isinstance(obj, Address):
        return {"kind": "address", "value": str(obj)}
    if isinstance(obj, Scalar):
        return {"kind": "scalar", "value": obj.getValue(), "signed": obj.isSigned()}
    return {"kind": type(obj).__name__}


def _operands(program, instruction) -> list[dict]:
    from ghidra.program.model.lang import OperandType  # noqa: PLC0415

    rows = []
    for index in range(instruction.getNumOperands()):
        try:
            type_name = OperandType.toString(instruction.getOperandType(index))
        except Exception:  # noqa: BLE001
            type_name = None
        rows.append(
            {
                "index": index,
                "representation": instruction.getDefaultOperandRepresentation(index),
                "objects": [_object_name(o) for o in instruction.getOpObjects(index)],
                "type": type_name,
            }
        )
    return rows


def _pcode(instruction) -> list[dict]:
    rows = []
    for op in instruction.getPcode():
        output = op.getOutput()
        rows.append(
            {
                "opcode": str(op.getMnemonic()),
                "out_register": output.isRegister() if output is not None else False,
                "out_size": output.getSize() if output is not None else None,
                "inputs": [str(v) for v in op.getInputs()],
            }
        )
    return rows


def _assembler_for(program):
    """Return an assembler bound to this program, or None.

    ``Assemblers.getAssembler(Language)`` alone yields a sleigh assembler whose
    program is unset; assembling then fails with a null program context.
    """
    from ghidra.app.plugin.assembler import AssemblySelector, Assemblers  # noqa: PLC0415

    # Only the Program-taking overload binds the program context; the
    # Language-only overload returns an assembler whose program is unset, and
    # assembling then fails when it needs the program context.
    try:
        return Assemblers.getAssembler(program)
    except Exception:  # noqa: BLE001
        try:
            return Assemblers.getAssembler(program, AssemblySelector())
        except Exception:  # noqa: BLE001
            return None


def _assemble(assembler, address, text: str) -> dict:
    # assembleLine returns the encoded bytes without patching the program. The
    # block-returning assemble() overload changed shape between 12.1 and 12.2
    # (InstructionBlock with getBytes, then an InstructionRecordIterator that
    # writes), so the line form is the portable read-only call.
    try:
        raw = assembler.assembleLine(address, text)
        data = bytes(raw)
        return {
            "text": text,
            "assembled": True,
            "bytes": data.hex(),
            "length": len(data),
        }
    except Exception as exc:  # noqa: BLE001 - a refusal is a result
        return {
            "text": text,
            "assembled": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", required=True)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--language", default=DEFAULT_LANGUAGE)
    parser.add_argument("--offsets", required=True)
    parser.add_argument("--assemble", default="")
    parser.add_argument("--base", type=lambda s: int(s, 0), default=0)
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    offsets = [int(value, 0) for value in args.offsets.split(",") if value.strip()]
    statements = [s.strip() for s in args.assemble.split(";") if s.strip()]
    payload = Path(args.payload).resolve()
    project_dir = Path(args.project_dir).resolve()
    project_dir.mkdir(parents=True, exist_ok=True)

    import pyghidra  # noqa: PLC0415

    pyghidra.start()
    from ghidra.app.cmd.disassemble import DisassembleCommand  # noqa: PLC0415
    from ghidra.app.plugin.assembler import Assemblers  # noqa: PLC0415
    from ghidra.framework.model import ProjectLocator  # noqa: PLC0415
    from ghidra.program.model.address import AddressSet  # noqa: PLC0415
    from ghidra.program.model.lang import LanguageID  # noqa: PLC0415
    from ghidra.program.util import DefaultLanguageService  # noqa: PLC0415
    from ghidra.pyghidra import PyGhidraProjectManager  # noqa: PLC0415
    from java.io import File  # noqa: PLC0415
    from java.lang import Object  # noqa: PLC0415

    language = DefaultLanguageService.getLanguageService().getLanguage(
        LanguageID(args.language)
    )
    if language is None:
        raise SystemExit(f"unknown language: {args.language}")

    project = PyGhidraProjectManager().createProject(
        ProjectLocator(str(project_dir), args.project), None, False
    )
    result: dict = {
        "schema": "ghidra-x86-segment-compare/1",
        "tool": "tools/ghidra/ghidra_x86_segment_compare.py",
        "payload": {"name": payload.name, "size": payload.stat().st_size},
        "language_requested": args.language,
        "ghidra": {
            "install_dir": os.environ.get("GHIDRA_INSTALL_DIR"),
            "application_properties": _application_properties(),
            "java_home": os.environ.get("JAVA_HOME"),
        },
        "instructions": [],
        "assembly": [],
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
        space = program.getAddressFactory().getDefaultAddressSpace()

        for offset in offsets:
            address = space.getAddress(args.base + offset)
            instruction = program.getListing().getInstructionAt(address)
            if instruction is None:
                transaction = program.startTransaction("segment compare decode")
                try:
                    DisassembleCommand(
                        address, AddressSet(address, address), True
                    ).applyTo(program, pyghidra.task_monitor())
                finally:
                    program.endTransaction(transaction, True)
                instruction = program.getListing().getInstructionAt(address)
            if instruction is None:
                result["instructions"].append(
                    {"offset": offset, "address": str(address), "decoded": False}
                )
                continue
            original = bytes(instruction.getBytes())
            row = {
                "offset": offset,
                "address": str(instruction.getAddress()),
                "decoded": True,
                "bytes": original.hex(),
                "length": instruction.getLength(),
                "text": instruction.toString(),
                "mnemonic": instruction.getMnemonicString(),
                "operand_count": instruction.getNumOperands(),
                "operands": _operands(program, instruction),
                "pcode": _pcode(instruction),
            }
            assembler = _assembler_for(program)
            if assembler is not None and str(
                instruction.getMnemonicString()
            ).upper() == "MOV":
                # Assembly may consult program context and, on some builds, try
                # to patch; a discarded transaction keeps the probe read-only.
                transaction = program.startTransaction("segment compare assemble")
                try:
                    assembled = _assemble(assembler, instruction.getAddress(),
                                          instruction.toString())
                finally:
                    program.endTransaction(transaction, False)
                row["roundtrip"] = assembled
                row["roundtrip_matches_bytes"] = (
                    assembled.get("bytes") == original.hex()
                    if assembled.get("assembled")
                    else None
                )
            result["instructions"].append(row)

        if statements:
            assembler = _assembler_for(program)
            # Assemble inside mapped memory: an unmapped scratch address makes
            # the assembler fail with MemoryAccessException before it can encode.
            scratch = program.getMinAddress()
            if assembler is None:
                result["assembly"] = [
                    {"text": text, "assembled": False,
                     "error": "no assembler for this language"}
                    for text in statements
                ]
            else:
                transaction = program.startTransaction("segment compare assemble list")
                try:
                    result["assembly"] = [
                        _assemble(assembler, scratch, text) for text in statements
                    ]
                finally:
                    program.endTransaction(transaction, False)
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
