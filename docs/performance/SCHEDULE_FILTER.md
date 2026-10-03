# Schedule consultation performance

## Scope and implementation

Always-on internal optimization; no feature switch or scheduling-algorithm change.

- Normalize domain search strings once per schedule refresh/removal. Matching still
  uses Unicode NFKD, case folding, accent removal and AND matching across words.
- Read filter widgets/normalize the query once per filter pass; evaluate each
  known session once. Both tables and the grid use the resulting session IDs.
- Change Qt row visibility only when it actually differs. Sorting remains native
  and row identities continue to come from `UserRole`, never cached row numbers.
- Inactive grid changes coalesce behind a dirty flag. Entering the grid renders
  the latest state synchronously; unchanged tab round trips reuse it. Visible
  grid filtering remains immediate. No debounce timer or stale export window.
- Removing/replacing/clearing data invalidates keys. Pin refresh and language
  changes invalidate grid presentation without changing searchable domain data.
- Filtered exports evaluate the current filters independently of active tab/local
  grid classroom. Complete exports and authoritative assignments are unchanged.

## Reproduce

From `project_root`, using the project's development environment:

```sh
QT_QPA_PLATFORM=offscreen python tools/benchmark_schedule_filter.py \
  --sizes 100 1000 5000 --repeats 5 --output /tmp/filter-results.json
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

Benchmark source introduced at `88ce1fd157e05e2810bf7d50f21d85f619fb3b59`
(baseline application `4de7373a6f43626aa1d33a3330f6c70b73b654b2`).
Optimized application: `8a38ca19b52b7c02c74a05db212ff66bbc9c29c0`.
Run each revision in its own worktree with the same interpreter. Do not run other
benchmarks/tests simultaneously. This is a comparison tool, not a timing gate.

Deterministic fixtures contain 100/1,000/5,000 groups, 80% assigned, Unicode names,
20 room identifiers (16 have assignments), five weekdays and eight time slots.
Dense same-room conflicts are intentional stress cases. Six broad/narrow/no-match
queries run twice as warm-up then five measured cycles: 30 samples per view/size.
Median and nearest-rank p95 include synchronous `setText` handling and Qt
`processEvents`; `events_only` separately reports the post-handler event flush.
The window is shown at 1200×800 with Fusion style on the offscreen Qt platform.
This is not a monitor-present latency measurement or a Windows UI test.

## Measured results, 2026-10-03 UTC

Linux 6.18.44 x86_64/glibc2.41, Intel Xeon Platinum 8370C @2.80GHz,
Python 3.12.14, PyQt/Qt 6.11.0, Fusion/offscreen. Shared-host scheduling is not
controlled; repeated raw results are included, rather than claiming precision or
native Windows timing. No dependencies changed.

Primary pass, milliseconds (median / p95), filter through event processing:

| Groups | View | Before | After |
|---:|---|---:|---:|
| 100 | List | 6.70 / 10.36 | 3.28 / 6.43 |
| 100 | Grid | 7.16 / 10.93 | 4.22 / 6.75 |
| 100 | Classroom | 5.65 / 8.68 | 2.91 / 5.80 |
| 1,000 | List | 24.23 / 29.93 | 9.11 / 20.63 |
| 1,000 | Grid | 34.75 / 47.91 | 10.70 / 12.60 |
| 1,000 | Classroom | 23.10 / 28.12 | 7.64 / 10.08 |
| 5,000 | List | 98.32 / 141.84 | 36.47 / 59.24 |
| 5,000 | Grid | 153.44 / 227.20 | 36.88 / 62.05 |
| 5,000 | Classroom | 97.10 / 141.69 | 34.81 / 56.16 |

Independent repeat at 5,000: list 98.04/142.79 →39.63/60.30;
grid 170.45/427.20 →38.82/68.33; classroom 97.62/138.80 →36.78/58.96.
Small-workload medians also improved on the repeat: list 6.01→3.72,
grid 7.06→4.48, classroom 5.39→3.06. Shared-host p95 outliers remain visible
in the raw data. No substantial small-workload filtering regression observed.

End-of-run cumulative process peak RSS was 201,100→202,712 KiB (repeat
201,436→202,740 KiB), about 1.3–1.6 MiB additional peak. `ru_maxrss` is a
process high-water mark including Qt/Python allocations across sizes, not live
cache size, leak detection or memory attribution. The initial 5,000-group load
still takes roughly 1.7–2.1 seconds here; this change targets repeated filtering,
not virtualizing the table's initial population. There is no claim that loading
or every frame now meets a 16ms budget.

Raw reports: [before](schedule-filter-before.json),
[before repeat](schedule-filter-before-repeat.json),
[after](schedule-filter-after.json), [after repeat](schedule-filter-after-repeat.json).
Each records environment, initialization time, event-only timing, sample count
and cumulative peak RSS. The comparison supports localized optimization rather
than a wholesale Qt model/view rewrite; remeasure on native Windows and actual
institutional scale before considering that larger change.

## Regression verification

The focused suite checks reference-equivalent results across all room/day/status
combinations, accent/case/multiword/no-match queries, removal and replacement,
sorted selection identity, clearing selection when hidden, pin preservation,
language changes, lazy grid entry, repeated navigation, immediate filtered exports
and the existing complete CSV/Excel export paths. Existing grid tests now enter
the grid tab before inspecting its intentionally lazy cells.

Final core run: 592 passed, 12 skipped, 3 subtests passed. The skipped tests are
existing optional/platform conditions, not newly disabled checks. Static security
review passed with no new findings (`tools/security_review.py static`). Native Windows timings, screen-reader
behavior and monitor-present visual QA remain outside this Linux offscreen run.
