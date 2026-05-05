# Changelog

## v1.0.15
- Complete updater rewrite using PowerShell PID-wait swap approach
- New EXE downloaded to %APPDATA%/KPI-assistant/update/ (never touches running EXE)
- Watchdog, hotkey listener and tray stopped before exit so zero lingering file handles
- PowerShell stub waits for PID to fully disappear from process list then does atomic rename
- Falls back to copy+delete if cross-volume rename fails (antivirus edge case)
- Clean sys.exit(0) instead of os.kill or os._exit — proper Python/CTk teardown
- App relaunches automatically after swap completes

## v1.0.14
- Fixed config tab section headers taking up too much vertical space — now fixed 24px height
- Fixed mouse wheel scroll not working on config tab — binds to all child widgets after build
- Fixed scroll speed too slow — increased from 1 to 3 units per wheel tick

## v1.0.13
- Completely replaced hot-swap updater with simple desktop download — no more bat scripts, no file locking, no process killing
- Update now downloads new EXE to Desktop as KPI_Assistant_v{version}.exe, opens Desktop in Explorer, and shows "close and run" instructions
- Progress window now shows a dismissable OK button after download completes

## v1.0.12
- Full skills matrix injected into AI prompt per developer level — AI now classifies against actual KPA criteria, not just category names
- Added skills matrix text files for all levels: Intern, Graduate, Junior, Intermediate, Senior, Tech Lead
- Added Tech Lead level with Team Management KPA (exclusive to that level)
- AI prompt now includes role description, KPA criteria, subcategories and evidence examples for the selected level
- Category matching now fuzzy-validates against the level's actual applicable KPAs
- Level selector changed from segmented button to dropdown to accommodate all 6 levels

## v1.0.11
- Added "Show context window" toggle — disable for zero-friction silent processing
- Added independent notification toggles for success and failure events
- Fixed auto-updater stuck at 85% — replaced close_fds+DETACHED_PROCESS with STARTUPINFO SW_HIDE
- Multi-provider AI: Gemini, Claude, OpenAI, Ollama — model and key configurable per provider
- Full config overhaul: 6 sections, editable KPA categories, custom prompt, capture format, notifications

## v1.0.10
- Fixed update progress window hanging — removed grab_set() which was starving the Tk event loop
- Fixed progress bar and labels never updating — now schedule via parent.after()
- Fixed installer stuck at 85% — background thread now returns after scheduling exit
- Fixed double context dialog on screenshot capture — overlay guard flag prevents concurrent overlays
- Fixed Esc cancel not resetting overlay guard
- Replaced hotkey text input with keyboard recorder

## v1.0.9
- Added update progress bar window showing download percentage and install stages
- Fixed update process leaving old instance alive — replaced os.kill(pid, 9) with os._exit(0)

## v1.0.8
- Fixed auto-updater stuck after download — bat now wipes both _MEIPASS and APPDATA runtime folders
- Fixed two CMD windows appearing after update — using STARTUPINFO SW_HIDE and start /b

## v1.0.7
- Fixed version label always showing v0.0.0 in bundled EXE — now reads from sys._MEIPASS
- Fixed update check incorrectly triggering on every launch due to stale version read

## v1.0.6
- Added built-in screenshot capture tool with global hotkey (default: Ctrl+Shift+S)
- Fullscreen dark overlay with drag-to-select region and live W×H size indicator
- Screenshot hotkey customisable from Configuration tab — applies without restart
- Non-intrusive tray balloon notification when image fails to process

## v1.0.5
- Fixed PyInstaller DLL error after auto-update
- Improved hot-swap bat — polls for _MEI DLL release before launching new EXE

## v1.0.4
- Fixed file handle leak preventing deletion of processed screenshots from watch folder
- Fixed context dialog thumbnail holding file handle open for duration of dialog
- Custom STAR context dialog with screenshot thumbnail (replaces pyautogui prompt)

## v1.0.3
- Fixed file handle leak — watch folder files can now be deleted after processing
- Improved hot-swap updater bat — cleans stale runtime folder before restarting

## v1.0.2
- Modern CustomTkinter UI — rounded buttons, stat cards, animated pulse indicator
- Processed image registry moved to %APPDATA%/KPI-assistant/processed_log.json
- Migrated to google-genai SDK (gemini-2.0-flash)
- Refactored into clean package structure (app/, app/ui/)

## v1.0.1
- GitHub Actions CI/CD — auto-bumps patch version on every push to main
- Auto-updater with hot-swap EXE batch script
- Dark-theme tkinter dashboard with system tray integration

## v1.0.0
- Initial release
- Folder monitoring with watchdog
- Gemini Flash image classification into STAR-method KPA folders
