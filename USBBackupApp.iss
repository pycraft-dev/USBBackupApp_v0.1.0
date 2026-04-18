; Inno Setup 6 — шаблон установщика USB Backup App
; Компиляция: ISCC.exe USBBackupApp.iss (из корня репозитория)
; Требуется предварительно собранный source\dist\USBBackupApp.exe

#define MyAppName "USB Backup App"
#define MyAppVersion "1.0"
#define MyAppPublisher "pycraft-dev"

[Setup]
AppId={{E4B8F2A1-6C0D-4F3E-9A7B-2D1E8F5C3A90}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=installer_output
OutputBaseFilename=USBBackupApp_Setup_{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "source\dist\USBBackupApp.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "README_RU.md"; DestDir: "{app}"; DestName: "README_КЛИЕНТУ.md"; Flags: ignoreversion
Source: "README_CLIENT.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion
Source: "docs\CHANGELOG.md"; DestDir: "{app}"; DestName: "CHANGELOG.md"; Flags: ignoreversion
Source: "SUPPORT.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "config\app_state.json.example"; DestDir: "{app}\config"; Flags: ignoreversion
Source: "screenshots\*"; DestDir: "{app}\screenshots"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\USBBackupApp.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\USBBackupApp.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\USBBackupApp.exe"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
