@echo off
REM Dashboard Startup Script for Windows

echo ====================================
echo Discord Bot Dashboard Startup
echo ====================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if pip is available
pip --version >nul 2>&1
if errorlevel 1 (
    echo Error: pip is not available
    pause
    exit /b 1
)

REM Install requirements if needed
echo Installing dashboard requirements...
pip install -r requirements.txt

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
    echo Please update the .env file with your Discord credentials!
    pause
)

REM Start the dashboard
echo.
echo Starting Dashboard on http://localhost:5000
echo Press Ctrl+C to stop
echo.

python app.py

pause
