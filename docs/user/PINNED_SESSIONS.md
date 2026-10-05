# Pinned sessions / Sesiones fijadas

Issue: https://github.com/RodrigoUC/SORTH-AI/issues/12

Select an assigned session in either table and choose **Fijar sesión / Pin session**.
The same button unpins it. Pinning is explicit; manual edits and preferences do
not create pins. The visible status begins with **Fijada / Pinned**, independent
of color. Unpin before moving/removing a pinned session or clearing the schedule.

Identity is the course code + group ordinal, with a part ordinal for split
sessions (`CODE-G1-P1`). Renaming the displayed course keeps identity; changing
its code does not. A pin keeps its exact room, day, start and end. Split parts
are pinned independently; remaining parts still require different days and the
same start. Changing the number of split parts, a pinned part's duration,
removing its course/group/room, capacity or restrictions is reviewed against all
pins before commit. Compatible edits keep valid pins and mark all other sessions
pending. An incompatible edit/import offers **cancel** (default; preserve all
inputs and schedule) or explicitly unpin *all* and apply. No automatic remapping.
Changing the duration of an unpinned sibling alone is permitted if the pinned
part's identity, duration and split-part count stay valid.

Reimporting a changed repeated-code course with saved resource relationships or
pins additionally requires explicit positional-identity review, even with optional
Excel preview disabled. This lists the affected associations and pins, preserves
the existing ordinal IDs only after confirmation, and never remaps them to rows.
Ordinary orphan and incompatible-pin reviews still apply afterward. Identical
normalized rows cannot reveal their reordering; see
[Excel import review](EXCEL_IMPORT_WORKFLOW.md#revisión-obligatoria-de-asociaciones-por-posición).

Generation validates all pinned assignments together using the independent
validator, then reserves their occupancy on isolated copies. Greedy passes and
retries skip them. Confirmed manual LAB exceptions are carried only for their
specific pinned sessions; all hard constraints still apply. Partial results
remain partial. The main thread checks both validity and unchanged pins before
accepting a result. Generation failure preserves the last accepted schedule.
**Cancelar generación / Cancel generation** discards a running result and leaves
pins/schedule untouched. This cancellation is cooperative at the worker boundary:
it waits for the isolated calculation to finish, never terminates a live thread.

## Persistence and rollback

Schema 2 adds `assignments.pinned` with default false and a 0/1 check. Migration
keeps courses, placements, enrollment, suggestions, restrictions, LAB exceptions
and metadata. Existing sessions are never automatically pinned. A consistent
pre-migration SQLite backup is made first. Migration and saves roll back on
failure; failed saves remain visibly unsaved. Older schema-1 applications reject
schema 2. To roll back an application version, preserve the schema-2 database
and restore its pre-upgrade schema backup; never open or overwrite v2 with an
older executable. Named scenario snapshots must copy the complete database.

## Evidence and limits

Synthetic service tests cover repeated regeneration, different seeds, collisions,
unknown rooms/courses, capacity/restrictions, LAB overrides, partial schedules and
split parts. Native Qt tests cover explicit pin/unpin, sorting identity, guarded
edits/import cancellation, restoration, rejected generation and cancelled results.
SQLite tests cover v1 migration/backup, pin/LAB round-trip and transactional failure.
Linux offscreen captures at 960×640 cover ES and EN; native Windows screen-reader
and packaged executable testing remain release-platform checks.
