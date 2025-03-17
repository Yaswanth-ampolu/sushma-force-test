@echo off
echo Installing dependencies for Spring Force Test File Converter...

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in the PATH.
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Upgrade pip and install dependencies
python -m pip install --upgrade pip
python -m pip install tk

echo.
echo Dependencies installed successfully.
echo.
echo You can now run the application using run_converter.bat
pause 