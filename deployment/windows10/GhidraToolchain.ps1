#requires -Version 5.1
<#
.SYNOPSIS
    Shared evidence-based Ghidra/JDK discovery for the lab scripts.
.DESCRIPTION
    Dot-source this file, then call Get-LabGhidraToolchain or the individual
    helpers. Every answer comes from metadata the installation records about
    itself:

    * Ghidra: Ghidra/application.properties (version, build date, revision,
      minimum Java).
    * JDK: the JDK's own release file (JAVA_VERSION).

    A launcher script's presence is never sufficient to claim a working
    installation, and a directory name is never evidence of a Java version.
    Nothing here writes an environment variable, starts a JVM, or modifies an
    installation or project.

    Java candidate precedence, highest first, mirrors
    tools/ghidra/ghidra_toolchain.py: explicit argument, environment
    (GHIDRA_JAVA_HOME then JAVA_HOME), Ghidra's launch.properties
    JAVA_HOME_OVERRIDE, then discovered installations.
#>

function Read-LabKeyValueFile {
    # Returns a case-insensitive map of key=value lines, ignoring comments.
    param([Parameter(Mandatory)][string]$Path)
    $map = @{}
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $map }
    foreach ($line in Get-Content -LiteralPath $Path -ErrorAction Stop) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#')) { continue }
        $index = $trimmed.IndexOf('=')
        if ($index -lt 1) { continue }
        $key = $trimmed.Substring(0, $index).Trim()
        $value = $trimmed.Substring($index + 1).Trim().Trim('"')
        $map[$key] = $value
    }
    return $map
}

function Get-LabJavaMajor {
    # Major version from a JDK's release file, or $null when unprovable.
    # The parameter is not named $home: PowerShell's $HOME is read-only.
    param([string]$JavaHomePath)
    if (-not $JavaHomePath) { return $null }
    $map = Read-LabKeyValueFile -Path (Join-Path $JavaHomePath 'release')
    if (-not $map.ContainsKey('JAVA_VERSION')) { return $null }
    $parts = ([string]$map['JAVA_VERSION']).Replace('_', '.').Split('.')
    $major = 0
    if (-not [int]::TryParse([string]$parts[0], [ref]$major)) { return $null }
    if ($major -eq 1 -and $parts.Length -gt 1) {
        $legacy = 0
        if ([int]::TryParse([string]$parts[1], [ref]$legacy)) { return $legacy }
        return $null
    }
    return $major
}

function Get-LabGhidraInstall {
    # Identity of one Ghidra installation, read from its own version record.
    param([Parameter(Mandatory)][string]$InstallDir)
    $record = [ordered]@{
        install_dir = $InstallDir
        launcher = $false
        version = $null
        build_date = $null
        revision = $null
        java_min = $null
        error = $null
    }
    if (-not (Test-Path -LiteralPath $InstallDir -PathType Container)) {
        $record.error = 'directory does not exist'
        return $record
    }
    $record.launcher = Test-Path -LiteralPath (Join-Path $InstallDir 'support\analyzeHeadless.bat') -PathType Leaf
    if (-not $record.launcher) {
        $record.error = 'no headless launcher'
        return $record
    }
    $propertiesPath = Join-Path $InstallDir 'Ghidra\application.properties'
    $map = Read-LabKeyValueFile -Path $propertiesPath
    if ($map.Count -eq 0) {
        $record.error = 'no Ghidra/application.properties, so the version is unproven'
        return $record
    }
    if ($map.ContainsKey('application.version')) { $record.version = $map['application.version'] }
    if ($map.ContainsKey('application.build.date')) { $record.build_date = $map['application.build.date'] }
    if ($map.ContainsKey('application.revision.ghidra')) { $record.revision = $map['application.revision.ghidra'] }
    if ($map.ContainsKey('application.java.min')) {
        $minimum = 0
        $raw = ([string]$map['application.java.min']).Split('.')[0]
        if ([int]::TryParse($raw, [ref]$minimum)) { $record.java_min = $minimum }
    }
    if (-not $record.version) {
        $record.error = 'application.properties records no application.version'
    }
    return $record
}

