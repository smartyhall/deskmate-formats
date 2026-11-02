"""Policy tests against an authored simulator; no emulator or guest required."""
import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    'automation23_mock', Path(__file__).resolve().parents[2] / 'tools/experimental/automation23_mock.py')
mock = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mock)


class AutomationModelTests(unittest.TestCase):
    def setUp(self):
        self.model = mock.Model()
        self.bridge = mock.ObservationHarness(self.model.line)

    def test_stable_held_observation_and_synthetic_marker(self):
        epoch = self.bridge.attach()
        observation = self.bridge.observe(epoch, 0x380, 4, framebuffer=True)
        self.assertTrue(observation['mock_only'])
        self.assertEqual(observation['data'], self.model.memory[0x380:0x384].hex())
        self.assertEqual(observation['ms'], 0)

    def test_wrong_target_is_rejected(self):
        self.model.version = 'DIFFERENT'
        with self.assertRaises(ValueError):
            self.bridge.attach()
        self.assertFalse(self.bridge.ready)

    def test_reconnect_requires_new_epoch(self):
        old = self.bridge.attach()
        self.model.connected = False
        with self.assertRaises(ConnectionError):
            self.bridge.observe(old, 0, 4)
        self.model.connected = True
        new = self.bridge.attach()
        self.assertNotEqual(old, new)
        with self.assertRaises(ValueError):
            self.bridge.observe(old, 0, 4)

    def test_time_or_reset_change_invalidates_snapshot(self):
        for change in ('time', 'reset'):
            with self.subTest(change=change):
                self.setUp()
                epoch = self.bridge.attach()
                def exchange(line):
                    response = self.model.line(line)
                    if line == 'regs':
                        if change == 'time':
                            self.model.ms += 1
                        else:
                            self.model.resets += 1
                    return response
                self.bridge.exchange = exchange
                with self.assertRaises(ValueError):
                    self.bridge.observe(epoch, 0, 4)
                self.assertFalse(self.bridge.ready)

    def test_backward_time_between_valid_observations_invalidates_epoch(self):
        epoch = self.bridge.attach()
        self.model.ms = 10
        first = self.bridge.observe(epoch, 0x380, 4)
        self.assertEqual(first['ms'], 10)
        # Rewinding the emulator clock without a reported reset must never
        # allow previous segment mappings or observations to remain trusted.
        self.model.ms = 0
        with self.assertRaises(ValueError):
            self.bridge.observe(epoch, 0x380, 4)
        self.assertFalse(self.bridge.ready)
        with self.assertRaises(ValueError):
            self.bridge.observe(epoch, 0x380, 4)

    def test_truncated_memory_is_rejected(self):
        epoch = self.bridge.attach()
        def exchange(line):
            response = self.model.line(line)
            return json.dumps({'ok': True, 'addr': 0, 'data': '00'}) if line.startswith('memr ') else response
        self.bridge.exchange = exchange
        with self.assertRaises(ValueError):
            self.bridge.observe(epoch, 0, 4)

    def test_ram_bounds_and_protocol_injection(self):
        epoch = self.bridge.attach()
        for address, length in [(0, 0), (-1, 4), (0, 4097), (65535, 2), (False, 4)]:
            with self.assertRaises(ValueError):
                self.bridge.observe(epoch, address, length)
        with self.assertRaises(ValueError):
            self.model.line('status\nmemw 0 aa')

    def test_model_denies_write_command(self):
        self.assertFalse(json.loads(self.model.line('memw 0 aa'))['ok'])

    def test_lost_key_reply_is_ambiguous_and_not_replayed(self):
        self.bridge.attach()
        self.model.fail_after_apply = True
        with self.assertRaises(ConnectionError):
            self.bridge.call('key down 30')
        self.assertIn(30, self.model.keys)
        self.assertEqual(self.model.ms, 2)
        self.assertFalse(self.bridge.ready)
