# 🐍 PyLauncher - Portable Python to EXE Converter

![Python Version](https://img.shields.io/badge/Python-3.11-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Beta-orange)

**PyLauncher** is a powerful, fully portable Python-to-EXE converter designed specifically for restricted environments where you cannot install Python, PyInstaller, or any third-party software. 

Whether you are dealing with strict corporate IT policies, no internet access, or aggressive antivirus software, PyLauncher provides a seamless way to convert your `.py` scripts into standalone executables.

---

## ✨ Killer Features

- **🚀 Truly Portable (Zero Installation):** Runs entirely from a flash drive or a local folder. No admin rights, no registry changes, and no Python installation required on the target machine.
- **📦 Dual-Mode Architecture:** 
  - *Single-File Mode:* Just copy `PyLauncher.exe` and run it. It extracts the environment to a temp folder, does the job, and cleans up after itself.
  - *Folder Mode:* Place the `env` folder next to the `PyLauncher.exe` for instant startup and persistent package installs.
- **🧹 Auto-Cleanup & Self-Destructing:** When running in Single-File mode, closing the app automatically deletes all temporary files from your system. Leaves zero footprints!
- **⚙️ Built-in Package Manager (Config):** 
  - **Check for Updates:** See which installed libraries are outdated.
  - **Install Online:** Search for packages (e.g., `pandas`), check size/version via PyPI API, and install.
  - **Install Offline:** No internet? Simply load a `.whl` or `.tar.gz` file and install it directly into the portable environment.
- **🕵️ Smart Dependency Scanner:** Before converting, the app analyzes your script using AST (Abstract Syntax Tree) to verify if all required third-party libraries are installed. It highlights missing packages in red, preventing failed EXE builds.
- **🛡️ Antivirus Friendly:** Uses `--onedir` and `--noupx` flags by default. This structure is significantly less likely to trigger false positives from strict antivirus software.
- **🖥️ Beautiful UI & Advanced Options:** Drag & drop files, add data files, choose onefile/onedir, set custom icons, and select output directories.
- **📥 Live Download Progress:** Integrated terminal output that parses `pip` output to show real-time download progress.
- **🚨 Crash Protection:** Global exception handling ensures the app never closes unexpectedly and always saves a crash log.

---

## 🛠️ How to Use

### Option 1: The Ready-to-Use EXE (Single File)
1. Download the latest `PyLauncher.exe` from the **Releases** page.
2. Place it in an empty folder.
3. Drop your `.py` files next to it.
4. Double-click `PyLauncher.exe`. The GUI will open, scan your files, and convert them into the `dist` folder.

### Option 2: The Developer / Folder Mode
1. Download the source code and the `env` folder.
2. Keep `PyLauncher.py`, `Build.bat`, and the `env` folder in the same directory.
3. Run `env\python.exe PyLauncher.py`.
4. *Pro Tip:* In this mode, any package you install via the Config menu is saved permanently in the `env` folder.

---

## 🏗️ Building the EXE from Source

We have included an automated build script! If you modify the `converter_gui.py` or update packages, simply run:

```cmd
Build.bat
```

**What `Build.bat` does:**
1. Automatically detects the project root.
2. Runs `clean_env.py` to remove unnecessary test files and reduce final EXE size.
3. Compresses the `env` folder into `env_pack.zip` using the fastest available tool (WinRAR, 7-Zip, or Windows `tar`).
4. Runs PyInstaller using the *internal portable Python* (no system Python needed).
5. Outputs the final `PyLauncher.exe` in the `dist` folder.

---

## ⚠️ Important Notes

- **Antivirus Warning:** Because PyInstaller bundles a whole Python environment, some aggressive enterprise antivirus solutions might flag the generated `.exe` files as suspicious. This is a known PyInstaller behavior (False Positive). We recommend asking your IT department to whitelist the app.
- **First Run Delay:** In Single-File mode, the first launch takes 3-5 seconds because it needs to extract the Python environment to the Temp folder.

---
*Designed & Developed with ❤️ by [Mohammad Azadfar](https://github.com/Azadfar2009)*
