"""Exercise the actual archive launcher, without contacting a server."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


LAUNCHER = Path(__file__).resolve().parents[2] / "tools/archive/Mirror-Archive.ps1"
POWERSHELL = shutil.which("powershell.exe") or shutil.which("pwsh")


@unittest.skipUnless(POWERSHELL, "PowerShell not installed")
class ArchiveLauncherTests(unittest.TestCase):
    def test_default_and_explicit_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script_dir = root / "archive tools"
            script_dir.mkdir()
            script = script_dir / LAUNCHER.name
            shutil.copyfile(LAUNCHER, script)
            (script_dir / "archive_mirror.py").write_text(
                "import json, sys\nprint(json.dumps(sys.argv[1:]))\n",
                encoding="utf-8",
            )
            default = script_dir / "mirror-targets.example.toml"
            custom = root / "custom targets.toml"
            for config in (default, custom):
                config.touch()
                args = [] if config == default else ["-Config", str(config)]
                process = subprocess.run(
                    [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass",
                     "-File", str(script), "-Target", "local", "-Status", *args],
                    cwd=root, capture_output=True, text=True, timeout=60,
                )
                self.assertEqual(process.returncode, 0, process.stderr)
                actual = json.loads(process.stdout.strip())
                self.assertEqual(actual[actual.index("--config") + 1], str(config))
                self.assertIn("--status", actual)
                self.assertEqual(actual[actual.index("--target") + 1], "local")
