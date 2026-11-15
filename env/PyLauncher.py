import os
import sys
import tempfile
import zipfile
import shutil
import subprocess
import ctypes
import time

def safe_extract(zip_path, target_dir):
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for member in zf.infolist():
            target_path = os.path.abspath(os.path.join(target_dir, member.filename))
            if not target_path.startswith(os.path.abspath(target_dir)):
                raise Exception(f"Security Alert: Attempted Zip Slip in {member.filename}")
            zf.extract(member, target_dir)

def main():
    try:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except: pass

    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    local_env_dir = os.path.join(base_dir, "env")
    output_dir = os.path.join(base_dir, "output")
    temp_dir = None
    env_dir = None

    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        if os.path.exists(os.path.join(local_env_dir, "python.exe")):
            env_dir = local_env_dir
        else:
            meipass = getattr(sys, '_MEIPASS', base_dir)
            zip_path = os.path.join(meipass, "env_pack.zip")
            
            if not os.path.exists(zip_path):
                zip_path = os.path.join(base_dir, "temp", "env_pack.zip")

            if not os.path.exists(zip_path):
                ctypes.windll.user32.MessageBoxW(0, "Critical Error: env folder or env_pack.zip not found!", "Error", 1)
                return

            temp_dir = tempfile.mkdtemp(prefix="PyLauncher_")
            safe_extract(zip_path, temp_dir)

            extracted_env = os.path.join(temp_dir, "env")
            env_dir = extracted_env if os.path.exists(extracted_env) else temp_dir

        python_exe = os.path.join(env_dir, "python.exe")
        gui_script = os.path.join(env_dir, "converter_gui.py")

        if not os.path.exists(python_exe):
            ctypes.windll.user32.MessageBoxW(0, "Critical Error: python.exe not found!", "Error", 1)
            return

        process = subprocess.Popen(
            [python_exe, gui_script, base_dir],
            cwd=env_dir,
            creationflags=0x08000000
        )
        
        process.wait()
        
        if process.returncode != 0:
            crash_log = os.path.join(base_dir, "temp", "crash_log.txt")
            error_msg = f"The GUI application exited unexpectedly (Code: {process.returncode})."
            if os.path.exists(crash_log):
                with open(crash_log, "r", encoding="utf-8") as f:
                    error_msg += f"\n\nError Details:\n{f.read()[:1000]}..."
            ctypes.windll.user32.MessageBoxW(0, error_msg, "Application Crash", 1)

    except Exception as e:
        ctypes.windll.user32.MessageBoxW(0, f"Launch Error: {e}", "PyLauncher Error", 1)
    finally:
        if temp_dir:
            time.sleep(1) 
            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()