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
import time
import gzip
import io
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

try:
    from packaging import version as pkg_version
except ImportError:
    pkg_version = None

# --- PyInstaller import ---
try:
    import PyInstaller
    PYINSTALLER_AVAILABLE = True
except ImportError:
    PYINSTALLER_AVAILABLE = False

# --- Font & Colors ---
FONT_FAMILY = "Tahoma"
FONT_NORMAL = (FONT_FAMILY, 10)
FONT_BOLD = (FONT_FAMILY, 10, "bold")
FONT_BTN = (FONT_FAMILY, 9, "bold")
FONT_TITLE = (FONT_FAMILY, 15, "bold")
FONT_MONO = ("Consolas", 9)

BG_COLOR = "#f4f7f6"
CARD_BG = "#ffffff"
PRIMARY = "#2c3e50"
ACCENT = "#3498db"
SUCCESS = "#2ecc71"
DANGER = "#e74c3c"
WARNING = "#f39c12"
TEXT_COLOR = "#34495e"
HIGHLIGHT_BG = "#e0f2fe"

STDLIB_MODULES = set(sys.builtin_module_names) | {
    'os', 'sys', 're', 'json', 'math', 'datetime', 'pathlib', 'subprocess',
    'threading', 'tkinter', 'typing', 'collections', 'itertools', 'functools',
    'importlib', 'shutil', 'tempfile', 'ast', 'traceback', 'logging', 'csv',
    'sqlite3', 'urllib', 'http', 'socket', 'ssl', 'hashlib', 'base64',
    'zlib', 'gzip', 'pickle', 'copy', 'random', 'time', 'uuid', 'glob',
    'argparse', 'configparser', 'unittest', 'xml', 'html', 'email'
}

ACTIVE_PROCESSES = []

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

