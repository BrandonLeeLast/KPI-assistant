"""
Fullscreen screenshot capture overlay.

Displays a semi-transparent dark overlay over all monitors. The user
drags to select a region — on mouse release the selected area is
captured with mss and saved to the watch folder.
"""

import tkinter as tk
import time
import os
import threading
from datetime import datetime
from typing import Callable

import mss
import mss.tools
from PIL import Image

from app.constants import MAUVE, SURFACE2


class CaptureOverlay:
    """
    One Toplevel per monitor, stitched together to cover all screens.
    The drag rectangle is drawn on whichever window the mouse starts on.
    """

    def __init__(self, watch_folder: str, on_captured: Callable[[str], None]):
        self._watch_folder  = watch_folder
        self._on_captured   = on_captured  # called with saved file path
        self._root          = tk.Tk()
        self._windows: list[tk.Toplevel] = []
        self._drag_start    = (0, 0)
        self._active_win    = None
        self._rect_id       = None
        self._cancelled     = False

        self._build()

    def _build(self):
        # Hidden root — we don't show this, just use it as a Tk host
        self._root.withdraw()
        self._root.attributes("-alpha", 0)

        with mss.mss() as sct:
            monitors = sct.monitors[1:]  # index 0 is the combined virtual screen

        for mon in monitors:
            self._create_window(mon)

        self._root.mainloop()

    def _create_window(self, mon: dict):
        win = tk.Toplevel(self._root)
        win.geometry(f"{mon['width']}x{mon['height']}+{mon['left']}+{mon['top']}")
        win.overrideredirect(True)           # no title bar
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.35)
        win.configure(bg="black")
        win.config(cursor="crosshair")

        canvas = tk.Canvas(win, bg="black", highlightthickness=0,
                           cursor="crosshair")
        canvas.pack(fill="both", expand=True)

        # Instruction label — centre of screen
        canvas.create_text(
            mon["width"] // 2, mon["height"] // 2,
            text="Drag to select area   ·   Esc to cancel",
            fill=MAUVE, font=("Segoe UI", 14),
            tags="hint",
        )

        canvas.bind("<ButtonPress-1>",   lambda e, w=win, c=canvas, m=mon: self._on_press(e, w, c, m))
        canvas.bind("<B1-Motion>",       lambda e, c=canvas: self._on_drag(e, c))
        canvas.bind("<ButtonRelease-1>", lambda e, c=canvas, m=mon: self._on_release(e, c, m))
        win.bind("<Escape>",             lambda e: self._cancel())

        self._windows.append((win, canvas, mon))

    # ── Drag logic ────────────────────────────────────────────────────────────
    def _on_press(self, event, win, canvas, mon):
        self._active_win  = (win, canvas, mon)
        self._drag_start  = (event.x, event.y)
        self._rect_id     = None
        canvas.delete("hint")

    def _on_drag(self, event, canvas):
        if self._rect_id:
            canvas.delete(self._rect_id)
        x0, y0 = self._drag_start
        self._rect_id = canvas.create_rectangle(
            x0, y0, event.x, event.y,
            outline=MAUVE, width=2,
            fill="#cba6f7", stipple="gray25",  # semi-transparent fill
        )
        # Size indicator
        canvas.delete("size_hint")
        w = abs(event.x - x0)
        h = abs(event.y - y0)
        canvas.create_text(
            event.x + 10, event.y + 10,
            text=f"{w} × {h}",
            fill="white", font=("Segoe UI", 10, "bold"),
            anchor="nw", tags="size_hint",
        )

    def _on_release(self, event, canvas, mon):
        x0, y0 = self._drag_start
        x1, y1 = event.x, event.y

        # Normalise so top-left is always the smaller coord
        left   = mon["left"] + min(x0, x1)
        top    = mon["top"]  + min(y0, y1)
        width  = abs(x1 - x0)
        height = abs(y1 - y0)

        self._close_all()

        if width < 10 or height < 10:
            return  # too small — treat as accidental click

        self._capture(left, top, width, height)

    def _cancel(self):
        self._cancelled = True
        self._close_all()

    def _close_all(self):
        for win, _, __ in self._windows:
            try:
                win.destroy()
            except Exception:
                pass
        try:
            self._root.destroy()
        except Exception:
            pass

    # ── Capture ───────────────────────────────────────────────────────────────
    def _capture(self, left: int, top: int, width: int, height: int):
        os.makedirs(self._watch_folder, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename  = f"kpi_{timestamp}.png"
        filepath  = os.path.join(self._watch_folder, filename)

        with mss.mss() as sct:
            region = {"left": left, "top": top, "width": width, "height": height}
            shot   = sct.grab(region)
            img    = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            img.save(filepath, "PNG")

        if self._on_captured:
            self._on_captured(filepath)


def launch_overlay(watch_folder: str, on_captured: Callable[[str], None]) -> None:
    """
    Spawn the capture overlay in its own thread so it doesn't block
    the main Tkinter loop. The overlay creates its own Tk root internally.
    """
    def _run():
        CaptureOverlay(watch_folder, on_captured)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
