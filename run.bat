@echo off
title All-in-One Image and PDF Studio
cd /d "%~dp0"
cls
echo ================================================================
echo           ALL-IN-ONE IMAGE and PDF LOCAL STUDIO
echo ================================================================
echo.
echo Please choose how you want to open the tool:
echo.
echo   [1] Open Desktop GUI Application (Recommended)
echo   [2] Open Web Browser UI (Chrome / Edge / Firefox)
echo   [3] Exit
echo.
echo ================================================================
set /p choice="Enter your choice (1, 2, or 3): "

if "%choice%"=="1" (
    echo.
    echo Starting Desktop Application...
    start pythonw gui_app.py
    exit
)
if "%choice%"=="2" (
    echo.
    echo Starting Local Web Server...
    python web_app.py
    pause
    exit
)
if "%choice%"=="3" (
    exit
)

echo Invalid choice. Starting Desktop GUI by default...
python gui_app.py
pause
