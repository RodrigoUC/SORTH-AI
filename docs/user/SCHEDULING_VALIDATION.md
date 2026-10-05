# Scheduling validity and truthful partial results

The application validates generated results before presentation and persistence,
restored results before presentation, proposed manual edits before acceptance,
and the whole current schedule before either full-scope or filtered export.
Invalid generation results are not substituted for the prior result. Invalid
restored schedules enter recovery mode and cannot overwrite the original session.
Legacy LAB-to-regular placements without a recorded manual exception are removed
and shown as pending, retaining the existing migration behavior.

## Hard rules represented by this version

- Each group identifier is unique and each assigned group/room exists.
- A placement has one room and integer day/start/end values (not booleans,
  fractional values, missing fields, or malformed tuples).
- The assigned duration matches the group; day and interval are within operating
  bounds; no overlap with the lunch interval.
- Room capacity is sufficient. LAB sessions require a LAB unless the user has
  explicitly confirmed the manual exception. That exception does not relax
  capacity, time, collision, course-room restrictions, or split-session rules.
- Assignments never overlap in the same room on the same day. Touching endpoints
  are allowed.
- Both directions of the existing reserved-course-room rule are enforced. A
  reserved room only accepts its allowed courses; the reverse rule applies when
  the group's suggested room belongs to the reserved set for its course.
- Parts of a split group occupy distinct days with the same start time.

Preferred day/time and a suggested room outside the reserved-room rule are soft
preferences. Regular sessions may use laboratories. The model does not include
teacher availability, teacher collisions, student cohort/curriculum collisions,
campus travel times, institutional holidays, or arbitrary resource calendars.
Validation must not be represented as a guarantee about those unmodeled rules.
The low-level ScheduleExporter formats assignments; callers outside the supported
application/service flows must validate domain constraints before calling it.

## Partial, empty, failed, and exported results

The GUI also checks the worker's complete group population against the requested
courses, including every split-session part, before accepting its result. Missing,
extra, duplicate, or changed request-derived group metadata rejects the result
and preserves the previous schedule. Reordering groups is allowed. This is a
defensive result-boundary check, not evidence that the normal scheduler omits
groups. A partial assignment set remains valid when all requested groups are
present, so unscheduled sessions retain their pending status.

A nonempty set of assignments does not imply completeness. The status explicitly
labels a partial result (including zero assigned with expected groups) and shows
assigned/expected counts. Pending sessions remain visible in the detailed list.
The export action is named “Export all assignments”, describing scope rather than
claiming every requested session was scheduled. Both full-scope and filtered
export dialogs and completion messages retain a partial-result warning with the
pending count. Filtering does not remove the warning about the source schedule.
The seven-column CSV and Excel assignment tables contain assigned sessions only.
Desktop Excel adds Estado/Pendientes for partial or filtered exports, retaining
global completion counts and pending IDs/reasons separately from the exported
assignment subset. Filtered-out assignments never become pending. Complete,
unfiltered Excel retains its previous sheet structure; CSV remains an
assignments-only interchange format. See [export scope](SCHEDULE_EXPORT_NOTES.md#excel-parcial-y-filtrado).

Static reasons explain missing laboratories, insufficient capacity, excluded
rooms, and durations that cannot fit. Otherwise the message states that the
search did not find a placement and recommends reviewing constraints or manual
placement. Greedy failure is not proof of mathematical infeasibility. A fixed
seed supports reproduction, not completeness or optimality. Cancelling export
leaves the current result and filters unchanged; a generation exception remains
an error, not an infeasibility claim.

## Export filenames and replacement

The save picker retains the system's native behavior and Excel, CSV and PDF
filters. Only supported extensions (`.xlsx`, `.csv`, `.pdf`, case-insensitive)
override the selected format. Otherwise SORTH retains the entered basename and
appends the selected format's extension, including for version/date names such
as `horario.v2` or `horario.2026.10.03` and unknown extensions such as `.txt`. If that resolved destination already exists, SORTH asks before
replacing it; No is the default, and dismissing the question preserves the file,
schedule, filters and previous export status. Supported explicit extensions keep the
existing dispatch behavior and the picker's own overwrite confirmation, without
a second prompt. A successful export replaces its destination atomically; a
failed write preserves the prior file and reports the failure.

## Reproducible verification

Run `QT_QPA_PLATFORM=offscreen python -m pytest -q` from project_root on Linux
(or set QT_QPA_PLATFORM in PowerShell). Added boundary tests use a separate
interval oracle across 288 day/start/duration combinations, collision endpoint
cases, malformed restored placements, duplicate IDs, room restrictions,
capacity, split groups, injected invalid scheduler output, and presentation,
restore, partial/empty status and export boundaries. Existing mixed-seed tests,
small feasible/impossible cases and explicit manual Yes/No exception tests remain.
Offscreen verification is not native Windows, Excel or print acceptance.

Synthetic partial-result captures at 960×640 (Linux Qt offscreen):
[Español](../evidence/validation/partial-es-960.png) ·
[English](../evidence/validation/partial-en-960.png).
Both show 1/2 scheduled sessions, one pending LAB without an available laboratory,
an enabled export of assigned sessions, and explicit partial status.
