# Prepared-data schedule flow audit

Date: 2026-10-04. Baseline: `3f1b49abc9bfa5fa963364903a6617f8fe89967a`.
Scope: the existing Windows-first PyQt6 workflow, without adding features or
turning on optional tools. Measurements below came from real Qt 6 widgets,
mouse/keyboard events and background workers on Linux/offscreen/Fusion at
1200×800, 960×640 and 1200×920. OS open/save pickers returned synthetic paths;
their native appearance and Windows input behavior were **not** tested.
This is source-level development evidence, not Windows release acceptance.

## Action budget

A prepared workbook uses three principal application commands: **Cargar Excel →
Generar horario → Exportar todas las asignaciones**. Generation automatically
opens the result tab and has no routine completion dialog. Counting file
selection, output destination selection and the export success acknowledgment
as separate interaction stages gives six stages. This does not count searching
for files, typing a filename or multiple pointer events inside a native picker.
It is not a claim of three literal mouse clicks.

Reviewing a pending session adds one row-selection stage when that row is
visible. If it is buried in a large result, opening Estado, choosing Sin asignar
and selecting a row adds three stages. Its explanation then appears inline;
there is no extra explanation dialog. These review and warning steps must not
be hidden to make an artificial click target.

Reopening a saved session adds a restore decision instead of selecting an input
file. A restored result opens on course management; the user can switch to
Horario Generado to review it, or generate again directly. Changing this landing
behavior is a separate product choice and was not part of this correction.

## Observed outcomes

- The shipped synthetic `Cursos_Ejemplo.xlsx` generated all 42 sessions. The
  exported `Asignaciones` sheet reopened with all 42 rows.
- A synthetic workbook with one regular classroom, one regular course and one
  laboratory course generated 1/2 sessions. The pending row explained that no
  laboratories were configured. Both export picker and completion text identified
  the partial result. At 960×640, primary actions and the selected reason remained
  visible, and filtered export correctly disabled with only pending rows shown.
- A workbook referring to an unknown room produced the existing warning review.
  Cancel preserved the accepted state and session database bytes. All optional
  features remained off, including the optional import-difference preview.
- A missing workbook and a real export destination failure retained the prior
  accepted schedule. Errors remained readable after their dialogs closed; a new
  export to a valid destination succeeded.
- Reopening the complete saved session preserved its domain fingerprint.
- Main-window capture checks found no clipped native button captions in the
  inspected states. This is narrower than a full accessibility audit.

## Corrected inconsistency

A valid generated result with **zero assignments** showed `0/1` and one pending
session in the result/status areas, while the spacious overview and F6 still
said **Listo para generar**. The overview used assignment-map truthiness.

`MainWindow._refresh_overview` now uses the same `current_groups is not None`
result-presence sentinel as edit history and status handling. Fresh empty data
still requests an input workbook; loaded but ungenerated data still says it is
ready; zero, partial and complete results show their actual assigned counts.
Export remains disabled when there are no assignments. No scheduling,
persistence, preferences, workflow or export format changed.

- [Corrected spacious Spanish result](zero-result-es.png)
- [Corrected English F6 status](zero-result-f6-en.png)

Regression: `test_overview_and_f6_distinguish_no_result_from_zero_assignments`
checks ungenerated/zero/partial/complete results in ES and EN, the empty-catalog
state, export enablement and the text in the real F6 dialog. Independent review
also exercised the F6 keyboard shortcut and invalidation without an explicit
refresh.

## Separate findings, deliberately not fixed here

1. **Partial Excel is not self-contained.** Desktop Excel currently saves only
   classroom grids, Asignaciones and Por Aula. Pending IDs/reasons and completion
   counts shown in the GUI are absent from the artifact. The existing
   `ScheduleExporter.to_excel_bytes` path already owns optional Estado/Pendientes
   sheets for MCP. A separate candidate should reuse that infrastructure helper,
   keep complete unfiltered exports stable, and distinguish filtered-out assigned
   sessions from globally unassigned sessions. No GUI-to-MCP dependency is needed.
2. **Restore-time result presence is ambiguous.** Storage represents both absent
   and empty assignments as `None`; restore reconstructs pending groups from saved
   courses. The overview correction does not change this storage/lifecycle
   contract or claim that never-generated and zero-result saved states are now
   distinguishable.

## Existing no-click MCP route

Inspection of `project_root/MCP_OPTIONAL.md` and the existing exporter confirmed
that no desktop click flow is required by the protocol: `prepare_configuration`
returns missing-data questions or a validated configuration; after explicit scope
confirmation, `generate_excel` returns a validated complete/partial proposal and
an ephemeral Excel resource. The host must read and deliver it in the same
connection before expiration. No provider connection, credentials, actual
commercial host or native host attachment delivery was tested in this audit.
Missing-data questions and scope confirmation remain mandatory. This observation
is not a claim of tested ChatGPT/OpenCode/Claude integration.

## Verification

Focused regression: eight cases passed. Independent checks: all 22 tests in
`test_main_window.py` and 22 compact/optional-control tests passed. The strict
project UI audit reported zero findings; its web-oriented static checks do not
certify this native Qt application. The prescribed fresh-process source suite passed: 1,681 GUI; 190 layout; 24
theme-runtime; and 1,050 remaining tests, with the expected platform-only skips.
The selection verifier covered all 2,957 unique collected tests (1,062 selected
remaining cases, including 12 skips). Two module-collection skips recur in each
batch and are not additional tests. Three subtests also passed. `pip check`,
architecture, source compilation, `git diff --check` and the reviewed Bandit
baseline passed with no new findings. Windows visual and packaged acceptance
remain separate controls. The isolated source smoke also passed all 20 stages.
