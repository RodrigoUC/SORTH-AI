# Run only on Windows CI after the reviewed ZIP is prepared.
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
$version = '6.7.3'
$url = 'https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe'
$sha = '9c73c3bae7ed48d44112a0f48e66742c00090bdb5bef71d9d3c056c66e97b732'
$download = Join-Path $PWD 'build/innosetup-6.7.3.exe'
Invoke-WebRequest -Uri $url -OutFile $download
if ((Get-FileHash $download -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sha) { throw 'Compiler download hash mismatch.' }
$signature = Get-AuthenticodeSignature $download
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Pyrsys B.V.') { throw 'Compiler signature verification failed.' }
$compilerDir = Join-Path $PWD 'build/inno-compiler'
$process = Start-Process $download -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER', "/DIR=`"$compilerDir`"") -PassThru -Wait
if ($process.ExitCode -ne 0) { throw 'Compiler installation failed.' }
$info = Get-Content build/artifacts/build-info.json -Raw | ConvertFrom-Json
$archive = Get-ChildItem build/artifacts/*.zip
if (@($archive).Count -ne 1) { throw 'Expected exactly one review archive.' }
$payload = Join-Path $PWD 'build/installer-payload'
if (Test-Path $payload) { throw 'Use a fresh installer payload directory.' }
Expand-Archive $archive.FullName $payload
& "$compilerDir/ISCC.exe" "/DBuildId=$($info.build_id)" "/DAppVersion=$($info.version)" "/DPayloadDir=$payload/SORTH" "/DOutputPath=$PWD/build/artifacts" installer/sorth.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
$installer = Get-ChildItem build/artifacts/*-setup.exe
if (@($installer).Count -ne 1) { throw 'Expected exactly one installer.' }
$hash = (Get-FileHash $installer.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  $($installer.Name)" | Add-Content -Encoding utf8 build/artifacts/SHA256SUMS.txt
@{compiler_version=$version; compiler_url=$url; compiler_sha256=$sha; compiler_signature=$signature.Status.ToString(); build_id=$info.build_id; installer_sha256=$hash; signed=$false} | ConvertTo-Json | Set-Content -Encoding utf8 build/reports/installer-provenance.json
