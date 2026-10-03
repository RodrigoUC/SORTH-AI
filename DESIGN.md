# SORTH desktop design

## Product and audience
Spanish-first native PyQt6 application for academic timetable planning. The primary task is reviewing courses, generating a schedule, checking pending sessions and exporting the result. Spanish and English are selectable in the masthead. Additional locales use a central language registry and independent catalogs; see `docs/development/LOCALIZATION.md`.

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
See `docs/development/ACCESSIBILITY.md` for inventory, shortcuts and outstanding
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
where to reactivate controls. See `docs/user/OPTIONAL_FEATURES.md`.

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
`docs/user/EXCEL_IMPORT_WORKFLOW.md` for lifecycle and measured rendering limits.

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

Settings action labels reflow using native multiline button/checkbox text when
platform font metrics exceed the scroll viewport. The localized source Message,
full accessible name, font size, click target and native keyboard behavior remain
intact. Widening the window or switching ES/EN reflows from the original message;
no caption is clipped, abbreviated, or progressively wrapped. Save/Cancel remain
outside the scroller. Geometry tests cover native-default/Fusion/Windows styles
at 460×420, including enlarged font metrics and narrow→wide→narrow transitions.
The first Settings show, viewport resize and locale change reflow synchronously;
zero timers only coalesce later layout/style work. Save/Cancel use a native
vertical button box when their horizontal minimum cannot fit, including width-only
font changes. Qt layout tests wait for bounded, stable native geometry and retain
zero-overflow, exact-window-size and complete-action-visibility assertions.

## Distinct course blocks

`src/scheduling/course_style.py` is the Qt-free source for course fills, accents
and markers shared with printable schedules. Sixteen muted blue, teal, violet,
sage and neutral pairs extend the established identity. CRC32 of the literal
course code chooses a permanent pair and an independent solid, dashed, dotted or
double marker; rooms, sort order, filters, language and process restarts cannot
reassign it. A finite palette can repeat: the code/name, marker and physical
boundaries identify courses without relying only on color. Red remains reserved
for room conflicts; pinned-session wording remains explicit.

The classroom grid uses one native item delegate, never per-cell child widgets.
Each session span has a 3px white inset, contrasting 1px outline and course edge.
Bold session code, exact time and course name are left aligned for scanning;
long names wrap to two lines and elide only in paint. Full plain text remains in
the model, tooltip and accessible text, and the detailed list stays available.
Selection uses a violet ring with a white separator without erasing course color.
Native keyboard navigation, exact minute boundaries and schedule data are retained.
Runtime-font-derived minimum heights keep short sessions readable. Text contrast
is at least 4.5:1; accents against fill and white gutters are at least 3:1.

Real Qt paint tests cover gutters, repeated fills with different markers,
selection, conflicts, filtering, multiple rooms, restart identity and ES/EN.
Synthetic Fusion/offscreen captures cover 1440×1060, 1200×900 and 960×720 plus
empty/filtered/short-session states. This remains development evidence rather
than native Windows or screen-reader acceptance.

### Settings section navigation
Settings uses one native section selector and one body scroll area, with General,
Academic resources, Advanced tools and MCP connection presented independently.
A single-column native combo remains usable at 460×420 and with enlarged fonts;
its keyboard arrow keys select sections, retaining every unsaved checkbox value.
The selector and Save/Cancel remain outside the body scroller. Below 520px tall,
the duplicate header gives way to the native window title and visible section
heading. Compact shell insets and gaps preserve reading space without reducing
fonts. Section navigation uses concise names (General, Resources, Advanced, MCP);
the body keeps full headings. The compact save status keeps its full meaning in
its accessible description, including the exact unsaved-change count. The application
navy header, white reading surface, teal Save and violet focus use existing
semantic tokens in theme.py. No new palette, dependencies or web components.

The persistent footer counts unsaved preference changes across all four sections;
returning a checkbox to its saved value removes that change. Reopening reads the
committed preferences. The count reads MCP permission without replacing its
expected save generation. Separately confirmed MCP preparation remains immediate
and is not included in the preference count. During an owned MCP operation the
MCP section stays visible so its progress and cancel action remain discoverable.
General opens initially; optional features still begin OFF. Native Save/Cancel,
resource confirmation, recovery, conflict checks and MCP safeguards are unchanged.

Section containers have zero horizontal insets inside the established scroll
content margins. ResponsiveActionLabels and ResponsiveDialogButtonBox remain the
canonical owners of label wrapping and footer stacking. ES/EN catalogs own all
new copy. Native Qt tests visit every section at 460×420 in Fusion/Windows styles,
with both standard fonts and 20pt controls/labels; verify zero horizontal overflow,
complete footer bounds, accessible names and keyboard cancellation. Linux captures
are development evidence, not packaged Windows or screen-reader certification.

