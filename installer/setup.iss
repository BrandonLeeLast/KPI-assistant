; KPI Assistant — Inno Setup installer script

#define MyAppName      "KPI Assistant"
#define MyAppPublisher "Brandon Lee"
#define MyAppURL       "https://github.com/BrandonLeeLast/KPI-assistant"
#define MyAppExeName   "KPI_Assistant.exe"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

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
DisableDirPage=no
AllowNoIcons=yes
; Output
OutputDir=..\dist
OutputBaseFilename=KPI_Assistant_Setup
; Compression
Compression=lzma2/ultra64
SolidCompression=yes
; Branding
WizardStyle=modern
WizardImageFile=wizard.bmp
WizardSmallImageFile=wizard_small.bmp
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
; No UAC
PrivilegesRequired=lowest
; Add/Remove Programs
UninstallDisplayName={#MyAppName}
; Version info embedded in Setup EXE
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
WelcomeLabel1=Welcome to KPI Assistant Setup
WelcomeLabel2=Born to explore the cosmos. Forced to watch C:\Users\User\KPI_Proof.%n%nThis wizard will install KPI Assistant on your computer. Click Next to continue.
FinishedLabel=KPI Assistant has been installed. Your evidence folder awaits.%n%nBorn to explore the cosmos. Forced to watch KPI_Proof.

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}";           Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";     Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill.exe"; Parameters: "/f /im {#MyAppExeName}"; Flags: runhidden; RunOnceId: "KillApp"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssInstall then
    Exec('taskkill.exe', '/f /im {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;
