"""Provider-neutral Ghidra toolchain discovery, verification and selection.

The lab holds more than one Ghidra release and more than one JDK, and the
historical releases must stay reproducible. This module answers three
questions from evidence on disk rather than from a launcher's presence:

* Which Ghidra installations exist, and what version/build/revision does each
  actually record?
* Which Java runtimes exist, and which major version does each actually
  report?
* Given an optional requirement, which pair is compatible?

Selection precedence, highest first, is reported in every result:

``explicit``
    ``--ghidra-dir`` / ``--java-home``. An explicit but incompatible choice is
    an error: the caller asked for that one, so answering with another would
    hide the problem.
``profile``
    ``--profile FILE`` JSON, the reproducible way to pin a historical
    toolchain for a campaign without changing any global environment.
``environment``
    ``GHIDRA_INSTALL_DIR``, ``GHIDRA_JAVA_HOME`` and ``JAVA_HOME`` of this
    process only. Nothing here writes a global variable.
``ghidra-override``
    ``support/launch.properties`` ``JAVA_HOME_OVERRIDE``, which Ghidra's own
    launcher obeys. Reported and validated rather than assumed.
``discovery``
    Installation directories under the supplied roots. A candidate here must
    prove its version; a directory whose *name* looks newer is not evidence.

Compatibility is established by comparing the JDK's reported major version
with the ``application.java.min`` the Ghidra installation records. A JDK
whose major cannot be determined is rejected, never assumed.

Exit codes::

    0  a complete, compatible selection
    1  no compatible selection (reported candidates explain why)
    2  usage or configuration error

Example::

    python tools/ghidra/ghidra_toolchain.py \\
        --require-ghidra-version 12.2 --java-home 'C:/Tools/jdk-25.0.5.1+2'

    python tools/ghidra/ghidra_toolchain.py --profile ops/tasks/ghidra-1214.json
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCHEMA = "ghidra-toolchain-selection/1"

EXIT_OK = 0
EXIT_NO_SELECTION = 1
EXIT_USAGE = 2

PRECEDENCE = ("explicit", "profile", "environment", "ghidra-override", "discovery")

#: How a discovered JDK is chosen from the compatible ones. ``minimum`` keeps
#: the historical release's own era, which is what reproduces an old receipt;
#: ``newest`` opts into the newest compatible runtime deliberately.
JAVA_STRATEGIES = ("minimum", "newest")

REQUIRED_GHIDRA_FILES = ("Ghidra/application.properties",)
LAUNCHER_NAMES = ("support/analyzeHeadless.bat", "support/analyzeHeadless")

WANTED_PROPERTIES = (
    "application.version",
    "application.release.name",
    "application.build.date",
    "application.java.min",
    "application.java.compiler",
    "application.revision.ghidra",
)

JAVA_VERSION_RE = re.compile(r'version "([^"]+)"')

_JAVA_BIN = "java.exe" if os.name == "nt" else "java"


class ToolchainError(ValueError):
    """Raised for a malformed request or configuration file."""


# --------------------------------------------------------------------------
# identity readers
# --------------------------------------------------------------------------
def parse_properties(path: Path) -> dict:
    """Read the ``key=value`` Ghidra properties file, keeping known keys."""
    values: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return values
    for line in text.splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        if key.strip() in WANTED_PROPERTIES:
            values[key.strip()] = value.strip()
    return values


def major_from_version(text: str | None) -> int | None:
    """Return the JDK major for a version string, or None if unknowable.

    Handles both the modern form (``25.0.5.1+2``) and the legacy form
    (``1.8.0_402``), and refuses strings that carry no leading number instead
    of guessing. A directory name is never used as evidence.
    """
    if not text:
        return None
    parts = str(text).strip().replace("_", ".").split(".")
    try:
        major = int(parts[0])
    except ValueError:
        return None
    if major == 1 and len(parts) > 1:
        try:
            return int(parts[1])
        except ValueError:
            return None
    return major


def _unknown_major(version: str | None) -> int | None:
    """Major for a dotted version where the first component is the major."""
    if not version:
        return None
    head = version.split(".")[0]
    try:
        return int(head)
    except ValueError:
        return None


def read_java_home(home: Path) -> dict:
    """Describe a Java home from its own ``release`` file.

    The release file is authoritative and needs no subprocess. Only when it is
    absent is ``bin/java -version`` consulted, under a timeout, and a failure
    there leaves the version unknown rather than borrowed from the directory
    name.
    """
    record: dict = {
        "home": str(home),
        "exists": home.is_dir(),
        "java_executable": (home / "bin" / _JAVA_BIN).is_file(),
        "version": None,
        "major": None,
        "vendor": None,
        "source": None,
        "error": None,
    }
    if not record["exists"]:
        record["error"] = "directory does not exist"
        return record
    release = home / "release"
    if release.is_file():
        fields = {}
        try:
            for line in release.read_text(encoding="utf-8", errors="replace").splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    fields[key.strip()] = value.strip().strip('"')
        except OSError as exc:
            record["error"] = f"unreadable release file: {exc}"
        record["version"] = fields.get("JAVA_VERSION")
        record["vendor"] = fields.get("IMPLEMENTOR") or fields.get("JAVA_VENDOR")
        record["source"] = "release"
        record["major"] = major_from_version(record["version"])
        if record["major"] is None:
            record["error"] = "release file carries no parseable JAVA_VERSION"
        return record
    executable = home / "bin" / _JAVA_BIN
    if not executable.is_file():
        record["error"] = "no release file and no java executable"
        return record
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            [str(executable), "-version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        record["error"] = f"java -version failed: {type(exc).__name__}"
        return record
    text = (completed.stderr or "") + (completed.stdout or "")
    match = JAVA_VERSION_RE.search(text)
    record["version"] = match.group(1) if match else None
    record["major"] = major_from_version(record["version"])
    record["source"] = "java -version"
    if record["major"] is None:
        record["error"] = "java -version produced no parseable version"
    return record


def read_ghidra_install(directory: Path) -> dict:
    """Describe a Ghidra installation from its own version record.

    A launcher script is necessary but never sufficient: without a parseable
    ``Ghidra/application.properties`` the installation identity is unknown and
    the candidate is rejected.
    """
    record: dict = {
        "install_dir": str(directory),
        "exists": directory.is_dir(),
        "launcher": None,
        "properties": {},
        "version": None,
        "build_date": None,
        "revision": None,
        "java_min": None,
        "error": None,
    }
    if not record["exists"]:
        record["error"] = "directory does not exist"
        return record
    for name in LAUNCHER_NAMES:
        candidate = directory / name
        if candidate.is_file():
            record["launcher"] = str(candidate)
            break
    if record["launcher"] is None:
        record["error"] = "no headless launcher"
        return record
    properties_path = directory / REQUIRED_GHIDRA_FILES[0]
    if not properties_path.is_file():
        record["error"] = "no Ghidra/application.properties, so the version is unproven"
        return record
    properties = parse_properties(properties_path)
    record["properties"] = properties
    record["version"] = properties.get("application.version")
    record["build_date"] = properties.get("application.build.date")
    record["revision"] = properties.get("application.revision.ghidra")
    record["java_min"] = _unknown_major(properties.get("application.java.min"))
    if not record["version"]:
        record["error"] = "application.properties records no application.version"
    return record


def ghidra_java_override(directory: Path) -> str | None:
    """Read ``JAVA_HOME_OVERRIDE`` from the installation's launch properties."""
    path = directory / "support" / "launch.properties"
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("JAVA_HOME_OVERRIDE") and "=" in stripped:
            value = stripped.split("=", 1)[1].strip().strip('"')
            return value or None
    return None


