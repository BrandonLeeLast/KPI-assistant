# Changelog

## v1.0.9
- Fixed installer hanging at 85% — background thread now returns after scheduling exit via after()
- Fixed double context dialog on screenshot capture — overlay guard flag prevents concurrent overlays
- Fixed Esc cancel not resetting overlay guard — cancel now signals app via on_captured(None)
- Replaced hotkey text input with keyboard recorder — click Record then press your combination

## v1.0.8
- Fixed update progress window hanging after download — removed grab_set() which was starving the Tk event loop
- Fixed progress bar and labels never updating — set_step/set_progress now schedule via parent.after() instead of win.after()
- Fixed app not closing after update — os._exit(0) now scheduled via after(2500) so finish() renders before exit
- Fixed race condition where download thread started before progress window widgets were built

## v1.0.7
- Fixed update process leaving old instance alive after install — replaced os.kill(pid, 9) with os._exit(0) (signal 9 is not SIGKILL on Windows)

## v1.0.6
- Added update progress bar window showing download percentage and install stages
- Fixed update hanging after download — progress window now uses CTkToplevel on the main thread instead of a second CTk root (which deadlocked on background threads)

## v1.0.5
- Added built-in screenshot capture tool with global hotkey (default: Ctrl+Shift+S)
- Fullscreen dark overlay with drag-to-select region and live W×H size indicator
- Screenshot hotkey customisable from Configuration tab — applies without restart
- Non-intrusive tray balloon notification when image fails to process
- Fixed version label always showing v0.0.0 in bundled EXE — now reads from sys._MEIPASS
- Fixed update check incorrectly triggering on every launch due to stale version read

## v1.0.4
- Fixed version label always showing v0.0.0 — now reads correctly from sys._MEIPASS when bundled
- Fixed update check incorrectly triggering on every launch due to stale version read
- Improved hot-swap bat — polls for _MEI DLL release before launching new EXE
- Reverted runtime_tmpdir to None (env var expansion not supported by PyInstaller spec)

## v1.0.3
- Fixed file handle leak preventing deletion of processed screenshots from watch folder
- Fixed context dialog thumbnail holding file handle open for duration of dialog

## v1.0.2
- Fixed file handle leak — watch folder files can now be deleted after processing
- Fixed PyInstaller DLL error after auto-update (stable runtime dir in APPDATA)
- Improved hot-swap updater bat — cleans stale runtime folder before restarting
- Custom STAR context dialog with screenshot thumbnail (replaces pyautogui prompt)
- Removed pyautogui dependency

## v1.0.1
- Modern CustomTkinter UI — rounded buttons, stat cards, animated pulse indicator
- Processed image registry moved to %APPDATA%/KPI-assistant/processed_log.json
- JSON registry replaces plain text log — O(1) lookups, timestamps, category stored
- Migrated to google-genai SDK (gemini-2.0-flash)
- Refactored into clean package structure (app/, app/ui/)
- GitHub Actions CI/CD — auto-bumps patch version on every push to main
- Auto-updater with hot-swap EXE batch script

## v1.0.0
- Initial release
- ShareX folder monitoring with watchdog
- Gemini Flash image classification into STAR-method KPA folders
- Dark-theme tkinter dashboard with system tray integration
