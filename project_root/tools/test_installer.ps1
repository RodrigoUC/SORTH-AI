# Disposable Windows CI runner only. Never execute against an existing user profile.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Installer lifecycle test requires disposable CI.' }
Set-Location (Join-Path $PSScriptRoot '..')
. (Join-Path $PSScriptRoot 'installer_test_helpers.ps1')
$installer = Get-ChildItem build/artifacts/*-setup.exe
if (@($installer).Count -ne 1) { throw 'Expected exactly one installer.' }
$info = Get-Content build/artifacts/build-info.json -Raw | ConvertFrom-Json
if ($info.build_id -notmatch '^[0-9]+\.[0-9]+\.[0-9]+-[0-9a-f]{12}$') { throw 'Unexpected build identity.' }
$uninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\SORTH-$($info.build_id)_is1"
if (Test-Path -LiteralPath $uninstallKey) { throw 'Refusing to replace an existing uninstall record.' }
$shortcutName = "SORTH-AI $($info.build_id).lnk"
$startShortcut = Join-Path ([Environment]::GetFolderPath('Programs')) $shortcutName
$desktopShortcut = Join-Path ([Environment]::GetFolderPath('DesktopDirectory')) $shortcutName
foreach ($shortcutPath in @($startShortcut, $desktopShortcut)) {
    if (Test-Path -LiteralPath $shortcutPath) { throw 'Refusing to replace an existing shortcut.' }
}
$testStarted = Get-Date
$root = Join-Path $env:RUNNER_TEMP ('sorth-installer-' + [guid]::NewGuid())
$destination = Join-Path $root 'application'
$dataDir = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'SORTH'
if (Test-Path $dataDir) { throw 'Refusing to use a pre-existing data directory.' }
New-Item -ItemType Directory $dataDir | Out-Null
$sentinel = Join-Path $dataDir 'installer-retention-sentinel.txt'
'preserve synthetic user data' | Set-Content $sentinel
$originalHash = (Get-FileHash $sentinel).Hash
function Check-Data {
    if (-not (Test-Path $sentinel) -or (Get-FileHash $sentinel).Hash -ne $originalHash) { throw 'Installer changed user data.' }
}
function Get-ShortcutEvidence([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return @{path=$path; exists=$false} }
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($path)
    $explorer = New-Object -ComObject Shell.Application
    $folder = $explorer.Namespace((Split-Path -Parent $path))
    $item = $folder.ParseName((Split-Path -Leaf $path))
    return @{path=$path; exists=$true; target=$shortcut.TargetPath;
        working_directory=$shortcut.WorkingDirectory; icon=$shortcut.IconLocation;
        description=$shortcut.Description; app_user_model_id=$item.ExtendedProperty('System.AppUserModel.ID')}
}
function Check-IconPath([string]$icon, [string]$expected) {
    # Windows may serialize the default icon as a bare path or a path plus ,0.
    $iconPath = ($icon -replace ',0$', '').Trim('"')
    if ($iconPath -ine $expected) { throw "Unexpected native icon: $icon" }
}
function Check-Shortcut($evidence, [string]$exe) {
    if (-not $evidence.exists) { throw "Missing installed shortcut: $($evidence.path)" }
    if ($evidence.target -ine $exe) { throw 'Shortcut target does not match installed executable.' }
    if ($evidence.working_directory -ine $destination) { throw 'Shortcut working directory does not match install directory.' }
    Check-IconPath $evidence.icon $exe
    if ($evidence.app_user_model_id -cne 'SORTH.App') { throw 'Shortcut AppUserModelID mismatch.' }
    if ($evidence.description -notlike 'SORTH-AI*') { throw 'Shortcut description identity mismatch.' }
}
function Check-NativeIdentity([string]$stage, [bool]$expectDesktop = $false) {
    $exe = (Get-Item -LiteralPath (Join-Path $destination 'SORTH.exe')).FullName
    $appVersion = (Get-Item -LiteralPath $exe).VersionInfo
    $setupVersion = $installer.VersionInfo
    $record = Get-ItemProperty -LiteralPath $uninstallKey -ErrorAction Stop
    $start = Get-ShortcutEvidence $startShortcut
    $desktop = Get-ShortcutEvidence $desktopShortcut
    # Record actual native values before asserting, including the failing surface.
    @{stage=$stage; executable=@{path=$exe; product_name=$appVersion.ProductName;
          file_description=$appVersion.FileDescription};
      setup=@{product_name=$setupVersion.ProductName; file_description=$setupVersion.FileDescription};
      registration=@{display_name=$record.DisplayName; display_icon=$record.DisplayIcon};
      start_menu=$start; desktop=$desktop; desktop_expected=$expectDesktop} |
        ConvertTo-Json -Depth 5 | Set-Content "build/reports/native-identity-$stage.json"
    if ($appVersion.ProductName -cne 'SORTH-AI') { throw 'Installed EXE product identity mismatch.' }
    if ($appVersion.FileDescription -cne 'SORTH-AI - Sistema de Organizacion de Horarios') { throw 'Installed EXE description identity mismatch.' }
    # Inno stores fixed-width version strings padded with trailing ASCII spaces.
    # Keep the raw resource above; normalize only that padding for comparison.
    if ($setupVersion.ProductName.TrimEnd(' ') -cne 'SORTH-AI') { throw 'Setup product identity mismatch.' }
    if ($record.DisplayName -cne "SORTH-AI $($info.build_id) (unsigned review)") { throw 'Registered display name mismatch.' }
    Check-IconPath $record.DisplayIcon $exe
    Check-Shortcut $start $exe
    if ($expectDesktop) { Check-Shortcut $desktop $exe }
    elseif ($desktop.exists) { throw 'Default installation unexpectedly created a desktop shortcut.' }
}
function Run-Checked($exe, $arguments) {
    # Resolve to a native, existing absolute path before crossing the Win32 boundary.
    $exe = (Get-Item -LiteralPath $exe -ErrorAction Stop).FullName
    $p = Start-Process -FilePath $exe -ArgumentList $arguments -PassThru
    if (-not $p.WaitForExit(180000)) { $p.Kill(); throw 'Installer lifecycle step timed out.' }
    if ($p.ExitCode -ne 0) { throw "Installer lifecycle exit $($p.ExitCode)." }
}
function Get-TestUninstaller([string]$stage) {
    $record = Get-ItemProperty -LiteralPath $uninstallKey -ErrorAction Stop
    # Preserve evidence even when path validation fails, rather than guessing why.
    @{stage=$stage; registry_key=$uninstallKey; install_location=$record.InstallLocation;
      uninstall_command=$record.UninstallString;
      files=@(Get-ChildItem -LiteralPath $destination | ForEach-Object {
          @{name=$_.Name; length=$_.Length; attributes=$_.Attributes.ToString();
            sha256=$(if (-not $_.PSIsContainer -and $_.Name -like 'unins*') { (Get-FileHash -LiteralPath $_.FullName).Hash })}
      })} |
        ConvertTo-Json -Depth 4 | Set-Content "build/reports/uninstaller-$stage.json"
    try {
        return Resolve-TestUninstaller $record $destination
    } catch {
        # Read-only failure evidence; never alter Defender or other protections.
        $validationError = $_
        try {
            Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Windows Defender/Operational'; StartTime=$testStarted} -ErrorAction Stop |
                Where-Object { $_.Message -like "*$root*" } |
                Select-Object TimeCreated, Id, Message | ConvertTo-Json -Depth 3 |
                Set-Content "build/reports/defender-$stage.json"
        } catch {
            "Defender evidence unavailable: $($_.Exception.Message)" | Set-Content "build/reports/defender-$stage.txt"
        }
        throw $validationError
    }
}
function Uninstall-TestBuild([string]$stage) {
    $exe = Get-TestUninstaller $stage
    Run-Checked $exe @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/LOG=`"$PWD/build/reports/uninstall-$stage.log`"")
    if (Test-Path -LiteralPath (Join-Path $destination 'SORTH.exe')) { throw 'Uninstall left the installed executable.' }
    if (Test-Path -LiteralPath $uninstallKey) { throw 'Uninstall left the registered build.' }
    Check-Data
    $remainingShortcuts = @(@($startShortcut, $desktopShortcut) | Where-Object { Test-Path -LiteralPath $_ })
    @{stage=$stage; remaining_shortcuts=$remainingShortcuts; user_data_retained=$true;
      sentinel_sha256=(Get-FileHash -LiteralPath $sentinel).Hash} |
        ConvertTo-Json -Depth 3 | Set-Content "build/reports/native-cleanup-$stage.json"
    if ($remainingShortcuts.Count -ne 0) { throw 'Uninstall left a build-owned shortcut.' }
}
try {
    # Install and idempotent re-install of the same exact reviewed build.
    foreach ($attempt in 1..2) {
        Run-Checked $installer.FullName @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/DIR=`"$destination`"", "/LOG=`"$PWD/build/reports/install-$attempt.log`"")
        if (-not (Test-Path "$destination/SORTH.exe")) { throw 'Installed executable missing.' }
        Check-NativeIdentity "install-$attempt"
        Get-TestUninstaller "install-$attempt" | Out-Null
        Check-Data
    }
    Get-TestUninstaller 'before-smoke' | Out-Null
    $oldPath = $env:PATH
    $oldPythonHome = $env:PYTHONHOME
    $oldPythonPath = $env:PYTHONPATH
    try {
        $env:PATH = "$env:SystemRoot/System32;$env:SystemRoot"
        $env:PYTHONHOME = $null
        $env:PYTHONPATH = $null
        $smokeDir = Join-Path $PWD 'build/reports/installed-smoke'
        Run-Checked "$destination/SORTH.exe" @('--smoke-test', '--smoke-output', "`"$smokeDir`"")
        $report = Get-Content "$smokeDir/smoke-result.json" -Raw | ConvertFrom-Json
        if (-not $report.ok -or -not $report.frozen) { throw 'Installed workflow failed.' }
        foreach ($phase in @('startup', 'es', 'en')) {
            if (-not $report.text_rendering.$phase.ok) { throw "Missing installed readable text evidence: $phase." }
        }
    } finally {
        $env:PATH = $oldPath
        $env:PYTHONHOME = $oldPythonHome
        $env:PYTHONPATH = $oldPythonPath
    }
    Get-TestUninstaller 'after-smoke' | Out-Null
    Uninstall-TestBuild 'first'
    # Reinstall recovery checks package-level rollback mechanics only. A real
    # prior-version + current-schema compatibility exercise remains required.
    Run-Checked $installer.FullName @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/DIR=`"$destination`"", '/TASKS="desktopicon"', "/LOG=`"$PWD/build/reports/install-recovery.log`"")
    Check-Data
    if (-not (Test-Path "$destination/SORTH.exe")) { throw 'Recovery reinstall failed.' }
    Check-NativeIdentity 'recovery' $true
    Uninstall-TestBuild 'recovery'
    @{ok=$true; install=$true; same_build_reinstall=$true; uninstall_retains_data=$true; recovery_reinstall=$true; isolated_path=$true; native_identity=$true; default_desktop_absent=$true; opt_in_desktop=$true; shortcut_cleanup=$true; clean_pc_without_python='NOT TESTED'; cross_version_rollback='NOT TESTED'} | ConvertTo-Json | Set-Content build/reports/installer-lifecycle.json
} finally {
    # Delete only the exact synthetic file created here, never the data folder.
    Remove-Item -LiteralPath $sentinel -ErrorAction SilentlyContinue
}
