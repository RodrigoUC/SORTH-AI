Param(
    [switch]$OneFile = $false,
    [string]$IconPath = ".\assets\sorth.ico",
    [switch]$WithoutMcp = $false,
    [switch]$McpPrepared = $false
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
& $pythonExe -c "import importlib.util; assert importlib.util.find_spec('mcp') is None, 'Build the GUI in the SDK-free base environment'"
if ($LASTEXITCODE -ne 0) { throw 'The main build environment must remain MCP SDK-free.' }

if (-not $env:SOURCE_COMMIT) {
    $env:SOURCE_COMMIT = (& git rev-parse HEAD)
    if ($LASTEXITCODE -ne 0) { throw 'Set SOURCE_COMMIT to the exact source SHA.' }
}
& $pythonExe tools/build_identity.py --commit $env:SOURCE_COMMIT
if ($LASTEXITCODE -ne 0) { throw 'Build identity failed.' }

if ($WithoutMcp -and $McpPrepared) { throw 'WithoutMcp and McpPrepared are mutually exclusive.' }
if (-not $WithoutMcp) {
    if (-not $McpPrepared) { & .\build_mcp.ps1 -PythonExe $pythonExe }
    & $pythonExe tools/mcp_payload.py verify --commit $env:SOURCE_COMMIT
    if ($LASTEXITCODE -ne 0) { throw 'Companion payload must be built and verified before the GUI.' }
}

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
    '--add-data', ((Join-Path $PSScriptRoot 'MCP_OPTIONAL.md') + ';.'),
    '--add-data', ((Join-Path $PSScriptRoot '../CREDITS.md') + ';.'),
    '--add-data', ((Join-Path $PSScriptRoot '../LICENSE') + ';.'),
    '--add-data', ((Join-Path $PSScriptRoot '../LICENSING.md') + ';.'),
    '--add-data', ((Join-Path $PSScriptRoot '../third_party') + ';third_party'),
    (Join-Path $PSScriptRoot 'gui_app.py')
)

if (-not $WithoutMcp) {
    # Compile the manifest into the GUI. An editable JSON beside the ZIP is not
    # a trust anchor. The readable JSON is included only as audit evidence.
    $baseArgs = @('--paths', (Join-Path $PSScriptRoot 'build/identity'),
                  '--hidden-import', '_sorth_mcp_bundle',
                  '--add-data', ((Join-Path $PSScriptRoot 'build/identity/mcp-component.json') + ';.'),
                  '--add-data', ((Join-Path $PSScriptRoot 'build/optional/mcp-component.zip') + ';optional')) + $baseArgs
}

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
if (-not $OneFile) {
    & $pythonExe tools/prune_unused_qt_pdf.py
    if ($LASTEXITCODE -ne 0) { throw 'Qt PDF dependency review failed; do not distribute.' }
}
Write-Host 'Compilacion local sin firma. Aun requiere validacion de Windows y revision de distribucion.'
Get-FileHash -LiteralPath $outputExe -Algorithm SHA256
