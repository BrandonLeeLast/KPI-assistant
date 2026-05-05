import os
import sys
import time
import configparser
import PIL.Image, PIL.ImageDraw
import pyautogui
import google.generativeai as genai
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import pystray

import updater

# ── Palette (Catppuccin Mocha) ────────────────────────────────────────────────
BG        = "#1e1e2e"
BG2       = "#181825"
SURFACE   = "#313244"
SURFACE2  = "#45475a"
OVERLAY   = "#6c7086"
TEXT      = "#cdd6f4"
SUBTEXT   = "#a6adc8"
LAVENDER  = "#b4befe"
MAUVE     = "#cba6f7"
GREEN     = "#a6e3a1"
RED       = "#f38ba8"
BLUE      = "#89b4fa"
YELLOW    = "#f9e2af"
TEAL      = "#94e2d5"
HEADER_BG = "#11111b"

# ── PATH & CONFIG ─────────────────────────────────────────────────────────────
APP_DIR     = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_PATH = os.path.join(APP_DIR, "config.ini")


def get_default_config():
    cfg = configparser.ConfigParser()
    cfg['DEFAULT'] = {
        'GEMINI_API_KEY': 'YOUR_API_KEY_HERE',
        'MY_LEVEL':       'Intermediate',
        'WATCH_FOLDER':   os.path.join(os.path.expanduser('~'), 'Documents', 'Temp').replace('\\', '/'),
        'BASE_KPI_FOLDER':os.path.join(os.path.expanduser('~'), 'Documents', 'KPI_Evidence').replace('\\', '/'),
        'LOG_FILE':       os.path.join(os.path.expanduser('~'), 'Documents', 'processed_log.txt').replace('\\', '/'),
    }
    return cfg


def load_config():
    cfg = get_default_config()
    if os.path.exists(CONFIG_PATH):
        cfg.read(CONFIG_PATH)
    else:
        with open(CONFIG_PATH, 'w') as f:
            cfg.write(f)
    return cfg


# ── WATCHER ───────────────────────────────────────────────────────────────────
class WatcherDaemon:
    def __init__(self, ui):
        self.ui       = ui
        self.observer = None
        self.running  = False

    def start(self, settings):
        if self.running:
            return
        self.running  = True
        self.observer = Observer()
        self.observer.schedule(GeminiKPIHandler(settings, self.ui),
                               settings.get('WATCH_FOLDER'), recursive=False)
        self.observer.start()
        self.ui.log("📡 File watcher daemon started.", "info")

    def stop(self):
        if not self.running:
            return
        self.observer.stop()
        self.observer.join()
        self.running = False
        self.ui.log("🛑 File watcher daemon stopped.", "warn")


# ── FILE PROCESSING ───────────────────────────────────────────────────────────
def is_already_processed(filename, log_file):
    if not os.path.exists(log_file):
        return False
    with open(log_file, "r") as f:
        return filename in f.read().splitlines()


def mark_as_processed(filename, log_file):
    with open(log_file, "a") as f:
        f.write(filename + "\n")


