# Windows review acceptance and safe manual updates

This is an unsigned review build, not a stable release. Passing automation does
not approve publication, legal compliance, signing, or production use.

## Implemented evidence

- `project_root/VERSION` is the package version; `build_id` combines it with the
  exact 12-character source identifier, and `source_commit` retains all 40 hex
  characters. The EXE ProductVersion, ZIP, installer and build manifests carry
  this identity. Rebuild instructions use `build_exe.ps1`; the legacy spec alone
  is not the release entry point. ZIP member times are normalized, but bitwise
  reproducibility of PyInstaller/compiler output is not claimed.
- `build-info.json` enumerates every bundled app file, size and SHA-256, including
  native DLLs/plugins. This enables component mapping; it does not supply missing
  corresponding sources or establish license clearance.
- Frozen Qt smoke now imports the bundled example, runs scheduling, edits an
  actual course dialog, regenerates after edit, saves, opens a new window through
  the restore dialog, verifies export row counts and Unicode content, rejects
  missing/corrupt input without database modification, then imports/schedules/
  exports a synthetic 500-course, 50-room fixture. It records elapsed time.
  Large-file testing is a bounded service/IO check, not a UI responsiveness or
  arbitrary workload guarantee. OS-native file picker and Excel rendering are
  still manual checks.
- CI executes the frozen app and the installed app with Python locations removed
  from PATH and PYTHONHOME/PYTHONPATH cleared. The runner still has Python
  installed. A clean machine without Python has NOT been tested.
- The installer uses distinct per-build directories and uninstall identities.
  It requests no admin rights, adds a versioned Start Menu shortcut, and never
  writes/deletes the application-data directory. CI installs, reinstalls,
  launches the installed workflow, uninstalls and recovery-reinstalls while
  checking an independent synthetic user-data sentinel. This is not an actual
  cross-version schema rollback test.

## Installer provenance

Compiler: [Inno Setup 6.7.3 official immutable release](https://github.com/jrsoftware/issrc/releases/tag/is-6_7_3).
Download SHA-256 from its GitHub release asset metadata:
`9c73c3bae7ed48d44112a0f48e66742c00090bdb5bef71d9d3c056c66e97b732`.
The build also requires a valid Authenticode signature with publisher Pyrsys B.V.
See [official verification guidance](https://jrsoftware.org/isdl-verify.php),
[non-admin installation](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm)
and [uninstall deletion warnings](https://jrsoftware.org/ishelp/topic_uninstalldeletesection.htm).
Inno's signature authenticates the compiler installer only; SORTH remains unsigned.
No certificate, purchase, signing service, trusted certificate, security bypass,
automatic installation, or public release is configured. An opt-in official-release
checker and explicitly confirmed download/launch workflow are described in
[Updates](user/UPDATES.md). It does not publish or sign a release.

## Safe update / recovery policy

1. Close all SORTH processes. Preserve the complete `%LOCALAPPDATA%\SORTH` folder
   (including any WAL/SHM files) in a separate backup location. Do not back up a
   running database with a plain file copy; use SORTH's validated snapshot where
   available, then close the application.
2. Obtain the approved installer and SHA256SUMS from the same maintainer release;
   compare SHA-256 before execution. A hash alone does not authenticate its source.
   Verify the expected commit/version and, when introduced, publisher signature.
3. Install side by side and launch the version-labelled shortcut deliberately.
   Do not run old and new versions concurrently. Installers preserve user data,
   but application schema changes may affect whether an older app can read it.
4. Retain the previous verified installer and pre-update validated database backup.
   A newer schema must use a compatible binary. For a downgrade, restore a
   compatible pre-update backup only after separately retaining the current data,
   accepting that changes after that backup are absent. Never aim an old binary
   at newer-schema data; older releases might lack a forward-version guard.
5. Uninstall removes only files registered to that specific build and its shortcut.
   User sessions/backups remain. Removing them is a separate deliberate action.

## Remaining release gates

- Native Windows 10/11 standard-user clean-PC test with no Python installed;
  OS dialogs, scaling, sleep/relaunch, Excel/printing, and representative large
  user workbooks. Record device, Windows version, build hash and results.
- Real previous-version → current-version → compatible recovery test using
  supported schema versions. Same-build CI reinstall is insufficient evidence.
- Maintainer choice of signing identity/account and any paid certificate/service.
  Signing cannot promise SmartScreen reputation or absence of warnings. Do not
  disable protection or instruct users to bypass an unverified warning.
- Exact Qt/native DLL/plugin version, licenses/notices, corresponding sources,
  patches/build configuration and durable source availability review. See
  SOURCE_AVAILABILITY.md. File hashes and wheel notices do not close this gate.
- Maintainer approval before any release publication; CI artifacts expire.

## Narrow Qt PDF perimeter reduction

The supported onedir build now removes only the unused `imageformats/qpdf.dll`
and `Qt6Pdf.dll`, after parsing normal and delay-load PE imports of every retained
EXE/DLL/PYD. Unexpected locations, QtPdf Python bindings, unreadable PE files or
retained dependencies fail the build. QtNetwork, Mesa and all other plugins stay.
The report is `build/reports/qt-pdf-pruning.json`; use fresh build/evidence output
when rebuilding. `package_windows.py` rejects a candidate still containing either
PDF DLL. Legacy direct-spec and optional onefile builds are not this reviewed
release path and do not receive this onedir pruning.

This removes Qt PDF/PDFium from a newly validated package, not retroactively from
older artifacts. The final source/notice review remains required for retained
Qt modules and other native dependencies. PE import inspection cannot establish
absence of dynamic loading, so packaged/installed smoke also decodes ICO/SVG/PNG
and exports PDF in Spanish and English, as well as the existing user workflow.

The reusable `tools/verify_cross_version_recovery.py` exercises two distinct
source implementations and a genuine schema increase in isolated subprocesses:
old creates → new migrates/saves → old rejects newer data unchanged → old opens
pre-update copy, with current data retained separately. Its report identifies
source file hashes and does not claim a Windows binary or installer rollback.
Rerun against the final candidate source and retain a separate real two-build
Windows acceptance record from [the template](WINDOWS_ACCEPTANCE_RECORD.md).
