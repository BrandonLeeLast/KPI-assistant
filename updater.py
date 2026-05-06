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
_STUB_PATH    = os.path.join(_UPDATE_DIR, "swap.vbs")


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
    Write a VBScript stub — always executable on Windows, never blocked
    by execution policy or zone restrictions unlike PowerShell .ps1 files.
    Uses WMI to wait for PID death, then FileCopy to swap, then Shell to relaunch.
    """
    log_path   = os.path.join(_UPDATE_DIR, "swap.log")
    update_dir = _UPDATE_DIR

    # Build VBScript as plain string concatenation — avoids f-string/quote conflicts
    q = '"'  # double-quote shorthand for embedding in VBScript strings
    stub = (
        "Dim appPid, oldExe, newExe, logFile, updateDir\n"
        f"appPid    = {pid}\n"
        f"oldExe    = {q}{current_exe}{q}\n"
        f"newExe    = {q}{_STAGED_EXE}{q}\n"
        f"logFile   = {q}{log_path}{q}\n"
        f"updateDir = {q}{update_dir}{q}\n"
        "\n"
        "Dim fso, shell\n"
        "Set fso   = CreateObject(\"Scripting.FileSystemObject\")\n"
        "Set shell = CreateObject(\"WScript.Shell\")\n"
        "\n"
        "Sub Log(msg)\n"
        "    Dim f\n"
        "    Set f = fso.OpenTextFile(logFile, 8, True)\n"
        "    f.WriteLine Now & \" \" & msg\n"
        "    f.Close\n"
        "End Sub\n"
        "\n"
        "Log \"Swap stub started. Waiting for PID \" & appPid & \" to exit...\"\n"
        "\n"
        "Dim wmi, done\n"
        "Set wmi = GetObject(\"winmgmts://./root/cimv2\")\n"
        "done = False\n"
        "Do While Not done\n"
        "    Dim procs\n"
        "    Set procs = wmi.ExecQuery(\"SELECT * FROM Win32_Process WHERE ProcessId=\" & appPid)\n"
        "    If procs.Count = 0 Then\n"
        "        done = True\n"
        "    Else\n"
        "        WScript.Sleep 200\n"
        "    End If\n"
        "Loop\n"
        "\n"
        "Log \"PID gone. Settling 1 second...\"\n"
        "WScript.Sleep 1000\n"
        "\n"
        "Dim tempDir\n"
        "tempDir = shell.ExpandEnvironmentStrings(\"%TEMP%\")\n"
        "On Error Resume Next\n"
        "Dim tempFolders\n"
        "Set tempFolders = fso.GetFolder(tempDir).SubFolders\n"
        "Dim tf\n"
        "For Each tf In tempFolders\n"
        "    If Left(tf.Name, 4) = \"_MEI\" Then\n"
        "        Log \"Removing stale MEI folder: \" & tf.Name\n"
        "        fso.DeleteFolder tf.Path, True\n"
        "    End If\n"
        "Next\n"
        "On Error GoTo 0\n"
        "Log \"MEI cleanup done. Settling 500ms...\"\n"
        "WScript.Sleep 500\n"
        "\n"
        "shell.Run \"cmd.exe /c echo.>\"\"\" & newExe & \":Zone.Identifier\"\"\"\", 0, True\n"
        "Log \"Zone identifier cleared.\"\n"
        "\n"
        "Dim swapOk, copyCmd, copyRet\n"
        "swapOk  = False\n"
        "copyCmd = \"cmd.exe /c copy /y \"\"\" & newExe & \"\"\" \"\"\" & oldExe & \"\"\"\"\n"
        "copyRet = shell.Run(copyCmd, 0, True)\n"
        "\n"
        "If copyRet = 0 Then\n"
        "    Log \"cmd copy succeeded.\"\n"
        "    On Error Resume Next\n"
        "    fso.DeleteFile newExe, True\n"
        "    On Error GoTo 0\n"
        "    swapOk = True\n"
        "Else\n"
        "    Log \"cmd copy failed (exit \" & copyRet & \") - trying robocopy...\"\n"
        "    Dim srcDir, dstDir, fileName, roboCmd, roboRet\n"
        "    srcDir   = fso.GetParentFolderName(newExe)\n"
        "    dstDir   = fso.GetParentFolderName(oldExe)\n"
        "    fileName = fso.GetFileName(newExe)\n"
        "    roboCmd  = \"cmd.exe /c robocopy \"\"\" & srcDir & \"\"\" \"\"\" & dstDir & \"\"\" \"\"\" & fileName & \"\"\" /COPYALL /R:2 /W:1 /NFL /NDL /NJH /NJS\"\n"
        "    roboRet  = shell.Run(roboCmd, 0, True)\n"
        "    If roboRet <= 1 Then\n"
        "        Log \"robocopy succeeded (exit \" & roboRet & \").\"\n"
        "        On Error Resume Next\n"
        "        fso.DeleteFile newExe, True\n"
        "        On Error GoTo 0\n"
        "        swapOk = True\n"
        "    Else\n"
        "        Log \"robocopy failed (exit \" & roboRet & \"). All methods exhausted.\"\n"
        "    End If\n"
        "End If\n"
        "\n"
        "If swapOk And fso.FileExists(oldExe) Then\n"
        "    Log \"EXE in place. Relaunching: \" & oldExe\n"
        "    shell.Run Chr(34) & oldExe & Chr(34), 1, False\n"
        "Else\n"
        "    Log \"ERROR: Swap failed. Opening update folder for manual copy.\"\n"
        "    shell.Run \"explorer.exe \" & Chr(34) & updateDir & Chr(34), 1, False\n"
        "End If\n"
        "\n"
        "WScript.Sleep 500\n"
        "Log \"Stub complete.\"\n"
        "fso.DeleteFile WScript.ScriptFullName, True\n"
    )
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

    # Launch VBScript stub via wscript.exe — silent, no execution policy,
    # never zone-blocked, always available on Windows
    si = subprocess.STARTUPINFO()
    si.dwFlags    |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0  # SW_HIDE

    subprocess.Popen(
        ["wscript.exe", "//B", "//NoLogo", _STUB_PATH],
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
