<#
.SYNOPSIS
    Sets up VeriGreen-ops on Windows.

.DESCRIPTION
    1. Locates a Python 3.11+ interpreter (preferring real installs over the
       Microsoft Store "WindowsApps" alias stubs).
    2. Creates the project virtual environment (.venv) and installs requirements.txt.
    3. Creates directory junctions .claude\skills and .gemini\skills -> skills\
       (junctions do not require Administrator privileges).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -Path $RepoRoot

Write-Host "==> VeriGreen-ops Windows Setup" -ForegroundColor Cyan
Write-Host "    Repository Root: $RepoRoot"

function Test-PythonVersion {
    <# Returns $true if the given interpreter runs and is Python 3.11+. #>
    param([Parameter(Mandatory)][string]$Exe)

    try {
        $result = & $Exe -c "import sys; print(int(sys.version_info >= (3, 11)))" 2>$null
        return ($LASTEXITCODE -eq 0 -and "$result".Trim() -eq "1")
    } catch {
        Write-Verbose "Interpreter '$Exe' could not be executed: $($_.Exception.Message)"
        return $false
    }
}

function Resolve-Python311 {
    <# Returns the path of the first usable Python 3.11+ interpreter. #>
    $preferred = [System.Collections.Generic.List[string]]::new()
    $storeAliases = [System.Collections.Generic.List[string]]::new()

    $candidates = [System.Collections.Generic.List[string]]::new()
    $localPy = Join-Path -Path $env:LocalAppData -ChildPath "Python\bin\python.exe"
    if (Test-Path -Path $localPy) { $candidates.Add($localPy) }

    $pyLauncher = Get-Command -Name "py" -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        try {
            $py3Path = & $pyLauncher.Source -3 -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $py3Path) { $candidates.Add("$py3Path".Trim()) }
        } catch {
            Write-Verbose "py launcher unavailable: $($_.Exception.Message)"
        }
    }

    foreach ($name in @("python", "python3")) {
        foreach ($cmd in @(Get-Command -Name $name -All -ErrorAction SilentlyContinue)) {
            if ($cmd.Source) { $candidates.Add($cmd.Source) }
        }
    }

    # Real installs first; Microsoft Store alias stubs only as a last resort.
    foreach ($exe in ($candidates | Select-Object -Unique)) {
        if ($exe -like "*\WindowsApps\*") { $storeAliases.Add($exe) } else { $preferred.Add($exe) }
    }

    foreach ($exe in @($preferred) + @($storeAliases)) {
        if (Test-PythonVersion -Exe $exe) { return $exe }
    }
    throw "Python 3.11+ not found. Please install Python 3.11 or newer and re-run."
}

function Install-SkillJunction {
    <# Creates (or recreates) a directory junction LinkPath -> TargetPath. #>
    param(
        [Parameter(Mandatory)][string]$LinkPath,
        [Parameter(Mandatory)][string]$TargetPath
    )

    if (Test-Path -LiteralPath $LinkPath) {
        $item = Get-Item -LiteralPath $LinkPath -Force
        $isReparsePoint = ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0
        if (-not $isReparsePoint) {
            throw "Path '$LinkPath' is a regular directory/file, not a junction. Remove or rename it manually."
        }
        # Non-recursive delete removes only the junction itself, never the skills\ contents.
        [System.IO.Directory]::Delete($LinkPath, $false)
    }

    New-Item -ItemType Junction -Path $LinkPath -Target $TargetPath | Out-Null
    Write-Host "==> Junction created: $LinkPath -> $TargetPath" -ForegroundColor Green
}

# --- 1. Python & virtual environment -------------------------------------------
$PythonExe = Resolve-Python311
Write-Host "==> Using Python: $PythonExe" -ForegroundColor Green

$VenvDir = Join-Path -Path $RepoRoot -ChildPath ".venv"
$VenvPython = Join-Path -Path $VenvDir -ChildPath "Scripts\python.exe"

if (-not (Test-Path -Path $VenvPython)) {
    Write-Host "==> Creating virtual environment (.venv)..." -ForegroundColor Cyan
    & $PythonExe -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw "Failed to create .venv." }
} else {
    Write-Host "==> Existing .venv detected." -ForegroundColor DarkGray
}

# --- 2. Dependencies -----------------------------------------------------------
Write-Host "==> Installing Python requirements..." -ForegroundColor Cyan
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip." }
& $VenvPython -m pip install -r (Join-Path -Path $RepoRoot -ChildPath "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Failed to install requirements.txt." }

# --- 3. Directory scaffold & skill junctions -----------------------------------
$RequiredDirs = @("skills", "src", "data\raw_docs", "data\sample", "output", ".claude", ".gemini")
foreach ($rel in $RequiredDirs) {
    $full = Join-Path -Path $RepoRoot -ChildPath $rel
    if (-not (Test-Path -Path $full)) {
        New-Item -ItemType Directory -Path $full -Force | Out-Null
    }
}

$SkillsTarget = Join-Path -Path $RepoRoot -ChildPath "skills"
Install-SkillJunction -LinkPath (Join-Path -Path $RepoRoot -ChildPath ".claude\skills") -TargetPath $SkillsTarget
Install-SkillJunction -LinkPath (Join-Path -Path $RepoRoot -ChildPath ".gemini\skills") -TargetPath $SkillsTarget

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Activate venv (optional): .\.venv\Scripts\Activate.ps1"
Write-Host "  2. Generate sample corpus:   .\.venv\Scripts\python.exe scripts\create_sample_data.py"
Write-Host "  3. Launch your CLI agent:    claude   (or: gemini)"
