@echo off
REM Batch script to execute the Python script

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed. Please install Python and try again.
    exit /b 1
)

REM Execute the Python script
python map_germany_plz_integrated_ui.py

REM Pause to keep the command prompt open after execution
pause