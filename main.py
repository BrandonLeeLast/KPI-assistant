import os
import sys
import shutil
import tempfile


def _cleanup_stale_mei() -> None:
    """
    Delete any _MEI* folders in %TEMP% that don't belong to the current process.
    PyInstaller creates a new _MEI folder on every launch and is supposed to clean
    up the old one on exit — but crashes or hard-kills leave them behind, causing
    "python3xx.dll not found" on the next launch if the folder name is reused.
    """
    if not hasattr(sys, '_MEIPASS'):
        return  # running in dev mode — nothing to clean

    current_mei = sys._MEIPASS
    temp_dir    = tempfile.gettempdir()

    for name in os.listdir(temp_dir):
        if not name.startswith('_MEI'):
            continue
        full = os.path.join(temp_dir, name)
        if full == current_mei:
            continue  # never delete our own extraction folder
        try:
            shutil.rmtree(full, ignore_errors=True)
        except Exception:
            pass


_cleanup_stale_mei()

from app.ui.app import KPIDashboardApp

if __name__ == "__main__":
    app = KPIDashboardApp()
    app.mainloop()
