import os
import sys
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

import updater
from app.config import load_config, save_config, APPDATA_DIR
from app.constants import (BG, BG2, SURFACE, SURFACE2, OVERLAY,
                            TEXT, SUBTEXT, MAUVE, GREEN, RED, HEADER_BG)
from app.processor import process_file, is_already_processed
from app.watcher import WatcherDaemon
from app.tray import create_tray_icon
from app.screenshot import HotkeyListener
from app.ui.capture_overlay import launch_overlay
from app.ui.widgets import PulseIndicator
from app.ui import dashboard as dashboard_builder
from app.ui import config_tab as config_tab_builder
from app.ollama_setup import setup_ollama, get_status

# Lock CustomTkinter to dark mode — app has its own palette
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class KPIDashboardApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("KPEye")
        self.geometry("880x640")
        self.minsize(780, 560)
        self.configure(fg_color=BG)

        self.config_data    = load_config()
        self.watcher        = WatcherDaemon(self)
        self.tray_icon      = None
        self._stats         = {"queued": 0, "filed": 0, "errors": 0}
        self._hotkey        = HotkeyListener()

        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

        d = self.config_data['DEFAULT']

        # ── AI provider ───────────────────────────────────────────────────────
        self.provider_var  = tk.StringVar(value=d.get('AI_PROVIDER', 'Gemini'))
        # Per-provider key storage — each provider keeps its own value
        self._provider_keys = {
            'Gemini':     d.get('API_KEY_GEMINI',     '') or d.get('API_KEY', '') or d.get('GEMINI_API_KEY', ''),
            'Claude':     d.get('API_KEY_CLAUDE',     ''),
            'OpenAI':     d.get('API_KEY_OPENAI',     ''),
            'Ollama':     d.get('API_KEY_OLLAMA',     ''),
            'Cloudflare': d.get('API_KEY_CLOUDFLARE', ''),
            'Custom URL': d.get('API_KEY_CUSTOM',     ''),
        }
        _cur = self.provider_var.get()
        self.api_key_var   = tk.StringVar(value=self._provider_keys.get(_cur, ''))
        self._prev_provider = _cur
        self.provider_var.trace_add("write", self._on_provider_key_swap)
        self.model_var     = tk.StringVar(value=d.get('AI_MODEL', 'gemini-2.0-flash'))

        # ── Developer level ───────────────────────────────────────────────────
        self.level_var     = tk.StringVar(value=d.get('MY_LEVEL',      'Intermediate'))

        # ── Folders ───────────────────────────────────────────────────────────
        self.watch_folder_var    = tk.StringVar(value=d.get('WATCH_FOLDER',    ''))
        self.evidence_folder_var = tk.StringVar(value=d.get('BASE_KPI_FOLDER', ''))

        # ── Capture ───────────────────────────────────────────────────────────
        self.hotkey_var          = tk.StringVar(value=d.get('HOTKEY',          'ctrl+shift+s'))
        self.capture_format_var  = tk.StringVar(value=d.get('CAPTURE_FORMAT',  'PNG'))

        # ── Processing ────────────────────────────────────────────────────────
        self.auto_process_var    = tk.BooleanVar(value=d.get('AUTO_PROCESS',    'true')  == 'true')
        self.show_context_var    = tk.BooleanVar(value=d.get('SHOW_CONTEXT',    'true')  == 'true')
        self.kpa_categories_var  = tk.StringVar(value=d.get('KPA_CATEGORIES', ''))
        self.context_prompt_var  = tk.StringVar(value=d.get('CONTEXT_PROMPT',  ''))

        # ── Notifications ─────────────────────────────────────────────────────
        self.notify_success_var  = tk.BooleanVar(value=d.get('NOTIFY_ON_SUCCESS', 'false') == 'true')
        self.notify_failure_var  = tk.BooleanVar(value=d.get('NOTIFY_ON_FAILURE', 'true')  == 'true')

        self._build_topbar()
        self._build_tabs()
        self._setup_tray()
        self.start_service()
        self.apply_hotkey()
        updater.check_for_update(self._on_update_available)

    # ── TOPBAR ────────────────────────────────────────────────────────────────
    def _build_topbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color=HEADER_BG, corner_radius=0, height=60)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        left = ctk.CTkFrame(bar, fg_color="transparent")
        left.pack(side="left", padx=20, pady=10)

        _base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        try:
            from PIL import Image
            import customtkinter as _ctk
            _logo_img = _ctk.CTkImage(Image.open(os.path.join(_base, "static", "KPEye.png")), size=(40, 40))
            ctk.CTkLabel(left, image=_logo_img, text="").pack(side="left", padx=(0, 8))
        except Exception:
            ctk.CTkLabel(left, text="👁", text_color=MAUVE,
                         font=ctk.CTkFont("Segoe UI", 26)).pack(side="left", padx=(0, 8))
        try:
            self.iconbitmap(os.path.join(_base, "app_icon.ico"))
        except Exception:
            pass

        title_block = ctk.CTkFrame(left, fg_color="transparent")
        title_block.pack(side="left")
        ctk.CTkLabel(title_block, text="KPEye", text_color=TEXT,
                     font=ctk.CTkFont("Segoe UI", 16, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(title_block, text="Portfolio Evidence Collector", text_color=OVERLAY,
                     font=ctk.CTkFont("Segoe UI", 9)).pack(anchor="w")

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right", padx=20)

        # version chip
        ctk.CTkLabel(right, text=f"v{updater.LOCAL_VERSION}",
                     fg_color=SURFACE, text_color=OVERLAY,
                     corner_radius=6, font=ctk.CTkFont("Segoe UI", 9),
                     padx=8, pady=2).pack(side="left", padx=(0, 10))

        # pulse dot (raw canvas — still tkinter)
        self._pulse = PulseIndicator(right)
        self._pulse.pack(side="left", padx=(0, 8))

        # status badge
        self.lbl_badge = ctk.CTkLabel(
            right, text="  STOPPED  ",
            fg_color=RED, text_color=HEADER_BG, corner_radius=6,
            font=ctk.CTkFont("Segoe UI", 10, weight="bold"),
        )
        self.lbl_badge.pack(side="left")

    # ── TABS ──────────────────────────────────────────────────────────────────
    def _build_tabs(self) -> None:
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=BG,
            segmented_button_fg_color=HEADER_BG,
            segmented_button_selected_color=SURFACE,
            segmented_button_selected_hover_color=SURFACE2,
            segmented_button_unselected_color=HEADER_BG,
            segmented_button_unselected_hover_color=SURFACE,
            text_color=SUBTEXT,
            text_color_disabled=OVERLAY,
        )
        self.tabview.pack(fill="both", expand=True, padx=0, pady=0)
        self.tabview.add("  Dashboard  ")
        self.tabview.add("  Configuration  ")

        dash_refs = dashboard_builder.build(
            self.tabview.tab("  Dashboard  "), self
        )
        self.btn_toggle   = dash_refs["btn_toggle"]
        self.btn_update   = dash_refs["btn_update"]
        self._card_queued = dash_refs["card_queued"]
        self._card_filed  = dash_refs["card_filed"]
        self._card_errors = dash_refs["card_errors"]
        self.log_text     = dash_refs["log_text"]

        config_tab_builder.build(
            self.tabview.tab("  Configuration  "), self
        )

    # ── TRAY ──────────────────────────────────────────────────────────────────
    def _setup_tray(self) -> None:
        self.tray_icon = create_tray_icon(
            on_show=self.restore_from_tray,
            on_toggle=self.toggle_service,
            on_exit=self.exit_completely,
        )
        self.tray_icon.run_detached()

    def minimize_to_tray(self) -> None:
        self.withdraw()
        self.tray_icon.notify("Running in background.", "KPEye")

    def restore_from_tray(self, *_) -> None:
        self.after(0, self.deiconify)

    def exit_completely(self, *_) -> None:
        self._hotkey.stop()
        self.stop_service()
        self.tray_icon.stop()
        self.destroy()
        sys.exit(0)

    # ── LOGGING ───────────────────────────────────────────────────────────────
    def log(self, text: str, level: str = "info") -> None:
        def _append():
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] ", "ts")
            self.log_text.insert(tk.END, f"{text}\n", level)
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
        self.after(0, _append)

    def notify(self, message: str, title: str = "KPEye") -> None:
        """Non-intrusive tray balloon notification — fires from any thread."""
        if self.tray_icon:
            try:
                self.tray_icon.notify(message, title)
            except Exception:
                pass

    def log_message(self, text: str) -> None:
        level = ("success" if "✅" in text
                 else "error" if "❌" in text
                 else "warn"  if "⚠️" in text
                 else "info")
        self.log(text, level)

    # ── STATS ─────────────────────────────────────────────────────────────────
    def increment_stat(self, key: str) -> None:
        self._stats[key] = self._stats.get(key, 0) + 1
        card = {"queued": self._card_queued,
                "filed":  self._card_filed,
                "errors": self._card_errors}.get(key)
        if card:
            self.after(0, lambda: card.set(self._stats[key]))

    # ── SERVICE CONTROL ───────────────────────────────────────────────────────
    def toggle_service(self) -> None:
        if self.watcher.running:
            self.stop_service()
        else:
            self.start_service()

    def start_service(self) -> None:
        key = self.api_key_var.get().strip()
        if not key or key == "YOUR_API_KEY_HERE":
            self.log("⚠️  Enter your AI URL or API key in Configuration first.", "warn")
            self.tabview.set("  Configuration  ")
            return
        watch_folder = self.config_data['DEFAULT'].get('WATCH_FOLDER', '')
        if not watch_folder or not os.path.exists(watch_folder):
            self.log("⚠️  Watch folder not found — set it in Configuration.", "warn")
            self.tabview.set("  Configuration  ")
            return
        self.watcher.start(self.config_data['DEFAULT'])
        self.lbl_badge.configure(text="  RUNNING  ", fg_color=GREEN, text_color=HEADER_BG)
        self.btn_toggle.configure(text="⏹  Stop Daemon", fg_color=RED, hover_color="#e0728a")
        self._pulse.set_active(True)

    def stop_service(self) -> None:
        self.watcher.stop()
        self.lbl_badge.configure(text="  STOPPED  ", fg_color=RED, text_color=HEADER_BG)
        self.btn_toggle.configure(text="▶  Start Daemon", fg_color=GREEN, hover_color="#8ecf8a")
        self._pulse.set_active(False)

    # ── BACKLOG SCAN ──────────────────────────────────────────────────────────
    def run_manual_backlog_scan(self) -> None:
        threading.Thread(target=self._backlog_scan_logic, daemon=True).start()

    def _backlog_scan_logic(self) -> None:
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
                    process_file(full, settings, self)
                    count += 1

        self.log(f"✅ Backlog scan complete — {count} item(s) filed.", "success")

    # ── CONFIG ACTIONS ────────────────────────────────────────────────────────
    def browse_folder(self, var: tk.StringVar) -> None:
        path = filedialog.askdirectory()
        if path:
            var.set(path.replace('\\', '/'))

    # ── OLLAMA SETUP ──────────────────────────────────────────────────────────
    def run_ollama_setup(self, model, on_log, on_done, on_error,
                         btn, lbl_docker, lbl_container, lbl_api) -> None:
        btn.configure(state="disabled", text="⏳  Setting up…")
        self.log(f"🐳 Starting Ollama setup for model: {model}", "info")

        def _done():
            self.after(0, on_done)
            self.after(0, lambda: self.log("🎉 Ollama setup complete!", "success"))

        def _error(msg):
            self.after(0, lambda: on_error(msg))
            self.after(0, lambda: self.log(f"❌ Ollama setup failed: {msg}", "error"))

        def _log(msg, level="info"):
            self.after(0, lambda: on_log(msg, level))

        setup_ollama(model, _log, _done, _error)

    def refresh_ollama_status(self, lbl_docker, lbl_container, lbl_api) -> None:
        def _check():
            status = get_status()
            def _update():
                lbl_docker.configure(
                    text="⬤ Docker",
                    text_color="#a6e3a1" if status["docker"] else "#f38ba8"
                )
                lbl_container.configure(
                    text="⬤ Container",
                    text_color="#a6e3a1" if status["container"] else "#f38ba8"
                )
                lbl_api.configure(
                    text="⬤ API",
                    text_color="#a6e3a1" if status["api"] else "#f38ba8"
                )
            self.after(0, _update)
        threading.Thread(target=_check, daemon=True).start()

    def _on_provider_key_swap(self, *_) -> None:
        new_provider = self.provider_var.get()
        if new_provider == self._prev_provider:
            return
        self._provider_keys[self._prev_provider] = self.api_key_var.get()
        self.api_key_var.set(self._provider_keys.get(new_provider, ''))
        self._prev_provider = new_provider

    def open_evidence_folder(self) -> None:
        path = self.evidence_folder_var.get()
        if os.path.exists(path):
            os.startfile(path)
        else:
            messagebox.showwarning("Not Found", f"Folder does not exist:\n{path}")

    def save_settings(self) -> None:
        d = self.config_data['DEFAULT']
        # AI provider
        d['AI_PROVIDER']       = self.provider_var.get()
        d['AI_MODEL']          = self.model_var.get()
        # Save current key into per-provider store before persisting
        self._provider_keys[self.provider_var.get()] = self.api_key_var.get()
        d['API_KEY']           = self.api_key_var.get()
        d['GEMINI_API_KEY']    = self._provider_keys.get('Gemini', '')  # legacy compat
        d['API_KEY_GEMINI']    = self._provider_keys.get('Gemini',     '')
        d['API_KEY_CLAUDE']    = self._provider_keys.get('Claude',     '')
        d['API_KEY_OPENAI']    = self._provider_keys.get('OpenAI',     '')
        d['API_KEY_OLLAMA']    = self._provider_keys.get('Ollama',     '')
        d['API_KEY_CLOUDFLARE']= self._provider_keys.get('Cloudflare', '')
        d['API_KEY_CUSTOM']    = self._provider_keys.get('Custom URL', '')
        # Level
        d['MY_LEVEL']          = self.level_var.get()
        # Folders
        d['WATCH_FOLDER']      = self.watch_folder_var.get()
        d['BASE_KPI_FOLDER']   = self.evidence_folder_var.get()
        d['LOG_FILE']          = os.path.join(APPDATA_DIR, 'processed_log.json').replace('\\', '/')
        # Capture
        d['HOTKEY']            = self.hotkey_var.get()
        d['CAPTURE_FORMAT']    = self.capture_format_var.get()
        # Processing
        d['AUTO_PROCESS']      = str(self.auto_process_var.get()).lower()
        d['SHOW_CONTEXT']      = str(self.show_context_var.get()).lower()
        d['KPA_CATEGORIES']    = self.kpa_categories_var.get()
        d['CONTEXT_PROMPT']    = self.context_prompt_var.get()
        # Notifications
        d['NOTIFY_ON_SUCCESS'] = str(self.notify_success_var.get()).lower()
        d['NOTIFY_ON_FAILURE'] = str(self.notify_failure_var.get()).lower()

        self.config_data['DEFAULT']['HOTKEY'] = self.hotkey_var.get()

        save_config(self.config_data)
        self.log("💾 Configuration saved.", "success")
        self.apply_hotkey()

        if self.watcher.running:
            self.stop_service()
        self.start_service()

    # ── SCREENSHOT HOTKEY ─────────────────────────────────────────────────────
    def apply_hotkey(self) -> None:
        hotkey = self.hotkey_var.get().strip()
        if not hotkey:
            return
        try:
            self._hotkey.start(hotkey, self._trigger_capture)
            self.log(f"⌨️  Screenshot hotkey active: {hotkey}", "success")
        except ValueError as e:
            self.log(f"❌ Invalid hotkey — {e}", "error")

    def _trigger_capture(self) -> None:
        # Guard: ignore hotkey if an overlay is already open
        if getattr(self, '_capture_active', False):
            return
        self._capture_active = True
        watch_folder = self.watch_folder_var.get()
        launch_overlay(watch_folder, self._on_screenshot_captured)
        # Safety reset — if callback is never called, unblock after 30s
        self.after(30_000, lambda: setattr(self, '_capture_active', False))

    def _on_screenshot_captured(self, filepath: str) -> None:
        self._capture_active = False
        if filepath:
            filename = os.path.basename(filepath)
            self.log(f"📸 Screenshot captured: {filename}", "success")
        # Watchdog picks up the file and shows the context dialog — don't duplicate here

    # ── AUTO-UPDATER ──────────────────────────────────────────────────────────
    def _on_update_available(self, remote_info: dict) -> None:
        def _prompt():
            new_ver = remote_info.get("version", "?")
            notes   = remote_info.get("release_notes", "")
            self.log(f"🔔 Update available: v{new_ver}", "warn")
            if messagebox.askyesno(
                "Update Available",
                f"KPI Assistant v{new_ver} is ready (you have v{updater.LOCAL_VERSION}).\n\n"
                f"{notes}\n\n"
                f"Install now? The installer will run silently and relaunch the app automatically."
            ):
                dl_url = remote_info.get("download_url", "")
                if not dl_url:
                    messagebox.showerror("Update Error", "No download URL in version manifest.")
                    return

                from app.ui.update_dialog import UpdateProgressWindow
                progress = UpdateProgressWindow(self)

                # on_ready runs on main thread after download — triggers clean shutdown
                def on_ready():
                    self.after(0, lambda: updater.launch_installer_and_exit(self))

                threading.Thread(
                    target=updater.perform_update,
                    args=(dl_url, new_ver, self.log_message, progress),
                    kwargs={"on_ready": on_ready},
                    daemon=True,
                ).start()
        self.after(0, _prompt)

    def manual_update_check(self) -> None:
        self.log("☁  Checking for updates…", "info")
        self.btn_update.configure(state="disabled")

        def _check():
            from packaging.version import Version
            remote = updater._fetch_remote_version_info()
            if remote is None:
                self.after(0, lambda: self.log("⚠️  Could not reach update server.", "warn"))
            elif Version(remote["version"]) > Version(updater.LOCAL_VERSION):
                self._on_update_available(remote)
            else:
                self.after(0, lambda: self.log("✅ You're on the latest version.", "success"))
            self.after(0, lambda: self.btn_update.configure(state="normal"))

        threading.Thread(target=_check, daemon=True).start()