# ================= Config Window (Package Manager) =================
class ConfigWindow:
    def __init__(self, parent, scan_dir):
        self.parent = parent
        self.scan_dir = scan_dir
        self.is_busy = False # فلگ برای بررسی اینکه آیا عملیاتی در جریان است یا نه
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
        style.configure("TNotebook.Tab", background="#dcdde1", foreground="#7f8c8d", padding=[12, 6], font=(FONT_FAMILY, 9))
        style.map("TNotebook.Tab", 
                  background=[("selected", CARD_BG)], 
                  foreground=[("selected", PRIMARY)],
                  font=[("selected", (FONT_FAMILY, 10, "bold"))],
                  padding=[("selected", [15, 8])])

        self.notebook = ttk.Notebook(self.win)
        self.notebook.pack(fill="both", expand=False, padx=10, pady=(10, 5))

        self._build_installed_tab()
        self._build_online_tab()
        self._build_offline_tab()

        log_frame = tk.LabelFrame(self.win, text=" Output ", font=FONT_BOLD, bg=CARD_BG, fg=PRIMARY)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        log_toolbar = tk.Frame(log_frame, bg=CARD_BG)
        log_toolbar.pack(fill="x", side="top", pady=(0, 5), padx=5)
        
        tk.Button(log_toolbar, text="💾 Save Log", font=(FONT_FAMILY, 9), bg="#7f8c8d", fg="white", relief="flat", cursor="hand2", bd=0, activebackground="#95a5a6", activeforeground="white", padx=10, pady=2, command=self._save_log).pack(side="right")
        
        self.log = scrolledtext.ScrolledText(log_frame, height=10, font=FONT_MONO, bg="#1e272e", fg="#d2dae2", state="disabled")
        self.log.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        self._load_installed_packages()

    def _on_close(self):
        # فقط اگر عملیاتی در حال انجام باشد پیغام میدهد
        if self.is_busy:
            if not messagebox.askokcancel("Exit", "An operation is currently in progress. Are you sure you want to cancel and close?", parent=self.win):
                return
        
        # بستن پروسه‌های فعال در صورت بستن پنجره
        for p in ACTIVE_PROCESSES:
            try:
                subprocess.run(f"taskkill /F /T /PID {p.pid}", shell=True, creationflags=0x08000000)
            except: pass
            
        self.win.destroy()

    def _log(self, msg):
        if not self.win.winfo_exists(): return
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def _save_log(self):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filepath = self.scan_dir / f"pkg_manager_log_{timestamp}.txt"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self.log.get("1.0", "end-1c"))
            messagebox.showinfo("Success", f"Log saved successfully to:\n{filepath}", parent=self.win)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save log:\n{e}", parent=self.win)

    def _build_installed_tab(self):
        tab = tk.Frame(self.notebook, bg=CARD_BG)
        self.notebook.add(tab, text="Installed Packages")

        toolbar = tk.Frame(tab, bg=CARD_BG)
        toolbar.pack(fill="x", pady=10, padx=10)
        
        tk.Button(toolbar, text="🔄 Check for Updates", font=FONT_BTN, bg=ACCENT, fg="white", relief="flat", activebackground="#2980b9", activeforeground="white", cursor="hand2", command=self._check_updates).pack(side="left", padx=(0, 10))
        tk.Button(toolbar, text="⬆️ Update Selected", font=FONT_BTN, bg=SUCCESS, fg="white", relief="flat", activebackground="#27ae60", activeforeground="white", cursor="hand2", command=self._update_selected).pack(side="left")

        columns = ("package", "version", "latest")
        tree_frame = tk.Frame(tab, bg=CARD_BG)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended", height=10)
        self.tree.heading("package", text="Package Name", anchor="w")
        self.tree.heading("version", text="Installed Version", anchor="center")
        self.tree.heading("latest", text="Latest Version", anchor="center")
        self.tree.column("package", width=300)
        self.tree.column("version", width=150, anchor="center")
        self.tree.column("latest", width=150, anchor="center")
        
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _build_online_tab(self):
        tab = tk.Frame(self.notebook, bg=CARD_BG)
        self.notebook.add(tab, text="Install from Internet")

        center_frame = tk.Frame(tab, bg=CARD_BG)
        center_frame.pack(expand=True)
        
        tk.Label(center_frame, text="Enter Package Name to Install:", font=FONT_BOLD, bg=CARD_BG, fg=PRIMARY).pack(pady=(0, 10))
        
        entry_frame = tk.Frame(center_frame, bg=CARD_BG)
        entry_frame.pack(pady=5)
        
        self.entry_pkg = tk.Entry(entry_frame, font=(FONT_FAMILY, 12), width=30, relief="solid", bd=1)
        self.entry_pkg.pack(side="left", padx=(0, 10), ipady=5)
        # اتصال کلید اینتر به دکمه جستجو
        self.entry_pkg.bind("<Return>", lambda e: self._check_and_install())
        
        self.btn_check_install = tk.Button(entry_frame, text="🌐 Search & Install", font=FONT_BOLD, bg=ACCENT, fg="white", relief="flat", activebackground="#2980b9", activeforeground="white", cursor="hand2", padx=15, pady=5, command=self._check_and_install)
        self.btn_check_install.pack(side="left")

    def _build_offline_tab(self):
        tab = tk.Frame(self.notebook, bg=CARD_BG)
        self.notebook.add(tab, text="Install from File")

        center_frame = tk.Frame(tab, bg=CARD_BG)
        center_frame.pack(expand=True)
        
        tk.Label(center_frame, text="Install Local Package File", font=(FONT_FAMILY, 14, "bold"), bg=CARD_BG, fg=PRIMARY).pack(pady=(0, 20))
        
        file_box = tk.Frame(center_frame, bg="#f8f9fa", bd=2, relief="groove")
        file_box.pack(pady=10, padx=20, fill="x")
        
        self.lbl_file = tk.Label(file_box, text="No file selected (.whl or .tar.gz)", font=FONT_NORMAL, bg="#f8f9fa", fg="#7f8c8d", pady=20)
        self.lbl_file.pack()
        
        btn_frame = tk.Frame(center_frame, bg=CARD_BG)
        btn_frame.pack(pady=15)
        
        tk.Button(btn_frame, text="📁 Browse File", font=FONT_BOLD, bg="#95a5a6", fg="white", relief="flat", activebackground="#7f8c8d", activeforeground="white", cursor="hand2", padx=20, pady=5, command=self._browse_file).pack(side="left", padx=10)
                  
        self.btn_install_offline = tk.Button(btn_frame, text="📥 Install File", font=FONT_BOLD, bg=SUCCESS, fg="white", relief="flat", activebackground="#27ae60", activeforeground="white", cursor="hand2", padx=20, pady=5, state="disabled", command=self._install_offline)
        self.btn_install_offline.pack(side="left", padx=10)
        
        self.selected_file = None

    def _load_installed_packages(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        def fetch():
            try:
                out = subprocess.check_output([sys.executable, "-m", "pip", "list", "--format=json"], text=True, creationflags=0x08000000)
                json_str = out[out.find('['):out.rfind(']')+1]
                packages = json.loads(json_str)
                packages.sort(key=lambda x: x['name'].lower())
                
                def update_ui():
                    if not self.win.winfo_exists(): return
                    for p in packages:
                        self.tree.insert("", "end", values=(p['name'], p['version'], "-"))
                self.win.after(0, update_ui)
            except Exception as e:
                self.win.after(0, lambda: self._log(f"Error loading packages: {e}"))
        
        threading.Thread(target=fetch, daemon=True).start()

    def _check_updates(self):
        self._log("Checking for updates... (This might take a moment)")
        
        def fetch():
            try:
                out = subprocess.check_output([sys.executable, "-m", "pip", "list", "--outdated", "--format=json"], text=True, creationflags=0x08000000)
                json_str = out[out.find('['):out.rfind(']')+1]
                outdated = json.loads(json_str)
                outdated_dict = {p['name'].lower(): p['latest_version'] for p in outdated}
                
                def update_ui():
                    if not self.win.winfo_exists(): return
                    for item in self.tree.get_children():
                        vals = self.tree.item(item, "values")
                        pkg_name = str(vals[0]).lower()
                        if pkg_name in outdated_dict:
                            self.tree.item(item, values=(vals[0], vals[1], outdated_dict[pkg_name]))
                    self._log("Check complete. See 'Latest Version' column.")
                self.win.after(0, update_ui)
            except Exception as e:
                self.win.after(0, lambda: self._log(f"Error checking updates: {e}"))
                
        threading.Thread(target=fetch, daemon=True).start()

    def _update_selected(self):
        selections = self.tree.selection()
        if not selections:
            messagebox.showinfo("Info", "Please select at least one package to update.", parent=self.win)
            return
            
        packages_to_update = []
        for sel in selections:
            vals = self.tree.item(sel, "values")
            pkg = vals[0]
            latest = vals[2]
            
            if latest == "-":
                self._log(f"Skipping {pkg} (No update available or not checked)")
                continue
                
            packages_to_update.append(pkg)
            self.tree.item(sel, values=(pkg, latest, "Up to date"))
            
        if not packages_to_update:
            messagebox.showinfo("Info", "None of the selected packages have available updates.", parent=self.win)
            return

        pkg_str = " ".join(packages_to_update)
        self._log(f"Updating: {pkg_str}...")
        self._run_pip(["install", "--upgrade"] + packages_to_update)

    def _check_and_install(self):
        pkg = self.entry_pkg.get().strip()
        if not pkg: return
        
        self.is_busy = True
        self.btn_check_install.config(state="disabled", text="⏳ Checking...")
        self._log(f"Checking status for '{pkg}'...")
        
        def process():
            local_version = None
            try:
                local_version = importlib.metadata.version(pkg)
            except importlib.metadata.PackageNotFoundError:
                pass
            
            remote_version = None
            size_str = "Unknown"
            summary = ""
            
            try:
                url = f"https://pypi.org/pypi/{pkg}/json"
                # استفاده از gzip برای دانلود سریع‌تر فایل JSON
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept-Encoding': 'gzip'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    data_bytes = response.read()
                    if response.info().get('Content-Encoding') == 'gzip':
                        data_bytes = gzip.decompress(data_bytes)
                    
                    data = json.loads(data_bytes.decode())
                    info = data['info']
                    remote_version = info['version']
                    summary = info['summary'] or "No description."
                    
                    if 'urls' in data and len(data['urls']) > 0:
                        for u in data['urls']:
                            if u['packagetype'] == 'bdist_wheel' and u['size']:
                                size_mb = u['size'] / (1024 * 1024)
                                size_str = f"~{size_mb:.2f} MB"
                                break
            except Exception as e:
                self.win.after(0, lambda: self._log(f"Error connecting to PyPI: {e}"))
                self.win.after(0, lambda: self._reset_check_btn())
                return

            def show_dialog():
                self._reset_check_btn()
                if local_version and remote_version:
                    try:
                        if pkg_version.parse(local_version) >= pkg_version.parse(remote_version):
                            messagebox.showinfo("Up to Date", f"Package '{pkg}' is already installed.\n\nInstalled Version: {local_version}\nLatest Version: {remote_version}", parent=self.win)
                            self._log(f"'{pkg}' is already up to date.")
                            return
                        else:
                            msg = f"Update available!\n\nInstalled: {local_version}\nLatest: {remote_version}\nApprox Size: {size_str}\n\nDo you want to update?"
                            if messagebox.askyesno("Confirm Update", msg, parent=self.win):
                                self._log(f"Updating {pkg} to {remote_version}...")
                                self._run_pip(["install", "--upgrade", pkg])
                            return
                    except Exception:
                        pass

                msg = f"Package: {pkg}\nLatest Version: {remote_version}\nApproximate Size: {size_str}\n\nDescription:\n{summary}\n\nDo you want to install?"
                if messagebox.askyesno("Confirm Installation", msg, parent=self.win):
                    self._log(f"Starting installation of {pkg}...")
                    self._run_pip(["install", pkg])
                else:
                    self._log("Installation cancelled by user.")
                    
            self.win.after(0, show_dialog)
                
        threading.Thread(target=process, daemon=True).start()

    def _reset_check_btn(self):
        self.is_busy = False
        self.btn_check_install.config(state="normal", text="🌐 Search & Install")

    def _browse_file(self):
        filepath = filedialog.askopenfilename(parent=self.win, title="Select Package", filetypes=[("Python Packages", "*.whl *.tar.gz"), ("All Files", "*.*")])
        if filepath:
            self.selected_file = os.path.abspath(filepath)
            self.lbl_file.config(text=os.path.basename(filepath), fg=SUCCESS, font=(FONT_FAMILY, 10, "bold"))
            self.btn_install_offline.config(state="normal")

    def _install_offline(self):
        if not self.selected_file: return
        self._log(f"Installing from local file: {self.selected_file}")
        self._run_pip(["install", self.selected_file])

    def _run_pip(self, args):
        self.is_busy = True
        def worker():
            try:
                cmd = [sys.executable, "-m", "pip"] + args
                if "--progress-bar" not in args:
                    cmd += ["--progress-bar", "on"]
                
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                    text=True, encoding='utf-8', errors='replace', creationflags=0x08000000
                )
                ACTIVE_PROCESSES.append(process)
                
                buffer = ""
                while True:
                    char = process.stdout.read(1)
                    if not char and process.poll() is not None:
                        break
                    if char in ('\r', '\n'):
                        if buffer.strip():
                            self.win.after(0, lambda l=buffer.strip(): self._log(l))
                        buffer = ""
                    else:
                        buffer += char
                
                if buffer.strip():
                    self.win.after(0, lambda l=buffer.strip(): self._log(l))
                
                process.wait()
                if process in ACTIVE_PROCESSES: ACTIVE_PROCESSES.remove(process)
                
                def finish_ui():
                    self.is_busy = False
                    if not self.win.winfo_exists(): return
                    if process.returncode == 0:
                        self._log("✅ Operation completed successfully.")
                        self._load_installed_packages()
                    else:
                        self._log("❌ Operation failed.")
                self.win.after(0, finish_ui)
                
            except Exception as e:
                self.win.after(0, lambda: self._log(f"❌ Error: {e}"))
                self.win.after(0, lambda: setattr(self, 'is_busy', False))
                
        threading.Thread(target=worker, daemon=True).start()


