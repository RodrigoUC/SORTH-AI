# Windows acceptance record (unexecuted template)

Status: **NOT EXECUTED**. A completed build or this template does not close issues
#4/#5. Use synthetic data, a standard account, active protections, and a fresh
Windows 10/11 test image. Keep the previous approved binary and source snapshot.
No Python is required to run the application or its recovery command.

## Identity and environment

Record date, tester, edition/build/architecture, hardware/RAM, display scaling,
language, clean-image origin, installed-app inspection, Excel version, exact
candidate version/build ID/source commit, download URL, filename and SHA-256.
Record the prior build's identity/hash separately. A PATH with no Python is not
proof of a machine with no installed Python. Do not include personal paths or
session data in a public report.

The bundled `project_root/tools/collect_windows_acceptance.ps1` captures hashes,
Authenticode, OS/hardware, Python discovery and read-only Defender status without
changing protections or claiming acceptance. Pass `-Artifact`,
`-ExpectedSha256`, `-SourceCommit`, `-DownloadOrigin`, `-Report` (new file).
Expected SHA-256 must come from the maintainer's approved distribution channel.
A ZIP ordinarily has no Authenticode signature; inspect the contained EXE and
installer separately. Preserve the exact artifact whose checksum was recorded.

## Results: PASS / FAIL / NOT RUN, with evidence for every row

| Case | Procedure and expected result | Result/evidence |
|---|---|---|
| Download/security | Download in browser from intended channel; record Mark of the Web, SmartScreen/Smart App Control and Defender experience. Record exact warning/detection and stop if blocked; never bypass it. | NOT RUN |
| Final-file scan | Scan exact final installer/extracted application using active Defender; record definition version, time, scan result and file hashes. A status query or absence of notifications is not a scan. | NOT RUN |
| Install | Standard-user installation, deliberate versioned shortcut; no Python, admin prompt or missing DLL/resource. | NOT RUN |
| Full workflow | Open → sample import → generate → edit → save → close → restore → Excel/CSV/PDF ES+EN; compare course, room, times and row counts. | NOT RUN |
| Real Excel | Open exports in Microsoft Excel, inspect accented text and print layout; PDF visual inspection at 100% and printing. | NOT RUN |
| Failure safety | Cancel import, invalid workbook, repeated generation, partial schedule, denied save and retry, relaunch recovery. Compare saved database and schedule before/after. Use only disposable data. | NOT RUN |
| Display/input | Paths with spaces/accents, keyboard-only workflow, 100/150/200% scaling, both languages, reduced motion and sleep/relaunch. | NOT RUN |
| Load envelope | Synthetic 10/100/500 courses with 5/20/50 compatible rooms, each one 60-minute session, fixed seed. Record actual workbook bytes, assigned/pending counts, generation/export seconds, peak RAM and UI responsiveness. These are test points, not advertised limits. | NOT RUN |
| Distinct-build upgrade | Install previous and new builds side by side; create/save synthetic session in old, close, preserve full data folder, open/save in new. Record both EXE hashes and schema versions. | NOT RUN |
| Real rollback | Close new; preserve its full data folder separately. Activate verified pre-update copy and launch previous shortcut. Check exact old schedule/data. New-version edits must remain in retained newer folder, never be silently merged/lost. | NOT RUN |
| Uninstall/reinstall | Uninstall each build separately; verify other build, data and backups remain; reinstall and restore. | NOT RUN |

For rollback, never point an old binary at a newer schema. The new recovery
command prepares a candidate for **the version running it**; using the newest
binary can migrate the candidate and therefore cannot make it compatible with
an old binary. Use the pre-update snapshot with its matching prior binary.
Record which post-backup edits are absent and explicitly accept that boundary.

## Publication decision (all required)

- Actual final candidate passed the required Windows/manual rows above.
- Corresponding sources, native dependency notices and durable delivery reviewed.
- Maintainer chose unsigned-review versus verified-publisher channel. A signed
  candidate requires valid Authenticode and timestamp checks on final files;
  new signatures do not guarantee SmartScreen reputation.
- Maintainer approved publication, final hashes, notes and limitations. This
  repository has no automatic signing or release-publishing step.

A failed/unrun row remains open. Do not convert CI or a filled checklist into a
manual test result. CI artifacts expire and are not a stable distribution channel.
