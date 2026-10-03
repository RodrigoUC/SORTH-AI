# Undo/bulk development evidence

Synthetic data only. Native PyQt6 widgets rendered using Qt offscreen on Linux.

- `courses-es-960.png`, `courses-en-960.png`: enabled optional controls at960×640,
  selected courses, visible keyboard focus and compact native toolbar.
- `bulk-es.png`, `bulk-en.png`:760×570 explicit-field review, mixed sizes,
  stable identifiers, before/after rows and scheduling impact. Selection details
  are read-only and scrollable; table and preview remain keyboard accessible.

Final standalone full suite:631 passed,13 skipped,3 subtests passed. The added resource
cross-feature test module is skipped on this baseline because resources are
separate follow-on work; run it after integration. Other12 skips are existing
optional/runtime tests. Static security review: reviewed, no new findings.
`compileall` and `git diff --check` passed. Dependency locks unchanged; dependency
network audit was not rerun for this isolated patch.

An intermediate full run caught4 schedule-status regressions (history notices
replacing complete/partial totals), all fixed before this evidence result.
Existing same-identity Group references now update only after durable acceptance,
so rejected/saved-failed transitions cannot partially mutate viewer state.

Injected renderer failures, failure after SQL writes/before commit, commit failure after materialization, undo failure and failed rollback recovery are covered by transaction regression tests.

These images do not verify native Windows, NVDA, high-DPI, installer behavior,
or the integrated resource/calendar/import feature set. No remote publication.

Final review regressions additionally cover complete view-state restoration, multi-selection, empty-room filters, persistent feedback failure, and accepted-durable postcommit feedback/close failure. Independent adversarial review tests passed separately. One earlier full-suite run stalled during GUI tests and was interrupted; the rerun with a30-second faulthandler guard completed631 tests successfully in29.36seconds.