Settings follows focus changes inside the section body with native
ensureWidgetVisible, so Tab, Shift+Tab and programmatic MCP-cancel focus reveal
the focused control even when it is nested in a section. Selectable MCP status,
permission and save-state labels explicitly participate in the native tab order.
The keyboard regression traverses every section without test-side scrolling.


### Native settings metric safeguards
Action wrapping uses each widget as the QTextLayout paint device and checks the
resulting native minimum-size hint. If native chrome changes after wrapping, it
reduces only the text-wrap budget, preserving the original Message, full text,
accessible name and font. A strictly decreasing budget bounds this correction.
Changed nested section layouts refresh before the outer content minimum is read;
no scrollbar is hidden to conceal overflow. Short-window mode uses 8px shell
insets, 6px gaps and 12px body insets. It updates only when crossing the height
threshold, not on every width change.

Geometry regressions visit each active section rather than trusting stale hidden
Qt widget rectangles. CI writes untruncated settings-geometry JSON reports with
section, visible child hints, actual font DPI, viewport and fixed-chrome sizes.
A larger logical-DPI144/20pt stress run is additional evidence, not a substitute
for the native Windows run.

Settings checkboxes reserve a transparent 2px border in their resting state;
focus changes only its color. This keeps Qt's Fusion native/style-sheet sizing
paths consistent during retranslation and focus changes without fixed heights.
The regression compares fresh native CT_CheckBox sizing and text-content height
as well as cached minimumSizeHint, because the latter can hide a stale focus-state
size on some platforms. Other application checkboxes retain their existing chrome.

## Selectable native appearance

`project_root/src/gui/theme_contract.py` is the single Qt-free v1 validator used
by the application and `.agents/skills/sorth-theme-designer`. A theme supplies a
complete, strictly validated data-only palette (30 opaque colors, bounded plain
text and at most 16 KiB UTF-8); it never supplies QSS, asset paths, fonts, code or
remote resources. `ThemeSpec` is frozen and defensively copies its color mapping.
The structural schema and contrast checks stay in that canonical owner.

`src/gui/theme.py` owns built-in Original claro, Nocturno and Alto contraste claro,
the dynamic read-only `COLORS` mapping, canonical QSS, and Active/Inactive/Disabled
QPalette roles. Header, heading and on-primary-soft are separate semantic roles;
selected input text uses on-accent. Original keeps the incumbent canonical palette,
typography and density. Previously independent literal-colored summary cards and
recovery headers now use validated semantic soft surfaces and foregrounds; these
small legacy treatments are deliberately not pixel-identical to the old palette.
Native Qt controls, i18n wrappers, selection helpers and responsive layout remain
canonical. No external design dependency or browser component is introduced.

QSS and palette changes apply to the existing QApplication, never to OS settings.
Owned dialogs, lists, text editors, menus, combo popups, tooltips, status areas and
headers follow the selected appearance. `refresh_theme()` updates only cached
pending-row and time-gutter brushes with item-change notifications blocked; it
never repopulates a model, clears a filter, regenerates a schedule or saves domain
data. Native system file pickers and window chrome can retain the operating
system's appearance. Palette tests do not establish full accessibility compliance.

Sort-arrow paths are trusted internal assets separate from imported color roles.
The runtime draws arrows using validated on-header into in-memory Qt resources,
retaining bundled white sort arrows for the original palette. Trusted checkmarks
and input arrows likewise use validated foreground roles and require no writable
temporary directory. No external paths or
content are read from a theme. Course category fills, accents, markers, text and
export palettes remain owned by the scheduling/export code. Classroom course
cards retain an explicit white gutter/separator and a fixed dark-red/pale-red
conflict presentation. Only the selection outline follows the theme's focus role,
validated against that fixed white separator as well as adjacent theme surfaces.

`src/gui/theme_preferences.py` owns one versioned appearance JSON record containing
both the selected key and complete normalized theme. It is independent of optional
feature flags, MCP/provider permissions, language, reduced motion and session data.
Deleting the source import file does not change the saved appearance. Writes use
QSaveFile with direct-write fallback disabled and verify byte counts and commit.
A cooperative writer lock and expected snapshot reject stale saves. A failed write
leaves both the prior saved record and live theme intact. A successful commit is
the success boundary, even if a subsequent verification read becomes unavailable.
Malformed or future records display Original and leave the exact bytes untouched;
replacement requires explicit recovery and first creates an exact sibling backup.

