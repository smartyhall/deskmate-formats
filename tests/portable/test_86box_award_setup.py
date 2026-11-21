"""Synthetic menu attributes must gate every Award submenu action."""
import importlib
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
award = importlib.import_module('86box_award_setup')


class AwardSetupTests(unittest.TestCase):
    def test_highlighted_menu_uses_attributes_and_observes_submenu(self):
        def row(text, attr):
            return text, bytes([attr]) * len(text)

        main = [row('CMOS SETUP UTILITY', 7), row('STANDARD CMOS SETUP', 0x4f),
                row('BIOS FEATURES SETUP', 0x1e)]
        submenu = [row('STANDARD CMOS SETUP', 7), row('Drive B: 1.44M', 7)]
        client = Mock()
        client.status.return_value = {'held': True, 'paused': False}
        client.text_attributes.return_value = main
        with self.assertRaisesRegex(ValueError, 'not uniquely highlighted'):
            award.open_highlighted(client, 'BIOS FEATURES SETUP', 0x4f)
        client.tap.assert_not_called()
        client.text_attributes.side_effect = [main, submenu]
        client.advance.return_value = {'status': {'ms': 250}}
        self.assertEqual(award.open_highlighted(client, 'STANDARD CMOS SETUP', 0x4f),
                         ({'ms': 250}, submenu))
        client.tap.assert_called_once_with(0x1c)


if __name__ == '__main__':
    unittest.main()
