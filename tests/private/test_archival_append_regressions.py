from dataclasses import replace
import unittest
from deskmate_formats.calendar.writer import TARGET,append_appointment
from test_calendar_personal import fixture_path

class ExactArchivalAppendTests(unittest.TestCase):
    def test_e07_to_e08(self):
        self.assertEqual(append_appointment(fixture_path('E07_date_20271101').read_bytes()),fixture_path('E08_two_events').read_bytes())
    def test_e09_to_e10(self):
        event=replace(TARGET,description='GAMMA45')
        self.assertEqual(append_appointment(fixture_path('E09_delete_beta456').read_bytes(),event),fixture_path('E10_reuse_gamma45').read_bytes())
