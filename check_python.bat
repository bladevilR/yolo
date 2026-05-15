@echo off
REM Python Environment Detection Script
echo.
echo ============================================================
echo   Python Environment Detection
echo ============================================================
echo.

echo Searching for Python installations...
echo.

REM Check python command
echo [1] Testing 'python' command:
where python 2>nul
if %errorlevel% equ 0 (
    python --version 2>nul
    echo.
) else (
    echo    NOT FOUND
    echo.
)

REM Check python3 command
echo [2] Testing 'python3' command:
where python3 2>nul
if %errorlevel% equ 0 (
    python3 --version 2>nul
    echo.
) else (
    echo    NOT FOUND
    echo.
)

REM Check py launcher
echo [3] Testing 'py' launcher (recommended on Windows):
where py 2>nul
if %errorlevel% equ 0 (
    py --version 2>nul
    echo    Available Python versions:
    py --list 2>nul
    echo.
) else (
    echo    NOT FOUND
    echo.
)

REM Check common installation paths
echo [4] Checking common Python installation paths:
echo.

if exist "C:\Python*\" (
    dir /b "C:\Python*" 2>nul
)

if exist "%LOCALAPPDATA%\Programs\Python\" (
    echo    Found: %LOCALAPPDATA%\Programs\Python\
    dir /b "%LOCALAPPDATA%\Programs\Python\" 2>nul
)

if exist "%PROGRAMFILES%\Python*\" (
    dir /b "%PROGRAMFILES%\Python*" 2>nul
)

if exist "%USERPROFILE%\Anaconda3\" (
    echo    Found: Anaconda3 at %USERPROFILE%\Anaconda3
)

if exist "%USERPROFILE%\miniconda3\" (
    echo    Found: Miniconda3 at %USERPROFILE%\miniconda3
)

echo.
echo ============================================================
echo   Recommendation
echo ============================================================
echo.
echo Option 1: Use 'py' launcher (recommended for Windows)
echo    py -m pip install -r requirements.txt
echo    py auto_train.py
echo.
echo Option 2: Install fresh Python 3.10+ from python.org
echo    https://www.python.org/downloads/
echo    Check "Add Python to PATH" during installation
echo.
echo Option 3: Use Anaconda/Miniconda
echo    conda create -n yolo python=3.10
echo    conda activate yolo
echo    pip install -r requirements.txt
echo.
echo ============================================================
echo.
pause
