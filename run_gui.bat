@echo off
title All-in-One Image and PDF Studio - Desktop GUI
cd /d "%~dp0"
python gui_app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo An error occurred while launching the desktop application.
    pause
)
