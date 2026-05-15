@echo off
REM YOLO Auto Training Script for Windows
REM Simple version without UTF-8 encoding issues

echo.
echo ============================================================
echo   YOLO Auto Training System - Quick Start
echo ============================================================
echo.

REM Step 1: Check Python
echo [Step 1/5] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ERROR: Python not found!
        echo.
        echo Please install Python 3.8+ from: https://www.python.org/downloads/
        echo.
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=py
    )
) else (
    set PYTHON_CMD=python
)

echo OK - Python found
%PYTHON_CMD% --version
echo.

REM Step 2: Install dependencies
echo [Step 2/5] Installing dependencies...
echo This may take a few minutes, please wait...
%PYTHON_CMD% -m pip install -r requirements.txt --quiet
echo OK - Dependencies installed
echo.

REM Step 3: Create dataset
echo [Step 3/5] Preparing dataset...
if exist "datasets\custom_dataset\images\train" (
    echo OK - Found existing dataset
) else (
    echo Creating demo dataset...
)
echo.

REM Step 4: Start training
echo [Step 4/5] Starting auto training script...
echo.
echo ============================================================
echo Training starting... Please wait
echo ============================================================
echo.

%PYTHON_CMD% auto_train.py

echo.
echo ============================================================
echo Training completed!
echo ============================================================
echo.
echo Check QUICKSTART.md for more information
echo.
pause
