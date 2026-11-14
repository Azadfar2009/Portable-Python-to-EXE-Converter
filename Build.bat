@echo off
setlocal
title Auto Build - Python to EXE Converter
color 0B

:: تغییر مسیر به پوشه‌ای که فایل bat در آن قرار دارد
cd /d "%~dp0"

:: 1. تشخیص خودکار مسیر (آیا داخل پوشه env هستیم یا پوشه اصلی؟)
if not exist "env\python.exe" (
    if exist "python.exe" (
        cd ..
    ) else (
        echo [ERROR] 'env' folder and python.exe not found!
        pause
        exit /b
    )
)

:: استفاده از پایتون داخلی پوشه env (نیازی به نصب پایتون روی سیستم نیست)
set "PY_EXE=env\python.exe"
set "CLEANUP="

:: 2. پیدا کردن فایل PyLauncher.py
if exist "PyLauncher.py" (
    set "LAUNCHER=PyLauncher.py"
) else if exist "env\PyLauncher.py" (
    echo [INFO] Found PyLauncher.py inside 'env' folder. Copying to root...
    copy "env\PyLauncher.py" "PyLauncher.py" >nul
    set "LAUNCHER=PyLauncher.py"
    set "CLEANUP=1"
) else (
    echo [ERROR] 'PyLauncher.py' not found in root or 'env' folder!
    pause
    exit /b
)

echo ====================================================
echo Building Final PyLauncher.exe
echo ====================================================
echo.

:: 3. فشرده‌سازی پوشه env (انتخاب هوشمند سریع‌ترین ابزار موجود)
echo [1/2] Compressing 'env' folder to 'env_pack.zip'...
if exist "env_pack.zip" del "env_pack.zip"

:: بررسی مسیرهای نصب WinRAR
set "WINRAR_EXE=C:\Program Files\WinRAR\WinRAR.exe"
if not exist "%WINRAR_EXE%" set "WINRAR_EXE=C:\Program Files (x86)\WinRAR\WinRAR.exe"

:: بررسی مسیرهای نصب 7-Zip
set "SEVENZIP_EXE=C:\Program Files\7-Zip\7z.exe"
if not exist "%SEVENZIP_EXE%" set "SEVENZIP_EXE=C:\Program Files (x86)\7-Zip\7z.exe"

if exist "%WINRAR_EXE%" (
    echo       Using WinRAR...
    "%WINRAR_EXE%" a -afzip -r -ibck env_pack.zip env
) else if exist "%SEVENZIP_EXE%" (
    echo       Using 7-Zip...
    "%SEVENZIP_EXE%" a -tzip env_pack.zip .\env >nul
) else (
    where tar >nul 2>nul
    if %errorlevel% equ 0 (
        echo       Using Windows Native 'tar' ^(Fast^)...
        tar -a -c -f env_pack.zip env
    ) else (
        echo       Using PowerShell ^(This is slow, please wait...^)
        powershell -NoProfile -Command "Compress-Archive -Path 'env' -DestinationPath 'env_pack.zip' -Force"
    )
)

if not exist "env_pack.zip" (
    echo [ERROR] Failed to create env_pack.zip!
    pause
    exit /b
)

:: 4. اجرای PyInstaller
echo [2/2] Running PyInstaller to build the EXE...
echo This may take a few minutes...
echo.

:: اجرای PyInstaller با استفاده از پایتون داخلی (env\python.exe)
%PY_EXE% -m PyInstaller --onefile --noconsole --clean --noconfirm --add-data "env_pack.zip;." "%LAUNCHER%" > build_log.txt 2>&1

:: 5. بررسی نتیجه
if %errorlevel% neq 0 (
    echo.
    echo ====================================================
    echo [ERROR] BUILD FAILED! 
    echo ====================================================
    echo Here is the error log. Please copy this text:
    echo.
    type build_log.txt
    echo.
    pause
    exit /b
)

if defined CLEANUP (
    del "PyLauncher.py"
)

:: 6. پایان موفقیت‌آمیز
echo.
echo ====================================================
echo [SUCCESS] BUILD SUCCESSFUL!
echo ====================================================
echo Your final EXE is ready in the 'dist' folder.
echo.
echo Opening the 'dist' folder now...
start "" "dist"
pause