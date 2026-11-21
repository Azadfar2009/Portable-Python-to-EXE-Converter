@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Setup Portable Python Environment
color 0B

:: ====================================================
::  setup_env.bat
::  Builds or repairs the portable 'env' folder.
::  Python + pip + tkinter + tool dependencies.
::  Files already inside 'env' (PyLauncher.py, converter_gui.py)
::  are NEVER deleted or overwritten by this script.
::
::  Offline use: download the .nupkg from PY_URL below, rename it to
::  python.zip and put it next to this script.
:: ====================================================

set "PY_VERSION=3.11.9"
set "PY_URL=https://www.nuget.org/api/v2/package/python/%PY_VERSION%"

:: Go to the repo root (this file lives in \scripts)
cd /d "%~dp0.."

set "WORK=%TEMP%\PyLauncher_Setup"
set "ZIP=%WORK%\python.zip"
set "EXTRACT=%WORK%\extracted"
set "PY=env\python.exe"

echo ====================================================
echo  Portable environment setup - Python %PY_VERSION%
echo ====================================================
echo.

if exist "%PY%" goto :have_python

:: ---------- 1/4 get Python ----------
if exist "%WORK%" rmdir /s /q "%WORK%"
mkdir "%WORK%"

echo [1/4] Getting Python %PY_VERSION% ...
if exist "%~dp0python.zip" (
    echo       Using local file: scripts\python.zip
    copy /y "%~dp0python.zip" "%ZIP%" >nul
) else (
    echo       Downloading from nuget.org ...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%ZIP%' -UseBasicParsing"
)
if errorlevel 1 goto :err_download
if not exist "%ZIP%" goto :err_download

:: ---------- 2/4 extract into env ----------
echo [2/4] Extracting into 'env' ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%ZIP%' -DestinationPath '%EXTRACT%' -Force"
if errorlevel 1 goto :err_extract
if not exist "%EXTRACT%\tools\python.exe" goto :err_extract

if not exist "env" mkdir "env"
echo       Copying files (This might take a minute)...
xcopy "%EXTRACT%\tools\*" "env\" /E /I /Y /Q >nul
if errorlevel 1 goto :err_copy
rmdir /s /q "%WORK%"
goto :check_python

:have_python
echo [1/4] env\python.exe already exists - skipping download.
echo [2/4] Skipped.

:: ---------- 3/4 pip + tkinter ----------
:check_python
echo [3/4] Checking pip and tkinter ...
"%PY%" -m pip --version >nul 2>nul
if errorlevel 1 (
    echo       pip not found - running ensurepip ...
    "%PY%" -m ensurepip --upgrade
    if errorlevel 1 goto :err_pip
)
"%PY%" -m pip install --upgrade pip --no-warn-script-location --quiet
"%PY%" -c "import tkinter" >nul 2>nul
if errorlevel 1 goto :err_tk

:: ---------- 4/4 packages ----------
echo.
echo [4/4] Install packages
echo       1. Minimal (PyInstaller, packaging, tkinterdnd2)
echo       2. Full    (requirements.txt - includes pandas, numpy, etc)
echo       3. Skip    (Exit without installing)
choice /c 123 /n /m "      Select an option [1, 2, or 3]: "

if errorlevel 3 goto :verify
if errorlevel 2 goto :full

"%PY%" -m pip install --no-warn-script-location pyinstaller packaging tkinterdnd2
if errorlevel 1 goto :err_pkgs
goto :verify

:full
if not exist "requirements.txt" (
    echo [WARNING] requirements.txt not found in the project root.
    echo           Installing minimal packages instead...
    "%PY%" -m pip install --no-warn-script-location pyinstaller packaging tkinterdnd2
    goto :verify
)
echo       Installing from requirements.txt...
"%PY%" -m pip install --no-warn-script-location -r requirements.txt
if errorlevel 1 goto :err_pkgs

:verify
echo.
echo       Verifying installation...
"%PY%" -c "import tkinter, PyInstaller, tkinterdnd2; print('OK: Core modules are healthy.')"
if errorlevel 1 goto :err_verify

echo.
echo ====================================================
echo [SUCCESS] Portable environment is ready.
echo ====================================================
echo You can now run RunConverter.bat from the root folder,
echo or scripts\Build.bat to build PyLauncher.exe.
echo.
pause
exit /b 0

:: ---------- errors ----------
:err_download
echo.
echo [ERROR] Download failed. Check your internet connection or proxy.
echo         Manual way: download the file from the address below, rename it
echo         to python.zip and put it next to this script, then run it again.
echo         %PY_URL%
goto :fail

:err_extract
echo.
echo [ERROR] Could not extract the Python package (tools\python.exe not found).
goto :fail

:err_copy
echo.
echo [ERROR] Could not copy Python files into 'env'.
goto :fail

:err_pip
echo.
echo [ERROR] pip could not be installed with ensurepip.
goto :fail

:err_tk
echo.
echo [ERROR] tkinter is missing from this Python, so the GUI cannot start.
echo         Make sure you are using a Full Python build (NuGet provides this).
goto :fail

:err_pkgs
echo.
echo [ERROR] Package installation failed. See the messages above.
goto :fail

:err_verify
echo.
echo [ERROR] Installed, but import check failed. See the messages above.
goto :fail

:fail
echo.
pause
exit /b 1
