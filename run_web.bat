@echo off
title All-in-One Image and PDF Studio - Web UI
cd /d "%~dp0"
python web_app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo An error occurred while launching the web server.
    pause
)
