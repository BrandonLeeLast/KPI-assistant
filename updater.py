"""
Auto-updater: async GitHub version check + hot-swap EXE via self-deleting batch script.

Flow:
  1. check_for_update() runs on a background thread at boot.
  2. If a newer version is found on GitHub, the UI callback is invoked with the
     remote version info so the dashboard can prompt the user.
  3. If the user confirms, perform_update() downloads the new EXE and spawns an
     updater.bat that:
       - Waits for this process to exit
       - Clears the entire APPDATA runtime folder so the new EXE gets a clean unpack
       - Replaces the running EXE (bypasses Windows file-lock)
       - Restarts the updated application silently
       - Deletes itself
"""

import os
import sys
import time
import subprocess
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
    """Returns parsed version.json dict from GitHub, or None on any error."""
    try:
        with urllib.request.urlopen(VERSION_CHECK_URL, timeout=8) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def check_for_update(on_update_available: callable) -> None:
    """
    Non-blocking boot check. Spawns a daemon thread so startup is never delayed.
    on_update_available(remote_info) is called on the background thread.
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

    threading.Thread(target=_worker, daemon=True).start()


def perform_update(download_url: str, on_progress: callable = None, progress=None) -> None:
    """
    Downloads the new EXE, updates the progress window, then spawns a hidden
    updater.bat to hot-swap it. Runs synchronously — call from a background thread.
    `progress` must be an UpdateProgressWindow created on the main Tk thread before
    this function is called.
    """
    def log(msg):
        if on_progress:
            on_progress(msg)

    current_exe = os.path.abspath(sys.argv[0])
    exe_dir     = os.path.dirname(current_exe)
    exe_name    = os.path.basename(current_exe)
    tmp_path    = os.path.join(exe_dir, f"_update_{exe_name}.tmp")
    bat_path    = os.path.join(exe_dir, "_kpi_updater.bat")

    mei_dir     = getattr(sys, '_MEIPASS', "") or ""
    appdata     = os.environ.get("APPDATA", "")
    runtime_dir = os.path.join(appdata, "KPI-assistant", "runtime") if appdata else ""

    if progress:
        progress.set_step("Downloading update…", download_url.split("/")[-1])
        progress.set_progress(0.05)

    # ── Download with live progress ───────────────────────────────────────────
    try:
        log("⬇️  Downloading update...")

        def _reporthook(block_num, block_size, total_size):
            if progress and total_size > 0:
                pct = min(block_num * block_size / total_size, 1.0)
                progress.set_progress(0.05 + pct * 0.75)

        urllib.request.urlretrieve(download_url, tmp_path, reporthook=_reporthook)
        log("✅ Download complete. Preparing hot-swap...")
    except Exception as e:
        log(f"❌ Download failed: {e}")
        if progress:
            progress.set_step("Download failed", str(e))
        return

    if progress:
        progress.set_step("Preparing installer…", "Building hot-swap script")
        progress.set_progress(0.85)

    bat_content = f"""@echo off

:: ── 1. Wait for old EXE file lock to release ───────────────────────────────
:wait_exe
timeout /t 2 /nobreak >nul
del /f /q "{current_exe}" >nul 2>&1
if exist "{current_exe}" goto wait_exe

:: ── 2. Nuke the old _MEIPASS extraction folder ─────────────────────────────
:: Poll until python*.dll is gone (process fully exited), then wipe the folder.
set "MEI={mei_dir}"
if not "%MEI%"=="" (
    :wait_mei
    if exist "%MEI%\\python*.dll" (
        timeout /t 2 /nobreak >nul
        goto wait_mei
    )
    rmdir /s /q "%MEI%" >nul 2>&1
)

:: ── 3. Wipe the APPDATA runtime folder (legacy location) ───────────────────
set "RT={runtime_dir}"
if not "%RT%"=="" (
    if exist "%RT%" rmdir /s /q "%RT%" >nul 2>&1
)

:: ── 4. Swap in the new EXE ──────────────────────────────────────────────────
move /y "{tmp_path}" "{current_exe}"

:: ── 5. Wait for filesystem to settle, then relaunch silently ───────────────
timeout /t 3 /nobreak >nul
start "" /b "{current_exe}"

:: ── 6. Self-destruct ────────────────────────────────────────────────────────
(goto) 2>nul & del /f /q "%~f0"
"""

    with open(bat_path, "w") as f:
        f.write(bat_content)

    log("🔄 Spawning updater — the app will restart automatically.")

    if progress:
        progress.set_step("Installing…", "Waiting for app to close")
        progress.set_progress(0.95)

    # Launch bat completely hidden — no console window at all
    subprocess.Popen(
        ["cmd.exe", "/c", bat_path],
        creationflags=(
            subprocess.CREATE_NEW_PROCESS_GROUP |
            subprocess.DETACHED_PROCESS        |
            subprocess.CREATE_NO_WINDOW
        ),
        close_fds=True,
    )

    if progress:
        progress.finish("Restarting KPI Assistant…")
    time.sleep(2.5)
    os.kill(os.getpid(), 9)
