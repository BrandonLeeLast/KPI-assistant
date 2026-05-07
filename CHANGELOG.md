# Changelog

## v1.0.46
- Renamed app to KPEye — new logo in topbar, tray, and installer wizard
- APPDATA path changed to %APPDATA%\KPEye (clean install, no legacy data)
- Per-provider API key storage — switching providers swaps the key field independently
- Label changes to "AI URL" for Cloudflare, Ollama, and Custom URL providers
- Model field hidden for Custom URL provider
- Deploy Cloudflare Worker button hidden for Custom URL provider
- Worker URL now parsed directly from wrangler deploy output (no more hanging on whoami)
- Installer wizard panel uses KPEye logo, text overlay removed

## v1.0.38
- Switched worker template to Gemma 4 26B (@cf/google/gemma-4-26b-a4b-it) — no license acceptance required
- Added worker version tracking — shows "Update Worker" button when new template version available
- Worker GET /version endpoint for version checking
- Removed "KPI Worker" option — all users deploy their own private Cloudflare Worker (free)
- Model field hidden for Cloudflare provider (uses fixed gemma-4-26b-a4b-it in worker template)
- Fixed User-Agent blocking — added `KPI-Assistant/1.0 (Windows)` header to prevent CF bot detection (error 1010)
- Default provider changed to Cloudflare
- Deployment wizard now reads URL from wrangler config + tests worker after deploy
- wrangler deploy shows console window with live progress output

## v1.0.32
- Fixed Node.js not detected in deployed EXE — PyInstaller strips PATH, now injects common install locations at runtime
- Supports standard installer (C:\Program Files\nodejs) and nvm for Windows (scans %APPDATA%\nvm\v* versioned dirs)
- Added app.worker_deploy and app.ui.worker_wizard to PyInstaller hiddenimports so wizard bundles correctly
- Removed AUTH_TOKEN from worker — each user's private worker URL is sufficient, no token needed

## v1.0.31
- Added one-click "Deploy My Own AI Worker" wizard — deploys user's private Cloudflare Worker from template repo
- Wizard handles: Node.js check, template download, npm install, CF login, AUTH_TOKEN secret, wrangler deploy, URL detection
- Deploy button appears automatically when Cloudflare or Custom URL provider is selected
- Worker URL + token saved to config automatically after successful deploy
- Removed hardcoded worker URL — every user gets their own private worker on their CF account
- Worker template uses Cloudflare Workers AI (llama-3.2-11b-vision) — no external API calls

## v1.0.29
- KPI Worker set as default provider — zero config for end users, no API key needed
- Auth token baked into EXE at build time via GitHub secret KPI_WORKER_TOKEN
- Config tab hides model/API key fields when KPI Worker selected, shows managed badge instead
- Added app/secrets.py — reads token from PyInstaller bundle, falls back to env var for dev
- _token.txt gitignored — never committed, injected by CI only

## v1.0.28
- Added Cloudflare Worker provider — deploy worker.js to CF, paste URL as API key, your Gemini key never leaves Cloudflare
- Added Custom URL provider — any endpoint accepting {image_base64, prompt, model} and returning {response}
- Optional auth token support for both: paste URL|token in the API key field
- Dynamic API key hint changes based on selected provider
- Added Docs button to dashboard — opens developer wiki
- Fixed CMD windows flashing when Ollama setup runs Docker commands
- Fixed context cancel now skips AI entirely — screenshot not filed, not marked processed

## v1.0.27
- Fixed Ollama model pull timeout — bumped from 120s to 300s for CPU-only setups
- Warns user that first Ollama call may take 30-60s while model loads into RAM
- Fixed Ollama setup CMD windows flashing — all subprocess calls now use CREATE_NO_WINDOW

