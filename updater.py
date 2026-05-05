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
    """
    Read version from version.json.
    When bundled by PyInstaller, the file lives in sys._MEIPASS (the extraction
    folder). In dev, it sits next to the script / repo root.
    """
    import os, sys, json
    candidates = []
    # 1. PyInstaller bundle extraction folder (_MEIPASS)
    if hasattr(sys, '_MEIPASS'):
        candidates.append(os.path.join(sys._MEIPASS, "version.json"))
    # 2. Next to the EXE / script (dev mode)
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

    # Capture the _MEI extraction folder for THIS process so we can wait
    # for it to be fully released before starting the new EXE.
    # sys._MEIPASS is set by PyInstaller; in dev it won't exist (that's fine).
    mei_dir = getattr(sys, '_MEIPASS', None) or ""

    bat_content = f"""@echo off

:: ── Step 1: wait for the old EXE file lock to release ──────────────────────
:wait_exe
timeout /t 2 /nobreak >nul
del /f /q "{current_exe}" >nul 2>&1
if exist "{current_exe}" goto wait_exe

:: ── Step 2: wait for PyInstaller _MEI temp folder to be released ───────────
:: This is the folder containing python3xx.dll for the OLD process.
:: The new EXE must not start until Windows has fully let go of it,
:: otherwise it picks up a half-cleaned DLL path and crashes.
set "MEI={mei_dir}"
if not "%MEI%"=="" (
    :wait_mei
    if exist "%MEI%\\python*.dll" (
        timeout /t 2 /nobreak >nul
        goto wait_mei
    )
    :: Folder is released — clean it up
    rmdir /s /q "%MEI%" >nul 2>&1
)

:: ── Step 3: swap in the new EXE ────────────────────────────────────────────
move /y "{tmp_path}" "{current_exe}"

:: ── Step 4: short settle, then launch ──────────────────────────────────────
timeout /t 2 /nobreak >nul
start "" "{current_exe}"

:: ── Step 5: self-destruct ───────────────────────────────────────────────────
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
