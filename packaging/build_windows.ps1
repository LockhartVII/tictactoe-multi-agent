$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\")).Path
$python = "C:\Users\Ywt\anaconda3\envs\tictactoe-gpu\python.exe"
$pyinstaller = Join-Path (Split-Path $python) "Scripts\pyinstaller.exe"

if (-not (Test-Path $python)) {
    throw "The tictactoe-gpu Python environment was not found: $python"
}
if (-not (Test-Path $pyinstaller)) {
    throw "PyInstaller was not found. Install it with: $python -m pip install pyinstaller"
}

Push-Location $projectRoot
try {
    if (Test-Path dist) { Remove-Item dist -Recurse -Force }
    if (Test-Path build) { Remove-Item build -Recurse -Force }
    if (Test-Path release) { Remove-Item release -Recurse -Force }
    New-Item -ItemType Directory -Path release | Out-Null

    & $pyinstaller --noconfirm --clean packaging\MultiAgentBoardLab.spec

    $iscc = Get-Command iscc.exe -ErrorAction SilentlyContinue
    $isccPath = if ($iscc) { $iscc.Source } else { $null }
    if (-not $isccPath) {
        $localIscc = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"
        if (Test-Path $localIscc) {
            $isccPath = $localIscc
        }
    }
    if (-not $isccPath) {
        throw "Inno Setup was not found. Install Inno Setup, then run this script again."
    }
    & $isccPath packaging\MultiAgentBoardLab.iss
    Write-Output "Installer created: $projectRoot\release\QizhiAgent-Setup.exe"
}
finally {
    Pop-Location
}
