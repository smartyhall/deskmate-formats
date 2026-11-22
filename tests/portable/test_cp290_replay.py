"""Check the offline CP290 replay against the RSX UART observations."""

import unittest

from tools.experimental.cp290_replay import VirtualCP290


SYNC = bytes.fromhex('ff' * 16)
ACK = bytes.fromhex('ff' * 6 + '01')


class CP290ReplayTests(unittest.TestCase):
    def setUp(self):
        self.controller = VirtualCP290()
        event, replies = self.command('0020')
        self.assertEqual(event, {'operation': 'set-house-code', 'house': 'C'})
        self.assertEqual(replies, (ACK,))

    def command(self, hex_body):
        return self.controller.command(SYNC + bytes.fromhex(hex_body))

    def test_direct_lamp_command_and_checksum(self):
        with self.assertRaisesRegex(ValueError, 'checksum'):
            self.command('0102200080a3')
        self.assertEqual(self.controller.units, {})
        event, replies = self.command('0102200080a2')
        self.assertEqual(event, {'operation': 'on', 'house': 'C', 'units': [1]})
        self.assertEqual(replies, (ACK, ACK + bytes.fromhex('22008020c2')))
        self.assertTrue(self.controller.units['C', 1])
        self.command('0103200080a3')
        self.assertFalse(self.controller.units['C', 1])

    def test_observed_schedule_round_trip(self):
        self.assertEqual(self.command('04')[1], (ACK + bytes.fromhex('2c15042065'),))
        self.assertEqual(self.command('05')[1], (ACK + b'\xff' * 128 + b'\x00',))
        self.assertEqual(self.command('030000087f06068000200235')[1], (ACK,))
        event = bytes.fromhex('087f060680002002')
        self.assertEqual(self.command('05')[1], (ACK + event + b'\xff' * 127 + b'\x35',))
        self.assertEqual(self.command('0020')[1], (ACK,))
        self.assertEqual(self.command('05')[1], (ACK + b'\xff' * 128 + b'\x00',))

    def test_unsupported_and_truncated_frames_raise(self):
        for body in ('', '0102', '06', '030800087f06068000200235'):
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.command(body)
        with self.assertRaisesRegex(ValueError, 'synchronization'):
            self.controller.command(SYNC[1:] + b'\x04')
