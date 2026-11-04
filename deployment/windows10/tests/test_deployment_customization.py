"""Guard against omissions in the public Windows 10 deployment recipe."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class DeploymentCustomizationTests(unittest.TestCase):
    def read(self, name):
        return (ROOT/name).read_text(encoding="utf-8")

    def test_builder_packages_both_automation_scripts(self):
        s = self.read("Build-LabISO.ps1")
        self.assertIn("'Configure-LabWorkstation.ps1'",s)
        self.assertIn("'Install-LabGuestAdditions.ps1'",s)
        self.assertIn("[string]$GuestAdditionsISO",s)
        self.assertIn("guest_additions_iso_sha256=$guestAdditionsHash",s)

    def test_lab_autologon_is_explicit_and_rotatable(self):
        builder = self.read("Build-LabISO.ps1")
        answer = self.read("autounattend-uefi.xml.in")
        helper = self.read("Set-LabLogon.ps1")
        self.assertIn("[switch]$EnableAutoLogon", builder)
        self.assertIn("'Set-LabLogon.ps1'", builder)
        self.assertIn("@AUTOLOGON_COUNT@", answer)
        self.assertIn("Microsoft-Windows-International-Core", answer)
        self.assertIn("'9999'", builder)
        self.assertIn("'1'", builder)
        self.assertIn("Read-Host", helper)
        self.assertIn("Set-LocalUser", helper)
        self.assertIn("DefaultPassword", helper)
        self.assertIn("AutoAdminLogon", helper)

    def test_winget_bootstrap_is_staged_before_chrome(self):
        builder=self.read("Build-LabISO.ps1")
        provision=self.read("Provision-Lab.ps1")
        helper=self.read("Initialize-LabWinGet.ps1")
        self.assertIn("'Initialize-LabWinGet.ps1'", builder)
        self.assertLess(provision.index("'Initialize-LabWinGet.ps1'"),
                        provision.index('googlechromestandaloneenterprise64.msi'))
        self.assertIn('RegisterByFamilyName',helper)
        self.assertIn('Microsoft.DesktopAppInstaller.msixbundle',helper)
        self.assertIn('WinGet is unavailable',helper)
        self.assertIn("'S-1-5-18'",helper)

    def test_delivery_optimization_is_local_only_and_configurable(self):
        builder=self.read("Build-LabISO.ps1")
        privacy=self.read("Privacy-Lab.ps1")
        self.assertIn("ValidateSet('Lan','HttpOnly')",builder)
        self.assertIn("delivery-optimization-mode.txt",builder)
        self.assertIn("delivery_optimization_mode=$DeliveryOptimizationMode",builder)
        self.assertIn('DODownloadMode',privacy)
        self.assertIn("if ($doMode -eq 'Lan') { 1 } else { 0 }",privacy)
        self.assertNotIn("'DODownloadMode' 3",privacy)

    def test_config_preserves_search_and_user_security(self):
        s = self.read("Configure-LabWorkstation.ps1")
        for needle in ("SearchboxTaskbarMode", "ShellFeedsTaskbarViewMode",
                       "EnableFeeds", "monitor-timeout-ac 0",
                       "standby-timeout-ac 0", "hibernate-timeout-ac 0",
                       "-UserOnly", "Active Setup"):
            self.assertIn(needle,s)
        self.assertNotIn('Set-Service WSearch',s)
        self.assertNotIn('Set-Service wuauserv',s)

    def test_optional_guest_install_and_signature_check(self):
        s = self.read("Install-LabGuestAdditions.ps1")
        for needle in ("VBoxWindowsAdditions.exe", "Get-AuthenticodeSignature",
                       "VBoxCertUtil.exe", "add-trusted-publisher",
                       "-ArgumentList '/S'", "guest-additions-deferred.txt"):
            self.assertIn(needle,s)
        self.assertNotIn('Invoke-WebRequest',s)

    def test_guest_stage_before_online_install(self):
        s = self.read("Provision-Lab.ps1")
        self.assertLess(s.index("'Configure-LabWorkstation.ps1'"),s.index("googlechromestandaloneenterprise64.msi"))
        self.assertLess(s.index("'Install-LabGuestAdditions.ps1'"),s.index("googlechromestandaloneenterprise64.msi"))

if __name__ == "__main__":
    unittest.main()
