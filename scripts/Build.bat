@echo off
setlocal
title Auto Build - Python to EXE Converter
color 0B

:: Go to root folder
cd /d "%~dp0.."

if not exist "env\python.exe" (
    echo [ERROR] 'env' folder and python.exe not found!
    pause
    exit /b
)

set "PY_EXE=env\python.exe"
set "CLEANUP="

:: Looking for PyLauncher.py inside env folder
if exist "env\PyLauncher.py" (
    echo [INFO] Found PyLauncher.py inside 'env' folder. Copying to root for build...
    copy "env\PyLauncher.py" "PyLauncher.py" >nul
    set "LAUNCHER=PyLauncher.py"
    set "CLEANUP=1"
) else if exist "PyLauncher.py" (
    set "LAUNCHER=PyLauncher.py"
) else (
    echo [ERROR] 'PyLauncher.py' not found in root or 'env'!
    pause
    exit /b
)

echo ====================================================
echo Building Final PyLauncher.exe
echo ====================================================
echo.

echo [1/3] Cleaning 'env' folder to reduce final size...
if exist "scripts\clean_env.py" (
    %PY_EXE% scripts\clean_env.py
) else (
    echo [WARNING] clean_env.py not found. Skipping size reduction.
)

:: FIX: Use system Temp directory instead of local temp folder
set "TEMP_BUILD=%TEMP%\PyLauncher_Build"
if not exist "%TEMP_BUILD%" mkdir "%TEMP_BUILD%"
if exist "%TEMP_BUILD%\env_pack.zip" del "%TEMP_BUILD%\env_pack.zip"

echo [2/3] Compressing 'env' folder to system Temp...
set "WINRAR_EXE=C:\Program Files\WinRAR\WinRAR.exe"
if not exist "%WINRAR_EXE%" set "WINRAR_EXE=C:\Program Files (x86)\WinRAR\WinRAR.exe"
set "SEVENZIP_EXE=C:\Program Files\7-Zip\7z.exe"
if not exist "%SEVENZIP_EXE%" set "SEVENZIP_EXE=C:\Program Files (x86)\7-Zip\7z.exe"

if exist "%WINRAR_EXE%" (
    echo       Using WinRAR...
    "%WINRAR_EXE%" a -afzip -r -ibck "%TEMP_BUILD%\env_pack.zip" env
) else if exist "%SEVENZIP_EXE%" (
    echo       Using 7-Zip...
    "%SEVENZIP_EXE%" a -tzip "%TEMP_BUILD%\env_pack.zip" .\env >nul
) else (
    where tar >nul 2>nul
    if %errorlevel% equ 0 (
        echo       Using Windows Native 'tar' ^(Fast^)...
        tar -a -c -f "%TEMP_BUILD%\env_pack.zip" env
    ) else (
        echo       Using PowerShell ^(This is slow^)...
        powershell -NoProfile -Command "Compress-Archive -Path 'env' -DestinationPath '%TEMP_BUILD%\env_pack.zip' -Force"
    )
)

if not exist "%TEMP_BUILD%\env_pack.zip" (
    echo [ERROR] Failed to create env_pack.zip!
    pause
    exit /b
)

echo [3/3] Running PyInstaller to build the EXE...
echo This may take a few minutes...
echo.

if not exist "output" mkdir output
:: Use TEMP_BUILD for workpath and specpath
%PY_EXE% -m PyInstaller --onefile --noconsole --clean --noconfirm --distpath "output" --workpath "%TEMP_BUILD%\build" --specpath "%TEMP_BUILD%" --add-data "%TEMP_BUILD%\env_pack.zip;." "%LAUNCHER%" > "%TEMP_BUILD%\build_log.txt" 2>&1

if %errorlevel% neq 0 (
    echo.
    echo ====================================================
    echo [ERROR] BUILD FAILED! 
    echo ====================================================
    type "%TEMP_BUILD%\build_log.txt"
    pause
    exit /b
)

if defined CLEANUP ( del "PyLauncher.py" )

echo.
echo ====================================================
echo [SUCCESS] BUILD SUCCESSFUL!
echo ====================================================
echo Your final EXE is ready in the 'output' folder.
start "" "output"
pause