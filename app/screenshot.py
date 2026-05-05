"""
Global hotkey listener for the built-in screenshot tool.

Uses pynput so the hotkey works system-wide — even when the dashboard
is minimised to the tray. Runs on a single persistent background thread.
"""

import threading
from typing import Callable

from pynput import keyboard


class HotkeyListener:
    """
    Listens for a configurable hotkey combination and fires a callback.

    Hotkey format matches pynput's GlobalHotKeys syntax:
        "<ctrl>+<shift>+s"   →  config value:  ctrl+shift+s
    """

    def __init__(self):
        self._listener: keyboard.GlobalHotKeys | None = None
        self._lock = threading.Lock()

    def start(self, hotkey_str: str, callback: Callable) -> None:
        """
        Start listening for `hotkey_str`. Stops any existing listener first.
        hotkey_str format: "ctrl+shift+s"  (user-friendly, from config)
        """
        self.stop()
        pynput_hotkey = _to_pynput(hotkey_str)
        with self._lock:
            try:
                self._listener = keyboard.GlobalHotKeys(
                    {pynput_hotkey: callback}
                )
                self._listener.start()
            except Exception as e:
                self._listener = None
                raise ValueError(f"Invalid hotkey '{hotkey_str}': {e}") from e

    def stop(self) -> None:
        with self._lock:
            if self._listener:
                try:
                    self._listener.stop()
                except Exception:
                    pass
                self._listener = None

    @property
    def running(self) -> bool:
        return self._listener is not None


def _to_pynput(hotkey: str) -> str:
    """
    Convert user-friendly hotkey string to pynput GlobalHotKeys format.

    "ctrl+shift+s"  →  "<ctrl>+<shift>+s"
    "ctrl+F12"      →  "<ctrl>+<F12>"
    """
    parts  = [p.strip().lower() for p in hotkey.split("+")]
    mapped = []
    # Keys that need angle-bracket wrapping in pynput
    special = {
        "ctrl", "control", "shift", "alt", "cmd", "super", "win",
        "f1","f2","f3","f4","f5","f6","f7","f8","f9","f10","f11","f12",
        "space","tab","enter","return","esc","escape",
        "up","down","left","right","home","end","pgup","pgdown",
        "insert","delete","backspace","capslock","numlock","scrolllock",
        "printscreen","pause","menu",
    }
    for part in parts:
        if part in special:
            mapped.append(f"<{part}>")
        else:
            mapped.append(part)  # single character key — no brackets
    return "+".join(mapped)
