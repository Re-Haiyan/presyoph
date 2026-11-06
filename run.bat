@echo off
rem PresyoPH launcher for Windows: sets up the environment on first run, then starts the app.
setlocal
cd /d "%~dp0"

rem Find a Python that really runs (the Microsoft Store "python" shortcut does not count).
set "PY="
py -3 --version >nul 2>nul && set "PY=py -3"
if not defined PY (
    python --version >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo Python was not found. Install Python 3.10-3.12 from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH", then run this file again.
    echo If you already installed it, turn off the "python" App execution alias in
    echo Settings ^> Apps ^> Advanced app settings ^> App execution aliases.
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PY% -m venv venv
    if errorlevel 1 ( echo Could not create the virtual environment. & pause & exit /b 1 )
)

echo Checking packages (the first run downloads them and can take a few minutes)...
"venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 ( echo Package installation failed. See docs\INSTALLATION.md. & pause & exit /b 1 )

echo Starting PresyoPH at http://localhost:8501  (press Ctrl+C to stop)
"venv\Scripts\python.exe" -m streamlit run app.py
