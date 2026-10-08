@echo off
title IntegrityShield — AI Proctoring System
echo.
echo ============================================================
echo    IntegrityShield - AI Exam Proctoring System
echo ============================================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install from https://python.org
    pause & exit /b 1
)

REM Check/create virtual environment
if not exist "venv\Scripts\activate.bat" (
    echo [SETUP] Creating virtual environment...
    python -m venv venv
)

REM Activate venv
call venv\Scripts\activate.bat

REM Install dependencies
echo [SETUP] Checking dependencies...
pip install -r requirements.txt -q

REM Create required directories
if not exist "logs" mkdir logs
if not exist "static\models" mkdir static\models

echo.
echo [OK] Starting server on http://localhost:5000
echo [OK] Press Ctrl+C to stop
echo.

python app.py
pause
