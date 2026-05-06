"""
Auto-updater — modern approach.

Strategy:
  1. Async boot check against GitHub version.json
  2. Download new EXE to %APPDATA%/KPI-assistant/update/KPI_Assistant.exe
     (completely separate from the running EXE — no file lock conflict)
  3. Stop the watchdog and hotkey listener (releases all file handles)
  4. Write a PowerShell stub to %APPDATA%/KPI-assistant/update/swap.ps1
     The stub:
       - Waits for our PID to fully disappear from the process list
       - Uses os.rename()-equivalent (Move-Item) for an atomic swap on the same drive
       - Relaunches the updated EXE
       - Deletes itself
  5. Launch the PS1 stub detached (PowerShell is always present on Windows)
  6. Clean sys.exit(0) — lets Python/CTk/pystray teardown properly
     so there are zero lingering file handles when the stub runs
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

# Staging area — completely separate from the running EXE location
_APPDATA      = os.environ.get("APPDATA", os.path.expanduser("~"))
_UPDATE_DIR   = os.path.join(_APPDATA, "KPI-assistant", "update")
_STAGED_EXE   = os.path.join(_UPDATE_DIR, "KPI_Assistant.exe")
_STUB_PATH    = os.path.join(_UPDATE_DIR, "swap.ps1")


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
    Phase 1 — runs on a background thread:
      Download new EXE to the staging area.
      When done, call on_ready() which triggers Phase 2 on the main thread.

    Phase 2 — triggered by on_ready() on the main thread:
      Stop watcher + hotkey, write PS1 stub, launch it, sys.exit(0).
    """
    def log(msg):
        if on_progress:
            on_progress(msg)

    os.makedirs(_UPDATE_DIR, exist_ok=True)

    if progress:
        progress.set_step("Downloading update…", f"v{new_version}")
        progress.set_progress(0.05)

    try:
        log("⬇️  Downloading update...")

        def _reporthook(block_num, block_size, total_size):
            if progress and total_size > 0:
                pct = min(block_num * block_size / total_size, 1.0)
                progress.set_progress(0.05 + pct * 0.88)

        urllib.request.urlretrieve(download_url, _STAGED_EXE, reporthook=_reporthook)
        log("✅ Download complete.")

    except Exception as e:
        log(f"❌ Download failed: {e}")
        if progress:
            progress.set_step("Download failed", str(e))
        return

    if progress:
        progress.set_progress(0.95)
        progress.set_step("Ready to install", "Preparing swap script…")

    # Write the PowerShell stub now (while still on background thread — just file I/O)
    current_exe = os.path.abspath(sys.argv[0])
    pid         = os.getpid()
    _write_swap_stub(pid, current_exe)

    log("🔄 Swap script ready. Closing app to apply update…")

    if progress:
        progress.set_progress(1.0)
        progress.set_step("Installing…", "Closing KPI Assistant and applying update.")
        progress.finish()

    # Hand control back to the main thread for clean shutdown
    if on_ready:
        on_ready()


def _write_swap_stub(pid: int, current_exe: str) -> None:
    """
    Write a PowerShell script that:
      1. Waits for our PID to fully exit (process list check, not file lock)
      2. Atomically renames the staged EXE over the old one (same drive = atomic)
      3. Relaunches the updated EXE
      4. Deletes itself
    """
    log_path = os.path.join(_UPDATE_DIR, "swap.log")
    stub = f"""
# KPI Assistant swap stub — auto-generated, do not edit
# NOTE: avoid $pid — reserved in PowerShell for the current session PID
$appPid   = {pid}
$oldExe   = '{current_exe.replace("'", "''")}'
$newExe   = '{_STAGED_EXE.replace("'", "''")}'
$logFile  = '{log_path.replace("'", "''")}'
$stubSelf = $MyInvocation.MyCommand.Path

function Log($msg) {{
    $ts = Get-Date -Format 'HH:mm:ss'
    Add-Content -Path $logFile -Value "[$ts] $msg"
}}

Log "Swap stub started. Waiting for app PID $appPid to exit..."

# Wait for the app process to fully exit
while (Get-Process -Id $appPid -ErrorAction SilentlyContinue) {{
    Start-Sleep -Milliseconds 200
}}

Log "App process exited. Settling 1s..."
Start-Sleep -Milliseconds 1000

# Swap the EXE
try {{
    Move-Item -Path $newExe -Destination $oldExe -Force
    Log "Move-Item succeeded."
}} catch {{
    Log "Move-Item failed: $_ — trying Copy-Item fallback."
    Copy-Item -Path $newExe -Destination $oldExe -Force
    Remove-Item -Path $newExe -Force -ErrorAction SilentlyContinue
    Log "Copy-Item fallback done."
}}

if (Test-Path $oldExe) {{
    Log "EXE in place. Relaunching: $oldExe"
    Start-Process -FilePath $oldExe
}} else {{
    Log "ERROR: EXE not found at $oldExe after swap!"
}}

Start-Sleep -Milliseconds 500
Log "Stub complete. Self-destructing."
Remove-Item -Path $stubSelf -Force -ErrorAction SilentlyContinue
"""
    with open(_STUB_PATH, "w", encoding="utf-8") as f:
        f.write(stub.strip())


def launch_swap_and_exit(app) -> None:
    """
    Called on the main thread after download is confirmed.
    Stops all background services, launches the PS1 stub detached,
    then exits cleanly so Python releases every file handle.
    """
    # Stop watchdog + hotkey listener — releases all file handles
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

    # Launch PowerShell stub fully detached — no window, outlives this process
    si = subprocess.STARTUPINFO()
    si.dwFlags    |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0  # SW_HIDE

    subprocess.Popen(
        [
            "powershell.exe",
            "-NonInteractive",
            "-WindowStyle", "Hidden",
            "-ExecutionPolicy", "Bypass",
            "-File", _STUB_PATH,
        ],
        startupinfo=si,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )

    # destroy() flushes CTk/tkinter — then os._exit(0) guarantees the process
    # dies immediately so the PS1 stub's PID-wait loop exits cleanly
    try:
        app.destroy()
    except Exception:
        pass
    os._exit(0)
