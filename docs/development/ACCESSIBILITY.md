# Keyboard and assistive-technology review

Tracks [issue #11](https://github.com/RodrigoUC/SORTH-AI/issues/11). This is an
implementation audit and a reproducible acceptance protocol, not certification.
Use synthetic courses, classrooms, paths and failures only. The deferred pilot
(#6) is not part of this work.

## Implemented keyboard contract

- Tab / Shift+Tab move between controls. Tables use arrow keys for cells; Tab
  leaves the table instead of walking every cell. Native tab bars use arrows.
- In sortable tables, Ctrl+Shift+Up sorts the current column ascending;
  Ctrl+Shift+Down sorts descending. The current item's identity is preserved by
  Qt sorting. Headers remain named; sorting instructions are an accessible
  description. Buttons below the table provide the context-menu actions without
  requiring a mouse.
- Ctrl+O imports, Ctrl+Enter generates, Ctrl+S exports the full schedule.
- F6 or **Leer estado / Read status** opens a read-only, keyboard-selectable
  snapshot of the current status, save state/error, overview, schedule totals and
  filtered result count. Escape closes it and returns to the invoker. Reopen to
  read newer state. This fallback does not claim automatic live announcements.
- Modal acceptance and cancellation restore the surviving, visible, enabled
  invoker. Qt handles ordinary Enter/default buttons and Escape rejection.
- Form labels name their inputs. Compound duration and preferred-time fields,
  seed, generation progress and both restriction lists have explicit names.
  Space checks restriction items; arrow keys change the current item.
- Course refresh retains the selected course code after sorting. If filtering
  hides that row, selection is cleared so actions cannot target an invisible
  course. Schedule row refresh retains the selected session ID where it remains.
  A newly displayed generation still resets its consultation filters as before.
- Missing course codes keep the dialog and entered data open, returning focus to
  the code field. Missing classroom selection returns focus to that control;
  manual scheduling validation errors become keyboard-focusable selectable text.
- Pending reasons and confirmed LAB exceptions are exposed on schedule cells as
  accessible descriptions, in addition to visible status and selected-row text.
  The weekly grid explicitly points to Detailed list as its linear alternative.
- Focus boundaries now include tables, restriction lists, time edits, checkboxes,
  tab labels, focusable feedback and the read-only status field. Existing reduced
  motion remains user-controlled. Classroom dialogs can be resized.
- Added strings are in both Spanish and English catalogs, including table
  instructions and item accessibility metadata. User data is never translated.

## Surface inventory and remaining acceptance

| Surface / task | Native roles and alternatives | Automated evidence / remaining work |
| --- | --- | --- |
| Main window / import | Named language selector, native buttons and file picker; Ctrl+O | Existing import/state tests. Native Windows picker, cancel and error narration pending. |
| Course list / edit | Named table, headers, search, buttons; arrows / Tab; keyboard sorting | Tab/Shift+Tab, sorting, stable refresh, hidden-row safety, compound names, invalid input preservation tested. Windows cell/header/selection speech pending. |
| Classroom editor | Buddy labels and explicit names; resizable native dialog | Names and missing-code focus implemented. Windows text enlargement and modal return pending. |
| Restrictions | Named native checkable lists, Space/arrow behavior; all/none buttons | Names, ES/EN switch and Space tested. Windows checked-state speech pending. No restriction-policy semantics changed. |
| Generate / results | Named busy indicator, existing textual progress; F6 status snapshot | F6 content, close and invoker restoration tested. Live progress announcements and native busy state pending. |
| Schedule detailed / room list | Named native row tables, headers, visible states and native action buttons | Stable ID refresh, localized reason metadata, filtering and existing assignment tests pass. Windows ordering, readout and all action round trips pending. |
| Weekly grid | Named table, exact times, textual conflicts, linear Detailed list alternative | Existing span/filter/conflict tests. Windows merged-cell navigation remains unverified; use Detailed list for task completion. |
| Manual assignment | Named room/day/time controls; native save/cancel; focusable validation | Missing selection and invalid-time focus with preserved inputs tested. Native LAB confirmation readout pending. |
| Summary / validation | Native labels/tables, scroll areas; selected-session reason | Existing quality tests. Complete Windows readout of long summary and all error paths pending. |
| Save / recovery | Visible saved/unsaved text, retry, F6 detailed state; native confirmation | Existing persistence/recovery tests and F6 synthetic failure readout. OS failures, recovery dialog speech and retry focus pending. |
| Export | Native buttons / file picker; full/filtered labels; Ctrl+S | Existing CSV/Excel/PDF suites. Native picker and overwrite/error narration pending. |

## Development checks

Run from `project_root` with development dependencies:

```sh
QT_QPA_PLATFORM=offscreen python -m pytest -q
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_gui/test_accessibility.py -q
```

`test_accessibility.py` exercises real Qt events and modal loops. Offscreen focus
assertions use the owner's remembered focus where no window manager can reactivate
it. Tests do not install or query a screen reader. Linux Fusion screenshots at
960×640 in ES/EN inspect focus and the status action; 2× Qt scaling checks pixel
scaling only, not Windows text-size settings or High Contrast.

## Required Windows acceptance record (not executed here)

Record final app commit/build, Windows version and scaling/text settings, Qt
version, screen reader name/version (for example NVDA), tester and date. For each
step record PASS, FAIL or NOT RUN with exact speech, keystrokes and issue link.

1. Start with an empty synthetic session. Traverse forward/backward by Tab through
   all main controls. Ensure focus is visible and no trap or clipped control.
2. Import a valid synthetic workbook with Ctrl+O; cancel then retry. Repeat with
   invalid/empty data and verify that the existing session survives and errors are
   understandable. Check the native file picker and return focus.
3. Search, sort, select, add and edit courses using only keys. Trigger missing
   code validation. Change ES/EN and verify names, entered data, selection and
   focus. Add a classroom and toggle course restrictions using Space.
4. Generate a complete and a partial schedule. Read progress/result and use F6
   during and after generation. Verify the dialog reads the snapshot, can copy
   text, and returns focus. Check reduced motion with and without a generation.
5. Traverse all schedule views. Read headers, exact times, pending reasons, LAB
   exceptions and conflict text. Perform manual assignment, reject/confirm an
   exception and remove a session. Cancel every dialog once. Confirm selection
   and focus remain meaningful after filtering, sorting, refresh and removal.
6. Save/restart/restore; exercise a synthetic unwritable destination or safe mock
   failure and retry. Read the save error using F6. Export complete and filtered
   Excel/CSV/PDF, including picker cancellation and overwrite confirmation.
7. Repeat core paths at Windows 100%, 150%, 200% scaling, enlarged text, and High
   Contrast. Check that no control is hidden and focus/selection remains legible.

Any failure remains open with reproduction details. Do not close #11 until its
criteria have final-commit evidence, including real Windows screen-reader tasks.
