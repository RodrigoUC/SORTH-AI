# Read-only environment/provenance collection. Does not launch the candidate,
# change protection settings, install Python, sign, or assert manual acceptance.
param(
    [Parameter(Mandatory=$true)][string]$Artifact,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{64}$')][string]$ExpectedSha256,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{40}$')][string]$SourceCommit,
    [Parameter(Mandatory=$true)][string]$DownloadOrigin,
    [Parameter(Mandatory=$true)][string]$Report
)
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Run on the Windows acceptance machine.' }
if (Test-Path -LiteralPath $Report) { throw 'Use a fresh report path.' }
$file = Get-Item -LiteralPath $Artifact
if ($file.PSIsContainer) { throw 'Select one exact downloaded installer or ZIP.' }
$actual = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $ExpectedSha256.ToLowerInvariant()) { throw 'Artifact hash mismatch. Do not execute it.' }
$signature = Get-AuthenticodeSignature -LiteralPath $file.FullName
$os = Get-CimInstance Win32_OperatingSystem
$computer = Get-CimInstance Win32_ComputerSystem
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$python = @()
foreach ($name in @('python', 'python3', 'py')) {
    $python += @(Get-Command $name -ErrorAction SilentlyContinue | Select-Object Name, Source)
}
# Discovery is evidence only: PATH absence never proves Python is uninstalled.
$installedPython = @()
foreach ($key in @('HKCU:\Software\Python', 'HKLM:\Software\Python', 'HKLM:\Software\WOW6432Node\Python')) {
    if (Test-Path -LiteralPath $key) { $installedPython += $key }
}
$defender = $null
$defenderError = $null
try {
    $defender = Get-MpComputerStatus | Select-Object AMServiceEnabled, AntivirusEnabled, RealTimeProtectionEnabled,
        AntivirusSignatureVersion, AntivirusSignatureLastUpdated, AMProductVersion, QuickScanEndTime, FullScanEndTime
} catch { $defenderError = $_.Exception.Message }
$zone = $null
try { $zone = Get-Content -LiteralPath $file.FullName -Stream Zone.Identifier -Raw -ErrorAction Stop }
catch { $zone = 'Unavailable; do not infer browser reputation from this.' }
$record = [ordered]@{
    recorded_utc=(Get-Date).ToUniversalTime().ToString('o'); source_commit=$SourceCommit;
    artifact_name=$file.Name; artifact_sha256=$actual; bytes=$file.Length; download_origin=$DownloadOrigin;
    windows=@{caption=$os.Caption; version=$os.Version; build=$os.BuildNumber; architecture=$os.OSArchitecture};
    hardware=@{manufacturer=$computer.Manufacturer; model=$computer.Model; memory_bytes=$computer.TotalPhysicalMemory};
    elevated=$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator);
    python_commands=$python; python_registry_keys=$installedPython;
    clean_pc_without_python='NOT VERIFIED: record clean image provenance and installed-app inspection';
    authenticode=@{status=$signature.Status.ToString(); message=$signature.StatusMessage;
        signer=$(if ($signature.SignerCertificate) { $signature.SignerCertificate.Subject });
        timestamp_signer=$(if ($signature.TimeStamperCertificate) { $signature.TimeStamperCertificate.Subject })};
    defender_status=$defender; defender_read_error=$defenderError;
    defender_artifact_scan='NOT RUN by this collector'; mark_of_the_web=$zone;
    smartscreen_download_experience='NOT TESTED by this collector';
    interactive_acceptance='NOT TESTED'; cross_version_rollback='NOT TESTED'; license_clearance='PENDING'
}
# CreateNew refuses races and avoids replacing any prior acceptance evidence.
$stream = [IO.File]::Open($Report, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
try {
    $writer = New-Object IO.StreamWriter($stream, (New-Object Text.UTF8Encoding($false)))
    try { $writer.Write(($record | ConvertTo-Json -Depth 8)) } finally { $writer.Dispose() }
} finally { $stream.Dispose() }
Write-Host 'Evidence recorded. Manual acceptance, final artifact scan and distribution approval remain pending.'