function Find-LabGhidraInstalls {
    # Ghidra directories under the given roots, newest name last.
    param([string[]]$Roots)
    $found = New-Object System.Collections.Generic.List[string]
    foreach ($root in $Roots) {
        if (-not $root) { continue }
        if (-not (Test-Path -LiteralPath $root -PathType Container)) { continue }
        Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like 'ghidra*' } |
            ForEach-Object { $found.Add($_.FullName) }
    }
    return $found
}

function Find-LabJavaHomes {
    # JDK homes under vendor directories and unpacked archives alike.
    param([string[]]$Roots)
    $homes = New-Object System.Collections.Generic.List[string]
    foreach ($root in $Roots) {
        if (-not $root) { continue }
        if (-not (Test-Path -LiteralPath $root -PathType Container)) { continue }
        foreach ($vendor in @('Eclipse Adoptium', 'Java', 'Microsoft', 'Amazon Corretto')) {
            $base = Join-Path $root $vendor
            if (-not (Test-Path -LiteralPath $base -PathType Container)) { continue }
            Get-ChildItem -LiteralPath $base -Directory -ErrorAction SilentlyContinue |
                ForEach-Object { $homes.Add($_.FullName) }
        }
        Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like 'jdk*' -or $_.Name -like 'jre*' } |
            ForEach-Object { $homes.Add($_.FullName) }
    }
    return $homes
}

