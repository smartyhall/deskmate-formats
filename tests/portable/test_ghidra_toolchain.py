"""Portable probes for Ghidra/JDK discovery and selection.

The fixtures are synthetic directories carrying the same two version records a
real installation carries: ``Ghidra/application.properties`` for Ghidra and
``release`` for a JDK. No Ghidra release, JDK or JVM is needed, and no network
access is used, so the precedence rules can be checked exactly.
"""
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    'ghidra_toolchain', ROOT / 'tools/ghidra/ghidra_toolchain.py'
)
toolchain = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(ROOT / 'src'))
spec.loader.exec_module(toolchain)


def write_properties(directory: Path, **fields) -> None:
    path = directory / 'Ghidra' / 'application.properties'
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f'{key.replace("_", ".")}={value}' for key, value in fields.items()]
    path.write_text('# synthetic\n' + '\n'.join(lines) + '\n', encoding='utf-8')


def make_ghidra(root: Path, name: str, *, version: str, java_min: int,
                build_date: str = '2026-Oct-16 1220 UTC',
                revision: str = 'abc123',
                launcher: bool = True,
                properties: bool = True) -> Path:
    directory = root / name
    directory.mkdir(parents=True, exist_ok=True)
    if launcher:
        support = directory / 'support'
        support.mkdir(exist_ok=True)
        (support / 'analyzeHeadless.bat').write_text('@echo off\n', encoding='utf-8')
    if properties:
        write_properties(
            directory,
            application_version=version,
            application_build_date=build_date,
            application_java_min=java_min,
            application_revision_ghidra=revision,
        )
    return directory


def make_jdk(root: Path, name: str, *, version: str | None,
             vendor: str = 'Eclipse Adoptium', release: bool = True) -> Path:
    home = root / 'Eclipse Adoptium' / name
    (home / 'bin').mkdir(parents=True, exist_ok=True)
    (home / 'bin' / toolchain._JAVA_BIN).write_bytes(b'')
    if release:
        fields = ['IMPLEMENTOR="{0}"'.format(vendor)]
        if version is not None:
            fields.append('JAVA_VERSION="{0}"'.format(version))
        (home / 'release').write_text('\n'.join(fields) + '\n', encoding='utf-8')
    return home


