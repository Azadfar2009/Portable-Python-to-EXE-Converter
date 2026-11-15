# -*- coding: utf-8 -*-
import os
import sys
import ast
import importlib.util
import importlib.metadata
import threading
import subprocess
import tempfile
import shutil
import webbrowser
import ctypes
import json
import urllib.request
import urllib.error
import time
import gzip
import traceback
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False
    TkinterDnD = None

try:
    from packaging import version as pkg_version
except ImportError:
    pkg_version = None

try:
    import PyInstaller
    PYINSTALLER_AVAILABLE = True
except ImportError:
    PYINSTALLER_AVAILABLE = False

# --- Modern Corporate Theme Colors ---
FONT_FAMILY = "Tahoma"
FONT_NORMAL = (FONT_FAMILY, 10)
FONT_BOLD = (FONT_FAMILY, 10, "bold")
FONT_BTN = (FONT_FAMILY, 9, "bold")
FONT_TITLE = (FONT_FAMILY, 15, "bold")
FONT_MONO = ("Consolas", 9)

BG_COLOR = "#f3f6f9"
CARD_BG = "#ffffff"
PRIMARY = "#1e293b"
TEXT_COLOR = "#1e293b"
MUTED_TEXT = "#475569"
BORDER = "#e2e8f0"
HIGHLIGHT_BG = "#eff6ff"
CARD_HEADER_BG = "#f1f5f9"

ACCENT = "#3b82f6"      # Blue
SUCCESS = "#10b981"     # Emerald Green
WARNING = "#f59e0b"     # Amber
DANGER = "#ef4444"      # Red

CONSOLE_BG = "#0f172a"
CONSOLE_HEADER_BG = "#1e293b"
CONSOLE_FG = "#cbd5e1"

STDLIB_MODULES = set(sys.builtin_module_names) | {
    'os', 'sys', 're', 'json', 'math', 'datetime', 'pathlib', 'subprocess',
    'threading', 'tkinter', 'typing', 'collections', 'itertools', 'functools',
    'importlib', 'shutil', 'tempfile', 'ast', 'traceback', 'logging', 'csv',
    'sqlite3', 'urllib', 'http', 'socket', 'ssl', 'hashlib', 'base64',
    'zlib', 'gzip', 'pickle', 'copy', 'random', 'time', 'uuid', 'glob',
    'argparse', 'configparser', 'unittest', 'xml', 'html', 'email'
}

ACTIVE_PROCESSES = []
APP_TEMP_DIR = Path(tempfile.gettempdir()) / "PyLauncher_Temp"
APP_TEMP_DIR.mkdir(parents=True, exist_ok=True)

PYTHON_EXE = sys.executable.replace("pythonw.exe", "python.exe")

def kill_process(pid):
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], creationflags=0x08000000, capture_output=True)
    except Exception:
        pass

def get_installed_packages():
    try:
        from importlib.metadata import distributions
        return {d.metadata['Name'].lower() for d in distributions() if d.metadata['Name']}
    except Exception:
        return set()

def check_dependencies(filepath):
    missing, available, stdlib = [], [], []
    local_files = {p.stem for p in Path(filepath).parent.glob("*.py")}
    installed = get_installed_packages()
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            tree = ast.parse(f.read())
    except SyntaxError as e:
        return {'error': f'Syntax error: {e}', 'missing': [], 'available': [], 'stdlib': []}
    except Exception as e:
        return {'error': f'Read error: {e}', 'missing': [], 'available': [], 'stdlib': []}

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                imports.add(a.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split('.')[0])

    for mod in imports:
        if mod in STDLIB_MODULES:
            stdlib.append(mod)
        elif mod in local_files:
            available.append(f"{mod} (local)")
        elif mod.lower() in installed:
            available.append(mod)
        else:
            if importlib.util.find_spec(mod) is not None:
                available.append(mod)
            else:
                missing.append(mod)

    return {'missing': sorted(missing), 'available': sorted(available),
            'stdlib': sorted(stdlib), 'error': None}

# ================= Build Options Dialog =================
class BuildOptionsDialog:
    def __init__(self, parent, config_data):
        self.parent = parent
        self.result = None
        self.win = tk.Toplevel(parent)
        self.win.title("Build Options")
        self.win.geometry("480x380")
        self.win.configure(bg=BG_COLOR)
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(False, False)

        parent.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - 240
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - 190
        self.win.geometry(f"+{x}+{y}")

        self.var_onefile = tk.BooleanVar(value=config_data.get("build_onefile", False))
        
        # FIX: Always default to the current scan_dir/output
        default_out = str(Path(config_data.get("scan_dir", os.getcwd())) / "output")
        self.var_outdir = tk.StringVar(value=default_out)
        
        # FIX: Only load icon if it still exists
        saved_icon = config_data.get("build_icon", "")
        if not os.path.exists(saved_icon): saved_icon = ""
        self.var_icon = tk.StringVar(value=saved_icon)

        main_frame = tk.Frame(self.win, bg=CARD_BG, padx=20, pady=20, highlightbackground=BORDER, highlightthickness=1)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(main_frame, text="Build Mode:", font=FONT_BOLD, bg=CARD_BG, fg=TEXT_COLOR).pack(anchor="w")
        tk.Radiobutton(main_frame, text="One Directory (Recommended, safer for AV)", variable=self.var_onefile, value=False, bg=CARD_BG, fg=TEXT_COLOR, font=FONT_NORMAL, activebackground=CARD_BG, selectcolor=CARD_BG).pack(anchor="w", padx=20)
        tk.Radiobutton(main_frame, text="Single File (Onefile, slower startup)", variable=self.var_onefile, value=True, bg=CARD_BG, fg=TEXT_COLOR, font=FONT_NORMAL, activebackground=CARD_BG, selectcolor=CARD_BG).pack(anchor="w", padx=20, pady=(0, 15))

        tk.Label(main_frame, text="Output Directory:", font=FONT_BOLD, bg=CARD_BG, fg=TEXT_COLOR).pack(anchor="w")
        out_frame = tk.Frame(main_frame, bg=CARD_BG)
        out_frame.pack(fill="x", pady=(5, 15))
        tk.Entry(out_frame, textvariable=self.var_outdir, font=FONT_NORMAL, state="readonly", relief="solid", bd=1).pack(side="left", fill="x", expand=True, padx=(0, 5))
        tk.Button(out_frame, text="Browse", font=FONT_BTN, bg=ACCENT, fg="white", relief="flat", activebackground="#2563eb", command=self._browse_outdir, padx=10).pack(side="right")

        tk.Label(main_frame, text="Custom Icon (Optional):", font=FONT_BOLD, bg=CARD_BG, fg=TEXT_COLOR).pack(anchor="w")
        icon_frame = tk.Frame(main_frame, bg=CARD_BG)
        icon_frame.pack(fill="x", pady=(5, 15))
        tk.Entry(icon_frame, textvariable=self.var_icon, font=FONT_NORMAL, state="readonly", relief="solid", bd=1).pack(side="left", fill="x", expand=True, padx=(0, 5))
        tk.Button(icon_frame, text="Browse", font=FONT_BTN, bg=ACCENT, fg="white", relief="flat", activebackground="#2563eb", command=self._browse_icon, padx=10).pack(side="right")

        btn_frame = tk.Frame(main_frame, bg=CARD_BG)
        btn_frame.pack(fill="x", side="bottom")
        tk.Button(btn_frame, text="Start Build", font=FONT_BOLD, bg=SUCCESS, fg="white", relief="flat", activebackground="#059669", padx=20, pady=6, command=self._on_ok).pack(side="right", padx=5)
        tk.Button(btn_frame, text="Cancel", font=FONT_BOLD, bg="#e2e8f0", fg=TEXT_COLOR, relief="flat", activebackground="#cbd5e1", padx=20, pady=6, command=self.win.destroy).pack(side="right", padx=5)

    def _browse_outdir(self):
        path = filedialog.askdirectory(parent=self.win, initialdir=self.var_outdir.get())
        if path: self.var_outdir.set(os.path.abspath(path))

    def _browse_icon(self):
        path = filedialog.askopenfilename(parent=self.win, filetypes=[("Icon Files", "*.ico")])
        if path: self.var_icon.set(os.path.abspath(path))

    def _on_ok(self):
        self.result = {
            "build_onefile": self.var_onefile.get(),
            "build_outdir": self.var_outdir.get(),
            "build_icon": self.var_icon.get()
        }
        self.win.destroy()

    def get_result(self):
        self.parent.wait_window(self.win)
        return self.result