Appearance uses a separate Apply/Cancel transaction. `preview_theme(widget, spec)`
styles only a dialog-owned representative subtree. Preview never saves or changes
the main UI; Cancel therefore leaves the current appearance and all other unsaved
settings intact. Restore original selects a candidate and still requires Apply.
Apply validates and persists before updating the shared application. A post-commit
refresh failure is reported separately as saved-but-incomplete, and remaining
controls still update; it never claims the former theme is still active. Reopening
Appearance rereads the external preference snapshot without silently applying it.
Imported
metadata renders as plain text. AI-generated files pass the same validator and
preview, without activating a provider, network call or paid service in SORTH.

Verification includes strict contract/contrast tests, actual Qt palette/paint and
repeated light/dark/high-contrast changes, preservation of drafts/focus/selection/
filters/scroll and course identity, atomic failures, corruption/recovery, restart
and deleted import sources. Fusion/offscreen captures are genuine Qt development
evidence; packaged Windows/native chrome and screen-reader acceptance remain
separate release checks.

Appearance action wrapping also accounts for the preview frame, nested layout
insets and allocated grid column; an old oversized content minimum cannot keep
horizontal overflow alive. Native Resize/LayoutRequest notifications settle the
same controls in place. The shared footer wraps any individually over-wide
Message caption before choosing horizontal or vertical layout. It always starts
from the complete localized source, preserves the full accessible name and font,
and unwraps on widening. No scrollbar, action or text is hidden to meet width.
Native-metric stress tests cover every built-in preview, ES/EN, Fusion/Windows
styles, 20pt fonts, narrow/wide boundaries, selection/focus and idle timer state.
CI retains Appearance control/font geometry JSON alongside strict assertions.
Wrapping reuses the complete caption rendered by the existing localization
boundary, never a previously wrapped display string. Native fitting therefore
cannot re-enter translation callbacks during parent LanguageChange propagation;
setText and locale changes still refresh both source text and accessible names.
Responsive controls distinguish generated full-caption accessible names from
explicit names. A generated name follows Message or literal caption replacements
and drops obsolete translation bindings; an explicitly assigned name remains
independent through wrapping, text changes and locale changes. The helper still
uses already-rendered canonical text and never translates during native fitting.

### Schedule consultation height budget
The schedule shell uses three independent, deterministic presentation budgets.
Selection-help captions and retained-data notices return above 760px. Secondary summary/resource chrome
returns above 802px; below that it remains in the established native F7 menu.
Dense gaps/insets remain through 920px, so the full chrome can fit four readable
rows before spacious margins return. The native 2px focused-frame cost is included. No mode decision reads the current viewport,
avoiding responsive feedback or oscillation. The thresholds are verified on both
sides with actual native metrics and every optional feature restored.

The viewer uses 2px inter-row gaps in dense mode, retaining native fonts, table
row heights, action targets, the visible scope line and existing F6/F7 routes.
Spacious windows restore the 6px viewer gaps. Counts, filters, details and exports
retain their existing semantics; no preference or domain data changes.

Regressions save/reopen the session/preferences and check ES/EN, all three shipped
themes, native-default/Fusion/Windows styles, optional tools OFF/all ON, all three
consultation tabs and tall→short resize. The native viewport retains at least
four 30px row heights at every tested size, including 759/760/761, 799/800/801/802/803/804 and
919/920/921/922. No font, row, scope visibility or exact-size assertion is relaxed.

Main-tab navigation completes its synchronous native chrome/layout update before
the existing 150ms reveal starts. It does not pump events or queue user input.
This prevents a responsive resize from canceling the new reveal; actual external
resize, hide, close and reduced-motion preferences retain their cancellation rules.

### External-AI theme creation guide

Appearance offers a small native **Create a theme with AI** guide with three
explicit steps: copy, generate in the user's chosen external AI, then import and
review. The read-only, selectable specification derives its structural schema and
contrast pairs from `theme_contract.py`; there is no second compatibility contract.
Only revalidated colors and mode enter the example template. Imported names and
descriptions are replaced by fixed safe examples because plain text can still be
instructions to an AI. No course, timetable, source filename or project data enters
the guide. Clipboard writes require the Copy action. No provider, browser launch,
account, credentials, network call, paid call or template file export is added.

The guide uses shared native localized controls, semantic focus, responsive action
wrapping, and a persistent Close footer. Tab leaves the specification editor;
focus reveal considers its whole frame rather than only its input cursor. Compact
460×420 and 20pt layouts retain the same controls and font. Closing returns focus
to the Appearance entry. Import result closes the guide and invokes the existing
bounded JSON picker/validator; validation errors remain selectable in Appearance.
The guide explicitly says AI output can be invalid. Opening, copying, canceling,
and rejected imports do not save or apply anything. Appearance's existing
Apply/Cancel/Restore and atomic recovery contracts remain the only commit path.
