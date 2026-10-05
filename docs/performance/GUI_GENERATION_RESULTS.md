# GUI generation result payloads

## Observed problem and narrow change

A real generated result retains each group's candidate search domain, including
references to copied solver classrooms. On the next accepted generation or edit,
`MainWindow._persist_edit_state` deep-copies the previous group values for atomic
rollback. A 1,000-group synthetic result retained 2,652,000 candidate tuples; its
second completion callback blocked the GUI thread for about **5.64 seconds**.
A separate 500-group profile attributed 5.35 of 6.27 profiled seconds across the
two completion callbacks to `deepcopy`. Profiled times are excluded below.

`SchedulerWorker.run` now clears these worker-owned domains after scheduling and
before emitting its result, with a cooperative cancellation check for each group
and the existing final check before emission. The scheduling service creates fresh
groups; caller inputs, scheduling decisions, assignments and group metadata are
unchanged. Placement suggestions build fresh candidate domains from accepted
inputs. CLI and MCP continue using the unchanged service.

The production change is seven lines. Rollback snapshots, validation, Qt thread
ownership, synchronous view materialization and the SQLite transaction are
unchanged. No event pumping, deferred partial result, background widget access,
cache or new dependency is introduced.

## Measurements, 2026-10-04 UTC

Baseline `04f2d4cb59ddc49bc6f911d29f6cc5a0a0b76207` versus that tree with only the
worker cleanup applied. Python 3.12.14, PyQt 6.11.0, Qt runtime 6.11.2
(headers 6.11.0), Linux x86_64/glibc 2.41,
offscreen Qt. Three fresh processes per size and version; medians below. All
processes used the same diagnostic harness and interpreter, ran serially, and
kept a shown 1200×900 main window and real SQLite session in an isolated temporary
directory. Shared-host scheduling is not controlled.

| Groups | First completion, ms before → after | Second completion, ms before → after | Second-completion heartbeat gap, ms before → after | Process peak RSS, MiB before → after |
|---:|---:|---:|---:|---:|
| 100 | 39.00 → 40.47 | 103.39 → 45.27 | 110.82 → 52.53 | 146.58 → 142.33 |
| 500 | 228.35 → 182.00 | 1,612.30 → 221.89 | 1,624.64 → 232.62 | 299.16 → 198.46 |
| 1,000 | 316.12 → 324.79 | 5,636.39 → 415.72 | 5,644.76 → 425.01 | 746.41 → 350.04 |

The 1,000-group repeat callback is about 13.6× faster; the process high-water mark
is about 53% lower. These ratios do not describe first generation or the solver.
At 1,000 groups, repeat persistence including view materialization fell from
5,611.87 to 391.15 ms. The repository call itself, including rendering, was
330.88 versus 376.06 ms: the eliminated cost is the preceding rollback copy,
not faster SQLite storage. Stage timings are nested and must not be added.

Repeat worker wall time, including result cleanup, was 55.97 → 59.84 ms,
1,232.54 → 1,377.95 ms, and 4,463.26 → 4,723.74 ms at the three sizes. The
cleanup was not timed separately, so the observed worker-wall increase cannot
be attributed entirely to it rather than shared-host variance. The background
thread still shares Python's GIL. Pooled heartbeat intervals wholly
inside the repeat worker phase had p95/max of 26.42/182.28 → 68.33/264.24 ms at
500 groups, and 21.91/268.63 → 21.45/253.61 ms at 1,000. The 100-group repeat workers
were too short to provide wholly contained heartbeat samples. Clearing domains
substantially reduces the subsequent GUI freeze; it does not eliminate all
worker-phase stalls or improve worker throughput.

Repeated filters remained comparable: handler p95 across 45 search/room/day/reset
operations per size was 33.22 → 33.03, 8.56 → 8.85 and 15.30 → 13.06 ms.
Seed-change autosave medians were 4.08 → 3.90, 10.24 → 11.08 and 21.26 → 20.38 ms.
Grid/list/classroom round trips were exercised; grid-entry handler p95 at 1,000
was 6.28 → 16.22 ms (nine entries, including three first renders). These
consultation measurements do not establish an improvement from this change.
P95 uses nearest rank; with three or nine samples it is the maximum, not a
well-characterized tail estimate.

First population still takes roughly 0.3 seconds at 1,000 groups. There is no
60fps claim, monitor-present latency measurement, Windows speed claim, leak
analysis or institutional-data performance guarantee. Native Windows remains a
separate acceptance step. RSS includes Python, Qt and solver allocations; it is
not a measurement of only the domains or of live Qt allocations.

## Synthetic fixture and reproduction protocol

- Sizes: 100, 500 and 1,000 groups; two 60-minute regular-room groups per course,
  hence 50, 250 and 500 courses. Codes `C0000`, `C0001`, etc.; names
  `Synthetic course 0000`, etc.; enrollment 25.
- Rooms: `max(2, ceil(groups / 60))`, hence 2/9/17 regular classrooms, each capacity
  40. Default six-day calendar, 07:00–22:00 and 12:00–13:00 break. No resources,
  pins, restrictions or course preferences in the timing fixture; regression
  tests cover those result metadata and safety contracts separately.
- Load inputs and save once, show the window, allow 500 ms idle, then call the
  real `_generate_schedule` using seed 42. Keep a 10 ms precise Qt timer running
  throughout; wrap methods only for timestamps and use the ordinary event loop.
- After generation finishes, allow 300 ms idle, then perform three cycles of grid
  entry, room selection, searches `course 000`/`course`, global room/day filters,
  reset, classroom tab and list tab. Separate operations by 200 ms.
- Change seed to 43 through its spin box (real autosave), enter the grid, generate
  again, and verify every assignment against both the database and the independent
  schedule validator. Verify both table row counts and all requested groups.
- Completion time covers `_on_schedule_done`, including validation, rollback
  capture, table/grid materialization, transaction commit and history/status work.
  Heartbeat gaps crossing completion include the surrounding event-loop delay.
  Worker-only p95 excludes gaps that cross the completion boundary. These are
  timer intervals, not display frame times. A direct signal observer timestamps
  worker results; thread scheduling can move that observation slightly relative
  to the receiving GUI callback.
- Use process `ru_maxrss` for Linux high-water RSS and `/proc/self/status` for
  live RSS. Use a separate process for cProfile; never mix profiled samples with
  ordinary timings or run benchmarks concurrently with test suites.

The standalone diagnostic `profile_gui.py` is retained with the audit evidence,
not imported or shipped as application code. Its SHA-256, the candidate worker's
SHA-256, environment and individual timing samples are in the
[raw measurement summary](gui-generation-worker-domains.json). Commands used with
that diagnostic, substituting the two checkout paths and the same Python 3.12
virtual environment, were:

```sh
python profile_gui.py --root BASELINE_CHECKOUT --groups 1000 --regenerate --out baseline1000.json
python profile_gui.py --root CANDIDATE_CHECKOUT --groups 1000 --regenerate --out candidate1000.json
```

Repeat each command in fresh processes three times for each of 100/500/1,000.
The harness isolates its Qt configuration/cache/data and temporary SQLite file.
Its optional `--profile` run is diagnostic only. It does not add a CI timing gate.

All six before/after final assignment digests matched at every size, and all
persistence/validator/population/table checks passed. New focused tests cover
worker/service/caller isolation, complete metadata, GUI-thread signal delivery,
cancellation during and after cleanup, real repeat generation followed by
renderer or late-commit rollback, and rebuilt suggestions with undo/redo. Existing
full-suite and platform acceptance remain separate checks, never inferred from
these timings.
