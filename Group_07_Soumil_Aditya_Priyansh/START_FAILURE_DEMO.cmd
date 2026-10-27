@echo off
setlocal
cd /d "%~dp0"
set "PROJECT_PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PROJECT_PYTHON=%~dp0.venv\Scripts\python.exe"
"%PROJECT_PYTHON%" -B run_hospital_cleaning.py --scene assessment --seed 2011 --keep-open --cinematic --speed 2 --output-dir analytics/demo_failure %*
if errorlevel 1 pause
