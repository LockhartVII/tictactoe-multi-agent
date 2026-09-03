param(
    [string]$EnvironmentName = "tictactoe-gpu"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

conda --version | Out-Null
$existing = conda env list | Select-String "^$EnvironmentName\s"
if (-not $existing) {
    conda create -n $EnvironmentName python=3.11 -y
}

conda run -n $EnvironmentName python -m pip install --upgrade pip
conda run -n $EnvironmentName python -m pip install -r (Join-Path $projectRoot "requirements.txt")
conda run -n $EnvironmentName python -m pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124
Write-Host "Environment ready: $EnvironmentName"
Write-Host "Run with: conda run -n $EnvironmentName python upgrade.py"
