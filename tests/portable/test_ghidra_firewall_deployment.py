"""Guard the Windows 10 Ghidra firewall stage against broad exceptions."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / 'deployment/windows10'


class GhidraFirewallDeploymentTests(unittest.TestCase):
    def test_loopback_only_and_inbound_tcp(self):
        text = (DEPLOY / 'Configure-LabGhidraFirewall.ps1').read_text(encoding='utf-8')
        self.assertIn("address = '127.0.0.1'", text)
        self.assertIn("address = '::1'", text)
        self.assertIn("Direction = 'Inbound'", text)
        self.assertIn("Protocol = 'TCP'", text)
        self.assertIn("LocalAddress = $address", text)
        self.assertIn("RemoteAddress = $address", text)
        self.assertIn("Program = $program", text)
        self.assertNotIn("RemoteAddress = 'Any'", text)
        self.assertNotIn("LocalAddress = 'Any'", text)

    def test_installation_and_manual_retry_wired(self):
        helper = 'Configure-LabGhidraFirewall.ps1'
        self.assertIn(helper, (DEPLOY / 'Build-LabISO.ps1').read_text(encoding='utf-8'))
        self.assertIn(helper, (DEPLOY / 'Provision-Lab.ps1').read_text(encoding='utf-8'))
        self.assertIn('JavaHome', (DEPLOY / 'README.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