def process_file_thread_safe(file_path, settings, ui):
    filename = os.path.basename(file_path)
    if not os.path.exists(file_path) or not file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        return

    log_file = settings.get('LOG_FILE')
    if is_already_processed(filename, log_file):
        return

    ui.log(f"🔍 New screenshot detected: {filename}", "info")
    ui.increment_stat("queued")
    time.sleep(1.5)

    user_context = pyautogui.prompt(
        text=f"Enter STAR Context for:\n{filename}\n\n(Situation / Action / Result) — leave blank to skip:",
        title=f"KPI Assistant  ·  {settings.get('MY_LEVEL')} Level"
    )
    if user_context is None:
        user_context = ""

    try:
        instructions = (
            f"You are a Performance Auditor for an '{settings.get('MY_LEVEL')}' developer. "
            "Task: Use the STAR Method (Situation, Task, Action, Result). "
            f"User Context: '{user_context}'. "
            "Analyze the image and pick ONE KPA: Technical Mastery, Engineering Operations, "
            "Consultant Mindset, Communication & Collaboration, or Leadership. "
            "Format: CATEGORY | STAR SUMMARY."
        )

        ui.log("🤖 Calling Gemini Flash for classification…", "info")
        genai.configure(api_key=settings.get('GEMINI_API_KEY'))
        model = genai.GenerativeModel('gemini-3-flash-preview')

        img      = PIL.Image.open(file_path)
        response = model.generate_content([instructions, img])
        res      = response.text
        img.close()

        category_part, summary = (res.split("|") + ["No summary"])[:2]
        category = (category_part.strip()
                    .replace("*", "").replace(":", "")
                    .replace("/", "").replace("\\", ""))

        target   = os.path.join(settings.get('BASE_KPI_FOLDER'), category)
        os.makedirs(target, exist_ok=True)
        new_path = os.path.join(target, filename)
        shutil.copy2(file_path, new_path)

        if category.lower() not in ["junk", "nocontext"]:
            with open(f"{new_path}.txt", "w", encoding="utf-8") as f:
                f.write(f"USER CONTEXT: {user_context}\nGEMINI SUMMARY: {summary.strip()}")
            ui.log(f"✅ Filed → {category}", "success")
            ui.increment_stat("filed")
        else:
            ui.log(f"⚠️  Low-context item held in: {category}", "warn")

        mark_as_processed(filename, log_file)

    except Exception as e:
        ui.log(f"❌ Analysis error: {e}", "error")
        ui.increment_stat("errors")


class GeminiKPIHandler(FileSystemEventHandler):
    def __init__(self, settings, ui):
        self.settings = settings
        self.ui       = ui

    def on_created(self, event):
        if not event.is_directory:
            t = threading.Thread(target=process_file_thread_safe,
                                 args=(event.src_path, self.settings, self.ui),
                                 daemon=True)
            t.start()


# ── CUSTOM WIDGETS ────────────────────────────────────────────────────────────
class StatCard(tk.Frame):
    """A small rounded metric tile."""
    def __init__(self, parent, label, accent, **kw):
        super().__init__(parent, bg=SURFACE, **kw)
        self._value = tk.StringVar(value="0")
        tk.Label(self, text=label, bg=SURFACE, fg=SUBTEXT,
                 font=("Segoe UI", 8)).pack(pady=(10, 0))
        tk.Label(self, textvariable=self._value, bg=SURFACE, fg=accent,
                 font=("Segoe UI", 26, "bold")).pack()
        tk.Label(self, text="▬", bg=SURFACE, fg=accent,
                 font=("Segoe UI", 6)).pack(pady=(0, 8))

    def set(self, value: int):
        self._value.set(str(value))

    def increment(self):
        self._value.set(str(int(self._value.get()) + 1))


class PulseIndicator(tk.Canvas):
    """Animated pulsing circle for daemon status."""
    def __init__(self, parent, **kw):
        super().__init__(parent, width=14, height=14,
                         bg=HEADER_BG, highlightthickness=0, **kw)
        self._active = False
        self._phase  = 0
        self._dot    = self.create_oval(2, 2, 12, 12, fill=SURFACE2, outline="")
        self._animate()

    def set_active(self, active: bool):
        self._active = active

    def _animate(self):
        if self._active:
            self._phase = (self._phase + 1) % 20
            alpha = abs(self._phase - 10) / 10          # 0..1..0
            r, g, b = 166, 227, 161                      # GREEN rgb
            color = f"#{int(r*alpha+(69*(1-alpha))):02x}" \
                    f"{int(g*alpha+(71*(1-alpha))):02x}" \
                    f"{int(b*alpha+(90*(1-alpha))):02x}"
            self.itemconfig(self._dot, fill=color)
        else:
            self.itemconfig(self._dot, fill=SURFACE2)
        self.after(80, self._animate)


