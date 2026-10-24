# Builds Sunny on Windows: creates .venv, installs dependencies, produces dist\Sunny\ with
# PyInstaller and the installer dist\Sunny-X.Y.Z-setup.exe with Inno Setup 6.
#
#   .\build.ps1                 # everything
#   .\build.ps1 -NoInstaller    # only dist\Sunny\Sunny.exe
#   .\build.ps1 -Clean          # removes build\ and dist\ first
#   .\build.ps1 -Test           # runs the tests and stops

param(
    [switch]$NoInstaller,
    [switch]$Clean,
    [switch]$Test
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Native programs (pip, PyInstaller, ISCC) log to stderr and Windows PowerShell 5.1 turns that
# into errors when the output is redirected; run them through cmd to merge both streams.
function Invoke-Native([string]$Command) {
    cmd /c "$Command 2>&1"
    if ($LASTEXITCODE -ne 0) { throw "Failed: $Command" }
}

if ($Clean) {
    Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating .venv..."
    $py = Get-Command py, python, python3 -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $py -and (Test-Path "$env:USERPROFILE\scoop\apps\python\current\python.exe")) {
        $py = Get-Item "$env:USERPROFILE\scoop\apps\python\current\python.exe"
    }
    if (-not $py) { throw "Python 3.11+ not found. Install it (for example: scoop install python)." }
    $pyPath = if ($py.PSObject.Properties['Source']) { $py.Source } else { $py.FullName }
    if ($pyPath -like "*\py.exe") { & $pyPath -3 -m venv .venv } else { & $pyPath -m venv .venv }
}
$python = ".\.venv\Scripts\python.exe"

Write-Host "Installing dependencies..."
Invoke-Native "$python -m pip install --quiet --upgrade pip"
Invoke-Native "$python -m pip install --quiet -r requirements.txt"

if ($Test) {
    Invoke-Native "$python -m pytest -q"
    exit 0
}

$version = (Select-String -Path "sunny\__init__.py" -Pattern '__version__\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value
Write-Host "Sunny ${version}: PyInstaller..."
Invoke-Native "$python -m PyInstaller --noconfirm --clean --log-level WARN sunny.spec"

if ($NoInstaller) {
    Write-Host "Done: dist\Sunny\Sunny.exe"
    exit 0
}

$candidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)
$iscc = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $iscc) {
    $cmd = Get-Command iscc -ErrorAction SilentlyContinue
    if ($cmd) { $iscc = $cmd.Source }
}
if (-not $iscc) {
    throw "Inno Setup 6 (ISCC.exe) not found. Install it from https://jrsoftware.org/isdl.php or use -NoInstaller."
}

Write-Host "Inno Setup..."
Invoke-Native "`"$iscc`" /Q /DMyAppVersion=$version installer\Sunny.iss"

# The updater inside Sunny checks the installer against this file, published next to it in the release.
$setup = "dist\Sunny-$version-setup.exe"
$hash = (Get-FileHash $setup -Algorithm SHA256).Hash.ToLower()
Set-Content -Path "$setup.sha256" -Value "$hash *Sunny-$version-setup.exe" -Encoding ascii -NoNewline

Write-Host "Done: $setup (+ .sha256)"
