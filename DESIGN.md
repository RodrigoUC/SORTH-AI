# SORTH desktop design

## Product and audience
Spanish-first native PyQt6 application for academic timetable planning. The primary task is reviewing courses, generating a schedule, checking pending sessions and exporting the result. Spanish and English are selectable in the masthead. Additional locales use a central language registry and independent catalogs; see `project_root/LOCALIZATION.md`.

## Direction
Professional academic workspace with a more recognizable identity than the previous all-blue/gray surface. A navy masthead anchors the application. Teal marks the principal scheduling action and overview. Violet marks active navigation and keyboard focus. Pale reading surfaces keep dense course and schedule tables comfortable.

## Runtime source of truth
`project_root/src/gui/theme.py` owns semantic `COLORS` and the shared Qt stylesheet. Roles use English identifiers independent of displayed language. `main_window.py` assigns brandHeader/headerAction roles; schedule consultation assigns mutedText/dangerAction roles. No behavior, text, schedule allocation or exported data changes.

## Color roles
- Canvas: #EFF3F9; reading surface: #FFFFFF; alternate row: #F3F6FC
- Navy identity/table header: #183153; white text; secondary header text #D3E5FA
- Main action: #087F83; hover #066B70; pressed #055A61; white text
- Active tab/focus: #6545AD; soft accent #EFE9FA
- Body text: #1D2D44; secondary text and placeholders: #52647D
- Control boundaries: #7688A1; passive dividers: #D6DFEB
- Disabled surface/text: #E1E7F0 / #56667D
- Success: #246448 / #E3F3EA; caution: #88551A / #FFF0D5; danger: #A12D46 / #FCE8EC

## Components and behavior
Use native Segoe UI with DejaVu Sans fallback, keeping the existing 10pt desktop density. Keep existing keyboard shortcuts and native input behavior. Selection has a light violet surface; focused controls have a 2px contrasting boundary. A focused teal action uses a white inset boundary; the navy header action uses white. Destructive schedule actions retain explicit text and confirmation. Course category fills remain stable and shared with exported spreadsheets; labels and exact times carry meaning independently of color. Existing dialogs outside this palette slice retain their behavior and local status styling.

## Localization behavior
The language selector uses native language names and the shared navy header contrast token. Switching updates only marked presentation properties on existing Qt controls, retaining editing state, focus, filters and selection. The locale applies to owned widgets, never to the operating system or persisted domain data. Exact schedule times remain HH:mm and CSV/Excel use their existing Spanish headers and day names in every interface language. Native system file pickers retain the OS language. Future RTL languages require a dedicated layout review before release.

## Verification and limits
`tests/test_gui/test_theme.py` checks text ≥4.5:1, control/focus boundaries ≥3:1, schedule label contrast and packaged sorting icons. Real Qt screenshots cover list, classroom grid, course management, narrow layout, filters, pending/conflicting sessions and keyboard focus. Palette ratios are not a complete accessibility certification. Linux Qt offscreen/Fusion captures are development previews, not evidence of native Windows rendering. Confirm the Windows review workflow and native appearance before a release.

## Motion and accessibility preference
`project_root/src/gui/motion.py` owns native Qt motion. Tab/view changes and
replacement schedule results reveal from 90% to full opacity in 150 ms with
OutCubic easing. There is at most one effect; no per-row/per-cell animation,
geometry animation, stagger, startup sequence, or delayed input. Effects are
removed after finishing and cancelled on newer navigation, hide, resize, close,
or target deletion. Native table rendering resumes without a persistent effect.

The always-visible status-bar checkbox **Reducir animaciones** persists separately
from schedule data via QSettings `SORTH/SORTH`, `interface/reduced_motion`. Enabling
it immediately cancels transitions and replaces the indeterminate generation bar
with a static **En curso** label, without a fabricated percentage. Status text and
all scheduling state remain unchanged. This explicit preference does not claim
automatic detection of the operating system's reduced-motion setting.

Motion QA uses real Qt event-loop tests, recorded Qt frames, and screenshots at
1200×800 and 960×640; screenshots alone cannot establish animation behavior.
Native Windows timing and screen-reader announcement behavior require platform QA.

## Keyboard and assistive-technology support
Tables use arrow keys for cell navigation and Tab/Shift+Tab to leave; sortable
columns support Ctrl+Shift+Up/Down. Selection follows course/session identity
through supported row refreshes. Form labels supply accessible names; compound
inputs and checkable restriction lists have explicit ES/EN names. Focus rings
also cover tables, lists, time fields, checkboxes and selectable feedback.
The status-bar **Leer estado (F6)** action opens a keyboard-readable snapshot of
progress, save state, totals and errors, with focus returned on close. This is
an explicit fallback, not a claim of live screen-reader announcement support.
See `project_root/ACCESSIBILITY.md` for inventory, shortcuts and outstanding
Windows acceptance; do not declare issue #11 complete from offscreen tests.
## Named projects and scenario comparison

The status bar opens a native project dialog using existing localized Qt controls
and theme tokens. Scenario rows have native multi-selection and internal scrolling;
create/save/open are separated from duplicate/rename/compare in two action rows.
The comparison uses a wider metric-label column, explicit numerators/denominators,
and an incompatibility warning above the scrollable metrics. Close remains outside
the scroll area. User names remain literal, not translation keys or file paths.
Opening another scenario explicitly confirms and preserves a recovery copy. Naming
cancellation performs no write; duplicate names show an inline error and never
replace data. Shared i18n widgets own labels/buttons/tables, `ProjectRepository`
owns uniqueness and transactions, and quality v1 owns all descriptive measures.

