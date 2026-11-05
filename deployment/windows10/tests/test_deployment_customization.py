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

    def test_provisioning_disables_sysmain_and_compatibility_appraiser(self):
        workstation = self.read("Configure-LabWorkstation.ps1")
        privacy = self.read("Privacy-Lab.ps1")
        provision = self.read("Provision-Lab.ps1")
        verifier = self.read("Verify-Lab.ps1")
        self.assertIn("Set-Service -Name 'SysMain' -StartupType Disabled", workstation)
        self.assertIn("Stop-Service -Name 'SysMain' -Force", workstation)
        self.assertLess(workstation.index("if ($UserOnly) { return }"),
                        workstation.index("Set-Service -Name 'SysMain'"))
        self.assertIn("'\\Microsoft\\Windows\\Application Experience\\Microsoft Compatibility Appraiser'", privacy)
        self.assertIn("Get-ScheduledTask", privacy)
        self.assertLess(provision.index("'Privacy-Lab.ps1'"),
                        provision.index("'Configure-LabWorkstation.ps1'"))
        for key in ("sysMainService", "sysMainStartMode", "compatibilityAppraiserTask"):
            self.assertIn(key + "=", verifier)
        self.assertNotIn("Set-Service -Name 'wuauserv'", workstation)
        self.assertNotIn("Set-Service -Name 'WinDefend'", workstation)

    def test_optional_guest_install_and_signature_check(self):
        s = self.read("Install-LabGuestAdditions.ps1")
        for needle in ("VBoxWindowsAdditions.exe", "Get-AuthenticodeSignature",
                       "VBoxCertUtil.exe", "add-trusted-publisher",
                       "-ArgumentList '/S'", "guest-additions-deferred.txt"):
            self.assertIn(needle,s)
        self.assertNotIn('Invoke-WebRequest',s)

    def test_consumer_app_cleanup_is_allowlisted_and_disableable(self):
        builder = self.read("Build-LabISO.ps1")
        provision = self.read("Provision-Lab.ps1")
        cleanup = self.read("Clean-LabApps.ps1")
        self.assertIn("[switch]$KeepConsumerApps", builder)
        self.assertIn("'Clean-LabApps.ps1'", builder)
        self.assertIn("consumer-app-cleanup-mode.txt", builder)
        self.assertIn("'Keep' } else { 'Remove' }", builder)
        self.assertIn("consumer_app_cleanup_mode=$consumerAppMode", builder)
        self.assertIn("'Clean-LabApps.ps1'", provision)
        self.assertIn("consumer-app-cleanup-error.txt", provision)
        self.assertLess(provision.index("'Initialize-LabWinGet.ps1'"),
                        provision.index("'Clean-LabApps.ps1'"))
        self.assertLess(provision.index("'Clean-LabApps.ps1'"),
                        provision.index("googlechromestandaloneenterprise64.msi"))
        for name in ("Microsoft.SkypeApp", "Microsoft.MicrosoftOfficeHub",
                     "Microsoft.Office.OneNote", "Microsoft.OneDriveSync",
                     "Microsoft.XboxApp", "Microsoft.ZuneMusic"):
            self.assertIn("'" + name + "'", cleanup)
        for keep in ("'Microsoft.WindowsStore'", "'Microsoft.DesktopAppInstaller'",
                     "'Microsoft.VCLibs'", "'Microsoft.Windows.SecHealthUI'"):
            self.assertNotIn(keep, cleanup)
        for api in ("Get-AppxPackage -AllUsers", "Remove-AppxPackage -Package",
                    "Get-AppxProvisionedPackage -Online",
                    "Remove-AppxProvisionedPackage -Online",
                    "OneDriveSetup.exe", "SupportsShouldProcess=$true",
                    "consumer-app-cleanup.json"):
            self.assertIn(api, cleanup)
        self.assertNotIn("Remove-Item -Recurse", cleanup)
        self.assertNotIn("winget uninstall", cleanup)

    def test_rom_retrieval_is_opt_in_and_records_exact_commit(self):
        builder = self.read("Build-LabISO.ps1")
        provision = self.read("Provision-Lab.ps1")
        helper = self.read("Setup-86Box-ROMs.ps1")
        build = self.read("Setup-86Box-UCRT64.sh")
        self.assertIn("[switch]$Fetch86BoxROMs", builder)
        self.assertIn("'Setup-86Box-ROMs.ps1'", builder)
        self.assertIn("86box-roms-mode.txt", builder)
        self.assertIn("fetch_86box_roms=$Fetch86BoxROMs.IsPresent", builder)
        self.assertIn("if ($romFetchMode -eq 'Fetch' -and -not $SkipOnlinePackages)", provision)
        self.assertIn("86box-roms-error.txt", provision)
        self.assertIn("'Setup-86Box-ROMs.ps1'", provision)
        self.assertIn("'S-1-5-18'", helper)
        self.assertIn("https://github.com/86Box/roms.git", helper)
        self.assertIn("LOCALAPPDATA", helper)
        self.assertIn("git clone", helper)
        self.assertIn("clone --depth 1", helper)
        self.assertIn("pull --ff-only", helper)
        self.assertIn("86box-roms-commit.txt", helper)
        self.assertIn("non-Git ROM folder", helper)
        self.assertNotIn("git reset --hard", helper)
        self.assertIn("Setup-86Box-ROMs.ps1", build)

    def test_iso_staged_scripts_are_writable_and_service_statuses_are_scalar(self):
        provision = self.read("Provision-Lab.ps1")
        verifier = self.read("Verify-Lab.ps1")
        self.assertIn("Where-Object { $_.IsReadOnly }", provision)
        self.assertIn("$_.IsReadOnly = $false", provision)
        self.assertIn("function Get-OptionalServiceStatus", verifier)
        self.assertIn("return 'NotInstalled'", verifier)
        self.assertIn("return [string]$service.Status", verifier)
        for field in ("sshd", "guestAdditionsService", "vmwareToolsService"):
            self.assertIn(field + "=(Get-OptionalServiceStatus ", verifier)

    def test_verification_survives_absent_optional_registry_policy(self):
        verifier = self.read("Verify-Lab.ps1")
        self.assertIn("Set-StrictMode -Version Latest", verifier)
        self.assertIn("function Get-OptionalRegistryValue", verifier)
        self.assertIn("$entry.PSObject.Properties[$Name]", verifier)
        for key in (
            "deliveryOptimizationPolicy", "allowTelemetry",
            "taskbarSearchMode", "taskbarNewsMode", "feedsPolicy"
        ):
            self.assertIn(key + "=(Get-OptionalRegistryValue ", verifier)
        for direct_access in (
            ").DODownloadMode", ").AllowTelemetry", ").SearchboxTaskbarMode",
            ").ShellFeedsTaskbarViewMode", ").EnableFeeds"
        ):
            self.assertNotIn(direct_access, verifier)

    def test_guest_stage_before_online_install(self):
        s = self.read("Provision-Lab.ps1")
        self.assertLess(s.index("'Configure-LabWorkstation.ps1'"),s.index("googlechromestandaloneenterprise64.msi"))
        self.assertLess(s.index("'Install-LabGuestAdditions.ps1'"),s.index("googlechromestandaloneenterprise64.msi"))

if __name__ == "__main__":
    unittest.main()
