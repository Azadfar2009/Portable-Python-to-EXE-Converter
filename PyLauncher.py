import os
import sys
import tempfile
import zipfile
import shutil
import subprocess
import ctypes
import time

def zip_env_folder(folder_path, zip_path):
    """پوشه env را به فایل env_pack.zip تبدیل می‌کند"""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as ziph:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                # مسیر فایل‌ها را داخل زیپ با نام پوشه env ذخیره می‌کند
                arcname = os.path.relpath(file_path, os.path.dirname(folder_path))
                ziph.write(file_path, arcname)

def main():
    # پنهان کردن پنجره سیاه CMD
    try:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except:
        pass

    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    local_env_dir = os.path.join(base_dir, "env")
    local_zip_path = os.path.join(base_dir, "env_pack.zip")
    
    temp_dir = None
    env_dir = None

    try:
        # ========================================================
        # مرحله ۱: ساخت خودکار فایل env_pack.zip
        # ========================================================
        if os.path.exists(local_env_dir) and os.path.exists(os.path.join(local_env_dir, "python.exe")):
            try:
                # فشرده‌سازی پوشه env به env_pack.zip
                zip_env_folder(local_env_dir, local_zip_path)
            except Exception as e:
                ctypes.windll.user32.MessageBoxW(0, f"Warning: Failed to auto-create env_pack.zip.\n{e}", "Warning", 1)

        # ========================================================
        # مرحله ۲: تعیین حالت اجرا (پوشه‌ای یا تک‌فایلی)
        # ========================================================
        if os.path.exists(os.path.join(local_env_dir, "python.exe")):
            # حالت اول: پوشه env کنار برنامه هست (اجرا مستقیم)
            env_dir = local_env_dir
        else:
            # حالت دوم: فایل env_pack.zip وجود دارد (استخراج در Temp)
            zip_to_extract = None
            
            # چک کردن زیپ در کنار برنامه
            if os.path.exists(local_zip_path):
                zip_to_extract = local_zip_path
            else:
                # چک کردن زیپ داخل فایل EXE (نسخه یکپارچه)
                meipass = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
                embedded_zip = os.path.join(meipass, "env_pack.zip")
                if os.path.exists(embedded_zip):
                    zip_to_extract = embedded_zip

            if zip_to_extract:
                temp_dir = tempfile.mkdtemp(prefix="PyLauncher_")
                with zipfile.ZipFile(zip_to_extract, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                extracted_env = os.path.join(temp_dir, "env")
                env_dir = extracted_env if os.path.exists(extracted_env) else temp_dir
            else:
                ctypes.windll.user32.MessageBoxW(0, "Critical Error: Neither 'env' folder nor 'env_pack.zip' found!", "Error", 1)
                return

        # ========================================================
        # مرحله ۳: اجرای رابط گرافیکی
        # ========================================================
        python_exe = os.path.join(env_dir, "python.exe")
        gui_script = os.path.join(env_dir, "converter_gui.py")

        if not os.path.exists(python_exe):
            ctypes.windll.user32.MessageBoxW(0, "Critical Error: python.exe not found!", "Error", 1)
            return

        # مسیر base_dir (محل فایل exe) را پاس می‌دهیم تا خروجی‌ها همان‌جا ساخته شوند
        process = subprocess.Popen(
            [python_exe, gui_script, base_dir],
            cwd=env_dir,
            creationflags=0x08000000 # اجرای بدون پنجره سیاه
        )
        process.wait()

    except Exception as e:
        ctypes.windll.user32.MessageBoxW(0, f"Launch Error: {e}", "PyLauncher Error", 1)
    finally:
        # ========================================================
        # مرحله ۴: پاکسازی (فقط اگر از حالت Temp استفاده شده باشد)
        # ========================================================
        if temp_dir:
            time.sleep(1) 
            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()