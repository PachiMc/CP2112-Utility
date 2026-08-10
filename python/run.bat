@echo off
:: ============================================================
::  CP2112 Battery Analyzer — Windows launcher
::  Double-click this file to start the application.
:: ============================================================
title CP2112 Battery Analyzer

:: Try the Windows py launcher first, fall back to python
where py >nul 2>&1
if %ERRORLEVEL% == 0 (
    py -3 -m pyreader
) else (
    python -m pyreader
)

:: If python itself fails, show a helpful message
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Could not launch the application.
    echo Make sure Python 3.11+ is installed and PySide6 is available:
    echo.
    echo     pip install -r requirements.txt
    echo.
    pause
)
