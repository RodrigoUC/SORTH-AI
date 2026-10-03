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
}
try {
    # Install and idempotent re-install of the same exact reviewed build.
    foreach ($attempt in 1..2) {
        Run-Checked $installer.FullName @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/DIR=`"$destination`"", "/LOG=`"$PWD/build/reports/install-$attempt.log`"")
        if (-not (Test-Path "$destination/SORTH.exe")) { throw 'Installed executable missing.' }
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
    Run-Checked $installer.FullName @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/DIR=`"$destination`"", "/LOG=`"$PWD/build/reports/install-recovery.log`"")
    Check-Data
    if (-not (Test-Path "$destination/SORTH.exe")) { throw 'Recovery reinstall failed.' }
    Uninstall-TestBuild 'recovery'
    @{ok=$true; install=$true; same_build_reinstall=$true; uninstall_retains_data=$true; recovery_reinstall=$true; isolated_path=$true; clean_pc_without_python='NOT TESTED'; cross_version_rollback='NOT TESTED'} | ConvertTo-Json | Set-Content build/reports/installer-lifecycle.json
} finally {
    # Delete only the exact synthetic file created here, never the data folder.
    Remove-Item -LiteralPath $sentinel -ErrorAction SilentlyContinue
}
