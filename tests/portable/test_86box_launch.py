"""ROM-free launcher construction and working-profile preservation controls."""
import configparser
import importlib
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = str(Path(__file__).resolve().parents[2] / 'tools')
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
launch = importlib.import_module('86box_launch')


class LaunchTests(unittest.TestCase):
    def test_command_keeps_paths_as_individual_arguments_and_secure_defaults(self):
        args = launch.command('lab build/86Box.exe', 'private machine', 'private globals', 8765, 1)
        self.assertEqual(args[0], 'lab build/86Box.exe')
        self.assertEqual(args[args.index('--vmpath') + 1], 'private machine')
        self.assertIn('tcp:127.0.0.1:8765', args)
        self.assertIn('--automation-hold', args)
        self.assertIn('--nohook', args)
        self.assertNotIn('--automation-insecure', args)
        self.assertNotIn('--automation-token-file', args)

    def test_invalid_port_and_seed_rejected(self):
        for port, seed in ((0, 1), (65536, 1), (8765, -1), (8765, 2**32)):
            with self.assertRaises(ValueError):
                launch.command('exe', 'machine', 'global', port, seed)

    def test_display_environment_is_explicit_and_does_not_mutate_parent(self):
        original = {'PATH':'original', 'QT_QPA_PLATFORM':'inherited-offscreen'}
        for mode in ('visible', 'background', 'headless'):
            env = launch.child_environment('runtime', mode, original)
            self.assertEqual(env['QT_QPA_PLATFORM'], 'offscreen' if mode == 'headless' else 'windows')
            self.assertTrue(env['PATH'].startswith('runtime'))
        self.assertEqual(original['QT_QPA_PLATFORM'], 'inherited-offscreen')
        with self.assertRaises(ValueError):
            launch.child_environment('runtime', 'unknown', original)

    def test_input_preferences_preserve_hardware_and_exact_original_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            machine = Path(temp)
            run = machine / 'run'
            run.mkdir()
            original = b'\xef\xbb\xbf[General]\nkbd_req_capture = 1\n[Machine]\nmem_size = 4096\n[Input devices]\nmouse_type = ps2\n'
            (machine / '86box.cfg').write_bytes(original)
            launch.observer_preferences(machine, run)
            self.assertEqual((run/'86box.cfg.before').read_bytes(), original)
            cfg = configparser.ConfigParser()
            cfg.read(machine/'86box.cfg', encoding='utf-8')
            self.assertEqual(cfg['Machine']['mem_size'], '4096')
            self.assertEqual(cfg['Input devices']['mouse_type'], 'ps2')
            self.assertEqual(cfg['Input devices']['mouse_input_mode_initial'], '0')
            self.assertEqual(cfg['General']['kbd_req_capture'], '0')
            # Already-normalized preferences require no additional rewrite/backup.
            before = (machine/'86box.cfg').read_bytes()
            launch.observer_preferences(machine, run)
            self.assertEqual((machine/'86box.cfg').read_bytes(), before)
            self.assertEqual((run/'86box.cfg.before').read_bytes(), original)

    def test_sealed_baseline_is_rejected_without_writing_config(self):
        with tempfile.TemporaryDirectory() as temp:
            machine = Path(temp)
            (machine/'86box.cfg').write_text('[Machine]\nmem_size = 4096\n')
            (machine/'baseline-manifest.json').write_text('{}')
            before = (machine/'86box.cfg').read_bytes()
            with self.assertRaisesRegex(ValueError, 'clone'):
                launch.observer_preferences(machine, machine/'does-not-exist')
            self.assertEqual((machine/'86box.cfg').read_bytes(), before)
            self.assertFalse((machine/'does-not-exist').exists())


if __name__ == '__main__':
    unittest.main()
