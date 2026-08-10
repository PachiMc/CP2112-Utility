@echo off
:: Build standalone Windows executable
title CP2112 Battery Analyzer — Build

cd /d "%~dp0"

where py >nul 2>&1
if %ERRORLEVEL% == 0 (
    set PY=py -3
) else (
    set PY=python
)

echo Installing dependencies...
%PY% -m pip install --upgrade pip
%PY% -m pip install -r requirements.txt pyinstaller
if %ERRORLEVEL% NEQ 0 goto :error

if not exist "vendor\SLABHIDtoSMBus.dll" (
    echo.
    echo ERROR: vendor\SLABHIDtoSMBus.dll not found.
    echo See vendor\README.md for instructions.
    goto :error
)
if not exist "vendor\SLABHIDDevice.dll" (
    echo.
    echo ERROR: vendor\SLABHIDDevice.dll not found.
    echo See vendor\README.md for instructions.
    goto :error
)

echo.
echo Building standalone executable...
%PY% -m PyInstaller packaging\cp2112_analyzer.spec --noconfirm
if %ERRORLEVEL% NEQ 0 goto :error

echo.
echo Build complete: dist\CP2112-Battery-Analyzer.exe
goto :end

:error
echo.
echo Build failed.
pause
exit /b 1

:end
pause
