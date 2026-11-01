#define MyAppName "Minecraft Auto Advertiser"
#define MyAppVersion "1.0.0"
#define MyAppExeName "MinecraftAutoAdvertiser.exe"

[Setup]
AppId={{8E8F3E2A-5D7B-4C64-9D70-AAD161F6D0AD}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Minecraft Auto Advertiser
DefaultDirName={localappdata}\Programs\MinecraftAutoAdvertiser
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=MinecraftAutoAdvertiser-Setup-{#MyAppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; Flags: unchecked

[Files]
Source: "..\dist\MinecraftAutoAdvertiser.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Uygulamayı aç"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; App data is intentionally preserved. Remove startup preference in Settings before uninstall.
