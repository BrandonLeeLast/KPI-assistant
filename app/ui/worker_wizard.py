"""
Worker deployment wizard — CTkToplevel step-by-step UI.
Guides the user through deploying their own Cloudflare AI Worker.
"""

import tkinter as tk
import customtkinter as ctk
from app.constants import (BG, BG2, SURFACE, SURFACE2, OVERLAY,
                            TEXT, SUBTEXT, MAUVE, GREEN, RED, TEAL, YELLOW, HEADER_BG)


class WorkerWizard:
    """
    Must be created on the main Tk thread.
    Call start_deploy() to kick off the background deployment.
    """

    def __init__(self, parent: ctk.CTk, on_complete):
        """
        on_complete(worker_url, auth_token) — called when deploy succeeds.
        """
        self._parent      = parent
        self._on_complete = on_complete

        win = ctk.CTkToplevel(parent)
        self._win = win
        win.title("KPI Assistant — Deploy Your AI Worker")
        win.geometry("560x520")
        win.resizable(False, False)
        win.configure(fg_color=BG)
        win.attributes("-topmost", True)
        win.protocol("WM_DELETE_WINDOW", self._on_close)

        win.update_idletasks()
        x = (win.winfo_screenwidth()  - 560) // 2
        y = (win.winfo_screenheight() - 520) // 2
        win.geometry(f"560x520+{x}+{y}")

        # ── Header ────────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(win, fg_color=HEADER_BG, corner_radius=0, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="⬡", text_color=MAUVE,
                     font=ctk.CTkFont("Segoe UI", 22)).pack(side="left", padx=(16, 8))
        title_col = ctk.CTkFrame(hdr, fg_color="transparent")
        title_col.pack(side="left", pady=10)
        ctk.CTkLabel(title_col, text="Deploy Your AI Worker",
                     text_color=TEXT, font=ctk.CTkFont("Segoe UI", 14, weight="bold"),
                     anchor="w").pack(anchor="w")
        ctk.CTkLabel(title_col, text="One-click setup on your Cloudflare account",
                     text_color=OVERLAY, font=ctk.CTkFont("Segoe UI", 10),
                     anchor="w").pack(anchor="w")

        # ── Steps overview ────────────────────────────────────────────────────
        steps_frame = ctk.CTkFrame(win, fg_color=BG2, corner_radius=0)
        steps_frame.pack(fill="x")

        steps = [
            ("1", "Check Node.js",       MAUVE),
            ("2", "Download template",   MAUVE),
            ("3", "Cloudflare login",    MAUVE),
            ("4", "Deploy worker",       MAUVE),
            ("5", "Save config",         MAUVE),
        ]
        self._step_labels = {}
        row = ctk.CTkFrame(steps_frame, fg_color="transparent")
        row.pack(pady=10, padx=16)
        for num, label, color in steps:
            col = ctk.CTkFrame(row, fg_color="transparent")
            col.pack(side="left", padx=8)
            badge = ctk.CTkLabel(col, text=num, width=28, height=28,
                                  fg_color=SURFACE, text_color=OVERLAY,
                                  corner_radius=14,
                                  font=ctk.CTkFont("Segoe UI", 11, weight="bold"))
            badge.pack()
            lbl = ctk.CTkLabel(col, text=label, text_color=OVERLAY,
                                font=ctk.CTkFont("Segoe UI", 9))
            lbl.pack()
            self._step_labels[num] = (badge, lbl)

        # ── Log area ──────────────────────────────────────────────────────────
        log_frame = ctk.CTkFrame(win, fg_color="transparent")
        log_frame.pack(fill="both", expand=True, padx=16, pady=(12, 8))

        self._log = ctk.CTkTextbox(
            log_frame, fg_color=BG2, border_width=1, border_color=SURFACE,
            text_color=SUBTEXT, font=ctk.CTkFont("Consolas", 10),
            corner_radius=8, wrap="word", state="disabled",
        )
        self._log.pack(fill="both", expand=True)

        # ── Status label ──────────────────────────────────────────────────────
        self._lbl_status = ctk.CTkLabel(
            win, text="Ready to deploy.", text_color=OVERLAY,
            font=ctk.CTkFont("Segoe UI", 11), anchor="w"
        )
        self._lbl_status.pack(fill="x", padx=16)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(8, 16))

        self._btn_deploy = ctk.CTkButton(
            btn_row, text="🚀  Deploy My AI Worker",
            fg_color=TEAL, hover_color="#78c9bf", text_color=HEADER_BG,
            font=ctk.CTkFont("Segoe UI", 12, weight="bold"),
            corner_radius=8, height=40,
            command=self._start,
        )
        self._btn_deploy.pack(side="left", fill="x", expand=True)

        self._btn_close = ctk.CTkButton(
            btn_row, text="Cancel", width=90, height=40,
            fg_color=SURFACE2, hover_color="#585b70", text_color=TEXT,
            font=ctk.CTkFont("Segoe UI", 11), corner_radius=8,
            command=self._on_close,
        )
        self._btn_close.pack(side="right", padx=(8, 0))

        # Node check on open
        win.after(300, self._check_node_on_open)

    # ── Internal ───────────────────────────────────────────────────────────────
    def _log_msg(self, msg: str, color: str = None) -> None:
        self._parent.after(0, lambda: self._append_log(msg, color))

    def _append_log(self, msg: str, color: str = None) -> None:
        self._log.configure(state="normal")
        self._log.insert(tk.END, f"{msg}\n")
        self._log.see(tk.END)
        self._log.configure(state="disabled")

    def _set_status(self, msg: str, color: str = None) -> None:
        self._parent.after(0, lambda: self._lbl_status.configure(
            text=msg, text_color=color or OVERLAY
        ))

    def _activate_step(self, num: str) -> None:
        def _do():
            for n, (badge, lbl) in self._step_labels.items():
                if n == num:
                    badge.configure(fg_color=MAUVE, text_color=HEADER_BG)
                    lbl.configure(text_color=TEXT)
                elif int(n) < int(num):
                    badge.configure(fg_color=GREEN, text_color=HEADER_BG, text="✓")
                    lbl.configure(text_color=GREEN)
        self._parent.after(0, _do)

    def _check_node_on_open(self) -> None:
        from app.worker_deploy import check_node, check_npm
        ok_node, ver_node = check_node()
        ok_npm,  _        = check_npm()
        if ok_node and ok_npm:
            self._log_msg(f"✅ Node.js {ver_node} detected — ready to deploy.")
        else:
            self._log_msg("⚠️  Node.js not found.", RED)
            self._log_msg("   Download from: https://nodejs.org", YELLOW)
            self._log_msg("   Install it and reopen this window.", YELLOW)
            self._btn_deploy.configure(state="disabled",
                                        text="Node.js required — see log")

    def _start(self) -> None:
        self._btn_deploy.configure(state="disabled", text="⏳  Deploying…")
        self._btn_close.configure(state="disabled")
        self._log_msg("─" * 50)
        self._log_msg("Starting deployment...")
        self._activate_step("1")

        from app.worker_deploy import deploy_worker

        def _log(msg):
            # Activate steps based on log messages
            if "Downloading" in msg:
                self._activate_step("2")
            elif "login" in msg.lower() or "browser" in msg.lower():
                self._activate_step("3")
            elif "Deploying" in msg or "Deployed" in msg or "secret" in msg.lower():
                self._activate_step("4")
            self._log_msg(msg)
            self._set_status(msg.strip("🔍✅⬇️📦🚀🔒🔑🌐⏳ "))

        def _done(url):
            self._activate_step("5")
            self._log_msg(f"")
            self._log_msg(f"🎉 All done!")
            self._log_msg(f"   Worker URL: {url}")
            self._set_status("Deployment complete!", GREEN)
            self._parent.after(0, lambda: self._btn_close.configure(
                state="normal", text="Close"
            ))
            self._parent.after(0, lambda: self._btn_deploy.configure(
                text="✅  Deployed!", fg_color=GREEN, text_color=HEADER_BG
            ))
            if self._on_complete:
                self._parent.after(0, lambda: self._on_complete(url))

        def _error(msg):
            self._log_msg(f"❌ {msg}", RED)
            self._set_status("Deployment failed — see log.", RED)
            self._parent.after(0, lambda: self._btn_deploy.configure(
                state="normal", text="🚀  Retry Deploy"
            ))
            self._parent.after(0, lambda: self._btn_close.configure(state="normal"))

        deploy_worker(_log, _done, _error)

    def _on_close(self) -> None:
        try:
            self._win.destroy()
        except Exception:
            pass
