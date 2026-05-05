"""
Update progress window — CTkToplevel on the main thread.
Never calls grab_set() (that blocks the event loop).
Background thread calls set_step/set_progress which schedule
via after() so the main loop stays free to process them.
"""

import customtkinter as ctk
from app.constants import (BG, SURFACE, OVERLAY, TEXT, SUBTEXT,
                            MAUVE, GREEN, HEADER_BG)


class UpdateProgressWindow:
    """
    Instantiate on the main Tk thread, then pass to perform_update().
    All setter methods are thread-safe — they schedule via after().
    """

    def __init__(self, parent: ctk.CTk):
        self._parent = parent
        self._win    = None
        # Build on main thread immediately
        parent.after(0, self._build)

    def _build(self):
        win = ctk.CTkToplevel(self._parent)
        self._win = win

        win.title("KPI Assistant — Updating")
        win.geometry("440x200")
        win.resizable(False, False)
        win.configure(fg_color=BG)
        win.attributes("-topmost", True)
        # NO grab_set — that starves the event loop

        win.update_idletasks()
        x = (win.winfo_screenwidth()  - 440) // 2
        y = (win.winfo_screenheight() - 200) // 2
        win.geometry(f"440x200+{x}+{y}")

        # Header
        hdr = ctk.CTkFrame(win, fg_color=HEADER_BG, corner_radius=0, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="⬡", text_color=MAUVE,
                     font=ctk.CTkFont("Segoe UI", 20)).pack(side="left", padx=(14, 6), pady=8)
        ctk.CTkLabel(hdr, text="Updating KPI Assistant",
                     text_color=TEXT,
                     font=ctk.CTkFont("Segoe UI", 13, weight="bold")).pack(side="left")

        # Body
        body = ctk.CTkFrame(win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=14)

        self._lbl_step = ctk.CTkLabel(body, text="Starting download…",
                                       text_color=TEXT,
                                       font=ctk.CTkFont("Segoe UI", 12, weight="bold"),
                                       anchor="w")
        self._lbl_step.pack(fill="x")

        self._lbl_sub = ctk.CTkLabel(body, text="",
                                      text_color=SUBTEXT,
                                      font=ctk.CTkFont("Segoe UI", 10),
                                      anchor="w")
        self._lbl_sub.pack(fill="x", pady=(2, 12))

        self._bar = ctk.CTkProgressBar(body, height=10, corner_radius=5,
                                        fg_color=SURFACE, progress_color=MAUVE)
        self._bar.set(0)
        self._bar.pack(fill="x")

        self._lbl_pct = ctk.CTkLabel(body, text="0 %",
                                      text_color=OVERLAY,
                                      font=ctk.CTkFont("Segoe UI", 9))
        self._lbl_pct.pack(anchor="e", pady=(3, 0))

    # ── Thread-safe API ───────────────────────────────────────────────────────
    def set_step(self, title: str, subtitle: str = "") -> None:
        self._parent.after(0, lambda: self._safe_set_step(title, subtitle))

    def _safe_set_step(self, title: str, subtitle: str) -> None:
        if self._win and self._lbl_step:
            self._lbl_step.configure(text=title)
            self._lbl_sub.configure(text=subtitle)

    def set_progress(self, value: float) -> None:
        value = max(0.0, min(1.0, value))
        self._parent.after(0, lambda: self._safe_set_progress(value))

    def _safe_set_progress(self, value: float) -> None:
        if self._win and self._bar:
            self._bar.set(value)
            self._lbl_pct.configure(text=f"{int(value * 100)} %")
            if value >= 1.0:
                self._bar.configure(progress_color=GREEN)

    def finish(self, message: str = "Restarting…") -> None:
        self.set_progress(1.0)
        self.set_step("Update complete!", message)
