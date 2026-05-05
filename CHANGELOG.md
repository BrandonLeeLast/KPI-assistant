# Changelog

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
