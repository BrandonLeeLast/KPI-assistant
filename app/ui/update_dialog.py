"""
Lightweight update progress window shown during download + hot-swap.
Created as a CTkToplevel on the main thread so it shares the existing
Tk event loop — no second mainloop or daemon thread needed.
"""

import customtkinter as ctk

from app.constants import (BG, SURFACE, OVERLAY, TEXT, SUBTEXT, MAUVE, GREEN, HEADER_BG)


class UpdateProgressWindow:
    """
    Must be instantiated on the main Tk thread (pass the CTk root as parent).
    set_step / set_progress are safe to call from any background thread.
    """

    def __init__(self, parent: ctk.CTk):
        win = ctk.CTkToplevel(parent)
        self._win = win

        win.title("KPI Assistant — Updating")
        win.geometry("420x220")
        win.resizable(False, False)
        win.configure(fg_color=BG)
        win.attributes("-topmost", True)
        win.grab_set()

        win.update_idletasks()
        x = (win.winfo_screenwidth()  - 420) // 2
        y = (win.winfo_screenheight() - 220) // 2
        win.geometry(f"420x220+{x}+{y}")

        # ── Header ────────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(win, fg_color=HEADER_BG, corner_radius=0, height=50)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="⬡", text_color=MAUVE,
                     font=ctk.CTkFont("Segoe UI", 20)).pack(side="left", padx=(14, 6), pady=8)
        ctk.CTkLabel(hdr, text="Updating KPI Assistant",
                     text_color=TEXT, font=ctk.CTkFont("Segoe UI", 13, weight="bold")).pack(side="left")

        # ── Body ──────────────────────────────────────────────────────────────
        body = ctk.CTkFrame(win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=16)

        self._lbl_step = ctk.CTkLabel(body, text="Preparing…",
                                       text_color=TEXT,
                                       font=ctk.CTkFont("Segoe UI", 12, weight="bold"),
                                       anchor="w")
        self._lbl_step.pack(fill="x")

        self._lbl_sub = ctk.CTkLabel(body, text="",
                                      text_color=SUBTEXT,
                                      font=ctk.CTkFont("Segoe UI", 10),
                                      anchor="w")
        self._lbl_sub.pack(fill="x", pady=(2, 14))

        self._bar = ctk.CTkProgressBar(body, height=10, corner_radius=5,
                                        fg_color=SURFACE, progress_color=MAUVE)
        self._bar.set(0)
        self._bar.pack(fill="x")

        self._lbl_pct = ctk.CTkLabel(body, text="0%",
                                      text_color=OVERLAY,
                                      font=ctk.CTkFont("Segoe UI", 9))
        self._lbl_pct.pack(anchor="e", pady=(4, 0))

    # ── public API — safe to call from any thread ──────────────────────────────
    def set_step(self, title: str, subtitle: str = "") -> None:
        self._win.after(0, lambda: self._lbl_step.configure(text=title))
        self._win.after(0, lambda: self._lbl_sub.configure(text=subtitle))

    def set_progress(self, value: float) -> None:
        value = max(0.0, min(1.0, value))
        self._win.after(0, lambda: self._bar.set(value))
        self._win.after(0, lambda: self._lbl_pct.configure(text=f"{int(value * 100)}%"))
        if value >= 1.0:
            self._win.after(0, lambda: self._bar.configure(progress_color=GREEN))

    def finish(self, message: str = "Restarting…") -> None:
        self.set_progress(1.0)
        self.set_step("Update complete!", message)
