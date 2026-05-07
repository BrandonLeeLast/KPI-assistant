"""
Update progress window — CTkToplevel built synchronously on the main thread.
Background thread calls set_step/set_progress safely via after().
"""

import customtkinter as ctk
from app.constants import (BG, SURFACE, OVERLAY, TEXT, SUBTEXT,
                            MAUVE, GREEN, HEADER_BG)


class UpdateProgressWindow:
    """
    Must be instantiated on the main Tk thread.
    All public methods are safe to call from background threads.
    """

    def __init__(self, parent: ctk.CTk):
        self._parent = parent

        # ── Build window immediately (we are already on the main thread) ──────
        win = ctk.CTkToplevel(parent)
        self._win = win

        win.title("KPEye — Updating")
        win.geometry("440x210")
        win.resizable(False, False)
        win.configure(fg_color=BG)
        win.attributes("-topmost", True)
        win.protocol("WM_DELETE_WINDOW", self._on_close)

        win.update_idletasks()
        x = (win.winfo_screenwidth()  - 440) // 2
        y = (win.winfo_screenheight() - 210) // 2
        win.geometry(f"440x210+{x}+{y}")

        # ── Header ────────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(win, fg_color=HEADER_BG, corner_radius=0, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="⬡", text_color=MAUVE,
                     font=ctk.CTkFont("Segoe UI", 20)).pack(side="left", padx=(14, 6), pady=8)
        ctk.CTkLabel(hdr, text="Updating KPEye",
                     text_color=TEXT,
                     font=ctk.CTkFont("Segoe UI", 13, weight="bold")).pack(side="left")

        # ── Body ──────────────────────────────────────────────────────────────
        body = ctk.CTkFrame(win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=14)

        self._lbl_step = ctk.CTkLabel(
            body, text="Starting download…",
            text_color=TEXT,
            font=ctk.CTkFont("Segoe UI", 12, weight="bold"),
            anchor="w",
        )
        self._lbl_step.pack(fill="x")

        self._lbl_sub = ctk.CTkLabel(
            body, text="",
            text_color=SUBTEXT,
            font=ctk.CTkFont("Segoe UI", 10),
            anchor="w",
        )
        self._lbl_sub.pack(fill="x", pady=(2, 12))

        self._bar = ctk.CTkProgressBar(
            body, height=10, corner_radius=5,
            fg_color=SURFACE, progress_color=MAUVE,
        )
        self._bar.set(0)
        self._bar.pack(fill="x")

        self._lbl_pct = ctk.CTkLabel(
            body, text="0 %",
            text_color=OVERLAY,
            font=ctk.CTkFont("Segoe UI", 9),
        )
        self._lbl_pct.pack(anchor="e", pady=(3, 0))

        # Force render before returning so widgets are visible immediately
        win.update()

    # ── Thread-safe public API ────────────────────────────────────────────────
    def set_step(self, title: str, subtitle: str = "") -> None:
        self._parent.after(0, lambda: self._do_set_step(title, subtitle))

    def set_progress(self, value: float) -> None:
        value = max(0.0, min(1.0, value))
        self._parent.after(0, lambda: self._do_set_progress(value))

    def finish(self, message: str = "Applying update…") -> None:
        self._cancelled = True  # download done — X button now harmless
        self.set_progress(1.0)
        self.set_step("Installing update…", message)

    def _on_close(self) -> None:
        """X button — only allow closing if download isn't in flight."""
        if getattr(self, '_cancelled', False):
            # Download complete, app is about to exit anyway — just hide
            try:
                self._win.destroy()
            except Exception:
                pass
        else:
            # Download in progress — ask before cancelling
            from tkinter import messagebox
            if messagebox.askyesno(
                "Cancel Update?",
                "Download is in progress. Cancel the update?",
                parent=self._win,
            ):
                self._cancelled = True
                try:
                    self._win.destroy()
                except Exception:
                    pass

    # ── Internal (main thread only) ───────────────────────────────────────────
    def _do_set_step(self, title: str, subtitle: str) -> None:
        try:
            self._lbl_step.configure(text=title)
            self._lbl_sub.configure(text=subtitle)
        except Exception:
            pass

    def _do_set_progress(self, value: float) -> None:
        try:
            self._bar.set(value)
            self._lbl_pct.configure(text=f"{int(value * 100)} %")
            if value >= 1.0:
                self._bar.configure(progress_color=GREEN)
        except Exception:
            pass
