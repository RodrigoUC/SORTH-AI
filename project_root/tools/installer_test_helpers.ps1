# Read-only validation of the exact test build's registered Inno uninstaller.
# Never evaluate a registry command string or search for an arbitrary unins*.exe.
function Resolve-TestUninstaller($record, [string]$destination) {
    $expected = [IO.Path]::GetFullPath($destination).TrimEnd('\', '/')
    $location = [string]$record.InstallLocation
    if (-not [IO.Path]::IsPathFullyQualified($location) -or
        [IO.Path]::GetFullPath($location).TrimEnd('\', '/') -ine $expected) {
        throw 'Uninstall record does not belong to the temporary installation.'
    }
    # Inno's UninstallString is a quoted executable, optionally followed by /LOG.
    # Accept no arbitrary registry-supplied switches or shell syntax.
    if ([string]$record.UninstallString -notmatch '^"([^"\r\n]+)"(?: /LOG)?$') {
        throw 'Unexpected registered uninstall command.'
    }
    $exe = $Matches[1]
    if (-not [IO.Path]::IsPathFullyQualified($exe)) { throw 'Uninstaller path is not absolute.' }
    $exe = [IO.Path]::GetFullPath($exe)
    if ([IO.Path]::GetDirectoryName($exe) -ine $expected -or
        [IO.Path]::GetFileName($exe) -notmatch '^unins[0-9]{3}\.exe$') {
        throw 'Registered uninstaller is outside the temporary installation or has an unexpected name.'
    }
    # Reject redirection through junctions/symlinks, including parent directories.
    $item = Get-Item -LiteralPath $exe -ErrorAction Stop
    if ($item.PSIsContainer) { throw 'Registered uninstaller is not a file.' }
    for ($pathItem = $item; $null -ne $pathItem; $pathItem = $(if ($pathItem.PSIsContainer) { $pathItem.Parent } else { $pathItem.Directory })) {
        if ($pathItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw 'Refusing an uninstaller path containing a reparse point.'
        }
    }
    $dataFile = [IO.Path]::ChangeExtension($exe, '.dat')
    if (-not (Test-Path -LiteralPath $dataFile -PathType Leaf)) { throw 'Uninstaller data file missing.' }
    return $item.FullName
}
