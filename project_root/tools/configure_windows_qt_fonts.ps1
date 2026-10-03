# CI-only discovery for Qt's Windows offscreen FreeType font database.
# Read installed system fonts in place; never copy, bundle or upload font files.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:OS -ne 'Windows_NT') {
    throw 'Offscreen font discovery requires the disposable Windows CI runner.'
}
if ($env:QT_QPA_PLATFORM -ne 'offscreen') { throw 'Expected the offscreen QA platform.' }
$fontDir = [Environment]::GetFolderPath([Environment+SpecialFolder]::Fonts)
if (-not $fontDir -or -not (Test-Path -LiteralPath $fontDir -PathType Container)) {
    throw 'Windows system font directory is unavailable.'
}
$fontDir = (Get-Item -LiteralPath $fontDir).FullName
# Match the formats scanned by QFreeTypeFontDatabase (including Qt 6.11.2).
$fonts = @(Get-ChildItem -LiteralPath $fontDir -File | Where-Object {
    $_.Extension.ToLowerInvariant() -in @('.ttf', '.otf', '.pfa', '.pfb')
})
if ($fonts.Count -eq 0) { throw 'No supported system fonts for Windows offscreen QA.' }
"QT_QPA_FONTDIR=$fontDir" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
New-Item -ItemType Directory -Force build/reports | Out-Null
@{platform='offscreen'; font_directory=$fontDir; supported_font_files=$fonts.Count;
  source='installed Windows system fonts, read in place'; fonts_bundled=$false;
  native_desktop_acceptance='NOT TESTED'} | ConvertTo-Json |
    Set-Content -Encoding utf8 build/reports/qt-font-discovery.json