# --------------------------------------------------------------------------
# discovery
# --------------------------------------------------------------------------
def default_search_roots() -> list[Path]:
    roots: list[Path] = []
    if os.name == "nt":
        for name in ("ProgramFiles", "ProgramFiles(x86)"):
            value = os.environ.get(name)
            if value:
                roots.append(Path(value))
        roots.append(Path(r"C:\Tools"))
    else:
        roots.extend([Path("/opt"), Path("/usr/local")])
    return [root for root in roots if root.is_dir()]


def ghidra_root_candidates(root: Path) -> list[Path]:
    """Directories under ``root`` that could hold a Ghidra installation."""
    candidates = []
    if root.is_dir():
        if (root / "Ghidra" / "application.properties").is_file() or (
            root / "support" / "analyzeHeadless.bat"
        ).is_file():
            candidates.append(root)
        try:
            children = sorted(
                (child for child in root.iterdir() if child.is_dir()),
                key=lambda p: p.name.lower(),
            )
        except OSError:
            children = []
        for child in children:
            if child.name.lower().startswith("ghidra"):
                candidates.append(child)
    return candidates


def _looks_like_java_home(directory: Path) -> bool:
    return (directory / "release").is_file() or (
        directory / "bin" / _JAVA_BIN
    ).is_file()


