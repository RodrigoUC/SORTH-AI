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

A nonempty set of assignments does not imply completeness. The status explicitly
labels a partial result (including zero assigned with expected groups) and shows
assigned/expected counts. Pending sessions remain visible in the detailed list.
The export action is named “Export all assignments”, describing scope rather than
claiming every requested session was scheduled. Both full-scope and filtered
export dialogs and completion messages retain a partial-result warning with the
pending count. Filtering does not remove the warning about the source schedule.
CSV/Excel retain the existing seven-column contracts and sheet structure. They
contain assigned sessions only; pending sessions/reasons remain in the app and
are not additional rows in those interchange files.

Static reasons explain missing laboratories, insufficient capacity, excluded
rooms, and durations that cannot fit. Otherwise the message states that the
search did not find a placement and recommends reviewing constraints or manual
placement. Greedy failure is not proof of mathematical infeasibility. A fixed
seed supports reproduction, not completeness or optimality. Cancelling export
leaves the current result and filters unchanged; a generation exception remains
an error, not an infeasibility claim.

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
[Español](docs/validation/partial-es-960.png) ·
[English](docs/validation/partial-en-960.png).
Both show 1/2 scheduled sessions, one pending LAB without an available laboratory,
an enabled export of assigned sessions, and explicit partial status.