## v1.0.26
- Switched to proper Inno Setup Windows installer — installs to %LocalAppData%\Programs\KPI-assistant
- No UAC prompt required (user-level install)
- Creates Start Menu shortcut + optional Desktop shortcut
- Registers in Add/Remove Programs with uninstaller
- Auto-updater now downloads KPI_Assistant_Setup.exe and runs /VERYSILENT
- Only installer published to GitHub Releases — raw EXE removed
- Custom wizard branding with sad robot image, app icon generated in CI
- Fixed Ollama model pull charmap crash — UTF-8 with errors=replace, ANSI codes stripped

## v1.0.25
- Fixed "name BG2 is not defined" crash on startup
- Fixed Python 3.14 syntax error in updater.py — VBScript stub built with string concatenation
- Fixed Permission denied on CopyFile — swap now uses cmd /c copy then robocopy as fallbacks
- Added Zone.Identifier strip before copy to unblock downloaded EXEs

## v1.0.24
- Fixed "Permission denied" on CopyFile during update swap — xcopy then robocopy fallbacks

## v1.0.23
- Fixed python3xx.dll not found on launch — cleans stale _MEI folders from TEMP on startup
- Added one-click Ollama setup in Configuration tab
- Updated Gemini model list to verified working models — removed deprecated 1.5-pro/flash
- Default Gemini model changed to gemini-2.5-flash
- Added clear error messages for 429, 404, 401 errors with actionable tips

## v1.0.22
- Fixed config tab scroll — enter/leave canvas bind_all approach
- Improved evidence txt file format — structured layout with all metadata

## v1.0.21
- Fixed python3xx.dll not found after update — VBScript stub cleans _MEI folders before relaunch

## v1.0.20
- Test release — VBScript swap stub verification

## v1.0.19
- Replaced PowerShell swap stub with VBScript — never blocked by execution policy
- Uses WMI Win32_Process to wait for PID death
- Swap stub auto-elevates to admin if needed

## v1.0.18
- AI Provider and Model changed to dropdowns with known model lists
- "Other (type below)" reveals custom text input
- All selections persist to config.ini on Save

## v1.0.17
- Fixed app not relaunching after update — $pid is reserved in PowerShell, renamed to $appPid
- Added swap.log for diagnosing update issues

## v1.0.16
- Fixed update progress window X button
- Fixed process not dying after update — app.destroy() + os._exit(0)

## v1.0.15
- Complete updater rewrite — installer-based update flow

## v1.0.14
- Fixed config tab section headers height
- Fixed mouse wheel scroll on config tab

## v1.0.13
- Switched to desktop download approach for updates

## v1.0.12
- Full skills matrix injected into AI prompt per developer level
- Added skills matrix for all levels: Intern, Graduate, Junior, Intermediate, Senior, Tech Lead
- Tech Lead level with Team Management KPA

## v1.0.11
- Show context window toggle — zero-friction silent processing
- Multi-provider AI: Gemini, Claude, OpenAI, Ollama

## v1.0.10
- Fixed update progress window hanging
- Fixed double context dialog on screenshot capture
- Replaced hotkey text input with keyboard recorder

## v1.0.9
- Added update progress bar window
- Fixed update process leaving old instance alive

## v1.0.8
- Fixed auto-updater stuck after download

## v1.0.7
- Fixed version label always showing v0.0.0

## v1.0.6
- Added built-in screenshot capture tool with global hotkey
- Fullscreen dark overlay with drag-to-select region

## v1.0.5
- Fixed PyInstaller DLL error after auto-update

## v1.0.4
- Fixed file handle leak
- Custom STAR context dialog with screenshot thumbnail

## v1.0.3
- Fixed file handle leak preventing watch folder deletion

## v1.0.2
- Modern CustomTkinter UI
- Migrated to google-genai SDK

## v1.0.1
- GitHub Actions CI/CD — auto-bumps patch version
- Auto-updater with hot-swap EXE batch script

## v1.0.0
- Initial release
- Folder monitoring with watchdog
- Gemini Flash image classification into STAR-method KPA folders