# ================= Main GUI Application =================
class ConverterApp:
    def __init__(self, root, scan_path=None):
        self.root = root
        self.root.title("Python to EXE Converter")
        self.root.geometry("1050x650")
        self.root.configure(bg=BG_COLOR)
        self.root.minsize(950, 600)
        
        try:
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 6) 
        except: pass

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        if scan_path and os.path.isdir(scan_path):
            self.scan_dir = Path(scan_path).resolve()
        else:
            current_dir = Path(__file__).resolve().parent
            self.scan_dir = current_dir.parent if current_dir.name == "env" else current_dir
            
        self.file_infos = {}
        self.check_vars = {}
        self.converting = False
        self.active_process = None
        
        self.active_row_frame = None
        self.active_row_widgets = []
        
        self._setup_styles()
        self._build_ui()
        self._refresh_file_list()

    def _on_closing(self):
        if self.converting:
            if not messagebox.askyesno("Warning", "A conversion is currently in progress. Are you sure you want to exit?"):
                return
            if self.active_process:
                try:
                    subprocess.run(f"taskkill /F /T /PID {self.active_process.pid}", shell=True, creationflags=0x08000000)
                except: pass
        
        for p in ACTIVE_PROCESSES:
            try:
                subprocess.run(f"taskkill /F /T /PID {p.pid}", shell=True, creationflags=0x08000000)
            except: pass
            
        self.root.destroy()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TProgressbar", thickness=12, background=SUCCESS, troughcolor="#ecf0f1", bordercolor="#bdc3c7")

    def _build_ui(self):
        header = tk.Frame(self.root, bg=PRIMARY, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="🐍  Python to EXE Converter", font=FONT_TITLE, bg=PRIMARY, fg="white").pack(side="left", padx=20)

        btn_frame_header = tk.Frame(header, bg=PRIMARY)
        btn_frame_header.pack(side="right", padx=20, pady=15)

        tk.Button(btn_frame_header, text="⚙️ Config", font=FONT_BOLD, bg="#e67e22", fg="white", relief="flat", cursor="hand2", bd=0, activebackground="#d35400", activeforeground="white", command=self._open_config).pack(side="left", padx=(0, 10), ipadx=10)
        tk.Button(btn_frame_header, text="About", font=FONT_BOLD, bg=ACCENT, fg="white", relief="flat", cursor="hand2", bd=0, activebackground="#2980b9", activeforeground="white", command=self._show_about).pack(side="left", ipadx=15)

        bar = tk.Frame(self.root, bg=BG_COLOR)
        bar.pack(fill="x", padx=20, pady=(10, 5))
        tk.Label(bar, text=f"📂 Current Directory: {self.scan_dir}", font=FONT_NORMAL, bg=BG_COLOR, fg=TEXT_COLOR).pack(side="left")

        main_frame = tk.Frame(self.root, bg=BG_COLOR)
        main_frame.pack(fill="both", expand=True, padx=20, pady=5)
        main_frame.rowconfigure(0, weight=80) 
        main_frame.rowconfigure(1, weight=0) 
        main_frame.rowconfigure(2, weight=20) 
        main_frame.columnconfigure(0, weight=1)

        top_frame = tk.Frame(main_frame, bg=BG_COLOR)
        top_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        top_frame.rowconfigure(0, weight=1)
        top_frame.columnconfigure(0, weight=7)
        top_frame.columnconfigure(1, weight=3)

        files_frame = tk.LabelFrame(top_frame, text=" Python Files ", font=FONT_BOLD, bg=CARD_BG, fg=PRIMARY, padx=10, pady=10, bd=1, relief="solid")
        files_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        headers_frame = tk.Frame(files_frame, bg=BG_COLOR)
        headers_frame.pack(fill="x", pady=(0, 5))
        headers_frame.columnconfigure(0, weight=80)
        headers_frame.columnconfigure(1, weight=15)
        headers_frame.columnconfigure(2, weight=5)
        
        tk.Label(headers_frame, text="File Name", font=FONT_BOLD, bg=BG_COLOR, fg=PRIMARY, anchor="w").grid(row=0, column=0, sticky="w")
        tk.Label(headers_frame, text="Status", font=FONT_BOLD, bg=BG_COLOR, fg=PRIMARY, anchor="center").grid(row=0, column=1, sticky="nsew")
        tk.Label(headers_frame, text="Select", font=FONT_BOLD, bg=BG_COLOR, fg=PRIMARY, anchor="e").grid(row=0, column=2, sticky="e")

        self.canvas = tk.Canvas(files_frame, bg=CARD_BG, highlightthickness=0)
        self.files_sb = ttk.Scrollbar(files_frame, orient="vertical", command=self.canvas.yview)
        self.files_inner = tk.Frame(self.canvas, bg=CARD_BG)
        
        self.files_inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.files_inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.canvas.configure(yscrollcommand=self.files_sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.files_sb.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        details_frame = tk.LabelFrame(top_frame, text=" Details ", font=FONT_BOLD, bg=CARD_BG, fg=PRIMARY, padx=10, pady=10, bd=1, relief="solid")
        details_frame.grid(row=0, column=1, sticky="nsew")
        
        self.detail_text = tk.Text(details_frame, wrap="word", font=FONT_NORMAL, bg="#fafafa", fg=TEXT_COLOR, relief="flat", padx=15, pady=15, state="disabled")
        self.details_sb = ttk.Scrollbar(details_frame, orient="vertical", command=self.detail_text.yview)
        self.detail_text.configure(yscrollcommand=self.details_sb.set)
        self.detail_text.pack(side="left", fill="both", expand=True)
        self.detail_text.bind("<Configure>", self._update_details_scrollbar)

        btn_frame = tk.Frame(main_frame, bg=BG_COLOR)
        btn_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        btn_style = {"font": FONT_BTN, "relief": "flat", "bd": 0, "cursor": "hand2", "padx": 15, "pady": 6}
        
        self.convert_btn = tk.Button(btn_frame, text="🚀 Convert Selected", bg=SUCCESS, fg="white", activebackground="#27ae60", activeforeground="white", command=self._start_conversion, **btn_style)
        self.convert_btn.pack(side="left", padx=(0, 8))

        tk.Button(btn_frame, text="🔄 Refresh List", bg=ACCENT, fg="white", activebackground="#2980b9", activeforeground="white", command=self._refresh_file_list, **btn_style).pack(side="left", padx=(0, 8))
        tk.Button(btn_frame, text="☑️ Select All", bg="#95a5a6", fg="white", activebackground="#7f8c8d", activeforeground="white", command=self._select_all, **btn_style).pack(side="left", padx=(0, 15))

        self.progress = ttk.Progressbar(btn_frame, mode="indeterminate", style="TProgressbar")
        self.progress.pack(side="left", fill="x", expand=True)

        console_frame = tk.LabelFrame(main_frame, text=" Console Logs ", font=FONT_BOLD, bg=CARD_BG, fg=PRIMARY, padx=10, pady=5, bd=1, relief="solid")
        console_frame.grid(row=2, column=0, sticky="nsew")
        
        log_toolbar = tk.Frame(console_frame, bg=CARD_BG)
        log_toolbar.pack(fill="x", side="top", pady=(0, 5))
        
        tk.Button(log_toolbar, text="💾 Save Log", font=(FONT_FAMILY, 9), bg="#7f8c8d", fg="white", relief="flat", cursor="hand2", bd=0, activebackground="#95a5a6", activeforeground="white", padx=10, pady=2, command=self._save_log).pack(side="right")
        
        self.log = scrolledtext.ScrolledText(console_frame, font=FONT_MONO, bg="#1e272e", fg="#d2dae2", relief="flat", wrap="none", state="disabled")
        self.log.pack(fill="both", expand=True)

    def _open_config(self):
        ConfigWindow(self.root, self.scan_dir)

    def _save_log(self):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filepath = self.scan_dir / f"log_{timestamp}.txt"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self.log.get("1.0", "end-1c"))
            messagebox.showinfo("Success", f"Log saved successfully to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save log:\n{e}")

    def _update_details_scrollbar(self, event=None):
        if self.detail_text.yview()[1] < 1.0 or self.detail_text.yview()[0] > 0.0:
            self.details_sb.pack(side="right", fill="y")
        else:
            self.details_sb.pack_forget()

    def _on_mousewheel(self, event):
        widget = self.root.winfo_containing(event.x_root, event.y_root)
        if widget in [self.canvas, self.files_inner] or str(widget).startswith(str(self.files_inner)):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _show_about(self):
        about_win = tk.Toplevel(self.root)
        about_win.title("About")
        w, h = 500, 520
        
        self.root.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - (w // 2)
        y = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - (h // 2)
        about_win.geometry(f"{w}x{h}+{x}+{y}")
        
        about_win.configure(bg=CARD_BG)
        about_win.resizable(False, False)
        about_win.transient(self.root)
        about_win.grab_set()

        tk.Label(about_win, text="✨ Python to EXE Converter ✨", font=(FONT_FAMILY, 14, "bold"), bg=CARD_BG, fg=PRIMARY).pack(pady=(15, 0))
        tk.Label(about_win, text="Version 2.1.1", font=(FONT_FAMILY, 10, "bold"), bg=CARD_BG, fg=ACCENT).pack(pady=(0, 10))
        
        text = tk.Text(about_win, wrap="word", font=FONT_NORMAL, bg=CARD_BG, fg=TEXT_COLOR, relief="flat", height=3)
        text.insert("1.0", "A portable tool designed to convert Python scripts to standalone EXE files in restricted environments.")
        text.tag_configure("ltr", justify="left")
        text.tag_add("ltr", "1.0", "end")
        text.config(state="disabled")
        text.pack(padx=20, fill="x", pady=(0, 10))

        tk.Label(about_win, text="🧑‍💻 Designed & Developed by:", font=FONT_BOLD, bg=CARD_BG, fg=ACCENT).pack()
        tk.Label(about_win, text="Mohammad Azadfar", font=(FONT_FAMILY, 12, "bold"), bg=CARD_BG, fg=PRIMARY).pack()
        
        contact_frame = tk.Frame(about_win, bg=CARD_BG)
        contact_frame.pack(pady=(5, 10))
        
        lbl_email = tk.Label(contact_frame, text="📧 azadfar2009@gmail.com", font=FONT_NORMAL, bg=CARD_BG, fg=ACCENT, cursor="hand2")
        lbl_email.pack(side="left", padx=10)
        lbl_email.bind("<Button-1>", lambda e: webbrowser.open("mailto:azadfar2009@gmail.com"))
        
        lbl_phone = tk.Label(contact_frame, text="📞 09124198455", font=FONT_NORMAL, bg=CARD_BG, fg=ACCENT, cursor="hand2")
        lbl_phone.pack(side="left", padx=10)
        lbl_phone.bind("<Button-1>", lambda e: [self.root.clipboard_clear(), self.root.clipboard_append("09124198455"), messagebox.showinfo("Copied", "Phone number copied!")])

        tk.Label(about_win, text="📝 Changelog:", font=FONT_BOLD, bg=CARD_BG, fg=PRIMARY).pack(anchor="w", padx=20)
        
        changelog_text = scrolledtext.ScrolledText(about_win, wrap="word", font=(FONT_FAMILY, 9), bg="#f8f9fa", fg="#333", relief="solid", bd=1, height=7)
        changelog = """v2.1.1 (Current)
- Added Enter key support in search box.
- Config window close prompt now only shows when busy.
- Optimized PyPI connection using gzip compression (10x faster).

v2.1.0
- Added real-time download progress in console.
- Added local version check before installing packages.
- Added Changelog section.

v2.0.0
- Added Config window (Package Manager).
- Added Multi-select for package updates.
- Improved UI layout and threading safety."""
        changelog_text.insert("1.0", changelog)
        changelog_text.config(state="disabled")
        changelog_text.pack(padx=20, fill="both", expand=True, pady=(5, 10))

        tk.Button(about_win, text="Close", font=FONT_BOLD, bg="#bdc3c7", fg="white", relief="flat", activebackground="#95a5a6", activeforeground="white", command=about_win.destroy, padx=20).pack(pady=(0, 15))

    def _set_detail(self, text):
        self.detail_text.config(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", text)
        self.detail_text.config(state="disabled")
        self._update_details_scrollbar()

    def _log(self, msg):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def _refresh_file_list(self):
        for widget in self.files_inner.winfo_children():
            widget.destroy()
        self.file_infos.clear()
        self.check_vars.clear()
        self.active_row_frame = None
        self.active_row_widgets = []
        
        try:
            all_files = os.listdir(self.scan_dir)
            files = [f for f in all_files if f.endswith(".py") and f not in ("converter_gui.py", "get-pip.py")]
            files.sort(key=str.lower)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read directory:\n{e}")
            return
            
        if not files:
            tk.Label(self.files_inner, text="No .py files found in this directory.", font=FONT_NORMAL, bg=CARD_BG).pack(pady=20)
            self._log("⚠️ No files found.")
            return

        for f_name in files:
            p = self.scan_dir / f_name
            dep = check_dependencies(p)
            self.file_infos[f_name] = dep
            
            var = tk.BooleanVar(value=False)
            self.check_vars[f_name] = var
            
            row = tk.Frame(self.files_inner, bg=CARD_BG, pady=5)
            row.pack(fill="x")
            row.columnconfigure(0, weight=80)
            row.columnconfigure(1, weight=15)
            row.columnconfigure(2, weight=5)
            
            lbl_name = tk.Label(row, text=f_name, font=FONT_NORMAL, bg=CARD_BG, fg=TEXT_COLOR, anchor="w")
            lbl_name.grid(row=0, column=0, sticky="w")
            
            status_text, status_fg = ("Syntax Err", DANGER) if dep.get('error') else \
                                     ("Missing Libs", DANGER) if dep['missing'] else \
                                     ("Ready", SUCCESS)
                
            lbl_status = tk.Label(row, text=status_text, font=FONT_BOLD, bg=CARD_BG, fg=status_fg, anchor="center")
            lbl_status.grid(row=0, column=1, sticky="nsew")
            
            chk = tk.Checkbutton(row, variable=var, bg=CARD_BG, activebackground=CARD_BG, cursor="hand2")
            chk.grid(row=0, column=2, sticky="e", padx=5)
            
            row_widgets = [lbl_name, lbl_status, chk]
            for w in [row] + row_widgets:
                w.bind("<Button-1>", lambda e, r=row, ws=row_widgets, n=f_name: self._highlight_row(r, ws, n))
            chk.config(command=lambda r=row, ws=row_widgets, n=f_name: self._highlight_row(r, ws, n))
            
            tk.Frame(self.files_inner, height=1, bg="#ecf0f1").pack(fill="x")
            
        self._log(f"✅ List refreshed. Found {len(files)} file(s).")

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
            
        self.active_row_frame = row_frame
        self.active_row_widgets = widgets
        self._show_details(file_name)

    def _show_details(self, name):
        dep = self.file_infos.get(name)
        if not dep: return
        
        lines = [f"📄 File: {name}\n"]
        if dep.get('error'):
            lines.append(f"⚠️ Code Read Error:\n{dep['error']}\n")
        else:
            if dep['missing']:
                lines.append("❌ Missing Libraries (EXE might crash):")
                lines.append(f"   {', '.join(dep['missing'])}\n")
                lines.append("💡 Solution: Install these libraries using the ⚙️ Config button before converting.\n")
            else:
                lines.append("✅ All required libraries are available. Conversion will succeed.\n")
                
            if dep['available']:
                lines.append(f"✅ Available Libraries:\n   {', '.join(dep['available'])}\n")
            if dep['stdlib']:
                shown = ', '.join(dep['stdlib'][:15])
                more = '...' if len(dep['stdlib'])>15 else ''
                lines.append(f"📦 Standard Python Libraries:\n   {shown}{more}")
                
        self._set_detail("\n".join(lines))

    def _select_all(self):
        for var in self.check_vars.values():
            var.set(True)

    def _start_conversion(self):
        if self.converting or not PYINSTALLER_AVAILABLE: return
        sel = [n for n, v in self.check_vars.items() if v.get()]
        if not sel:
            messagebox.showwarning("No Selection", "Please select at least one file.")
            return
            
        self.converting = True
        self.convert_btn.config(state="disabled", bg="#95a5a6")
        self.progress.start(15)
        self._log(f"🚀 Starting batch conversion for {len(sel)} file(s)...\n")
        threading.Thread(target=self._worker, args=(sel,), daemon=True).start()

    def _worker(self, selected):
        success, failed = [], []
        
        for i, name in enumerate(selected):
            self.root.after(0, lambda n=name: self._log(f"--- Converting: {n} ---"))
            py_path = self.scan_dir / name
            
            temp_dir = tempfile.mkdtemp(prefix="pyinst_")
            work_path = os.path.join(temp_dir, "build")
            spec_path = os.path.join(temp_dir, "spec")
            
            cmd = [
                sys.executable, "-m", "PyInstaller",
                "--onedir", "--noupx", "--clean", "--noconfirm",
                "--distpath", str(self.scan_dir / "dist"),
                "--workpath", work_path,
                "--specpath", spec_path,
                str(py_path)
            ]
            
            try:
                self.active_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', creationflags=0x08000000)
                for line in self.active_process.stdout:
                    clean_line = line.strip()
                    if clean_line:
                        self.root.after(0, lambda l=clean_line: self._log(l))
                
                self.active_process.wait()
                
                exe_path = self.scan_dir / "dist" / py_path.stem / (py_path.stem + ".exe")
                if self.active_process.returncode == 0 and exe_path.exists():
                    success.append(name)
                    self.root.after(0, lambda n=name: self._log(f"✅ SUCCESS: {n} converted successfully.\n"))
                else:
                    failed.append((name, "Process exited with errors"))
                    self.root.after(0, lambda n=name: self._log(f"❌ FAILED: Could not create EXE for {n}.\n"))
            except Exception as e:
                failed.append((name, str(e)))
                self.root.after(0, lambda n=name, err=str(e): self._log(f"❌ ERROR: {err}\n"))
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        self.root.after(0, lambda: self._finish(success, failed, len(selected)))

    def _finish(self, success, failed, total):
        self.converting = False
        self.progress.stop()
        self.progress["value"] = 0
        self.convert_btn.config(state="normal", bg=SUCCESS)
        
        self._log(f"\n🏁 BATCH FINISHED: {len(success)} succeeded, {len(failed)} failed out of {total}.")
        
        if success:
            msg = f"Successfully converted {len(success)} file(s).\n\nOutput location:\n{self.scan_dir / 'dist'}"
            if failed: msg += f"\n\n{len(failed)} file(s) failed (check logs)."
            messagebox.showinfo("Operation Finished", msg)
        else:
            messagebox.showerror("Failed", "No files were converted. Check the logs.")

def main():
    scan_path = sys.argv[1] if len(sys.argv) > 1 else None
    root = tk.Tk()
    if not PYINSTALLER_AVAILABLE:
        messagebox.showerror("Critical Error", "PyInstaller not found in portable environment.")
        return
    ConverterApp(root, scan_path)
    root.mainloop()

if __name__ == "__main__":
    main()