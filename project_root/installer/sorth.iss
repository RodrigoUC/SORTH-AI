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
AppName=SORTH-AI
AppVersion={#AppVersion}
AppVerName=SORTH-AI {#BuildId} (unsigned review)
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
SetupIconFile=..\assets\sorth.ico
WizardImageFile=branding\wizard.png
WizardSmallImageFile=branding\mark.png
DisableWelcomePage=no
AppPublisherURL=https://github.com/RodrigoUC/SORTH-AI
AppSupportURL=https://github.com/RodrigoUC/SORTH-AI/issues
VersionInfoDescription=SORTH-AI Setup (unsigned review)
VersionInfoProductName=SORTH-AI
VersionInfoProductVersion={#AppVersion}
VersionInfoProductTextVersion={#BuildId}
UninstallDisplayIcon={app}\SORTH.exe
CloseApplications=no
RestartApplications=no
UsePreviousAppDir=no
[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
[Messages]
spanish.WelcomeLabel2=Este asistente instalará [name/ver] para su usuario.%n%nCompilación de revisión sin firma digital. El nombre y los iconos no verifican al editor ni eliminan las advertencias de Windows.%n%nLa sesión y sus copias se conservan al reinstalar o desinstalar.
english.WelcomeLabel2=This wizard installs [name/ver] for your user account.%n%nUnsigned review build. The name and icons do not verify the publisher or remove Windows warnings.%n%nYour session and backups are retained when reinstalling or uninstalling.
[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
[Icons]
Name: "{userprograms}\SORTH-AI {#BuildId}"; Filename: "{app}\SORTH.exe"; WorkingDir: "{app}"; IconFilename: "{app}\SORTH.exe"; AppUserModelID: "SORTH.App"; Comment: "SORTH-AI ({#BuildId})"
Name: "{userdesktop}\SORTH-AI {#BuildId}"; Filename: "{app}\SORTH.exe"; WorkingDir: "{app}"; IconFilename: "{app}\SORTH.exe"; AppUserModelID: "SORTH.App"; Comment: "SORTH-AI ({#BuildId})"; Tasks: desktopicon
; No Registry, Run, InstallDelete or UninstallDelete sections; no data cleanup.
