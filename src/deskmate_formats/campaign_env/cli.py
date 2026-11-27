"""Command line for campaign environments: inventory, provision, preflight.

The exit status is the point of the tool: ``preflight`` returns 0 only for a
qualified identity, 1 for a definite mismatch, and 2 for anything it could not
establish.  A caller that treats a non-zero status as a hard stop cannot
accidentally report an unattributed measurement.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import environment, identity, inventory, launch, preflight as preflight_module, probe, receipts


def _emit(document: object, *, output: "str | None" = None, public: bool = False,
          roots: "tuple[str, ...]" = ()) -> dict[str, object] | None:
    written = None
    if output:
        written = receipts.write(output, document)
    if public and isinstance(document, dict):
        print(json.dumps(receipts.public(document, roots=roots), indent=2, sort_keys=True))
    else:
        print(json.dumps(document, indent=2, sort_keys=True))
    return written


def _inventory(arguments: argparse.Namespace) -> int:
    record = inventory.inventory(
        arguments.checkout,
        extra_interpreters=tuple(arguments.interpreter or ()),
        environment_roots=tuple(arguments.environment_root),
    )
    _emit(record, output=arguments.out, public=arguments.public)
    return 0


def _provision(arguments: argparse.Namespace) -> int:
    try:
        record = environment.provision(
            arguments.checkout,
            arguments.campaign,
            root=arguments.root,
            python=arguments.python,
            replace=arguments.replace,
            package=arguments.package,
            allow_build_isolation=not arguments.no_build_isolation,
        )
    except environment.CampaignEnvironmentError as error:
        print(json.dumps({"campaign": arguments.campaign, "verdict": "failed", "reason": str(error)}))
        return 1
    _emit(record, output=arguments.out, public=arguments.public)
    return 0 if record["verdict"] == "qualified" else 1


def _preflight(arguments: argparse.Namespace) -> int:
    record = preflight_module.preflight(
        arguments.checkout,
        campaign=arguments.campaign,
        root=arguments.root,
        interpreter=arguments.interpreter,
        package=arguments.package,
    )
    _emit(record, output=arguments.out, public=arguments.public,
          roots=(str(Path(arguments.checkout).resolve()),))
    return preflight_module.exit_code(record["verdict"])


def _probe(arguments: argparse.Namespace) -> int:
    document = probe.report()
    if arguments.public:
        document = receipts.public(document, roots=(str(Path.cwd()),))
    print(json.dumps(document, indent=2, sort_keys=True))
    return 0


def _identity(arguments: argparse.Namespace) -> int:
    document = {
        "source": identity.source_identity(arguments.checkout),
        "package": identity.import_identity(),
        "interpreter": identity.interpreter_identity(arguments.interpreter),
    }
    _emit(document, output=arguments.out, public=arguments.public,
          roots=(str(Path(arguments.checkout).resolve()),))
    return 0


def _launch(arguments: argparse.Namespace) -> int:
    try:
        argv = launch.isolated_argv(arguments.interpreter, arguments.module,
                                    arguments=tuple(arguments.argument))
    except launch.LaunchError as error:
        print(json.dumps({"error": str(error)}))
        return 2
    if arguments.dry_run:
        print(json.dumps({"argv": argv}))
        return 0
    receipt = launch.run(argv, timeout=arguments.timeout)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["exit_status"] == 0 else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="deskmate-campaign-env", description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    def add_common(subparser: argparse.ArgumentParser, *, checkout: bool = True) -> None:
        if checkout:
            subparser.add_argument("--checkout", default=".", type=Path,
                                   help="campaign checkout to describe (default: current directory)")
        subparser.add_argument("--out", type=Path, help="write the full private receipt here")
        subparser.add_argument("--public", action="store_true",
                               help="print the redacted projection instead of the full receipt")

    described = subcommands.add_parser("inventory", help="read-only host and launch-site inventory")
    add_common(described)
    described.add_argument("--interpreter", action="append",
                           help="additional interpreter to describe (repeatable)")
    described.add_argument("--environment-root", action="append", default=[],
                           help="root that may contain virtual environments (repeatable)")
    described.set_defaults(handler=_inventory)

    provisioned = subcommands.add_parser("provision", help="create and populate a campaign environment")
    add_common(provisioned)
    provisioned.add_argument("--campaign", required=True)
    provisioned.add_argument("--root", type=Path, help="campaign environment root")
    provisioned.add_argument("--python", type=Path, help="bootstrap interpreter (must already have pip)")
    provisioned.add_argument("--package", default=identity.PACKAGE,
                             help="distribution package installed from the checkout")
    provisioned.add_argument("--replace", action="store_true",
                             help="rebuild an existing campaign environment")
    provisioned.add_argument("--no-build-isolation", action="store_true",
                             help="refuse the network-capable build-isolation fallback")
    provisioned.set_defaults(handler=_provision)

    checked = subcommands.add_parser("preflight", help="prove parent, child and checkout identity")
    add_common(checked)
    checked.add_argument("--campaign", required=True)
    checked.add_argument("--root", type=Path, help="campaign environment root")
    checked.add_argument("--interpreter", type=Path,
                         help="interpreter that is running this parent (default: this process)")
    checked.add_argument("--package", default=identity.PACKAGE,
                         help="distribution package whose identity is proven")
    checked.set_defaults(handler=_preflight)

    child = subcommands.add_parser("probe", help="report this child's own resolution")
    child.add_argument("--public", action="store_true")
    child.set_defaults(handler=_probe)

    described_identity = subcommands.add_parser("identity", help="source, package and interpreter identity")
    add_common(described_identity)
    described_identity.add_argument("--interpreter", type=Path)
    described_identity.set_defaults(handler=_identity)

    launched = subcommands.add_parser("launch", help="run an isolated child with an explicit interpreter")
    launched.add_argument("--interpreter", required=True, type=Path)
    launched.add_argument("--module", required=True)
    launched.add_argument("--argument", action="append", default=[])
    launched.add_argument("--timeout", type=int, default=600)
    launched.add_argument("--dry-run", action="store_true")
    launched.set_defaults(handler=_launch)
    return parser


def main(argv: "list[str] | None" = None) -> int:
    arguments = build_parser().parse_args(argv)
    return int(arguments.handler(arguments))


if __name__ == "__main__":
    raise SystemExit(main())
