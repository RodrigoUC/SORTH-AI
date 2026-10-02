# Disposable Windows CI runner only. Never execute against an existing user profile.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Installer lifecycle test requires disposable CI.' }
Set-Location (Join-Path $PSScriptRoot '..')
$installer = Get-ChildItem build/artifacts/*-setup.exe
if (@($installer).Count -ne 1) { throw 'Expected exactly one installer.' }
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
    $p = Start-Process -FilePath $exe -ArgumentList $arguments -PassThru
    if (-not $p.WaitForExit(180000)) { $p.Kill(); throw 'Installer lifecycle step timed out.' }
    if ($p.ExitCode -ne 0) { throw "Installer lifecycle exit $($p.ExitCode)." }
}
try {
    # Install and idempotent re-install of the same exact reviewed build.
    foreach ($attempt in 1..2) {
        Run-Checked $installer.FullName @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/DIR=`"$destination`"", "/LOG=`"$PWD/build/reports/install-$attempt.log`"")
        if (-not (Test-Path "$destination/SORTH.exe")) { throw 'Installed executable missing.' }
        Check-Data
    }
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
    } finally {
        $env:PATH = $oldPath
        $env:PYTHONHOME = $oldPythonHome
        $env:PYTHONPATH = $oldPythonPath
    }
    Run-Checked "$destination/unins000.exe" @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART')
    if (Test-Path "$destination/SORTH.exe") { throw 'Uninstall left the installed executable.' }
    Check-Data
    # Reinstall recovery checks package-level rollback mechanics only. A real
    # prior-version + current-schema compatibility exercise remains required.
    Run-Checked $installer.FullName @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/DIR=`"$destination`"")
    Check-Data
    if (-not (Test-Path "$destination/SORTH.exe")) { throw 'Recovery reinstall failed.' }
    Run-Checked "$destination/unins000.exe" @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART')
    Check-Data
    @{ok=$true; install=$true; same_build_reinstall=$true; uninstall_retains_data=$true; recovery_reinstall=$true; isolated_path=$true; clean_pc_without_python='NOT TESTED'; cross_version_rollback='NOT TESTED'} | ConvertTo-Json | Set-Content build/reports/installer-lifecycle.json
} finally {
    # Delete only the exact synthetic file created here, never the data folder.
    Remove-Item -LiteralPath $sentinel -ErrorAction SilentlyContinue
}
