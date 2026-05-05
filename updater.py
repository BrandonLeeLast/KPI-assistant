"""
Auto-updater: async GitHub version check + hot-swap EXE via self-deleting batch script.

Flow:
  1. check_for_update() runs on a background thread at boot.
  2. If a newer version is found on GitHub, the UI callback is invoked with the
     remote version info so the dashboard can prompt the user.
  3. If the user confirms, perform_update() downloads the new EXE and spawns an
     updater.bat that:
       - Waits for this process to exit
       - Replaces the running EXE (bypasses Windows file-lock)
       - Restarts the updated application
       - Deletes itself
"""

import os
import sys
import time
import subprocess
import tempfile
import threading
import urllib.request
import json
from packaging.version import Version

def _read_local_version() -> str:
    """Read version from version.json sitting next to the EXE (or repo root in dev)."""
    import os, sys, json
    base = os.path.dirname(os.path.abspath(sys.argv[0]))
    path = os.path.join(base, "version.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)["version"]
    except Exception:
        return "0.0.0"

LOCAL_VERSION = _read_local_version()

VERSION_CHECK_URL = (
    "https://raw.githubusercontent.com/BrandonLeeLast/KPI-assistant/main/version.json"
)


def _fetch_remote_version_info() -> dict | None:
    """Returns parsed version.json dict from GitHub, or None on any error."""
    try:
        with urllib.request.urlopen(VERSION_CHECK_URL, timeout=8) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def check_for_update(on_update_available: callable) -> None:
    """
    Non-blocking boot check. Spawns a daemon thread so startup is never delayed.

    on_update_available(remote_info: dict) is called on the background thread
    when a newer version exists — use root.after() inside the callback to
    safely touch Tkinter widgets.
    """
    def _worker():
        remote = _fetch_remote_version_info()
        if remote is None:
            return
        try:
            if Version(remote["version"]) > Version(LOCAL_VERSION):
                on_update_available(remote)
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def perform_update(download_url: str, on_progress: callable = None) -> None:
    """
    Downloads the new EXE and spawns updater.bat to hot-swap it.

    on_progress(message: str) is an optional logging callback.
    This function runs synchronously — call it from a background thread.
    """
    def log(msg):
        if on_progress:
            on_progress(msg)

    current_exe = os.path.abspath(sys.argv[0])
    exe_dir = os.path.dirname(current_exe)
    exe_name = os.path.basename(current_exe)

    # Download to a temp file in the same directory so the rename is atomic
    tmp_path = os.path.join(exe_dir, f"_update_{exe_name}.tmp")
    bat_path = os.path.join(exe_dir, "_kpi_updater.bat")

    try:
        log("⬇️  Downloading update...")
        urllib.request.urlretrieve(download_url, tmp_path)
        log("✅ Download complete. Preparing hot-swap...")
    except Exception as e:
        log(f"❌ Download failed: {e}")
        return

    # Write a self-deleting batch script that runs after this process exits.
    # Uses a :wait loop to poll until the EXE is released by Windows.
    bat_content = f"""@echo off
:wait
timeout /t 2 /nobreak >nul
del /f /q "{current_exe}" >nul 2>&1
if exist "{current_exe}" goto wait
move /y "{tmp_path}" "{current_exe}"
start "" "{current_exe}"
del /f /q "%~f0"
"""
    with open(bat_path, "w") as f:
        f.write(bat_content)

    log("🔄 Spawning updater — the app will restart automatically.")

    # Detach the bat so it outlives this process
    subprocess.Popen(
        ["cmd.exe", "/c", bat_path],
        creationflags=(
            subprocess.CREATE_NEW_PROCESS_GROUP |
            subprocess.DETACHED_PROCESS
        ),
        close_fds=True,
    )

    # Give the bat a moment to start, then exit so it can swap the file
    time.sleep(0.5)
    os.kill(os.getpid(), 9)  # Hard-exit; tray cleanup happens on next launch
