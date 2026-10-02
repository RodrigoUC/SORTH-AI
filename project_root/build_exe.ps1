Param(
    [switch]$OneFile = $false,
    [string]$IconPath = ".\assets\sorth.ico"
)

$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') {
    throw 'Los ejecutables de Windows deben compilarse en Windows.'
}
Set-Location -Path $PSScriptRoot

$pythonCandidates = @(
    ".\.venv-build\Scripts\python.exe",
    ".\venv\Scripts\python.exe",
    "..\venv\Scripts\python.exe",
    "python"
)

$pythonExe = $null
foreach ($candidate in $pythonCandidates) {
    if ($candidate -eq "python" -or (Test-Path $candidate)) {
        $pythonExe = $candidate
        break
    }
}

if (-not $pythonExe) {
    throw "No se encontró un ejecutable de Python para compilar."
}

Write-Host "Usando Python: $pythonExe"

# Validate critical dependency before build
& $pythonExe -c "import PyQt6, PyInstaller; print('Dependencias de compilacion OK')"
if ($LASTEXITCODE -ne 0) {
    throw 'Faltan dependencias. Prepare el entorno segun WINDOWS_DISTRIBUTION.md.'
}
& $pythonExe -m PyInstaller --version
if ($LASTEXITCODE -ne 0) { throw 'No se pudo verificar PyInstaller.' }

if (-not $env:SOURCE_COMMIT) {
    $env:SOURCE_COMMIT = (& git rev-parse HEAD)
    if ($LASTEXITCODE -ne 0) { throw 'Set SOURCE_COMMIT to the exact source SHA.' }
}
& $pythonExe tools/build_identity.py --commit $env:SOURCE_COMMIT
if ($LASTEXITCODE -ne 0) { throw 'Build identity failed.' }

$baseArgs = @(
    '--noconfirm',
    '--clean',
    '--noupx',
    '--specpath', 'build/spec',
    '--version-file', (Join-Path $PSScriptRoot 'build/identity/windows_version_info.txt'),
    '--name', 'SORTH',
    '--hidden-import', 'PyQt6',
    '--add-data', ((Join-Path $PSScriptRoot 'build/identity/build-identity.json') + ';.'),
    '--add-data', ((Join-Path $PSScriptRoot 'data/input') + ';data/input'),
    '--add-data', ((Join-Path $PSScriptRoot 'assets') + ';assets'),
    '--add-data', ((Join-Path $PSScriptRoot 'README.md') + ';.'),
    '--add-data', ((Join-Path $PSScriptRoot '../CREDITS.md') + ';.'),
    '--add-data', ((Join-Path $PSScriptRoot '../LICENSE') + ';.'),
    '--add-data', ((Join-Path $PSScriptRoot '../LICENSING.md') + ';.'),
    '--add-data', ((Join-Path $PSScriptRoot '../third_party') + ';third_party'),
    (Join-Path $PSScriptRoot 'gui_app.py')
)

if ($IconPath -and (Test-Path $IconPath)) {
    $resolvedIcon = (Resolve-Path $IconPath).Path
    $baseArgs = @('--icon', $resolvedIcon) + $baseArgs
    Write-Host "Usando icono: $resolvedIcon"
} elseif ($IconPath -and $PSBoundParameters.ContainsKey('IconPath')) {
    throw "No se encontró el archivo de icono: $IconPath"
} elseif (Test-Path ".\assets\sorth.ico") {
    $defaultIcon = (Resolve-Path ".\assets\sorth.ico").Path
    $baseArgs = @('--icon', $defaultIcon) + $baseArgs
    Write-Host "Usando icono por defecto: $defaultIcon"
}

if ($OneFile) {
    $buildArgs = @('--onefile', '--windowed') + $baseArgs
} else {
    $buildArgs = @('--onedir', '--windowed') + $baseArgs
}

Write-Host "Compilando ejecutable..."
& $pythonExe -m PyInstaller @buildArgs
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller fallo; no distribuir esta compilacion.' }

if ($OneFile) {
    Write-Host "Listo: dist/SORTH.exe"
} else {
    Write-Host "Listo: dist/SORTH/SORTH.exe"
}

$outputExe = if ($OneFile) { 'dist/SORTH.exe' } else { 'dist/SORTH/SORTH.exe' }
if (-not (Test-Path -LiteralPath $outputExe -PathType Leaf)) {
    throw "No se encontro la salida esperada: $outputExe"
}
Write-Host 'Compilacion local sin firma. Aun requiere validacion de Windows y revision de distribucion.'
Get-FileHash -LiteralPath $outputExe -Algorithm SHA256