class MajorVersionTests(unittest.TestCase):
    def test_modern_and_legacy_forms(self):
        self.assertEqual(toolchain.major_from_version('25.0.5.1+2'), 25)
        self.assertEqual(toolchain.major_from_version('21.0.4'), 21)
        self.assertEqual(toolchain.major_from_version('1.8.0_402'), 8)
        self.assertEqual(toolchain.major_from_version('9'), 9)

    def test_unparseable_versions_are_unknown_not_guessed(self):
        for value in (None, '', 'jdk-25', 'latest', 'LTS'):
            with self.subTest(value=value):
                self.assertIsNone(toolchain.major_from_version(value))


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        make_ghidra(self.root, 'ghidra_12.2_PUBLIC', version='12.2', java_min=25)
        make_ghidra(self.root, 'ghidra_12.1.4_PUBLIC', version='12.1.4', java_min=21)
        make_jdk(self.root, 'jdk-25.0.5.1+2', version='25.0.5.1')
        make_jdk(self.root, 'jdk-21.0.4', version='21.0.4')

    def tearDown(self):
        for path in sorted(self.root.rglob('*'), key=lambda p: len(p.parts),
                           reverse=True):
            path.unlink() if path.is_file() else path.rmdir()
        self.root.rmdir()

    def select(self, **kwargs):
        return toolchain.select(search_roots=[self.root], environment={}, **kwargs)

    def test_the_newest_compatible_pair_is_selected(self):
        result = self.select()
        self.assertTrue(result['compatible'])
        self.assertEqual(result['ghidra']['selected']['version'], '12.2')
        self.assertEqual(result['java']['selected']['major'], 25)
        self.assertEqual(result['requirements']['java_min'], 25)

    def test_the_minimum_strategy_keeps_a_historical_release_in_its_era(self):
        # 12.1.4 records java.min 21, and 25 is also installed. Reproducing the
        # historical receipt means using 21, not the newest runtime.
        result = self.select(require_version='12.1.4')
        self.assertEqual(result['java']['selected']['major'], 21)
        newest = self.select(require_version='12.1.4', java_strategy='newest')
        self.assertEqual(newest['java']['selected']['major'], 25)

    def test_an_unknown_strategy_is_refused(self):
        with self.assertRaises(toolchain.ToolchainError):
            self.select(java_strategy='whatever')

    def test_an_unpacked_jdk_directly_under_a_root_is_found(self):
        # The lab also holds an unpacked archive (`C:/Tools/jdk-25...`), not only
        # vendor-directory installs, so both layouts must be discovered.
        unpacked_root = Path(tempfile.mkdtemp())
        try:
            make_ghidra(unpacked_root, 'ghidra_12.2_PUBLIC', version='12.2',
                        java_min=25)
            home = unpacked_root / 'jdk-25.0.5.1+2'
            (home / 'bin').mkdir(parents=True)
            (home / 'bin' / toolchain._JAVA_BIN).write_bytes(b'')
            (home / 'release').write_text('JAVA_VERSION="25.0.5.1"\n',
                                          encoding='utf-8')
            result = toolchain.select(search_roots=[unpacked_root], environment={})
            self.assertTrue(result['compatible'])
            self.assertEqual(result['java']['selected']['home'], str(home))
        finally:
            for path in sorted(unpacked_root.rglob('*'), key=lambda p: len(p.parts),
                               reverse=True):
                path.unlink() if path.is_file() else path.rmdir()
            unpacked_root.rmdir()

    def test_a_requirement_pins_the_historical_release(self):
        result = self.select(require_version='12.1.4')
        self.assertEqual(result['ghidra']['selected']['version'], '12.1.4')
        self.assertEqual(result['requirements']['java_min'], 21)
        self.assertEqual(result['java']['selected']['major'], 21)

    def test_an_explicit_incompatible_java_home_is_an_error(self):
        java21 = self.root / 'Eclipse Adoptium' / 'jdk-21.0.4'
        result = self.select(
            ghidra_dir=str(self.root / 'ghidra_12.2_PUBLIC'),
            java_home=str(java21),
        )
        self.assertFalse(result['compatible'])
        self.assertIn('explicitly requested Java home', result['explicit_problem'])
        self.assertIn('below the 25', result['explicit_problem'])

    def test_an_explicit_pair_is_used_when_compatible(self):
        java25 = self.root / 'Eclipse Adoptium' / 'jdk-25.0.5.1+2'
        result = self.select(
            ghidra_dir=str(self.root / 'ghidra_12.2_PUBLIC'),
            java_home=str(java25),
        )
        self.assertTrue(result['compatible'])
        self.assertEqual(result['java']['selected']['major'], 25)

    def test_a_directory_name_never_decides_the_java_version(self):
        # A directory named for a newer JDK that actually holds Java 17 must be
        # rejected on its evidence, not trusted on its name.
        lying = make_jdk(self.root, 'jdk-30-newest', version='17.0.9', vendor='Other')
        result = self.select()
        self.assertEqual(result['java']['selected']['major'], 25)
        rejected = [
            candidate for candidate in result['java']['candidates']
            if candidate['home'] == str(lying)
        ]
        self.assertEqual(len(rejected), 1)
        self.assertIn('major 17 is below the 25', rejected[0]['rejected'])

    def test_a_launcher_without_a_version_record_is_not_an_installation(self):
        broken = make_ghidra(
            self.root, 'ghidra_99_unversioned', version='', java_min=0,
            launcher=True, properties=False,
        )
        result = self.select()
        self.assertEqual(result['ghidra']['selected']['version'], '12.2')
        rejected = [
            candidate for candidate in result['ghidra']['candidates']
            if candidate['install_dir'] == str(broken)
        ]
        self.assertIn('no Ghidra/application.properties', rejected[0]['error'])

    def test_a_directory_without_a_launcher_is_rejected(self):
        create_only = self.root / 'ghidra_12.0_props_only'
        write_properties(create_only, application_version='12.0',
                         application_java_min=21)
        result = self.select()
        rejected = [
            candidate for candidate in result['ghidra']['candidates']
            if candidate['install_dir'] == str(create_only)
        ]
        self.assertEqual(rejected[0]['error'], 'no headless launcher')

    def test_an_unreadable_java_home_is_rejected_rather_than_assumed(self):
        no_release = make_jdk(self.root, 'jdk-no-release', version=None,
                              release=False)
        result = self.select()
        # The previous selection is still 25; the broken home is recorded with
        # a reason instead of a guessed version.
        self.assertTrue(result['compatible'])
        rejected = [
            candidate for candidate in result['java']['candidates']
            if candidate['home'] == str(no_release)
        ]
        self.assertEqual(len(rejected), 1)
        self.assertIsNone(rejected[0]['major'])
        self.assertTrue(rejected[0]['rejected'])


class EnvironmentAndProfileTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.modern = make_ghidra(self.root, 'ghidra_12.2_PUBLIC',
                                  version='12.2', java_min=25)
        self.historic = make_ghidra(self.root, 'ghidra_12.1.4_PUBLIC',
                                    version='12.1.4', java_min=21)
        self.java25 = make_jdk(self.root, 'jdk-25.0.5.1+2', version='25.0.5.1')
        self.java21 = make_jdk(self.root, 'jdk-21.0.4', version='21.0.4')

    def tearDown(self):
        for path in sorted(self.root.rglob('*'), key=lambda p: len(p.parts),
                           reverse=True):
            path.unlink() if path.is_file() else path.rmdir()
        self.root.rmdir()

    def test_environment_variables_are_consulted_without_being_modified(self):
        result = toolchain.select(
            search_roots=[self.root],
            environment={
                'GHIDRA_INSTALL_DIR': str(self.historic),
                'JAVA_HOME': str(self.java21),
            },
        )
        self.assertEqual(result['ghidra']['selected']['version'], '12.1.4')
        self.assertEqual(result['ghidra']['selected']['origin'], 'environment')
        self.assertEqual(result['java']['selected']['origin'], 'environment')

    def test_an_incompatible_environment_java_is_rejected_not_used(self):
        # This mirrors the lab: JAVA_HOME stays at 21 while 12.2 needs 25.
        result = toolchain.select(
            search_roots=[self.root],
            environment={
                'GHIDRA_INSTALL_DIR': str(self.modern),
                'JAVA_HOME': str(self.java21),
            },
        )
        self.assertTrue(result['compatible'])
        self.assertEqual(result['java']['selected']['major'], 25)
        rejected = [
            candidate for candidate in result['java']['candidates']
            if candidate['home'] == str(self.java21)
        ]
        self.assertTrue(rejected[0]['rejected'])

    def test_ghidra_launch_override_is_validated(self):
        support = self.modern / 'support'
        (support / 'launch.properties').write_text(
            f'JAVA_HOME_OVERRIDE={self.java21}\n', encoding='utf-8'
        )
        result = toolchain.select(
            search_roots=[self.root],
            environment={'GHIDRA_INSTALL_DIR': str(self.modern)},
        )
        override = [
            candidate for candidate in result['java']['candidates']
            if candidate['origin'] == 'ghidra-override'
        ]
        self.assertEqual(len(override), 1)
        self.assertTrue(override[0]['rejected'])
        self.assertIn('below the 25', override[0]['rejected'])

    def test_a_profile_pins_a_historical_toolchain(self):
        profile = {
            'ghidra': {'install_dir': str(self.historic), 'version': '12.1.4'},
            'java': {'home': str(self.java21)},
        }
        result = toolchain.select(
            search_roots=[self.root], environment={}, profile=profile
        )
        self.assertTrue(result['compatible'])
        self.assertEqual(result['ghidra']['selected']['version'], '12.1.4')
        self.assertEqual(result['ghidra']['selected']['origin'], 'profile')
        self.assertEqual(result['java']['selected']['origin'], 'profile')

    def test_no_compatible_java_reports_every_reason(self):
        lonely = Path(tempfile.mkdtemp())
        try:
            make_ghidra(lonely, 'ghidra_12.2_PUBLIC', version='12.2', java_min=25)
            result = toolchain.select(search_roots=[lonely], environment={})
            self.assertFalse(result['compatible'])
            reasons = '\n'.join(toolchain.describe_failure(result))
            self.assertIn('no compatible Java home', reasons)
        finally:
            for path in sorted(lonely.rglob('*'), key=lambda p: len(p.parts),
                               reverse=True):
                path.unlink() if path.is_file() else path.rmdir()
            lonely.rmdir()


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        make_ghidra(self.root, 'ghidra_12.2_PUBLIC', version='12.2', java_min=25)
        make_jdk(self.root, 'jdk-25.0.5.1+2', version='25.0.5.1')

    def tearDown(self):
        for path in sorted(self.root.rglob('*'), key=lambda p: len(p.parts),
                           reverse=True):
            path.unlink() if path.is_file() else path.rmdir()
        self.root.rmdir()

    def run_cli(self, *argv):
        import contextlib
        from unittest import mock

        out, err = io.StringIO(), io.StringIO()
        # A hermetic environment: no GHIDRA_INSTALL_DIR or JAVA_HOME from the
        # host may take precedence over the fixture root.
        with mock.patch.dict('os.environ', {}, clear=True):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = toolchain.main([*argv, '--search-root', str(self.root)])
        return code, out.getvalue(), err.getvalue()

    def test_a_compatible_selection_prints_a_record_and_exits_zero(self):
        code, out, _ = self.run_cli()
        self.assertEqual(code, 0)
        record = json.loads(out)
        self.assertEqual(record['schema'], toolchain.SCHEMA)
        self.assertEqual(record['precedence'][0], 'explicit')
        self.assertEqual(record['ghidra']['selected']['version'], '12.2')
        self.assertIn('python', record)

    def test_an_unsatisfiable_requirement_exits_one_with_reasons(self):
        code, out, _ = self.run_cli('--require-ghidra-version', '11.0', '--quiet')
        self.assertEqual(code, 1)
        self.assertIn('no Ghidra installation proved a usable version', out)

    def test_a_missing_profile_is_a_usage_error(self):
        code, _, err = self.run_cli('--profile', str(self.root / 'absent.json'))
        self.assertEqual(code, 2)
        self.assertIn('profile file not found', err)

    def test_an_output_path_receives_the_record(self):
        target = self.root / 'selection.json'
        code, _, _ = self.run_cli('--output', str(target), '--quiet')
        self.assertEqual(code, 0)
        self.assertTrue(target.is_file())
        self.assertTrue(json.loads(target.read_text(encoding='utf-8'))['compatible'])


if __name__ == '__main__':
    unittest.main()
