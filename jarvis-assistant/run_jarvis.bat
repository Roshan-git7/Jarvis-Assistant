@echo off
setlocal
cd /d "%~dp0"

echo [JARVIS] Starting launcher...

if not exist ".venv\Scripts\python.exe" (
  echo [JARVIS] Creating virtual environment...
  py -3 -m venv .venv 2>nul
  if errorlevel 1 python -m venv .venv
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 (
  echo [JARVIS] Failed to activate virtual environment.
  pause
  exit /b 1
)

if not exist ".deps_installed" (
  echo [JARVIS] Installing dependencies (first run)...
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [JARVIS] Dependency installation failed.
    pause
    exit /b 1
  )
  type nul > .deps_installed
)

if not exist ".env" if exist ".env.example" (
  copy /Y ".env.example" ".env" >nul
)

echo [JARVIS] Launching assistant...
python jarvis.py

echo.
echo [JARVIS] Assistant stopped.
pause
endlocal
