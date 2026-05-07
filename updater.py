"""
Auto-updater — installer-based approach.

Flow:
  1. Async boot check against GitHub version.json
  2. If newer version found, prompt user
  3. Download KPI_Assistant_Setup.exe to %APPDATA%/KPI-assistant/update/
  4. Stop the watchdog + hotkey (release all handles)
  5. Launch the installer with /VERYSILENT — Inno Setup handles everything:
       - Kills any running instance
       - Installs new files to the correct location
       - Relaunches the app automatically
  6. os._exit(0) — we're done, installer takes over

No VBScript, no bat files, no PID watching, no file locks, no zone flags.
Windows treats it as a legitimate installer — no permission issues.
"""

import os
import sys
import threading
import urllib.request
import json
import subprocess
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

_APPDATA     = os.environ.get("APPDATA", os.path.expanduser("~"))
_UPDATE_DIR  = os.path.join(_APPDATA, "KPEye", "update")
_SETUP_EXE   = os.path.join(_UPDATE_DIR, "KPEye_Setup.exe")


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
                   on_progress: callable = None,
                   progress=None,
                   on_ready: callable = None) -> None:
    """
    Downloads the installer to the staging area.
    Calls on_ready() when download is complete so the main thread
    can stop services and launch the installer.
    """
    def log(msg):
        if on_progress:
            on_progress(msg)

    os.makedirs(_UPDATE_DIR, exist_ok=True)

    if progress:
        progress.set_step("Downloading update…", f"v{new_version}")
        progress.set_progress(0.05)

    try:
        log("Downloading update...")

        def _reporthook(block_num, block_size, total_size):
            if progress and total_size > 0:
                pct = min(block_num * block_size / total_size, 1.0)
                progress.set_progress(0.05 + pct * 0.90)

        urllib.request.urlretrieve(download_url, _SETUP_EXE, reporthook=_reporthook)
        log("Download complete.")

    except Exception as e:
        log(f"Download failed: {e}")
        if progress:
            progress.set_step("Download failed", str(e))
        return

    if progress:
        progress.set_progress(1.0)
        progress.set_step("Ready to install", "Closing app and running installer...")
        progress.finish()

    if on_ready:
        on_ready()


def launch_installer_and_exit(app) -> None:
    """
    Called on the main thread after download completes.
    Stops all services, launches the Inno Setup installer silently, exits.
    The installer handles killing old instances, copying files, relaunching.
    """
    try:
        app.watcher.stop()
    except Exception:
        pass
    try:
        app._hotkey.stop()
    except Exception:
        pass
    try:
        app.tray_icon.stop()
    except Exception:
        pass

    # Launch installer — /VERYSILENT = no UI, /NORESTART = don't force reboot
    # Inno Setup's [Run] section will relaunch the app after install
    si = subprocess.STARTUPINFO()
    si.dwFlags    |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0

    subprocess.Popen(
        [_SETUP_EXE, "/VERYSILENT", "/NORESTART", "/CLOSEAPPLICATIONS"],
        startupinfo=si,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )

    try:
        app.destroy()
    except Exception:
        pass
    os._exit(0)
