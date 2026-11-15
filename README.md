# 🐍 PyLauncher - Portable Python to EXE Converter

![Python Version](https://img.shields.io/badge/Python-3.11-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Production--Ready-success)

**PyLauncher** is a powerful, fully portable Python-to-EXE converter designed specifically for restricted environments where you cannot install Python, PyInstaller, or any third-party software. 

Whether you are dealing with strict corporate IT policies, no internet access, or aggressive antivirus software, PyLauncher provides a seamless way to convert your `.py` scripts into standalone executables.

> 🇮🇷 [نسخه فارسی مستندات را اینجا بخوانید](README.fa.md)

---

## 📸 Screenshots

<div align="center">
  <h3>Main Interface</h3>
  <img src="screenshots/main_ui.png" width="85%" alt="Main Interface" />
  
  <br><br>
  
  <h3>Build Options</h3>
  <img src="screenshots/build.png" width="50%" alt="Build Options" />
  
  <br><br>
  
  <h3>Package Manager</h3>
  <img src="screenshots/config1_ui.png" width="48%" alt="Config - Installed" />
  <img src="screenshots/config2_ui.png" width="48%" alt="Config - Internet" />
</div>

## ✨ Killer Features (v3.5.1)

- **🎨 Modern Corporate UI:** Completely redesigned interface with a professional dashboard theme, styled cards, and vibrant modern buttons.
- **🚀 Truly Portable (Zero Installation):** Runs entirely from a flash drive or a local folder. No admin rights, no registry changes, and no Python installation required on the target machine.
- **📦 Dual-Mode Architecture:** 
  - *Single-File Mode:* Just copy `PyLauncher.exe` and run it. It extracts the environment to a temp folder, does the job, and cleans up after itself.
  - *Folder Mode:* Place the `env` folder next to the `RunConverter.bat` for instant startup and persistent package installs.
- **📂 Clean Directory Structure:** Automatically organizes files into `/scripts`, `/logs`, and `/output` to keep your root folder clutter-free.
- **⚙️ Built-in Package Manager:** 
  - **Check for Updates:** See which installed libraries are outdated.
  - **Install Online:** Fast PyPI search (with smart local version check).
  - **Install Offline:** No internet? Simply load a `.whl` file and install it directly into the portable environment.
- **🕵️ Smart Dependency Scanner:** Before converting, the app analyzes your script using AST to verify if all required libraries are installed.
- **🛡️ Antivirus Friendly:** Uses `--onedir` and `--noupx` flags by default to minimize false positives.
- **🖥️ Advanced Options:** Drag & drop files, add data files, choose onefile/onedir, set custom icons, and select output directories.
- **🚨 Crash Protection:** Global exception handling ensures the app never closes unexpectedly and always saves a crash log.
- **📝 Persistent Logs:** All logs are safely saved in the `/logs` folder, even after closing the portable app.

---

## 📂 Directory Structure

```text
PortableConverter/
├── env/                      # Portable Python environment
├── scripts/                  # Build and helper scripts
│   ├── Build.bat             # Builds the final EXE
│   └── clean_env.py          # Reduces final size
├── logs/                     # Auto-generated: log files
├── output/                   # Auto-generated: your final EXE files go here
├── RunConverter.bat          # Launch folder mode
├── README.md
├── README.fa.md
├── .gitignore
└── LICENSE
```

---

## 🏗️ Building the EXE from Source

We have included an automated build script! To build the single-file EXE, simply navigate to the `scripts` folder and run:

```cmd
Build.bat
```

**What `Build.bat` does:**
1. Cleans the `env` folder to reduce size.
2. Compresses `env` into a temp zip using WinRAR, 7-Zip, or Windows `tar`.
3. Runs PyInstaller using the *internal portable Python*.
4. Outputs the final `PyLauncher.exe` in the `output` folder.

---

## ⚠️ Important Notes

- **Antivirus Warning:** Because PyInstaller bundles a whole Python environment, some aggressive enterprise antivirus solutions might flag the generated `.exe` files as suspicious (False Positive). We recommend asking your IT department to whitelist the app.
- **First Run Delay:** In Single-File mode, the first launch takes 3-5 seconds because it needs to extract the Python environment to the Temp folder.

---
*Designed & Developed with ❤️ by [Mohammad Azadfar](https://github.com/Azadfar2009)*
