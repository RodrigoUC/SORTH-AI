# Optional resource validation evidence

Branch: `feat/optional-teaching-resources`, based on frozen product `644ca13`.
This follow-on does not replace the already reviewed product batch.

## Verified

- Full suite, Qt offscreen: **669 passed, 12 skipped, 3 subtests passed**.
  Command: `QT_QPA_PLATFORM=offscreen /workspace/shared/sorth_work/venv/bin/python -m pytest -q -rs --disable-warnings`.
- All three optional kinds exercise shared-identity overlap, adjacent intervals,
  empty/unknown/declared availability, contiguous-window union, holes, retries,
  exact legacy behavior when absent, explicit split-session teachers, partial
  schedules, duplicate IDs, unknown references, malformed/future imports,
  resource-aware pins, and inactive structural validation.
- SQLite schema2→3 backup/migration, active/inactive snapshot round trips,
  scenario comparability, legacy save omission preservation, duplicate JSON field
  rejection and failed-write transaction preservation are tested.
- Native Qt tests cover cancel/accept parameter-off transitions, retained records,
  withdrawn results, no hidden active constraints, manual placement, editing,
  alias/ID preservation, availability confirmation, course-orphan consent,
  failed preference/database saves and recovery with active resource state.
- Atomic JSON optional-preference implementation from the frozen product is
  retained. Corrupt/read-only preferences cannot erase active constraints in a
  valid restored session. Recovery preserves their effective flags.
- Nine additional cross-feature tests passed using the actual undo/bulk worker
  application modules (commit `37de40d`) with this branch's resource implementation:
  all kinds/flags survive repeated undo/redo; orphan/split/conflict changes reject
  before persistence. Final combined GUI undo/calendar verification belongs to
  the follow-on integration branch, not this isolated branch.
- Dedicated optional MCP environment: **49 passed** (`tests/test_mcp`).
- Dedicated security environment: **12 passed, 3 subtests passed** (`tests/test_security_checks.py`).
- `python -m compileall -q src`: passed. `git diff --check`: passed.
- Repository static security review under its security environment: reviewed,
  zero new findings. Running it initially under the Qt environment lacked Bandit;
  rerunning with the installed security environment completed successfully.

## Visual evidence

Synthetic-data Qt/Fusion screenshots cover main window at 1200×800 and 960×640,
settings, group session editor and availability editor in Spanish and English.
Representative settings, compact main window, group editor and availability
frames were visually inspected. Controls retain the established native palette,
readable labels and keyboard focus. Full resource IDs remain available in the
editor/selection and table tooltips; identical aliases do not merge identities.
All strings introduced by resource/settings dialogs are included in literal-key
localization coverage. User aliases remain literal during language changes.

Evidence is retained alongside the development checkout under
`sorth-resource-evidence/`; these are local development artifacts, not a public
upload or a native Windows acceptance report.

## Explicit limitations

- Ten installer checks require native Windows PowerShell; offscreen Linux
  screenshots do not establish Windows rendering or screen-reader support.
- The main suite skips optional MCP stdio and live-analyzer contracts when those
  dependency sets are absent from the Qt environment; both pass in their dedicated
  environments as reported above. Native Windows checks remain unexecuted.
- No new workbook/roster format or identity-bearing export is introduced. Import
  coverage means strict session/scenario deserialization and unchanged legacy
  Excel compatibility. MCP remains its existing explicit contract.
- Student-group membership is not inferred from individual students. If a person
  needs identity-level protection, assign that person explicitly to each session.
- Simultaneous co-teaching is not inferred: each session has at most one teacher,
  while a course may use different teachers in different explicit sessions.
- No remote writes or issue closure were performed.