def java_root_candidates(root: Path) -> list[Path]:
    """Directories that could be JDK homes under an installation root.

    Two layouts are common and both are covered: a vendor directory holding
    versioned homes (``Eclipse Adoptium/jdk-25.0.5.1+2``), and an unpacked
    archive directly under the root (``C:/Tools/jdk-25.0.5.1+2``).
    """
    homes = []
    for relative in ("Eclipse Adoptium", "Java", "Microsoft", "Amazon Corretto"):
        base = root / relative
        if not base.is_dir():
            continue
        try:
            children = sorted(
                (child for child in base.iterdir() if child.is_dir()),
                key=lambda p: p.name.lower(),
            )
        except OSError:
            continue
        homes.extend(child for child in children if _looks_like_java_home(child))
    if not root.is_dir():
        return homes
    try:
        children = sorted(
            (child for child in root.iterdir() if child.is_dir()),
            key=lambda p: p.name.lower(),
        )
    except OSError:
        children = []
    for child in children:
        if child.name.lower().startswith(("jdk", "jre")) and _looks_like_java_home(child):
            homes.append(child)
    if _looks_like_java_home(root):
        homes.append(root)
    return homes


def version_key(version: str | None) -> tuple:
    """Numeric sort key for a version string.

    ``12.2`` must outrank ``12.1.4``, which a directory-name sort does not give.
    Non-numeric components sort below any number instead of raising.
    """
    parts = []
    for piece in str(version or "").replace("-", ".").split("."):
        digits = "".join(character for character in piece if character.isdigit())
        parts.append(int(digits) if digits else -1)
    return tuple(parts)


def _rank(records: list[dict], *, key_name: str) -> list[dict]:
    """Order candidates: declared precedence first, discovery newest-first.

    Explicit, profile and environment candidates keep the order the caller
    gave them. Discovered candidates are ranked by the version each one
    proves, then by build date, then by path, so discovery is deterministic
    and prefers the newest compatible installation rather than the first
    directory name an enumeration happens to return.
    """
    declared = [record for record in records if record["origin"] != "discovery"]
    discovered = [record for record in records if record["origin"] == "discovery"]
    discovered.sort(key=lambda record: record[key_name])
    discovered.sort(key=lambda record: _discovery_key(record, key_name), reverse=True)
    seen = set()
    ordered = []
    for record in declared + discovered:
        identity = os.path.normcase(os.path.realpath(record[key_name]))
        if identity in seen:
            continue
        seen.add(identity)
        ordered.append(record)
    return ordered


def _discovery_key(record: dict, key_name: str) -> tuple:
    if "version" in record and record.get("version") is not None:
        return (version_key(record.get("version")), record.get("build_date") or "")
    return (version_key(None), str(record.get("major")))


def _candidate(home: Path, origin: str) -> dict:
    record = read_java_home(home)
    record["origin"] = origin
    return record


def _candidate_ghidra(directory: Path, origin: str) -> dict:
    record = read_ghidra_install(directory)
    record["origin"] = origin
    return record


# --------------------------------------------------------------------------
# selection
# --------------------------------------------------------------------------
def load_profile(path: Path) -> dict:
    if not path.is_file():
        raise ToolchainError(f"profile file not found: {path}")
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ToolchainError(f"profile is not valid JSON: {exc}") from exc
    if not isinstance(body, dict):
        raise ToolchainError("profile must be a JSON object")
    return body


