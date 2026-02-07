#define AppName "IG Tracker"
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\\..\\release\\windows\\stage"
#endif

[Setup]
AppId={{B95E1E86-96D2-433E-8BF0-EAB2041EAEE9}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=IG Tracker
DefaultDirName={localappdata}\Programs\IG Tracker
DefaultGroupName=IG Tracker
DisableProgramGroupPage=no
OutputDir=..\..\release\windows
OutputBaseFilename=ig-tracker-setup-v{#AppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\ig-tracker-gui.exe

[Tasks]
Name: "traystartup"; Description: "Run tray app at Windows startup"; GroupDescription: "Startup options:"

[Files]
Source: "{#SourceDir}\ig-tracker-gui.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\ig-tracker-tray.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\ig-tracker-cli.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\ig-tracker-report.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\ig-tracker-db-tools.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\.env.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\.env.example"; DestDir: "{app}"; DestName: ".env"; Flags: onlyifdoesntexist
Source: "{#SourceDir}\docs\*"; DestDir: "{app}\docs"; Flags: recursesubdirs createallsubdirs ignoreversion

[Dirs]
Name: "{app}\reports"
Name: "{app}\exports"

[Icons]
Name: "{group}\IG Tracker GUI"; Filename: "{app}\ig-tracker-gui.exe"
Name: "{group}\IG Tracker Tray"; Filename: "{app}\ig-tracker-tray.exe"
Name: "{group}\README"; Filename: "{app}\README.md"
Name: "{userstartup}\IG Tracker Tray"; Filename: "{app}\ig-tracker-tray.exe"; Tasks: traystartup

[Run]
Filename: "{app}\ig-tracker-gui.exe"; Description: "Launch IG Tracker GUI"; Flags: nowait postinstall skipifsilent
