# Thin launcher; engine and configuration remain separately editable.
[CmdletBinding()]
param(
    [string]$Config,
    [string]$Target,
    [switch]$PolicyChecked,
    [switch]$Status,
    [switch]$Stop,
    [switch]$ClearStop,
    [switch]$RetryUnavailable,
    [ValidateRange(0,2147483647)][int]$MaxItems = 0
)
$ErrorActionPreference = 'Stop'
# Resolve the script directory after parameter binding (Windows PowerShell 5.1).
$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $Config) { $Config = Join-Path $scriptDir 'mirror-targets.example.toml' }
$python = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command py.exe -ErrorAction Stop }
$argv = @()
if ($python.Name -ieq 'py.exe') { $argv += '-3' }
$argv += @('-u', (Join-Path $scriptDir 'archive_mirror.py'), '--config', $Config, '--max-items', "$MaxItems")
if ($Target) { $argv += @('--target', $Target) }
if ($PolicyChecked) { $argv += '--policy-checked' }
if ($Status) { $argv += '--status' }
if ($Stop) { $argv += '--stop' }
if ($ClearStop) { $argv += '--clear-stop' }
if ($RetryUnavailable) { $argv += '--retry-unavailable' }
& $python.Source @argv
exit $LASTEXITCODE
