; Review-only per-user installation. Never touch SORTH session or backups.
#ifndef BuildId
  #error BuildId is required
#endif
#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef PayloadDir
  #error PayloadDir is required
#endif
#ifndef OutputPath
  #error OutputPath is required
#endif
[Setup]
; Separate uninstall record per exact build permits side-by-side rollback.
AppId=SORTH-{#BuildId}
AppName=SORTH
AppVersion={#AppVersion}
AppVerName=SORTH {#BuildId} (unsigned review)
DefaultDirName={localappdata}\Programs\SORTH\{#BuildId}
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputPath}
OutputBaseFilename=SORTH-{#BuildId}-windows-x64-unsigned-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\SORTH.exe
CloseApplications=no
RestartApplications=no
UsePreviousAppDir=no
[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{userprograms}\SORTH {#BuildId}"; Filename: "{app}\SORTH.exe"; WorkingDir: "{app}"
; No Registry, Run, InstallDelete or UninstallDelete sections; no data cleanup.
