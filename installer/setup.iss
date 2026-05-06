; KPI Assistant — Inno Setup installer script
; Builds a proper Windows installer that:
;   - Installs to %LocalAppData%\Programs\KPI-assistant (no UAC required)
;   - Creates Start Menu shortcut
;   - Optionally creates Desktop shortcut
;   - Registers in Add/Remove Programs with uninstaller
;   - Supports silent install via /SILENT or /VERYSILENT flags
;   - Works with the app's auto-updater (downloads new Setup EXE, runs /VERYSILENT)

#define MyAppName      "KPI Assistant"
#define MyAppPublisher "Brandon Lee"
#define MyAppURL       "https://github.com/BrandonLeeLast/KPI-assistant"
#define MyAppExeName   "KPI_Assistant.exe"
#define MyAppVersion   GetFileVersion("..\dist\KPI_Assistant.exe")

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
; Install to LocalAppData\Programs — no UAC prompt needed
DefaultDirName={localappdata}\Programs\KPI-assistant
DefaultGroupName={#MyAppName}
; Allow user to choose install dir
DisableDirPage=no
; Desktop shortcut page
AllowNoIcons=yes
; Output
OutputDir=..\dist
OutputBaseFilename=KPI_Assistant_Setup
; Compression
Compression=lzma2/ultra64
SolidCompression=yes
; Appearance
WizardStyle=modern
WizardSmallImageFile=icon_small.bmp
; No UAC elevation needed (user-level install)
PrivilegesRequired=lowest
; Uninstall
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
; Version info
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Installer

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; Main EXE
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}";        Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
; Desktop (optional, unchecked by default)
Name: "{autodesktop}\{#MyAppName}";  Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Offer to launch after install
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Kill the app if running before uninstall
Filename: "taskkill.exe"; Parameters: "/f /im {#MyAppExeName}"; Flags: runhidden; RunOnceId: "KillApp"

[Code]
// Kill any running instance before upgrading (silent installs)
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssInstall then
    Exec('taskkill.exe', '/f /im {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;
