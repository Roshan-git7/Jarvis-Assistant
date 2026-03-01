$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

Write-Host "[JARVIS] Starting PowerShell launcher..."

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[JARVIS] Creating virtual environment..."
    try {
        py -3 -m venv .venv
    }
    catch {
        python -m venv .venv
    }
}

& ".\.venv\Scripts\Activate.ps1"

if (-not (Test-Path ".deps_installed")) {
    Write-Host "[JARVIS] Installing dependencies (first run)..."
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    New-Item -Path ".deps_installed" -ItemType File -Force | Out-Null
}

if ((-not (Test-Path ".env")) -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env" -Force
}

Write-Host "[JARVIS] Launching assistant..."
python .\jarvis.py

Write-Host ""
Write-Host "[JARVIS] Assistant stopped."
Read-Host "Press Enter to close"