def select(
    *,
    ghidra_dir: str | None = None,
    java_home: str | None = None,
    profile: dict | None = None,
    require_version: str | None = None,
    require_java_major: int | None = None,
    java_strategy: str = "minimum",
    search_roots: list[Path] | None = None,
    environment: dict | None = None,
) -> dict:
    """Choose one compatible Ghidra/JDK pair and explain every candidate."""
    if java_strategy not in JAVA_STRATEGIES:
        raise ToolchainError(
            f"java strategy must be one of {', '.join(JAVA_STRATEGIES)}"
        )
    environment = dict(os.environ if environment is None else environment)
    profile = profile or {}
    java_strategy = (profile.get("java") or {}).get("strategy") or java_strategy
    roots = [Path(root) for root in (search_roots or [])]
    if not roots:
        roots = default_search_roots()

    profile_ghidra = (profile.get("ghidra") or {}).get("install_dir")
    profile_java = (profile.get("java") or {}).get("home")
    profile_version = (profile.get("ghidra") or {}).get("version")
    wanted = require_version or profile_version
    profile_major = (profile.get("java") or {}).get("major")
    pinned_major = require_java_major if require_java_major is not None else profile_major

    ghidra_candidates: list[dict] = []
    explicit_ghidra = None
    if ghidra_dir:
        explicit_ghidra = _candidate_ghidra(Path(ghidra_dir), "explicit")
        ghidra_candidates.append(explicit_ghidra)
    if profile_ghidra:
        candidate = _candidate_ghidra(Path(profile_ghidra), "profile")
        ghidra_candidates.append(candidate)
    if environment.get("GHIDRA_INSTALL_DIR"):
        ghidra_candidates.append(
            _candidate_ghidra(Path(environment["GHIDRA_INSTALL_DIR"]), "environment")
        )
    seen = {str(Path(candidate["install_dir"])) for candidate in ghidra_candidates}
    for root in roots:
        for directory in ghidra_root_candidates(root):
            if str(directory.resolve()) in seen:
                continue
            seen.add(str(directory.resolve()))
            ghidra_candidates.append(_candidate_ghidra(directory, "discovery"))

    ghidra_candidates = _rank(ghidra_candidates, key_name="install_dir")

    ghidra_rejected = []
    ghidra_selected = None
    for candidate in ghidra_candidates:
        if candidate["error"]:
            candidate["rejected"] = candidate["error"]
            ghidra_rejected.append(candidate)
            continue
        if wanted and candidate["version"] != wanted:
            candidate["rejected"] = (
                f"version {candidate['version']!r} does not satisfy the "
                f"requirement {wanted!r}"
            )
            ghidra_rejected.append(candidate)
            continue
        ghidra_selected = candidate
        break

    java_candidates: list[dict] = []
    explicit_java = None
    if java_home:
        explicit_java = _candidate(Path(java_home), "explicit")
        java_candidates.append(explicit_java)
    if profile_java:
        java_candidates.append(_candidate(Path(profile_java), "profile"))
    for name in ("GHIDRA_JAVA_HOME", "JAVA_HOME"):
        if environment.get(name):
            java_candidates.append(_candidate(Path(environment[name]), "environment"))
    if ghidra_selected:
        override = ghidra_java_override(Path(ghidra_selected["install_dir"]))
        if override:
            java_candidates.append(_candidate(Path(override), "ghidra-override"))
    # Only consult PATH when the caller's environment actually carries one, so
    # an explicit empty environment stays hermetic in tests.
    path_entry = environment.get("PATH")
    on_path = shutil.which("java", path=path_entry) if path_entry else None
    if on_path:
        java_candidates.append(
            _candidate(Path(on_path).resolve().parent.parent, "discovery")
        )
    for root in roots:
        for home in java_root_candidates(root):
            java_candidates.append(_candidate(home, "discovery"))

    java_min = ghidra_selected["java_min"] if ghidra_selected else None
    # Declared candidates keep the caller's precedence order; discovered JDKs
    # rank by the major version each one reports, so a directory name cannot
    # promote an older runtime.
    declared_java = [record for record in java_candidates if record["origin"] != "discovery"]
    discovered_java = [record for record in java_candidates if record["origin"] == "discovery"]
    discovered_java.sort(key=lambda record: record["home"])
    discovered_java.sort(
        key=lambda record: record["major"] if record["major"] is not None else -1,
        reverse=java_strategy == "newest",
    )
    java_candidates = declared_java + discovered_java
    java_selected = None
    java_rejected = []
    seen_homes = set()
    for candidate in java_candidates:
        key = os.path.normcase(os.path.realpath(candidate["home"]))
        if key in seen_homes:
            continue
        seen_homes.add(key)
        if candidate["error"]:
            candidate["rejected"] = candidate["error"]
            java_rejected.append(candidate)
            continue
        if not candidate["java_executable"]:
            candidate["rejected"] = "no java executable in the home"
            java_rejected.append(candidate)
            continue
        if java_min is not None and candidate["major"] is not None:
            if candidate["major"] < java_min:
                candidate["rejected"] = (
                    f"major {candidate['major']} is below the "
                    f"{java_min} required by the selected Ghidra"
                )
                java_rejected.append(candidate)
                continue
        if candidate["major"] is None:
            candidate["rejected"] = "major version is unknown, so compatibility is unproven"
            java_rejected.append(candidate)
            continue
        if pinned_major is not None and candidate["major"] != int(pinned_major):
            candidate["rejected"] = (
                f"major {candidate['major']} is not the pinned major {pinned_major}"
            )
            java_rejected.append(candidate)
            continue
        java_selected = candidate
        break

    explicit_problem = None
    if explicit_java is not None and java_selected is not explicit_java:
        explicit_problem = (
            "the explicitly requested Java home was rejected: "
            f"{explicit_java.get('rejected') or explicit_java.get('error')}"
        )
    if explicit_ghidra is not None and ghidra_selected is not explicit_ghidra:
        explicit_problem = (
            "the explicitly requested Ghidra installation was rejected: "
            f"{explicit_ghidra.get('rejected') or explicit_ghidra.get('error')}"
        )

    compatible = bool(ghidra_selected and java_selected) and not explicit_problem
    return {
        "schema": SCHEMA,
        "precedence": list(PRECEDENCE),
        "requirements": {
            "ghidra_version": wanted,
            "java_min": java_min,
            "java_major": int(pinned_major) if pinned_major is not None else None,
            "java_strategy": java_strategy,
        },
        "ghidra": {
            "selected": ghidra_selected,
            "candidates": ghidra_candidates,
            "rejected_count": len(ghidra_rejected),
        },
        "java": {
            "selected": java_selected,
            "candidates": java_candidates,
            "rejected_count": len(java_rejected),
        },
        "compatible": compatible,
        "explicit_problem": explicit_problem,
        "python": python_record(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "python": platform.python_version(),
        },
        "scope": (
            "selection reads each installation's own version record and each "
            "JDK's own release metadata; no global environment variable is "
            "written and no project or installation is modified"
        ),
    }


