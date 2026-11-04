@echo off
rem The SetupComplete hook runs as SYSTEM. Do NOT reboot from this hook.
rem Register a one-time logon provisioning task as fallback for VirtualBox's
rem own unattended setup, which has no FirstLogonCommands in our answer file.
if not exist C:\DeskMateLab\Provision-Lab.ps1 exit /b 1
rem Lab mode uses FirstLogonCommands with a real admin user's WinGet context.
findstr /i /x "VirtualBox" C:\DeskMateLab\installation-mode.txt >nul 2>&1 || exit /b 0
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$a=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -ExecutionPolicy Bypass -File C:\DeskMateLab\Provision-Lab.ps1';$t=New-ScheduledTaskTrigger -AtLogOn;Register-ScheduledTask -TaskName 'DeskMateLab-FirstLogon' -Action $a -Trigger $t -User 'SYSTEM' -RunLevel Highest -Force | Out-Null"
exit /b 0
