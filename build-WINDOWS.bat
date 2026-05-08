@echo off
REM Build a map. Double-click to run.

cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo   Python is not installed.
    echo   Open Microsoft Store, search for "Python", and click Install.
    echo.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo.
    echo   First run. Setting up Python environment ...
    echo.
    python -m venv .venv
    .venv\Scripts\pip install --upgrade pip -q
    .venv\Scripts\pip install -r scripts\requirements.txt -q
    echo.
    echo   Environment ready.
    echo.
)

.venv\Scripts\python scripts\build_map.py

echo.
pause
