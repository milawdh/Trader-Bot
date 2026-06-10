param(
    [switch]$FolderBuild,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Get-Python {
    if ($env:PYTHON) {
        return $env:PYTHON
    }
    $executable = (& py -3.13 -c "import sys; print(sys.executable)").Trim()
    if (-not $executable) {
        throw "Python 3.13 was not found. Install 64-bit Python or set PYTHON to python.exe."
    }
    return $executable
}

$Python = Get-Python
Write-Host "Using Python: $Python"

& $Python -c "import sys; raise SystemExit(0 if sys.maxsize > 2**32 else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller/PySide6 build requires 64-bit Python. Current interpreter is 32-bit."
}

Write-Host "Installing build dependencies..."
& $Python -m pip install -e . pyinstaller

if (-not $SkipTests) {
    Write-Host "Running tests..."
    & $Python -m pytest -q
}

$ConfigsPath = Join-Path $ProjectRoot "configs"
$SrcPath = Join-Path $ProjectRoot "src"
$PyInstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name", "TraderBot",
    "--paths", $SrcPath,
    "--add-data", "$ConfigsPath;configs",
    "--hidden-import", "MetaTrader5",
    "--hidden-import", "yaml",
    "--collect-all", "PySide6"
)

if (-not $FolderBuild) {
    $PyInstallerArgs += "--onefile"
}

$PyInstallerArgs += "main.py"

Write-Host "Building executable..."
& $Python -m PyInstaller @PyInstallerArgs

if (-not $FolderBuild) {
    $OutputDir = Join-Path $ProjectRoot "dist"
    $ExePath = Join-Path $OutputDir "TraderBot.exe"
} else {
    $OutputDir = Join-Path $ProjectRoot "dist\TraderBot"
    $ExePath = Join-Path $OutputDir "TraderBot.exe"
}

if ($FolderBuild) {
    $ExternalConfigs = Join-Path $OutputDir "configs"
    if (Test-Path -LiteralPath $ExternalConfigs) {
        Remove-Item -LiteralPath $ExternalConfigs -Recurse -Force
    }
    Copy-Item -LiteralPath $ConfigsPath -Destination $ExternalConfigs -Recurse -Force
}

Write-Host ""
Write-Host "Build complete:"
Write-Host $ExePath
Write-Host ""
if ($FolderBuild) {
    Write-Host "For delivery, send the whole output folder because -FolderBuild was used."
} else {
    Write-Host "For delivery, send only TraderBot.exe."
}
Write-Host "The app does not require Python on the target machine."
