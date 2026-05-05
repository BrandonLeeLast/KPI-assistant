"""
Auto-updater: async GitHub version check + simple download.

Strategy (no hot-swap, no bat scripts, no file locking):
  1. On boot, silently check GitHub for a newer version.json.
  2. If newer, prompt the user.
  3. Download the new EXE to the Desktop as KPI_Assistant_v{version}.exe
  4. Show a "Ready — close this app and run the new file" message.
  5. Open the Desktop folder in Explorer so the user can see it.
  The user just closes the old app and double-clicks the new one.
  No file locks. No bat scripts. No process killing.
"""

import os
import sys
import threading
import urllib.request
import json
from packaging.version import Version


def _read_local_version() -> str:
    candidates = []
    if hasattr(sys, '_MEIPASS'):
        candidates.append(os.path.join(sys._MEIPASS, "version.json"))
    candidates.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "version.json"))
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)["version"]
        except Exception:
            continue
    return "0.0.0"


LOCAL_VERSION = _read_local_version()

VERSION_CHECK_URL = (
    "https://raw.githubusercontent.com/BrandonLeeLast/KPI-assistant/main/version.json"
)


def _fetch_remote_version_info() -> dict | None:
    try:
        with urllib.request.urlopen(VERSION_CHECK_URL, timeout=8) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def check_for_update(on_update_available: callable) -> None:
    """Non-blocking boot check."""
    def _worker():
        remote = _fetch_remote_version_info()
        if remote is None:
            return
        try:
            if Version(remote["version"]) > Version(LOCAL_VERSION):
                on_update_available(remote)
        except Exception:
            pass
    threading.Thread(target=_worker, daemon=True).start()


def perform_update(download_url: str, new_version: str,
                   on_progress: callable = None, progress=None) -> None:
    """
    Downloads the new EXE to the user's Desktop.
    No process killing, no bat scripts, no file locks.
    Runs synchronously — call from a background thread.
    """
    def log(msg):
        if on_progress:
            on_progress(msg)

    desktop    = os.path.join(os.path.expanduser("~"), "Desktop")
    dest_name  = f"KPI_Assistant_v{new_version}.exe"
    dest_path  = os.path.join(desktop, dest_name)

    if progress:
        progress.set_step("Downloading update…", dest_name)
        progress.set_progress(0.05)

    try:
        log("⬇️  Downloading update...")

        def _reporthook(block_num, block_size, total_size):
            if progress and total_size > 0:
                pct = min(block_num * block_size / total_size, 1.0)
                progress.set_progress(0.05 + pct * 0.90)

        urllib.request.urlretrieve(download_url, dest_path, reporthook=_reporthook)
        log(f"✅ Downloaded to Desktop: {dest_name}")

    except Exception as e:
        log(f"❌ Download failed: {e}")
        if progress:
            progress.set_step("Download failed", str(e))
        return

    if progress:
        progress.set_progress(1.0)
        progress.set_step(
            "Update ready!",
            f"Close KPI Assistant and run {dest_name} from your Desktop."
        )

    log(f"🎉 Update ready! Close this app and open {dest_name} from your Desktop.")

    # Open Desktop in Explorer so the user can see the file immediately
    try:
        import subprocess
        subprocess.Popen(["explorer.exe", desktop])
    except Exception:
        pass
