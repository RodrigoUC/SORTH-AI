Param([string]$PythonExe = '.\.venv-build\Scripts\python.exe')
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Build the Windows MCP companion on Windows.' }
Set-Location -Path $PSScriptRoot
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw 'Prepare .venv-build first or pass the absolute CPython 3.12.10 executable.'
}
$PythonExe = (Resolve-Path -LiteralPath $PythonExe).Path
& $PythonExe -c "import platform,sys; assert sys.version_info[:3] == (3,12,10) and platform.machine().upper() == 'AMD64', 'Use CPython 3.12.10 x64'"
if ($LASTEXITCODE -ne 0) { throw 'Unsupported companion build interpreter.' }
if (-not $env:SOURCE_COMMIT) {
    $env:SOURCE_COMMIT = (& git rev-parse HEAD)
    if ($LASTEXITCODE -ne 0) { throw 'Set SOURCE_COMMIT to the exact source SHA.' }
}
# A clean, dedicated environment prevents GUI/model dependencies leaking in.
foreach ($path in @('build/mcp/venv', 'build/mcp/wheels', 'build/mcp/notices', 'dist/mcp/SORTH-MCP')) {
    if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Recurse -Force }
}
New-Item -ItemType Directory -Force build/mcp/wheels | Out-Null
& $PythonExe -m pip download --require-hashes --only-binary=:all: -r requirements-mcp-windows.lock --dest build/mcp/wheels
if ($LASTEXITCODE -ne 0) { throw 'Companion wheel download/hash validation failed.' }
& $PythonExe tools/collect_license_notices.py --wheel-dir build/mcp/wheels --lock requirements-mcp-windows.lock --output build/mcp/notices
if ($LASTEXITCODE -ne 0) { throw 'Companion notice collection incomplete.' }
& $PythonExe tools/mcp_payload.py notices --notices build/mcp/notices
if ($LASTEXITCODE -ne 0) { throw 'Collected companion notices incomplete.' }
& $PythonExe tools/mcp_payload.py notices
if ($LASTEXITCODE -ne 0) { throw 'Committed companion notices incomplete/stale.' }
& $PythonExe -m venv build/mcp/venv
if ($LASTEXITCODE -ne 0) { throw 'Companion environment creation failed.' }
$mcpPython = (Resolve-Path 'build/mcp/venv/Scripts/python.exe').Path
& $mcpPython -m pip install --no-index --find-links build/mcp/wheels --require-hashes --only-binary=:all: -r requirements-mcp-windows.lock
if ($LASTEXITCODE -ne 0) { throw 'Companion locked installation failed.' }
& $mcpPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Companion dependency validation failed.' }
& $mcpPython -c "import importlib.util, importlib.metadata as m; assert m.version('mcp') == '1.30.0'; assert m.version('openpyxl') == '3.1.5'; assert all(importlib.util.find_spec(n) is None for n in ('PyQt6','pandas','openai','anthropic','torch','pytest'))"
if ($LASTEXITCODE -ne 0) { throw 'Companion environment is contaminated.' }
& $mcpPython tools/build_identity.py --commit $env:SOURCE_COMMIT
if ($LASTEXITCODE -ne 0) { throw 'Companion build identity failed.' }
& $mcpPython -m PyInstaller --noconfirm --clean --distpath dist/mcp --workpath build/mcp/pyinstaller SORTH-MCP.spec
if ($LASTEXITCODE -ne 0) { throw 'Companion freezing failed.' }
& $mcpPython tools/mcp_payload.py create --commit $env:SOURCE_COMMIT
if ($LASTEXITCODE -ne 0) { throw 'Companion payload verification failed.' }
New-Item -ItemType Directory -Force build/reports | Out-Null
& $mcpPython -m pip freeze | Out-File -Encoding utf8 build/reports/mcp-build-environment.txt
Write-Host 'Dormant companion ready. No user component has been installed or enabled.'
