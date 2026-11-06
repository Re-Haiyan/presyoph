@echo off
rem PresyoPH launcher for Windows: sets up the environment on first run, then starts the app.
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Install Python 3.10-3.12 from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH", then run this file again.
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 ( echo Could not create the virtual environment. & pause & exit /b 1 )
)

echo Checking packages (the first run downloads them and can take a few minutes)...
"venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 ( echo Package installation failed. See docs\INSTALLATION.md. & pause & exit /b 1 )

echo Starting PresyoPH at http://localhost:8501  (press Ctrl+C to stop)
"venv\Scripts\python.exe" -m streamlit run app.py
