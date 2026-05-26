@echo off
REM run_local.cmd — Smogon ETL Pipeline (Windows batch launcher)
REM Usage: run_local.cmd [--format gen9ou] [--test] [--skip-discover]

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Installing dependencies...
.venv\Scripts\python -m pip install -q -r requirements.txt -r airflow\requirements-airflow.txt

if "%1"=="--test" (
    .venv\Scripts\python run_local.py --test
) else (
    .venv\Scripts\python run_local.py %*
)