def python_record() -> dict:
    record = {
        "executable": sys.executable,
        "version": platform.python_version(),
        "pyghidra": None,
        "pyghidra_error": None,
    }
    try:
        from importlib.metadata import version  # noqa: PLC0415

        record["pyghidra"] = version("pyghidra")
    except Exception as exc:  # noqa: BLE001 - absence is the normal case
        record["pyghidra_error"] = f"{type(exc).__name__}: {exc}"
    return record


def describe_failure(result: dict) -> list[str]:
    """Human-readable reasons a selection is incomplete."""
    reasons = []
    if result["explicit_problem"]:
        reasons.append(result["explicit_problem"])
    if not result["ghidra"]["selected"]:
        reasons.append("no Ghidra installation proved a usable version")
        for candidate in result["ghidra"]["candidates"]:
            reason = candidate.get("rejected") or candidate.get("error")
            if reason:
                reasons.append(f"  {candidate['install_dir']}: {reason}")
    if not result["java"]["selected"]:
        reasons.append("no compatible Java home was found")
        for candidate in result["java"]["candidates"]:
            reason = candidate.get("rejected") or candidate.get("error")
            if reason:
                reasons.append(f"  {candidate['home']}: {reason}")
    return reasons


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Select and verify a Ghidra/JDK pair from on-disk evidence.",
        epilog="Exit codes: 0 compatible selection, 1 no compatible selection, "
        "2 usage or configuration error.",
    )
    parser.add_argument("--ghidra-dir", help="explicit Ghidra installation to use")
    parser.add_argument("--java-home", help="explicit Java home to use")
    parser.add_argument("--profile", help="JSON profile pinning a toolchain")
    parser.add_argument(
        "--java-strategy",
        choices=JAVA_STRATEGIES,
        default="minimum",
        help="choose the lowest compatible JDK major (default: minimum, which "
        "reproduces a historical release's own era) or the newest compatible",
    )
    parser.add_argument("--require-ghidra-version", help="required application.version")
    parser.add_argument(
        "--require-java-major",
        type=int,
        help="require an exact JDK major version",
    )
    parser.add_argument(
        "--search-root",
        action="append",
        default=None,
        help="directory to scan for installations (repeatable)",
    )
    parser.add_argument("--output", help="write the selection record here")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="print only the failure reasons",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        profile = load_profile(Path(args.profile)) if args.profile else None
        result = select(
            ghidra_dir=args.ghidra_dir,
            java_home=args.java_home,
            profile=profile,
            require_version=args.require_ghidra_version,
            require_java_major=args.require_java_major,
            java_strategy=args.java_strategy,
            search_roots=[Path(root) for root in args.search_root]
            if args.search_root
            else None,
        )
    except ToolchainError as exc:
        sys.stderr.write(f"{exc}\n")
        return EXIT_USAGE

    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    if args.quiet:
        if not result["compatible"]:
            sys.stdout.write("\n".join(describe_failure(result)) + "\n")
    else:
        sys.stdout.write(text)
    return EXIT_OK if result["compatible"] else EXIT_NO_SELECTION


if __name__ == "__main__":
    raise SystemExit(main())