## Optional feature preferences
The masthead Settings button opens a native Save/Cancel dialog using the existing
palette, typography, localized controls and keyboard focus. Only implemented
advanced tools appear, all disabled initially. Disabling changes entry-point
visibility and never deletes project data or relaxes constraints. A main-window
text notice (also included in F6 status) explains retained pins/scenario data and
where to reactivate controls. See `project_root/OPTIONAL_FEATURES.md`.

Optional-tool preferences use one versioned atomic JSON record, separate from
QSettings language/motion preferences. Failed saves keep committed flags and
original bytes. Malformed/future settings require an explicit preserve-and-reset
action; the native recovery message explains that schedule data never changes.

## Staged Excel import

A native status-bar cancel action accompanies the existing busy indicator; a new
Load Excel request supersedes the previous reader. Input editing stays disabled
until the candidate is accepted or canceled. Optional change review uses one
780×560 native dialog, a keyboard-selectable scrolling text summary, explicit
replacement wording, and default Cancel. Changes show previous/new field values;
restrictions and assignments describe exactly what will be cleared or retained.
No silent merge or partially editable model replacement. The indicator respects
reduced motion; F6 exposes full status when the compact bar elides text. See
`project_root/EXCEL_IMPORT_WORKFLOW.md` for lifecycle and measured rendering limits.

## Calendar editor
The optional advanced calendar editor reuses native time controls, checkboxes,
tables and translated dialog buttons. Settings explicitly saves its preferences
before launching the project editor. The project editor previews affected session
IDs and defaults confirmation to Cancel. Invalid edits remain available to correct;
rejected persistence never replaces the live state. Custom calendar presence is
visible even when its editing controls are hidden. The editor follows the existing
navy table header, violet focus outline and semantic control boundaries.
## Reversible course changes and bulk review

The native course toolbar adds optional Undo/Redo and Bulk edit actions, hidden
initially. Bulk selection is native extended row selection, resolved by stable
course code and excluding filtered rows. A protected-focus review dialog uses
existing palette, controls, typography and localized text. Every optional field
has an explicit check box; mixed values and Clear preference are distinct from
Keep value. A read-only, scrollable selection summary and differences table make
large batches inspectable. Changing inputs invalidates the preview. Apply remains
disabled until review and rechecks stale session/selection before one transaction.
Errors remain inline, Cancel writes nothing, and one undo reverses the whole batch.
Native controls, shared i18n wrappers and theme.py remain canonical owners.
## Pending-session placement options
`placement_suggestions` is disabled initially. When enabled, the existing native
session action row exposes **Ver opciones** only for a selected pending session.
The 640×480 review dialog reuses the localized table, focus rings and shared
buttons. It states the current-schedule scope, 30-minute candidate grid and
truncation; rows never move other sessions or create laboratory exceptions.
Assignment requires an explicit selection, fresh-input fingerprint and independent
validation. Changed inputs recalculate and clear selection. The accepted action
uses the same persistence-first command path as manual assignment and supports undo.
Closing, hiding the feature or failed persistence preserves schedule and pins.

## Optional MCP preparation

Settings keeps the existing native Save/Cancel preference contract. A separate
**Preparar complemento MCP / Prepare MCP add-on** action opens a plain-text,
default-Cancel confirmation with validated version and destination. Preparation
copies only the bundled companion, checks integrity and runs a bounded local
probe. Static progress text avoids fabricated percentages and respects reduced
motion without introducing animation. Cancel/close requests cooperative cleanup
and waits asynchronously before releasing the worker; a committed component stays
prepared. Preparation never toggles the permission checkbox or starts a server.

Status is selectable by mouse/keyboard. ES/EN messages distinguish missing bundle,
unprepared component, integrity/version errors, cancellation and ready state. A
native client selector shows read-only, keyboard-copyable JSON using the verified
absolute companion command. OpenCode V2 defaults disconnected; Claude guidance
warns that client restart may start the process. ChatGPT shows manual HTTPS/tunnel
requirements rather than an invalid local config. Copy is explicit and does not
modify client files. Real Qt offscreen lifecycle tests and ES/EN renders cover
these views; native Windows host/packaged acceptance remains a separate gate.


### Guided MCP setup refinement
The existing MCP section uses three native, numbered step headings because the
sequence matters: prepare/check, save local permission, then configure a client.
Saved and pending permission are separate text states. A ready add-on disables
redundant preparation while keeping the read-only check available. Verification
has its own cancellation action. Save waits for a new permission check; selecting
OFF remains saveable without a successful check. No permission or client changes
are inferred from preparation or copying configuration.

The client guide uses the existing localized native combo, labels, JSON text area
and Close button. Numbered instructions retain protocol/configuration details,
commercial-host caveats and separate ChatGPT authorization. At narrow sizes only
the guide body scrolls; Close stays outside, and Tab leaves the JSON area for Copy.
Read-only permission snapshots never replace the preference store's expected
revision. The established stale-save guard still reconciles external changes.
The native Qt/i18n wrappers and theme.py remain the canonical control, focus,
typography and scrollbar owners; no palette or global styling changes are needed.
