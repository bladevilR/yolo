@echo off
REM Quick Setup Script - Auto-detect best Python and install
echo.
echo ============================================================
echo   YOLO Training System - Smart Setup
echo ============================================================
echo.

REM Try to find the best Python
set PYTHON_CMD=

REM Method 1: Try py launcher (best for Windows)
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    echo [OK] Found Python via 'py' launcher
    py --version
    goto :found_python
)

REM Method 2: Try python command
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    echo [OK] Found Python via 'python' command
    python --version
    goto :found_python
)

REM Method 3: Try python3 command
python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python3
    echo [OK] Found Python via 'python3' command
    python3 --version
    goto :found_python
)

REM No Python found
echo [ERROR] No Python installation found!
echo.
echo Please install Python 3.8+ from:
echo https://www.python.org/downloads/
echo.
echo OR run 'check_python.bat' to see all Python installations
echo.
pause
exit /b 1

:found_python
echo.
echo ============================================================
echo   Installing Dependencies
echo ============================================================
echo.
echo Installing required packages...
echo This will take 2-5 minutes...
echo.

%PYTHON_CMD% -m pip install --upgrade pip
%PYTHON_CMD% -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo [WARNING] Some packages may have failed to install
    echo But continuing anyway...
    echo.
)

echo.
echo ============================================================
echo   Setup Complete!
echo ============================================================
echo.
echo Now you can:
echo   1. Run: %PYTHON_CMD% auto_train.py
echo   2. Or double-click: RUN_AUTO_TRAIN.bat
echo.
echo Python command to use: %PYTHON_CMD%
echo.
pause
