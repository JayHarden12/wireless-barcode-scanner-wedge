@echo off
TITLE Your Company • Wireless Barcode Scanner Wedge
COLOR 0B

echo ==============================================================================
echo   YOUR COMPANY - WIRELESS BARCODE SCANNER WEDGE (WINDOWS)
echo ==============================================================================
echo.

:: 1. Check if Python is installed
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not found on this Windows PC!
    echo Please download and install Python from https://www.python.org/downloads/
    echo (Make sure to check "Add Python to PATH" during installation)
    echo.
    pause
    exit /b
)

:: 2. Check if Flask is installed, install if needed
python -c "import flask" >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [SETUP] Installing required Flask library...
    pip install flask --quiet
)

:: 3. Launch the browser to the web dashboard after 1.5 seconds
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:5000"

:: 4. Start the Scanner Wedge Python Server
echo [RUNNING] Starting Wireless Scanner Server on port 5000...
echo Keep this window open while scanning. Close this window or press Ctrl+C to quit.
echo ==============================================================================
echo.
python zoho_scanner_wedge.py

pause
