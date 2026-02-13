@echo off
REM Train Route Visualizer Launcher (Windows)
REM Auto-creates virtual environment and installs dependencies

setlocal

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed. Please install Python 3.8+ and try again.
    pause
    exit /b 1
)

REM Auto-create venv on first run
if not exist "%VENV_DIR%" (
    echo 🔧 First run — setting up virtual environment...
    python -m venv "%VENV_DIR%"
    echo ✓ Virtual environment created
)

REM Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"

REM Install dependencies only if requirements.txt changed
set "DEPS_MARKER=%VENV_DIR%\.deps_installed"
if not exist "%DEPS_MARKER%" goto install_deps
for %%i in ("%SCRIPT_DIR%requirements.txt") do set "REQ_TIME=%%~ti"
for %%i in ("%DEPS_MARKER%") do set "MARKER_TIME=%%~ti"
if "%REQ_TIME%" gtr "%MARKER_TIME%" goto install_deps
goto run_app

:install_deps
echo 📦 Installing dependencies...
python -m pip install --upgrade pip --quiet
python -m pip install -r "%SCRIPT_DIR%requirements.txt" --quiet
type nul > "%DEPS_MARKER%"
echo ✓ Dependencies installed

:run_app
REM Run the application
echo.
echo 🚂 Starting Train Route Visualizer...
echo.
python "%SCRIPT_DIR%app.py"

REM Pause to keep the command prompt open after execution
pause