function Select-LabJavaHome {
    # First candidate proving a major version at or above the requirement.
    param(
        [Parameter(Mandatory)][int]$JavaMin,
        [string[]]$Candidates
    )
    $rejected = New-Object System.Collections.Generic.List[object]
    $selected = $null
    $selectedMajor = $null
    # The same home arrives spelled several ways (environment values keep a
    # trailing separator, PATH-derived paths do not), so compare normalised.
    $seen = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
    foreach ($candidateHome in $Candidates) {
        if (-not $candidateHome) { continue }
        $normalized = $candidateHome
        try {
            $normalized = [System.IO.Path]::GetFullPath($candidateHome).TrimEnd('\')
        } catch {
            $normalized = $candidateHome.TrimEnd('\')
        }
        if (-not $seen.Add($normalized)) { continue }
        if (-not (Test-Path -LiteralPath (Join-Path $candidateHome 'bin\java.exe') -PathType Leaf)) {
            $rejected.Add([ordered]@{ home = $candidateHome; reason = 'no bin\java.exe' })
            continue
        }
        $major = Get-LabJavaMajor -JavaHomePath $candidateHome
        if ($null -eq $major) {
            $rejected.Add([ordered]@{
                    home = $candidateHome
                    reason = 'release metadata records no parseable JAVA_VERSION'
                })
            continue
        }
        if ($major -lt $JavaMin) {
            $rejected.Add([ordered]@{
                    home = $candidateHome
                    reason = ("major {0} is below the required {1}" -f $major, $JavaMin)
                })
            continue
        }
        $selected = $candidateHome
        $selectedMajor = $major
        break
    }
    # .ToArray() rather than @($rejected): PowerShell 5.1 mis-binds the array
    # subexpression of a generic List when it becomes a dictionary value.
    return [ordered]@{
        selected = $selected
        major = $selectedMajor
        required_min = $JavaMin
        rejected = $rejected.ToArray()
    }
}

function Get-LabGhidraToolchain {
    <#
    .SYNOPSIS
        Report every installation and select one compatible Ghidra/JDK pair.
    .DESCRIPTION
        PreferredVersion pins a release (for example '12.2'); without it the
        highest proven version wins. An explicitly supplied JavaHome that is
        incompatible is reported as a problem rather than silently replaced.
    #>
    param(
        [string]$PreferredVersion,
        [string[]]$Roots = @('C:\Tools', $env:ProgramFiles),
        [string]$JavaHome
    )
    $installs = New-Object System.Collections.Generic.List[object]
    foreach ($directory in (Find-LabGhidraInstalls -Roots $Roots)) {
        $installs.Add((Get-LabGhidraInstall -InstallDir $directory))
    }
    if ($PreferredVersion) {
        $explicitDir = Join-Path 'C:\Tools' ('ghidra_{0}_PUBLIC' -f $PreferredVersion)
        $known = $false
        foreach ($record in $installs) {
            if ($record.install_dir -eq $explicitDir) { $known = $true; break }
        }
        if (-not $known -and (Test-Path -LiteralPath $explicitDir -PathType Container)) {
            $installs.Add((Get-LabGhidraInstall -InstallDir $explicitDir))
        }
    }

    $usable = @($installs | Where-Object { -not $_.error })
    $selected = $null
    if ($PreferredVersion) {
        $selected = $usable | Where-Object { $_.version -eq $PreferredVersion } | Select-Object -First 1
    }
    if ($null -eq $selected -and $usable.Count -gt 0) {
        $selected = $usable | Sort-Object { [version]($_.version -replace '[^0-9.]', '') } |
            Select-Object -Last 1
    }

    $candidates = New-Object System.Collections.Generic.List[string]
    if ($JavaHome) { $candidates.Add($JavaHome) }
    if ($env:GHIDRA_JAVA_HOME) { $candidates.Add($env:GHIDRA_JAVA_HOME) }
    if ($env:JAVA_HOME) { $candidates.Add($env:JAVA_HOME) }
    $machineHome = [Environment]::GetEnvironmentVariable('JAVA_HOME', 'Machine')
    if ($machineHome) { $candidates.Add($machineHome) }
    if ($null -ne $selected) {
        $launch = Read-LabKeyValueFile -Path (Join-Path $selected.install_dir 'support\launch.properties')
        if ($launch.ContainsKey('JAVA_HOME_OVERRIDE')) { $candidates.Add($launch['JAVA_HOME_OVERRIDE']) }
    }
    $javaOnPath = Get-Command java.exe -ErrorAction SilentlyContinue
    if ($null -ne $javaOnPath -and $javaOnPath.Source) {
        $candidates.Add((Split-Path -Parent (Split-Path -Parent $javaOnPath.Source)))
    }
    foreach ($discoveredHome in (Find-LabJavaHomes -Roots $Roots)) {
        $candidates.Add($discoveredHome)
    }

    $javaSelection = $null
    if ($null -ne $selected) {
        $javaSelection = Select-LabJavaHome -JavaMin $selected.java_min -Candidates $candidates
    }

    $explicitProblem = $null
    if ($JavaHome -and $null -ne $javaSelection -and $javaSelection.selected -ne $JavaHome) {
        $explicitProblem = "The requested Java home was rejected: $JavaHome"
    }
    if ($null -eq $selected) {
        $explicitProblem = 'No Ghidra installation proved a usable version.'
    } elseif ($null -ne $javaSelection -and -not $javaSelection.selected) {
        $explicitProblem = ("No Java home records major {0} or newer." -f $selected.java_min)
    }

    $compatible = $false
    if ($null -ne $selected -and $null -ne $javaSelection) {
        if ($javaSelection.selected -and -not $explicitProblem) { $compatible = $true }
    }

    # Built field by field rather than as one literal: PowerShell 5.1
    # mis-binds a literal whose values mix collection, bool and null.
    $result = [ordered]@{}
    $result['preferred_version'] = $PreferredVersion
    $result['installs'] = $installs.ToArray()
    $result['selected'] = $selected
    $result['java'] = $javaSelection
    $result['compatible'] = $compatible
    $result['problem'] = $explicitProblem
    $result['precedence'] = @('explicit', 'environment', 'launch-override', 'discovery')
    return $result
}