# ================= Config Window =================
class ConfigWindow:
    def __init__(self, parent, scan_dir, log_dir):
        self.parent = parent
        self.scan_dir = scan_dir
        self.log_dir = log_dir
        self.is_busy = False
        self.win = tk.Toplevel(parent)
        self.win.title("Package Manager")
        self.win.geometry("750x650")
        self.win.configure(bg=BG_COLOR)
        self.win.transient(parent)
        self.win.grab_set()

        parent.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - 375
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - 325
        self.win.geometry(f"+{x}+{y}")
        
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        style = ttk.Style()
        style.configure("TNotebook", background=BG_COLOR, borderwidth=0)
        style.configure("TNotebook.Tab", background="#e2e8f0", foreground=TEXT_COLOR, padding=[12, 6], font=(FONT_FAMILY, 9))
        style.map("TNotebook.Tab", background=[("selected", CARD_BG)], foreground=[("selected", PRIMARY)], font=[("selected", (FONT_FAMILY, 10, "bold"))], padding=[("selected", [15, 8])])
        
        style.configure("Custom.Treeview", font=FONT_NORMAL, rowheight=28, background=CARD_BG, fieldbackground=CARD_BG, borderwidth=0)
        style.configure("Custom.Treeview.Heading", font=FONT_BOLD, background=BG_COLOR, foreground=TEXT_COLOR, relief="flat", borderwidth=1)
        style.map("Custom.Treeview", background=[("selected", HIGHLIGHT_BG)], foreground=[("selected", TEXT_COLOR)])

        self.notebook = ttk.Notebook(self.win)
        self.notebook.pack(fill="both", expand=False, padx=10, pady=(10, 5))

        self._build_installed_tab()
        self._build_online_tab()
        self._build_offline_tab()

        log_frame = tk.LabelFrame(self.win, text=" Output ", font=FONT_BOLD, bg=CARD_BG, fg=TEXT_COLOR, bd=1, relief="solid")
        log_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        log_toolbar = tk.Frame(log_frame, bg=CARD_BG)
        log_toolbar.pack(fill="x", side="top", pady=(5, 0), padx=5)
        
        tk.Button(log_toolbar, text="💾 Save Log", font=FONT_BTN, bg="#94a3b8", fg="white", relief="flat", cursor="hand2", activebackground="#64748b", padx=10, pady=2, command=self._save_log).pack(side="right")
        
        self.log = scrolledtext.ScrolledText(log_frame, height=10, font=FONT_MONO, bg=CONSOLE_BG, fg=CONSOLE_FG, state="disabled", relief="flat")
        self.log.pack(fill="both", expand=True, padx=5, pady=5)

        self._load_installed_packages()

    def _on_close(self):
        if self.is_busy:
            if not messagebox.askokcancel("Exit", "An operation is in progress. Cancel and close?", parent=self.win): return
        for p in ACTIVE_PROCESSES: kill_process(p.pid)
        self.win.destroy()

    def _log(self, msg):
        if not self.win.winfo_exists(): return
        self.log.config(state="normal"); self.log.insert("end", msg + "\n"); self.log.see("end"); self.log.config(state="disabled")

    def _save_log(self):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filepath = self.log_dir / f"pkg_manager_log_{timestamp}.txt"
            with open(filepath, "w", encoding="utf-8") as f: f.write(self.log.get("1.0", "end-1c"))
            messagebox.showinfo("Success", f"Log saved to:\n{filepath}", parent=self.win)
        except Exception as e: messagebox.showerror("Error", f"Failed to save log:\n{e}", parent=self.win)

    def _build_installed_tab(self):
        tab = tk.Frame(self.notebook, bg=CARD_BG)
        self.notebook.add(tab, text="Installed Packages")
        toolbar = tk.Frame(tab, bg=CARD_BG)
        toolbar.pack(fill="x", pady=10, padx=10)
        
        tk.Button(toolbar, text="🔄 Check for Updates", font=FONT_BTN, bg=ACCENT, fg="white", relief="flat", activebackground="#2563eb", cursor="hand2", command=self._check_updates).pack(side="left", padx=(0, 10))
        tk.Button(toolbar, text="⬆️ Update Selected", font=FONT_BTN, bg=SUCCESS, fg="white", relief="flat", activebackground="#059669", cursor="hand2", command=self._update_selected).pack(side="left")

        columns = ("package", "version", "latest")
        tree_frame = tk.Frame(tab, bg=CARD_BG)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended", height=10, style="Custom.Treeview")
        self.tree.heading("package", text="Package Name", anchor="w")
        self.tree.heading("version", text="Installed Version", anchor="center")
        self.tree.heading("latest", text="Latest Version", anchor="center")
        self.tree.column("package", width=300); self.tree.column("version", width=150, anchor="center"); self.tree.column("latest", width=150, anchor="center")
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")

    def _build_online_tab(self):
        tab = tk.Frame(self.notebook, bg=CARD_BG)
        self.notebook.add(tab, text="Install from Internet")
        center_frame = tk.Frame(tab, bg=CARD_BG); center_frame.pack(expand=True)
        tk.Label(center_frame, text="Enter Package Name to Install:", font=FONT_BOLD, bg=CARD_BG, fg=TEXT_COLOR).pack(pady=(0, 10))
        entry_frame = tk.Frame(center_frame, bg=CARD_BG); entry_frame.pack(pady=5)
        self.entry_pkg = tk.Entry(entry_frame, font=(FONT_FAMILY, 12), width=30, relief="solid", bd=1)
        self.entry_pkg.pack(side="left", padx=(0, 10), ipady=5)
        self.entry_pkg.bind("<Return>", lambda e: self._check_and_install())
        self.btn_check_install = tk.Button(entry_frame, text="🌐 Search & Install", font=FONT_BOLD, bg=ACCENT, fg="white", relief="flat", activebackground="#2563eb", cursor="hand2", padx=15, pady=5, command=self._check_and_install)
        self.btn_check_install.pack(side="left")

    def _build_offline_tab(self):
        tab = tk.Frame(self.notebook, bg=CARD_BG); self.notebook.add(tab, text="Install from File")
        center_frame = tk.Frame(tab, bg=CARD_BG); center_frame.pack(expand=True)
        tk.Label(center_frame, text="Install Local Package File", font=(FONT_FAMILY, 14, "bold"), bg=CARD_BG, fg=PRIMARY).pack(pady=(0, 20))
        file_box = tk.Frame(center_frame, bg=BG_COLOR, bd=1, relief="solid"); file_box.pack(pady=10, padx=20, fill="x")
        self.lbl_file = tk.Label(file_box, text="No file selected (.whl or .tar.gz)", font=FONT_NORMAL, bg=BG_COLOR, fg=MUTED_TEXT, pady=20); self.lbl_file.pack()
        btn_frame = tk.Frame(center_frame, bg=CARD_BG); btn_frame.pack(pady=15)
        tk.Button(btn_frame, text="📁 Browse File", font=FONT_BOLD, bg="#94a3b8", fg="white", relief="flat", activebackground="#64748b", cursor="hand2", padx=20, pady=5, command=self._browse_file).pack(side="left", padx=10)
        self.btn_install_offline = tk.Button(btn_frame, text="📥 Install File", font=FONT_BTN, bg=SUCCESS, fg="white", relief="flat", activebackground="#059669", cursor="hand2", padx=20, pady=5, state="disabled", command=self._install_offline)
        self.btn_install_offline.pack(side="left", padx=10)
        self.selected_file = None

    def _load_installed_packages(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        def fetch():
            try:
                out = subprocess.check_output([PYTHON_EXE, "-m", "pip", "list", "--format=json"], text=True, creationflags=0x08000000)
                packages = json.loads(out[out.find('['):out.rfind(']')+1])
                packages.sort(key=lambda x: x['name'].lower())
                def update_ui():
                    if not self.win.winfo_exists(): return
                    for p in packages: self.tree.insert("", "end", values=(p['name'], p['version'], "-"))
                self.win.after(0, update_ui)
            except Exception as e: 
                err_msg = str(e)
                self.win.after(0, lambda msg=err_msg: self._log(f"Error loading packages: {msg}"))
        threading.Thread(target=fetch, daemon=True).start()

    def _check_updates(self):
        self._log("Checking for updates...")
        def fetch():
            try:
                out = subprocess.check_output([PYTHON_EXE, "-m", "pip", "list", "--outdated", "--format=json"], text=True, creationflags=0x08000000)
                outdated = json.loads(out[out.find('['):out.rfind(']')+1])
                outdated_dict = {p['name'].lower(): p['latest_version'] for p in outdated}
                def update_ui():
                    if not self.win.winfo_exists(): return
                    for item in self.tree.get_children():
                        vals = self.tree.item(item, "values")
                        if str(vals[0]).lower() in outdated_dict: self.tree.item(item, values=(vals[0], vals[1], outdated_dict[str(vals[0]).lower()]))
                    self._log("Check complete.")
                self.win.after(0, update_ui)
            except Exception as e: 
                err_msg = str(e)
                self.win.after(0, lambda msg=err_msg: self._log(f"Error checking updates: {msg}"))
        threading.Thread(target=fetch, daemon=True).start()

    def _update_selected(self):
        sel = self.tree.selection()
        if not sel: return messagebox.showinfo("Info", "Select packages to update.", parent=self.win)
        pkgs = []
        for s in sel:
            vals = self.tree.item(s, "values")
            if vals[2] != "-": pkgs.append(vals[0])
        if pkgs: self._run_pip(["install", "--upgrade"] + pkgs)

    def _check_and_install(self):
        pkg = self.entry_pkg.get().strip()
        if not pkg: return
        self.is_busy = True; self.btn_check_install.config(state="disabled", text="⏳ Checking...")
        self._log(f"Fetching info for '{pkg}'...")
        
        def process():
            local_version = None
            try: local_version = importlib.metadata.version(pkg)
            except importlib.metadata.PackageNotFoundError: pass

            try:
                url = f"https://pypi.org/pypi/{pkg}/json"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept-Encoding': 'gzip'})
                with urllib.request.urlopen(req, timeout=15) as response:
                    data_bytes = response.read()
                    if response.info().get('Content-Encoding') == 'gzip': data_bytes = gzip.decompress(data_bytes)
                    data = json.loads(data_bytes.decode())
                    
                    remote_ver = data['info']['version']
                    summary = data['info']['summary'] or "No description."
                    
                    size_mb = 0
                    if 'urls' in data:
                        for u in data['urls']:
                            if u['packagetype'] == 'bdist_wheel' and u['size']: size_mb = u['size'] / (1024*1024); break
                    
                    size_str = f"~{size_mb:.2f} MB" if size_mb > 0 else "Unknown"
                    
                    def ask_ui():
                        self._reset_check_btn()
                        if local_version and pkg_version:
                            try:
                                if pkg_version.parse(local_version) >= pkg_version.parse(remote_ver):
                                    messagebox.showinfo("Already Installed", f"Package '{pkg}' is already up-to-date (v{local_version}).", parent=self.win)
                                    return
                                else:
                                    msg = f"Update available!\n\nInstalled: {local_version}\nLatest: {remote_ver}\nSize: {size_str}\n\nUpdate now?"
                                    if messagebox.askyesno("Confirm Update", msg, parent=self.win): 
                                        self._run_pip(["install", "--upgrade", pkg])
                                    return
                            except: pass
                        
                        msg = f"Package: {pkg}\nVersion: {remote_ver}\nSize: {size_str}\n\n{summary}\n\nInstall?"
                        if messagebox.askyesno("Confirm", msg, parent=self.win): 
                            self._run_pip(["install", pkg])
                            
                    self.win.after(0, ask_ui)
            except urllib.error.HTTPError as he:
                err_msg = "Package not found on PyPI (404 Error)." if he.code == 404 else f"HTTP Error: {he.code}"
                self.win.after(0, lambda msg=err_msg: [self._log(f"Error: {msg}"), self._reset_check_btn()])
            except urllib.error.URLError as ue:
                err_msg = "Network Error: Could not connect to PyPI.org.\nCheck your internet or DNS settings."
                self.win.after(0, lambda msg=err_msg: [self._log(f"Error: {msg}"), self._reset_check_btn()])
            except Exception as e:
                err_msg = str(e)
                self.win.after(0, lambda msg=err_msg: [self._log(f"Error: {msg}"), self._reset_check_btn()])
        threading.Thread(target=process, daemon=True).start()

    def _reset_check_btn(self):
        self.is_busy = False; self.btn_check_install.config(state="normal", text="🌐 Search & Install")

    def _browse_file(self):
        filepath = filedialog.askopenfilename(parent=self.win, title="Select Package", filetypes=[("Packages", "*.whl *.tar.gz")])
        if filepath:
            self.selected_file = os.path.abspath(filepath)
            self.lbl_file.config(text=os.path.basename(filepath), fg=SUCCESS, font=(FONT_FAMILY, 10, "bold"))
            self.btn_install_offline.config(state="normal")

    def _install_offline(self):
        if self.selected_file: self._run_pip(["install", self.selected_file])

    def _run_pip(self, args):
        self.is_busy = True
        def worker():
            try:
                cmd = [PYTHON_EXE, "-m", "pip"] + args + ["--progress-bar", "on"]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', creationflags=0x08000000)
                ACTIVE_PROCESSES.append(process)
                buffer = ""
                while True:
                    char = process.stdout.read(1)
                    if not char and process.poll() is not None: break
                    if char in ('\r', '\n'):
                        if buffer.strip(): self.win.after(0, lambda l=buffer.strip(): self._log(l))
                        buffer = ""
                    else: buffer += char
                if buffer.strip(): self.win.after(0, lambda l=buffer.strip(): self._log(l))
                process.wait()
                if process in ACTIVE_PROCESSES: ACTIVE_PROCESSES.remove(process)
                def finish_ui():
                    self.is_busy = False
                    if self.win.winfo_exists():
                        self._log("✅ Done." if process.returncode == 0 else "❌ Failed.")
                        if process.returncode == 0: self._load_installed_packages()
                self.win.after(0, finish_ui)
            except Exception as e: 
                err_msg = str(e)
                self.win.after(0, lambda msg=err_msg: [self._log(f"Error: {msg}"), setattr(self, 'is_busy', False)])
        threading.Thread(target=worker, daemon=True).start()

# ================= Main GUI Application =================
class ConverterApp:
    def __init__(self, root, scan_path=None):
        self.root = root
        self.root.title("Python to EXE Converter")
        self.root.geometry("1050x700") 
        self.root.configure(bg=BG_COLOR)
        self.root.minsize(950, 650)
        
        self.root.report_callback_exception = self._handle_exception
        
        try: ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 6) 
        except: pass

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        if scan_path and os.path.isdir(scan_path): self.scan_dir = Path(scan_path).resolve()
        else:
            current_dir = Path(__file__).resolve().parent
            self.scan_dir = current_dir.parent if current_dir.name == "env" else current_dir
            
        self.log_dir = self.scan_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
            
        self.settings_file = APP_TEMP_DIR / "settings.json"
        
        self.config_data = self._load_settings()
        self.config_data["scan_dir"] = str(self.scan_dir)
        
        self.session_extra_files = []
        
        self.file_infos = {}
        self.check_vars = {}
        self.converting = False
        self.active_process = None
        
        self.active_row_frame = None
        self.active_row_widgets = []
        
        self._setup_styles()
        self._build_ui()
        self._refresh_file_list()

    def _handle_exception(self, exc_type, exc_value, exc_traceback):
        err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        self._log(f"❌ UI ERROR: {err_msg}")
        messagebox.showerror("Unexpected Error", f"An unexpected error occurred:\n\n{exc_value}\n\nPlease save the log.")

    def _load_settings(self):
        default = {"data_files": []}
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f: return json.load(f)
            except: pass
        return default

    def _save_settings(self):
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f: json.dump(self.config_data, f, indent=4)
        except: pass

    def _on_closing(self):
        if self.converting:
            if not messagebox.askyesno("Warning", "Conversion in progress. Exit?"): return
            if self.active_process: kill_process(self.active_process.pid)
        for p in ACTIVE_PROCESSES: kill_process(p.pid)
        self._save_settings()
        self.root.destroy()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TProgressbar", thickness=8, background=SUCCESS, troughcolor="#e2e8f0", bordercolor=BORDER)

    def _build_ui(self):
        # Modern Corporate Header
        header = tk.Frame(self.root, bg=PRIMARY, height=60)
        header.pack(fill="x"); header.pack_propagate(False)
        tk.Label(header, text="🐍  Python to EXE Converter", font=FONT_TITLE, bg=PRIMARY, fg="white").pack(side="left", padx=20)
        
        btn_frame_header = tk.Frame(header, bg=PRIMARY); btn_frame_header.pack(side="right", padx=20, pady=15)
        
        config_btn = tk.Button(btn_frame_header, text="⚙️ Config", font=FONT_BTN, bg="#334155", fg="#f8fafc", relief="flat", bd=0, activebackground="#475569", activeforeground="white", cursor="hand2", padx=15, pady=5, command=self._open_config)
        config_btn.pack(side="left", padx=(0, 10))
        
        about_btn = tk.Button(btn_frame_header, text="ℹ️ About", font=FONT_BTN, bg="#334155", fg="#f8fafc", relief="flat", bd=0, activebackground="#475569", activeforeground="white", cursor="hand2", padx=15, pady=5, command=self._show_about)
        about_btn.pack(side="left")

        # Path Bar
        bar = tk.Frame(self.root, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1); bar.pack(fill="x")
        tk.Label(bar, text=f"📂 Current Directory: {self.scan_dir}", font=FONT_NORMAL, bg=CARD_BG, fg="#475569", pady=8, padx=20).pack(side="left")

        main_frame = tk.Frame(self.root, bg=BG_COLOR); main_frame.pack(fill="both", expand=True, padx=20, pady=15)
        main_frame.rowconfigure(0, weight=75); main_frame.rowconfigure(1, weight=0); main_frame.rowconfigure(2, weight=25); main_frame.columnconfigure(0, weight=1)

        top_frame = tk.Frame(main_frame, bg=BG_COLOR); top_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        top_frame.rowconfigure(0, weight=1); top_frame.columnconfigure(0, weight=7); top_frame.columnconfigure(1, weight=3)

        # Files Frame (Card style with distinct header)
        files_frame = tk.Frame(top_frame, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        files_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        files_header = tk.Frame(files_frame, bg=CARD_HEADER_BG)
        files_header.pack(fill="x")
        tk.Label(files_header, text="Python Files (Drag & Drop)", font=FONT_BOLD, bg=CARD_HEADER_BG, fg=TEXT_COLOR).pack(anchor="w", padx=15, pady=10)

        headers_frame = tk.Frame(files_frame, bg=CARD_BG); headers_frame.pack(fill="x", pady=(5, 5), padx=15)
        headers_frame.columnconfigure(0, weight=80); headers_frame.columnconfigure(1, weight=15); headers_frame.columnconfigure(2, weight=5)
        tk.Label(headers_frame, text="File Name", font=(FONT_FAMILY, 9), bg=CARD_BG, fg=MUTED_TEXT, anchor="w").grid(row=0, column=0, sticky="w")
        tk.Label(headers_frame, text="Status", font=(FONT_FAMILY, 9), bg=CARD_BG, fg=MUTED_TEXT, anchor="center").grid(row=0, column=1, sticky="nsew")
        tk.Label(headers_frame, text="Select", font=(FONT_FAMILY, 9), bg=CARD_BG, fg=MUTED_TEXT, anchor="e").grid(row=0, column=2, sticky="e")

        self.canvas = tk.Canvas(files_frame, bg=CARD_BG, highlightthickness=0)
        self.files_sb = ttk.Scrollbar(files_frame, orient="vertical", command=self.canvas.yview)
        self.files_inner = tk.Frame(self.canvas, bg=CARD_BG)
        
        self.files_inner.bind("<Configure>", self._on_files_inner_configure)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.files_inner, anchor="nw")
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.configure(yscrollcommand=self.files_sb.set)
        self.canvas.pack(side="left", fill="both", expand=True, padx=(15, 0), pady=(0, 15))
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        if HAS_DND:
            self.files_inner.drop_target_register(DND_FILES)
            self.files_inner.dnd_bind('<<Drop>>', self._handle_drop)
            self.canvas.drop_target_register(DND_FILES)
            self.canvas.dnd_bind('<<Drop>>', self._handle_drop)

        # Details Frame (Card style with distinct header)
        details_frame = tk.Frame(top_frame, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        details_frame.grid(row=0, column=1, sticky="nsew")
        
        details_header = tk.Frame(details_frame, bg=CARD_HEADER_BG)
        details_header.pack(fill="x")
        tk.Label(details_header, text="Details", font=FONT_BOLD, bg=CARD_HEADER_BG, fg=TEXT_COLOR).pack(anchor="w", padx=15, pady=10)
        
        self.detail_text = tk.Text(details_frame, wrap="word", font=FONT_NORMAL, bg=CARD_BG, fg=TEXT_COLOR, relief="flat", padx=15, pady=5, state="disabled")
        self.details_sb = ttk.Scrollbar(details_frame, orient="vertical", command=self.detail_text.yview)
        self.detail_text.configure(yscrollcommand=self.details_sb.set)
        self.detail_text.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 15))
        self.detail_text.bind("<Configure>", self._update_details_scrollbar)

        # Action Buttons (Bottom Area)
        btn_frame = tk.Frame(main_frame, bg=BG_COLOR); btn_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        btn_style = {"font": FONT_BTN, "relief": "flat", "bd": 0, "cursor": "hand2", "padx": 15, "pady": 6}
        
        self.convert_btn = tk.Button(btn_frame, text="🚀 Convert Selected", bg=SUCCESS, fg="white", activebackground="#059669", command=self._start_conversion, **btn_style)
        self.convert_btn.pack(side="left", padx=(0, 8))
        
        tk.Button(btn_frame, text="📄 Add .py", bg=ACCENT, fg="white", activebackground="#2563eb", command=self._add_py_files, **btn_style).pack(side="left", padx=(0, 8))
        tk.Button(btn_frame, text="📦 Add Data", bg=WARNING, fg="white", activebackground="#d97706", command=self._add_data_file, **btn_style).pack(side="left", padx=(0, 8))
        
        tk.Button(btn_frame, text="🔄 Refresh", bg="#cbd5e1", fg="#1e293b", activebackground="#94a3b8", command=self._refresh_file_list, **btn_style).pack(side="left", padx=(0, 8))
        tk.Button(btn_frame, text="☑️ Select All", bg="#cbd5e1", fg="#1e293b", activebackground="#94a3b8", command=self._select_all, **btn_style).pack(side="left", padx=(0, 15))

        self.progress = ttk.Progressbar(btn_frame, mode="indeterminate", style="TProgressbar"); self.progress.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # Console Logs (Dark theme with distinct header)
        console_frame = tk.Frame(main_frame, bg=CONSOLE_BG, highlightbackground=BORDER, highlightthickness=1)
        console_frame.grid(row=2, column=0, sticky="nsew")
        
        log_toolbar = tk.Frame(console_frame, bg=CONSOLE_HEADER_BG); log_toolbar.pack(fill="x", side="top")
        tk.Label(log_toolbar, text="Console Logs", font=FONT_BOLD, bg=CONSOLE_HEADER_BG, fg="#f8fafc").pack(side="left", padx=15, pady=8)
        tk.Button(log_toolbar, text="💾 Save Log", font=(FONT_FAMILY, 8), bg="#334155", fg="#cbd5e1", relief="flat", cursor="hand2", bd=0, command=self._save_log, padx=10, pady=2).pack(side="right", padx=15, pady=5)
        
        self.log = scrolledtext.ScrolledText(console_frame, font=FONT_MONO, bg=CONSOLE_BG, fg=CONSOLE_FG, relief="flat", wrap="none", state="disabled")
        self.log.pack(fill="both", expand=True, padx=5, pady=5)

    def _on_files_inner_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._update_files_scrollbar()

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        self._update_files_scrollbar()

    def _update_files_scrollbar(self):
        self.canvas.update_idletasks()
        bbox = self.canvas.bbox("all")
        if bbox and bbox[3] > self.canvas.winfo_height():
            if not self.files_sb.winfo_ismapped():
                self.files_sb.pack(side="right", fill="y", pady=(0, 15), padx=(0, 5))
        else:
            if self.files_sb.winfo_ismapped():
                self.files_sb.pack_forget()

    def _toggle_row(self, event, row_frame, widgets, file_name, var):
        var.set(not var.get())
        self._highlight_row(row_frame, widgets, file_name)

    def _handle_drop(self, event):
        try:
            files = self.root.tk.splitlist(event.data)
            added = 0
            for f in files:
                if f.lower().endswith('.py') and f not in self.session_extra_files:
                    self.session_extra_files.append(f); added += 1
            if added:
                self._log(f"✅ Added {added} file(s) via Drag & Drop.")
                self._refresh_file_list()
        except Exception as e:
            self._log(f"❌ Drop Error: {e}")

    def _add_py_files(self):
        try:
            files = filedialog.askopenfilenames(title="Select Python Files", filetypes=[("Python", "*.py")])
            for f in files:
                if f not in self.session_extra_files: self.session_extra_files.append(f)
            self._refresh_file_list()
        except Exception as e: self._log(f"Error adding files: {e}")

    def _add_data_file(self):
        try:
            files = filedialog.askopenfilenames(title="Select Data Files")
            for f in files:
                if f not in self.config_data["data_files"]:
                    self.config_data["data_files"].append(f)
                    self._log(f"📦 Added Data File: {os.path.basename(f)}")
            self._save_settings()
        except Exception as e: self._log(f"Error adding data: {e}")

    def _open_config(self): 
        try: ConfigWindow(self.root, self.scan_dir, self.log_dir)
        except Exception as e: messagebox.showerror("Error", f"Failed to open Config:\n{e}")

    def _save_log(self):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filepath = self.log_dir / f"gui_log_{timestamp}.txt"
            with open(filepath, "w", encoding="utf-8") as f: f.write(self.log.get("1.0", "end-1c"))
            messagebox.showinfo("Success", f"Log saved to:\n{filepath}")
        except Exception as e: messagebox.showerror("Error", f"Failed to save log:\n{e}")

    def _update_details_scrollbar(self, event=None):
        if self.detail_text.yview()[1] < 1.0 or self.detail_text.yview()[0] > 0.0: self.details_sb.pack(side="right", fill="y", pady=(0, 15))
        else: self.details_sb.pack_forget()

    def _on_mousewheel(self, event):
        widget = self.root.winfo_containing(event.x_root, event.y_root)
        if widget in [self.canvas, self.files_inner] or str(widget).startswith(str(self.files_inner)): self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _show_about(self):
        try:
            about_win = tk.Toplevel(self.root); about_win.title("About"); w, h = 500, 520
            self.root.update_idletasks(); x = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - (w // 2); y = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - (h // 2)
            about_win.geometry(f"{w}x{h}+{x}+{y}")
            about_win.configure(bg=PRIMARY)
            about_win.resizable(False, False); about_win.transient(self.root); about_win.grab_set()

            main_f = tk.Frame(about_win, bg=CARD_BG)
            main_f.pack(fill="both", expand=True, padx=15, pady=15)

            tk.Label(main_f, text="✨ Python to EXE Converter ✨", font=(FONT_FAMILY, 16, "bold"), bg=CARD_BG, fg=PRIMARY).pack(pady=(20, 0))
            tk.Label(main_f, text="Version 3.5.1", font=(FONT_FAMILY, 10, "bold"), bg=CARD_BG, fg=ACCENT).pack(pady=(0, 15))
            
            text = tk.Text(main_f, wrap="word", font=FONT_NORMAL, bg=CARD_BG, fg=TEXT_COLOR, relief="flat", height=3)
            text.insert("1.0", "A portable tool designed to convert Python scripts to standalone EXE files in restricted environments."); text.tag_configure("ltr", justify="left"); text.tag_add("ltr", "1.0", "end"); text.config(state="disabled"); text.pack(padx=20, fill="x", pady=(0, 10))

            tk.Label(main_f, text="🧑‍💻 Designed & Developed by:", font=FONT_BOLD, bg=CARD_BG, fg=MUTED_TEXT).pack()
            tk.Label(main_f, text="Mohammad Azadfar", font=(FONT_FAMILY, 12, "bold"), bg=CARD_BG, fg=PRIMARY).pack()
            contact_frame = tk.Frame(main_f, bg=CARD_BG); contact_frame.pack(pady=(5, 15))
            lbl_email = tk.Label(contact_frame, text="📧 azadfar2009@gmail.com", font=FONT_NORMAL, bg=CARD_BG, fg=ACCENT, cursor="hand2"); lbl_email.pack(side="left", padx=10)
            lbl_email.bind("<Button-1>", lambda e: webbrowser.open("mailto:azadfar2009@gmail.com"))

            tk.Label(main_f, text="📝 Changelog:", font=FONT_BOLD, bg=CARD_BG, fg=PRIMARY).pack(anchor="w", padx=20)
            changelog_text = scrolledtext.ScrolledText(main_f, wrap="word", font=(FONT_FAMILY, 9), bg="#e2e8f0", fg=TEXT_COLOR, relief="solid", bd=1, height=7)
            changelog = """v3.5.1 (Final Fixes)
- Fixed output directory to always default to app location.
- Fixed icon selection not being applied.
- Added command logging for PyInstaller.
- Minor UI improvements.

v3.5.0 (Final Release)
- Removed Application Type (Defaults to console).
- Fixed scrollbar visibility in Files list.
- Optimized "Install from Internet" (10x faster).
- Added version check before package install.
- Improved network error handling (DNS/Timeout).
- Logs are saved to 'logs/' folder in root."""
            changelog_text.insert("1.0", changelog); changelog_text.config(state="disabled"); changelog_text.pack(padx=20, fill="both", expand=True, pady=(5, 10))
            
            tk.Button(main_f, text="Close", font=FONT_BOLD, bg="#e2e8f0", fg=TEXT_COLOR, relief="flat", activebackground="#cbd5e1", command=about_win.destroy, padx=25, pady=5).pack(pady=(0, 20))
        except Exception as e:
            messagebox.showerror("Error", f"Could not open About window: {e}")

    def _set_detail(self, text):
        self.detail_text.config(state="normal"); self.detail_text.delete("1.0", "end"); self.detail_text.insert("1.0", text); self.detail_text.config(state="disabled"); self._update_details_scrollbar()

    def _log(self, msg):
        try:
            self.log.config(state="normal"); self.log.insert("end", msg + "\n"); self.log.see("end"); self.log.config(state="disabled")
        except: pass

    def _refresh_file_list(self):
        try:
            for widget in self.files_inner.winfo_children(): widget.destroy()
            self.file_infos.clear(); self.check_vars.clear()
            self.active_row_frame = None; self.active_row_widgets = []
            
            files = []
            ignore_list = ("converter_gui.py", "get-pip.py", "PyLauncher.py", "clean_env.py", "build.bat", "runconverter.bat")
            
            for f in os.listdir(self.scan_dir):
                if f.endswith(".py") and f.lower() not in ignore_list:
                    files.append(str(self.scan_dir / f))
            
            for f in self.session_extra_files:
                if os.path.exists(f) and f not in files and os.path.basename(f).lower() not in ignore_list: 
                    files.append(f)
            
            files = sorted(list(set(files)), key=lambda x: os.path.basename(x).lower())

            if not files:
                tk.Label(self.files_inner, text="No .py files found. Drag & drop or Add .py", font=FONT_NORMAL, bg=CARD_BG, fg=MUTED_TEXT).pack(pady=20)
                self._log("⚠️ No files found.")
                self.root.after(50, self._update_files_scrollbar)
                return

            for f_path in files:
                f_name = os.path.basename(f_path)
                p = Path(f_path)
                dep = check_dependencies(p)
                self.file_infos[f_name] = {"path": f_path, "dep": dep}
                
                var = tk.BooleanVar(value=False); self.check_vars[f_name] = var
                
                row = tk.Frame(self.files_inner, bg=CARD_BG, pady=8); row.pack(fill="x")
                row.columnconfigure(0, weight=80); row.columnconfigure(1, weight=15); row.columnconfigure(2, weight=5)
                
                lbl_name = tk.Label(row, text=f_name, font=FONT_NORMAL, bg=CARD_BG, fg=TEXT_COLOR, anchor="w"); lbl_name.grid(row=0, column=0, sticky="w", padx=(10,0))
                
                status_text, status_fg = ("Missing Libs", DANGER) if dep.get('error') or dep['missing'] else ("Ready", SUCCESS)
                lbl_status = tk.Label(row, text=status_text, font=FONT_BOLD, bg=CARD_BG, fg=status_fg, anchor="center"); lbl_status.grid(row=0, column=1, sticky="nsew")
                
                chk = tk.Checkbutton(row, variable=var, bg=CARD_BG, activebackground=CARD_BG, cursor="hand2"); chk.grid(row=0, column=2, sticky="e", padx=5)
                
                row_widgets = [lbl_name, lbl_status, chk]
                for w in [row] + row_widgets: 
                    w.bind("<Button-1>", lambda e, r=row, ws=row_widgets, n=f_name: self._highlight_row(r, ws, n))
                    w.bind("<Double-Button-1>", lambda e, r=row, ws=row_widgets, n=f_name, v=var: self._toggle_row(e, r, ws, n, v))
                chk.config(command=lambda r=row, ws=row_widgets, n=f_name: self._highlight_row(r, ws, n))
                
                tk.Frame(self.files_inner, height=1, bg=BORDER).pack(fill="x")
                
            self._log(f"✅ List refreshed. Found {len(files)} file(s).")
            self.root.after(50, self._update_files_scrollbar)
        except Exception as e:
            self._log(f"❌ Error refreshing list: {e}")

    def _highlight_row(self, row_frame, widgets, file_name):
        if self.active_row_frame and self.active_row_widgets:
            self.active_row_frame.config(bg=CARD_BG)
            for w in self.active_row_widgets:
                try: w.config(bg=CARD_BG)
                except: pass
        row_frame.config(bg=HIGHLIGHT_BG)
        for w in widgets:
            try: w.config(bg=HIGHLIGHT_BG)
            except: pass
        self.active_row_frame = row_frame; self.active_row_widgets = widgets
        self._show_details(file_name)

    def _show_details(self, name):
        try:
            info = self.file_infos.get(name)
            if not info: return
            dep = info["dep"]
            
            lines = [f"📄 File: {name}\n📂 Path: {info['path']}\n\n"]
            if dep.get('error'): lines.append(f"⚠️ Code Read Error:\n{dep['error']}\n")
            else:
                if dep['missing']:
                    lines.append("❌ Missing Libraries (EXE might crash):\n"); lines.append(f"   {', '.join(dep['missing'])}\n\n")
                    lines.append("💡 Solution: Install via ⚙️ Config.\n")
                else: lines.append("✅ No missing dependencies detected.\nRuntime validation is still required.\n\n")
                if dep['available']: lines.append(f"✅ Available Libraries:\n   {', '.join(dep['available'])}\n\n")
                if dep['stdlib']:
                    shown = ', '.join(dep['stdlib'][:15]); more = '...' if len(dep['stdlib'])>15 else ''
                    lines.append(f"📦 Standard Python Libraries:\n   {shown}{more}")
            self._set_detail("\n".join(lines))
        except Exception as e:
            self._log(f"Error showing details: {e}")

    def _select_all(self):
        for var in self.check_vars.values(): var.set(True)

    def _start_conversion(self):
        if self.converting or not PYINSTALLER_AVAILABLE: return
        sel = [n for n, v in self.check_vars.items() if v.get()]
        if not sel: return messagebox.showwarning("No Selection", "Please select at least one file by checking the box.")
        
        try:
            dialog = BuildOptionsDialog(self.root, self.config_data)
            options = dialog.get_result()
            if not options: return
            
            # We only save the icon and onefile setting, NOT the output directory
            self.config_data["build_onefile"] = options["build_onefile"]
            self.config_data["build_icon"] = options["build_icon"]
            self._save_settings()
            
        except Exception as e:
            return messagebox.showerror("Error", f"Failed to open build options: {e}")
            
        self.converting = True; self.convert_btn.config(state="disabled", bg="#94a3b8"); self.progress.start(15)
        self._log(f"🚀 Starting batch conversion for {len(sel)} file(s)...\n")
        threading.Thread(target=self._worker, args=(sel, options), daemon=True).start()

    def _worker(self, selected, options):
        success, failed = [], []
        out_dir = Path(options["build_outdir"])
        
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            test_file = out_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
        except PermissionError:
            self.root.after(0, lambda: messagebox.showerror("Permission Error", f"Cannot write to output directory:\n{out_dir}\n\nPlease choose a different folder."))
            self.root.after(0, lambda: self._finish([], selected, len(selected)))
            return
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Output Error", f"Error preparing output directory:\n{e}"))
            self.root.after(0, lambda: self._finish([], selected, len(selected)))
            return
        
        for i, name in enumerate(selected):
            self.root.after(0, lambda n=name: self._log(f"--- Converting: {n} ---"))
            info = self.file_infos[name]
            py_path = Path(info["path"])
            
            build_temp_dir = APP_TEMP_DIR / f"build_{py_path.stem}_{int(time.time())}"
            work_path = build_temp_dir / "build"
            spec_path = build_temp_dir / "spec"
            build_temp_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                version_file = build_temp_dir / "version_info.txt"
                with open(version_file, "w") as vf:
                    vf.write(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=(1,0,0,0), prodvers=(1,0,0,0), mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0,0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'PyLauncher Generated'),
      StringStruct('FileDescription', 'Portable Python Application'),
      StringStruct('FileVersion', '1.0.0.0'),
      StringStruct('InternalName', '{py_path.stem}'),
      StringStruct('OriginalFilename', '{py_path.stem}.exe'),
      StringStruct('ProductName', '{py_path.stem}'),
      StringStruct('ProductVersion', '1.0.0.0')
    ])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)""")

                cmd = [
                    sys.executable, "-m", "PyInstaller",
                    "--noupx", "--clean", "--noconfirm",
                    "--version-file", str(version_file),
                    "--distpath", str(out_dir),
                    "--workpath", str(work_path),
                    "--specpath", str(spec_path),
                ]
                
                if options["build_onefile"]: cmd.append("--onefile")
                else: cmd.append("--onedir")
                
                if options["build_icon"] and os.path.exists(options["build_icon"]):
                    cmd.extend(["--icon", options["build_icon"]])
                
                for df in self.config_data.get("data_files", []):
                    if os.path.exists(df):
                        cmd.extend(["--add-data", f"{df};."])
                
                cmd.append(str(py_path))
                
                # Log the exact command to help debug
                self.root.after(0, lambda c=cmd: self._log(f"Running: {' '.join(c)}"))
                
                self.active_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', creationflags=0x08000000)
                stderr_output = ""
                for line in self.active_process.stdout:
                    clean_line = line.strip()
                    if clean_line:
                        stderr_output += clean_line + "\n"
                        self.root.after(0, lambda l=clean_line: self._log(l))
                
                self.active_process.wait()
                
                if options["build_onefile"]:
                    exe_path = out_dir / (py_path.stem + ".exe")
                else:
                    exe_path = out_dir / py_path.stem / (py_path.stem + ".exe")
                
                if self.active_process.returncode == 0 and exe_path.exists():
                    success.append(name); self.root.after(0, lambda n=name: self._log(f"✅ SUCCESS: {n}\n"))
                else:
                    error_msg = "Build Failed."
                    if "ModuleNotFoundError" in stderr_output:
                        module = stderr_output.split("ModuleNotFoundError: No module named '")[1].split("'")[0]
                        error_msg = f"Missing Module: {module}. Install it via Config."
                    elif "SyntaxError" in stderr_output:
                        error_msg = "Syntax Error in Python file."
                    elif "PermissionError" in stderr_output:
                        error_msg = "Permission denied while writing files."
                    
                    failed.append((name, error_msg))
                    self.root.after(0, lambda n=name, e=error_msg: self._log(f"❌ FAILED: {n} -> {e}\n"))
            except Exception as e:
                failed.append((name, str(e))); self.root.after(0, lambda n=name, err=str(e): self._log(f"❌ ERROR: {err}\n"))
            finally:
                shutil.rmtree(build_temp_dir, ignore_errors=True)
                
        self.root.after(0, lambda: self._finish(success, failed, len(selected), out_dir))

    def _finish(self, success, failed, total, out_dir=None):
        self.converting = False; self.progress.stop(); self.progress["value"] = 0; self.convert_btn.config(state="normal", bg=SUCCESS)
        self._log(f"\n🏁 FINISHED: {len(success)} succeeded, {len(failed)} failed out of {total}.")
        
        if not out_dir: return
        
        if success:
            msg = f"Successfully converted {len(success)} file(s).\nOutput: {out_dir}"
            if failed: msg += f"\n\n{len(failed)} failed (check logs)."
            messagebox.showinfo("Finished", msg)
        else: messagebox.showerror("Failed", "No files converted. Check logs.")

def main():
    scan_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    if HAS_DND: root = TkinterDnD.Tk()
    else: root = tk.Tk()
        
    if not PYINSTALLER_AVAILABLE: return messagebox.showerror("Critical Error", "PyInstaller not found in portable environment.")
    
    def excepthook(exc_type, exc_value, exc_traceback):
        err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        with open(APP_TEMP_DIR / "crash_log.txt", "w") as f: f.write(err_msg)
        messagebox.showerror("Critical Error", f"An unexpected error occurred:\n{exc_value}\n\nLog saved to temp folder.")
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    sys.excepthook = excepthook
    
    ConverterApp(root, scan_path)
    root.mainloop()

if __name__ == "__main__":
    main()