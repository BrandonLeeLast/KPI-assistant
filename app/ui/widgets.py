import tkinter as tk
import customtkinter as ctk
from app.constants import GREEN, YELLOW, RED, SURFACE, SURFACE2, SUBTEXT, OVERLAY, HEADER_BG


class StatCard(ctk.CTkFrame):
    """Live-updating metric tile."""

    def __init__(self, parent, label: str, accent: str, **kw):
        super().__init__(parent, fg_color=SURFACE, corner_radius=12, **kw)
        self._accent = accent
        self._value  = tk.StringVar(value="0")

        ctk.CTkLabel(self, text=label, text_color=SUBTEXT,
                     font=ctk.CTkFont("Segoe UI", 11, weight="normal")).pack(pady=(14, 0))

        ctk.CTkLabel(self, textvariable=self._value, text_color=accent,
                     font=ctk.CTkFont("Segoe UI", 34, weight="bold")).pack()

        # accent underline bar
        bar = ctk.CTkFrame(self, fg_color=accent, height=3, corner_radius=2)
        bar.pack(fill="x", padx=20, pady=(2, 14))

    def set(self, value: int) -> None:
        self._value.set(str(value))

    def increment(self) -> None:
        self._value.set(str(int(self._value.get()) + 1))


class PulseIndicator(tk.Canvas):
    """Breathing dot shown in the topbar when the daemon is active."""

    def __init__(self, parent, **kw):
        super().__init__(parent, width=12, height=12,
                         bg=HEADER_BG, highlightthickness=0, **kw)
        self._active = False
        self._phase  = 0
        self._dot    = self.create_oval(1, 1, 11, 11, fill=SURFACE2, outline="")
        self._animate()

    def set_active(self, active: bool) -> None:
        self._active = active

    def _animate(self) -> None:
        if self._active:
            self._phase = (self._phase + 1) % 20
            t = abs(self._phase - 10) / 10
            r, g, b    = 166, 227, 161   # GREEN
            dr, dg, db = 69,  71,  90    # SURFACE2
            color = (f"#{int(r*t + dr*(1-t)):02x}"
                     f"{int(g*t + dg*(1-t)):02x}"
                     f"{int(b*t + db*(1-t)):02x}")
            self.itemconfig(self._dot, fill=color)
        else:
            self.itemconfig(self._dot, fill=SURFACE2)
        self.after(80, self._animate)
