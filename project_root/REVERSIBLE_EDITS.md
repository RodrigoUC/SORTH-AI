# Local undo and atomic bulk course edits

Optional settings `undo_redo` and `bulk_operations` start disabled. They expose
implemented native tools only. Bulk editing requires Undo and redo explicitly
enabled; changing one preference never silently enables another. Settings use
the existing feature preferences contract (integrate with the latest atomic
settings implementation, not the legacy INI writer).

## Undo contract

- Ctrl+Z undoes; Ctrl+Shift+Z or Ctrl+Y redoes. Buttons provide the same actions.
- History is session-local, bounded to 50 commands and 16 MiB of serialized
  snapshots across both branches. Oldest undo commands are evicted first.
  An individual command exceeding 16 MiB is rejected before saving.
- Course additions, edits/deletions, manual placement/removal, clear schedule,
  and explicit pin/unpin transitions save first and become one command each.
- Snapshots preserve courses, sizes, per-group suggestions, all classroom
  constraints, assignments, explicit LAB exceptions, pins and pending feedback.
- Candidate and travel targets are independently validated; one SQLite
  `save_session` transaction commits the complete accepted candidate before UI
  replacement or stack movement. Save/validation failure retains the accepted
  state and redo branch. Cancel performs no mutation.
- New accepted edits clear redo. Hiding history does not change data or erase
  still-valid commands. An edit while hidden, generation, seed/constraint changes
  or another untracked session mutation invalidates stale commands. Import,
  restoration and project changes explicitly reset history. No disk-persistent
  history or cross-project undo is promised.
- Invalidated pins require explicit existing confirmation; only a detached
  proposal is unpinned, so cancellation or persistence failure retains the pins.

## Bulk contract

Use Ctrl/Shift multi-selection in the course table. Hidden filtered rows are
excluded. Review identifies selected course codes and count, mixed values, exact
field-level before/after differences, pending assignments and preserved pins.

Only checked room type, enrollment size (0–100000) and preferred day fields are
changed. Unchecked means keep each individual value; Clear preference is an
explicit checked day edit. Codes, names, groups, duration and per-group preferences
are retained. Per-group day preferences may override a course-level preference;
the preview explains this. All unpinned placements become explicitly pending,
matching individual input editing; valid pins remain fixed. A change invalidating
pins is blocked until the user unpins them separately.

Changing any field invalidates the review. Apply verifies the session fingerprint,
selected stable codes, feature dependency, busy/recovery state, and the complete
candidate again. A batch is one persistence transaction and one undo command.

## Integration seams

`application/edit_history.py` owns detached validation, bounded commands and
fingerprinting; `application/bulk_courses.py` owns explicit-field previews.
The GUI's `_capture_edit_state`, `_persist_edit_state`, `_display_edit_state` and
`_commit_edit` connect these services to existing persistence and presentation.
Future calendar/resource fields must be included in those adapters. The validator
already accepts optional calendar and resources fields; the canonical serializer
uses their `to_data()` contracts. Soft preferred days remain canonical calendar
names even if the active custom calendar omits that day.

Background import must call `_reset_edit_history('import')` only after its atomic
`_commit_import` succeeds. Canceled/failed/stale imports must never reset history.
The separate resource/calendar integration adds their snapshot adapters and
staged orphan-membership consent; these modules are not included in this baseline.

## Verification and limitations

Regression tests cover repeated undo/redo, bounds, redo branching, failed saves,
invalid targets, pins, LAB exceptions, split structure, hidden controls, keyboard
shortcuts, stale review/selection, filtered IDs, mixed fields and explicit clear.
`test_edit_history_resources.py` is integration-only and skips when the resource
module is absent; it verifies all three resource types once integrated.

Linux Qt offscreen 960×640 screenshots are development evidence, not native
Windows, NVDA, high-DPI, or release-package certification. No remote publication
or Windows distribution changes are included.

### Transactional materialization

The repository accepts a keyword-only `before_commit` callback. It runs after SQL
writes but inside the same SQLite transaction, without importing GUI code. Edit
adapters use a synchronous, guarded UI materialization callback without dialogs
or nested event loops. Rendering failure rolls SQL back; commit failure after
rendering restores the accepted model references, view and dirty/save bookkeeping.
History moves only after successful commit. If the renderer also fails during
rollback, accepted data references and database remain preserved and editing locks
for explicit session recovery. There is no second render after committing.

Presentation state uses a shared identity-based snapshot: course/schedule searches,
all filters, selected cells and current identities, sorting/interactive widths,
scroll positions, selected room, tabs and focus survive refresh and rollback when
those identities still exist. Known empty-room filters are retained after the
last assignment is removed. A postcommit feedback failure reports that the change
was saved and locks the view for recovery; it never claims the earlier session
was preserved. Precommit rollback uses the distinct preserved-data recovery notice.