# ── MAIN APP ──────────────────────────────────────────────────────────────────
class KPIDashboardApp(tk.Tk):

    # stat keys → (StatCard widget ref, current count)
    _STATS = {"queued": 0, "filed": 0, "errors": 0}

    def __init__(self):
        super().__init__()
        self.title("KPI Evidence Assistant")
        self.geometry("820x600")
        self.minsize(760, 520)
        self.configure(bg=BG)

        self.config_data = load_config()
        self.watcher     = WatcherDaemon(self)
        self.tray_icon   = None
        self._stats      = {"queued": 0, "filed": 0, "errors": 0}

        self.protocol('WM_DELETE_WINDOW', self.minimize_to_tray)

        # Tk vars
        self.api_key_var       = tk.StringVar(value=self.config_data['DEFAULT']['GEMINI_API_KEY'])
        self.level_var         = tk.StringVar(value=self.config_data['DEFAULT']['MY_LEVEL'])
        self.watch_folder_var  = tk.StringVar(value=self.config_data['DEFAULT']['WATCH_FOLDER'])
        self.evidence_folder_var = tk.StringVar(value=self.config_data['DEFAULT']['BASE_KPI_FOLDER'])

        self._setup_styles()
        self._build_shell()
        self.setup_system_tray()
        self.start_service()
        updater.check_for_update(self._on_update_available)

    # ── STYLES ────────────────────────────────────────────────────────────────
    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use('clam')

        s.configure("TNotebook",      background=BG,      borderwidth=0)
        s.configure("TNotebook.Tab",  background=SURFACE,  foreground=SUBTEXT,
                    padding=[18, 6],  font=("Segoe UI", 9))
        s.map("TNotebook.Tab",
              background=[("selected", BG2)],
              foreground=[("selected", MAUVE)])

        s.configure("Vertical.TScrollbar",
                    background=SURFACE, troughcolor=BG2,
                    arrowcolor=SUBTEXT, borderwidth=0)

    # ── SHELL ─────────────────────────────────────────────────────────────────
    def _build_shell(self):
        self._build_topbar()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=0, pady=0)

        self.tab_dash    = tk.Frame(self.notebook, bg=BG)
        self.tab_config  = tk.Frame(self.notebook, bg=BG)

        self.notebook.add(self.tab_dash,   text="  Dashboard  ")
        self.notebook.add(self.tab_config, text="  Configuration  ")

        self._build_dashboard()
        self._build_config_tab()

    # ── TOPBAR ────────────────────────────────────────────────────────────────
    def _build_topbar(self):
        bar = tk.Frame(self, bg=HEADER_BG, height=56)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        # Left: icon + title
        tk.Label(bar, text="⬡", bg=HEADER_BG, fg=MAUVE,
                 font=("Segoe UI", 22)).pack(side="left", padx=(18, 6), pady=10)
        tk.Label(bar, text="KPI Assistant", bg=HEADER_BG, fg=TEXT,
                 font=("Segoe UI", 14, "bold")).pack(side="left")
        tk.Label(bar, text=f"v{updater.LOCAL_VERSION}", bg=HEADER_BG, fg=OVERLAY,
                 font=("Segoe UI", 9)).pack(side="left", padx=(6, 0), pady=(2, 0))

        # Right: pulse + badge
        right = tk.Frame(bar, bg=HEADER_BG)
        right.pack(side="right", padx=18)

        self._pulse = PulseIndicator(right)
        self._pulse.pack(side="left", padx=(0, 8))

        self.lbl_badge = tk.Label(right, text="STOPPED",
                                  bg=RED, fg=HEADER_BG,
                                  font=("Segoe UI", 8, "bold"),
                                  padx=10, pady=3)
        self.lbl_badge.pack(side="left")

    # ── DASHBOARD TAB ─────────────────────────────────────────────────────────
    def _build_dashboard(self):
        # ── stat cards row
        cards_row = tk.Frame(self.tab_dash, bg=BG)
        cards_row.pack(fill="x", padx=20, pady=(16, 8))

        self._card_queued = StatCard(cards_row, "QUEUED", YELLOW)
        self._card_filed  = StatCard(cards_row, "FILED",  GREEN)
        self._card_errors = StatCard(cards_row, "ERRORS", RED)

        for card in (self._card_queued, self._card_filed, self._card_errors):
            card.pack(side="left", expand=True, fill="x", padx=6, ipady=2)

        # ── action buttons
        btn_row = tk.Frame(self.tab_dash, bg=BG)
        btn_row.pack(fill="x", padx=20, pady=(4, 10))

        self.btn_toggle = self._btn(btn_row, "⏹  Stop Daemon",  RED,    self.toggle_service)
        self.btn_toggle.pack(side="left", padx=(0, 8))

        self._btn(btn_row, "🔍  Scan Backlog", BLUE, self.run_manual_backlog_scan).pack(side="left", padx=(0, 8))
        self._btn(btn_row, "↑  Open Evidence Folder", TEAL,
                  self._open_evidence_folder).pack(side="left")

        self.btn_update = self._btn(btn_row, "☁  Check Updates", SURFACE2,
                                    self._manual_update_check)
        self.btn_update.pack(side="right")

        # ── log console
        log_outer = tk.Frame(self.tab_dash, bg=BG2, highlightbackground=SURFACE,
                             highlightthickness=1)
        log_outer.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        log_hdr = tk.Frame(log_outer, bg=BG2)
        log_hdr.pack(fill="x", padx=10, pady=(8, 0))
        tk.Label(log_hdr, text="SYSTEM LOG", bg=BG2, fg=OVERLAY,
                 font=("Segoe UI", 8, "bold")).pack(side="left")

        btn_clear = tk.Label(log_hdr, text="clear", bg=BG2, fg=SURFACE2,
                             font=("Segoe UI", 8), cursor="hand2")
        btn_clear.pack(side="right")
        btn_clear.bind("<Button-1>", lambda _: self._clear_log())

        frame_scroll = tk.Frame(log_outer, bg=BG2)
        frame_scroll.pack(fill="both", expand=True, padx=6, pady=6)

        scrollbar = ttk.Scrollbar(frame_scroll, style="Vertical.TScrollbar")
        scrollbar.pack(side="right", fill="y")

        self.log_text = tk.Text(
            frame_scroll,
            bg=BG2, fg=SUBTEXT,
            insertbackground=TEXT,
            font=("Cascadia Code", 9) if self._font_exists("Cascadia Code") else ("Consolas", 9),
            state="disabled",
            wrap="word",
            relief="flat",
            yscrollcommand=scrollbar.set,
            padx=8, pady=4,
        )
        self.log_text.pack(fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

        # colour tags for log levels
        self.log_text.tag_config("ts",      foreground=OVERLAY)
        self.log_text.tag_config("info",    foreground=SUBTEXT)
        self.log_text.tag_config("success", foreground=GREEN)
        self.log_text.tag_config("warn",    foreground=YELLOW)
        self.log_text.tag_config("error",   foreground=RED)

    @staticmethod
    def _font_exists(name):
        import tkinter.font as tkfont
        return name in tkfont.families()

    def _btn(self, parent, text, color, command):
        return tk.Button(parent, text=text, bg=color,
                         fg=HEADER_BG if color not in (SURFACE2, OVERLAY) else TEXT,
                         font=("Segoe UI", 9, "bold"),
                         padx=12, pady=5, bd=0, relief="flat",
                         activebackground=color, activeforeground=HEADER_BG,
                         cursor="hand2", command=command)

    # ── CONFIG TAB ────────────────────────────────────────────────────────────
    def _build_config_tab(self):
        outer = tk.Frame(self.tab_config, bg=BG)
        outer.pack(fill="both", expand=True, padx=30, pady=20)

        def section(label):
            tk.Label(outer, text=label, bg=BG, fg=MAUVE,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(16, 2))

        def field(var, show=None):
            e = tk.Entry(outer, textvariable=var, bg=SURFACE, fg=TEXT,
                         insertbackground=TEXT, bd=0, relief="flat",
                         font=("Segoe UI", 10),
                         highlightthickness=1, highlightbackground=SURFACE2,
                         highlightcolor=LAVENDER)
            if show:
                e.config(show=show)
            e.pack(fill="x", ipady=6, pady=(0, 2))
            return e

        def folder_row(var):
            row = tk.Frame(outer, bg=BG)
            row.pack(fill="x", pady=(0, 2))
            tk.Entry(row, textvariable=var, bg=SURFACE, fg=TEXT,
                     insertbackground=TEXT, bd=0, relief="flat",
                     font=("Segoe UI", 10),
                     highlightthickness=1, highlightbackground=SURFACE2,
                     highlightcolor=LAVENDER).pack(side="left", fill="x",
                                                   expand=True, ipady=6)
            tk.Button(row, text="Browse", bg=SURFACE2, fg=TEXT,
                      bd=0, relief="flat", padx=10,
                      font=("Segoe UI", 9), cursor="hand2",
                      command=lambda: self._browse(var)).pack(side="right", padx=(6, 0), ipady=6)

        section("GEMINI API KEY")
        field(self.api_key_var, show="•")

        section("DEVELOPER LEVEL")
        level_frame = tk.Frame(outer, bg=BG)
        level_frame.pack(anchor="w", pady=(0, 2))
        for lvl in ("Junior", "Intermediate", "Senior", "Lead"):
            rb = tk.Radiobutton(level_frame, text=lvl,
                                variable=self.level_var, value=lvl,
                                bg=BG, fg=TEXT, selectcolor=SURFACE,
                                activebackground=BG, activeforeground=MAUVE,
                                font=("Segoe UI", 10))
            rb.pack(side="left", padx=(0, 16))

        section("SHAREX WATCH FOLDER")
        folder_row(self.watch_folder_var)

        section("KPI EVIDENCE FOLDER")
        folder_row(self.evidence_folder_var)

        # divider
        tk.Frame(outer, bg=SURFACE, height=1).pack(fill="x", pady=20)

        save_btn = tk.Button(outer, text="Save Configuration",
                             bg=GREEN, fg=HEADER_BG,
                             font=("Segoe UI", 11, "bold"),
                             bd=0, relief="flat", pady=10, cursor="hand2",
                             command=self.save_settings)
        save_btn.pack(fill="x")

    # ── LOG ───────────────────────────────────────────────────────────────────
    def log(self, text: str, level: str = "info"):
        def _append():
            self.log_text.config(state="normal")
            ts = time.strftime('%H:%M:%S')
            self.log_text.insert(tk.END, f"[{ts}] ", "ts")
            self.log_text.insert(tk.END, f"{text}\n", level)
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
        self.after(0, _append)

    # keep backward-compat alias used by watcher threads
    def log_message(self, text: str):
        level = ("success" if "✅" in text
                 else "error" if "❌" in text
                 else "warn"  if "⚠️" in text
                 else "info")
        self.log(text, level)

    def _clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")

    # ── STATS ─────────────────────────────────────────────────────────────────
    def increment_stat(self, key: str):
        self._stats[key] = self._stats.get(key, 0) + 1
        card = {"queued": self._card_queued,
                "filed":  self._card_filed,
                "errors": self._card_errors}.get(key)
        if card:
            self.after(0, lambda: card.set(self._stats[key]))

    # ── HELPERS ───────────────────────────────────────────────────────────────
    def _browse(self, var):
        path = filedialog.askdirectory()
        if path:
            var.set(path.replace('\\', '/'))

    def _open_evidence_folder(self):
        path = self.evidence_folder_var.get()
        if os.path.exists(path):
            os.startfile(path)
        else:
            messagebox.showwarning("Not Found", f"Folder does not exist:\n{path}")

    # ── TRAY ──────────────────────────────────────────────────────────────────
    def generate_icon_image(self):
        img  = PIL.Image.new('RGB', (64, 64), '#11111b')
        draw = PIL.ImageDraw.Draw(img)
        draw.ellipse([8, 8, 56, 56],  outline="#cba6f7", width=4)
        draw.ellipse([20, 20, 44, 44], fill="#cba6f7")
        return img

    def setup_system_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem("Show Controller", self.restore_from_tray, default=True),
            pystray.MenuItem("Toggle Daemon",   lambda *_: self.toggle_service()),
            pystray.MenuItem("Exit",            self.exit_completely),
        )
        self.tray_icon = pystray.Icon(
            "kpi_assistant", self.generate_icon_image(),
            "KPI Evidence Assistant", menu)
        self.tray_icon.run_detached()

    def minimize_to_tray(self):
        self.withdraw()
        if self.tray_icon:
            self.tray_icon.notify("Running in background.", "KPI Assistant")

    def restore_from_tray(self, *_):
        self.after(0, self.deiconify)

    def exit_completely(self, *_):
        self.stop_service()
        if self.tray_icon:
            self.tray_icon.stop()
        self.destroy()
        sys.exit(0)

    # ── SERVICE CONTROL ───────────────────────────────────────────────────────
    def toggle_service(self):
        if self.watcher.running:
            self.stop_service()
        else:
            self.start_service()

    def start_service(self):
        key = self.api_key_var.get().strip()
        if not key or key == "YOUR_API_KEY_HERE":
            self.log("⚠️  Enter your Gemini API key in Configuration first.", "warn")
            self.notebook.select(self.tab_config)
            return
        self.watcher.start(self.config_data['DEFAULT'])
        self.lbl_badge.config(text="RUNNING", bg=GREEN, fg=HEADER_BG)
        self.btn_toggle.config(text="⏹  Stop Daemon", bg=RED)
        self._pulse.set_active(True)

    def stop_service(self):
        self.watcher.stop()
        self.lbl_badge.config(text="STOPPED", bg=RED, fg=HEADER_BG)
        self.btn_toggle.config(text="▶  Start Daemon", bg=GREEN)
        self._pulse.set_active(False)

    def run_manual_backlog_scan(self):
        threading.Thread(target=self._backlog_scan_logic, daemon=True).start()

    def _backlog_scan_logic(self):
        self.log("🔄 Scanning backlog for unprocessed screenshots…", "info")
        settings   = self.config_data['DEFAULT']
        watch_path = settings.get('WATCH_FOLDER')

        if not os.path.exists(watch_path):
            self.log("❌ Watch folder not found.", "error")
            return

        count = 0
        for item in os.listdir(watch_path):
            full = os.path.join(watch_path, item)
            if os.path.isfile(full) and item.lower().endswith(('.png', '.jpg', '.jpeg')):
                if not is_already_processed(item, settings.get('LOG_FILE')):
                    process_file_thread_safe(full, settings, self)
                    count += 1

        self.log(f"✅ Backlog scan complete — {count} item(s) filed.", "success")

    def save_settings(self):
        self.config_data['DEFAULT']['GEMINI_API_KEY']  = self.api_key_var.get()
        self.config_data['DEFAULT']['MY_LEVEL']        = self.level_var.get()
        self.config_data['DEFAULT']['WATCH_FOLDER']    = self.watch_folder_var.get()
        self.config_data['DEFAULT']['BASE_KPI_FOLDER'] = self.evidence_folder_var.get()
        self.config_data['DEFAULT']['LOG_FILE']        = os.path.join(
            self.evidence_folder_var.get(), "../processed_log.txt").replace('\\', '/')

        with open(CONFIG_PATH, 'w') as f:
            self.config_data.write(f)

        self.log("💾 Configuration saved.", "success")
        if self.watcher.running:
            self.stop_service()
        self.start_service()

    # ── AUTO-UPDATER ──────────────────────────────────────────────────────────
    def _on_update_available(self, remote_info: dict):
        def _prompt():
            new_ver = remote_info.get("version", "?")
            notes   = remote_info.get("release_notes", "")
            self.log(f"🔔 Update available: v{new_ver}", "warn")
            if messagebox.askyesno(
                "Update Available",
                f"KPI Assistant v{new_ver} is ready (you have v{updater.LOCAL_VERSION}).\n\n"
                f"{notes}\n\nInstall now? (App will restart automatically.)"
            ):
                dl_url = remote_info.get("download_url", "")
                if not dl_url:
                    messagebox.showerror("Update Error", "No download URL in version manifest.")
                    return
                threading.Thread(target=updater.perform_update,
                                 args=(dl_url, self.log_message),
                                 daemon=True).start()
        self.after(0, _prompt)

    def _manual_update_check(self):
        self.log("☁  Checking for updates…", "info")
        self.btn_update.config(state="disabled")

        def _check():
            from packaging.version import Version
            remote = updater._fetch_remote_version_info()
            if remote is None:
                self.after(0, lambda: self.log("⚠️  Could not reach update server.", "warn"))
            elif Version(remote["version"]) > Version(updater.LOCAL_VERSION):
                self._on_update_available(remote)
            else:
                self.after(0, lambda: self.log("✅ You're on the latest version.", "success"))
            self.after(0, lambda: self.btn_update.config(state="normal"))

        threading.Thread(target=_check, daemon=True).start()


if __name__ == "__main__":
    app = KPIDashboardApp()
    app.mainloop()
