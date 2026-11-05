"""Install exactly one newly built wheel without shell-specific wildcards."""
from argparse import ArgumentParser
from pathlib import Path
import subprocess
import sys

parser = ArgumentParser(description=__doc__)
parser.add_argument("--observer", action="store_true", help="also install the optional image dependency")
args = parser.parse_args()
wheels = list(Path("dist").glob("*.whl"))
if len(wheels) != 1:
    raise SystemExit("Expected exactly one wheel in dist")

command = [sys.executable, "-m", "pip", "install", "--force-reinstall"]
if args.observer:
    command.append(f"{wheels[0]}[observer]")
else:
    command.extend(("--no-deps", str(wheels[0])))
subprocess.run(command, check=True)
