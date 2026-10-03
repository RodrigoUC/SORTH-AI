# Measured editor optimizations

This comparison isolates the editor optimizations: local baseline `dd82aeb` →
optimization-only tree `cecaa3e`. It does **not** compare final integrated
scheduler-v2 outputs against v1. Scheduler-v2 intentionally changes assignment
tie-breaking and provenance; integration must verify its own outputs.

## Workload and method

Synthetic 100 / 1,000 / 5,000 distinct courses, one 60-minute regular-room session
per course, and 2 / 17 / 84 rooms. Resource validation gives each session a distinct
teacher. History renames one course with a real validator and stubbed persistence.
Scenario comparison uses valid supplied assignments and supported metadata.
Calendar defaults, seed 42, no pins. The generation control uses preferred
room/day/start to bound candidate domains; it is not a worst-case search test.

Python 3.12.14, PyQt/Qt 6.11.0, Linux x86_64, offscreen Qt, Fusion style.
Each median has **three repeats after one excluded warm-up**. CPU and wall samples
are recorded separately; core and 100-row UI runs are separate to avoid retained
Qt-object/collection effects. These are observations, not CI timing thresholds.

## Median wall time (milliseconds)

| Operation | 100 before → after | 1,000 before → after | 5,000 before → after |
|---|---:|---:|---:|
| Final resource validation | 1.52 → 0.82 | 85.24 → 8.40 | 2,107.04 → 48.15 |
| Accepted history edit, excluding persistence/UI | 9.97 → 6.61 | 106.43 → 69.09 | 640.17 → 461.90 |
| Scenario comparison | 1.61 → 1.47 | 19.24 → 15.56 | 253.96 → 97.20 |

The visible **100-row course-table refresh** fell from **1,558.59 to 11.86 ms**
(including event processing). Larger baseline UI timings are deliberately omitted:
that path stalled during the initial bounded investigation. Do not extrapolate a
large-table ratio. CPU closely tracks wall time; raw samples are linked below.

The changes batch header sizing during table replacement, index final-validation
assignments by resource/day, reuse canonical history bytes within one transaction,
and index quality intervals by room/day. There are no cross-session caches.

## Correctness, tradeoffs, and limits

- Matching benchmark output checks: accepted-state fingerprints, full scenario
  comparison digests, generation assignment digests/counts at every size, empty
  resource notices, and the visible table's course-code inventory.
- Resource tests compare exact ordered notices with the unchanged admission rule;
  quality tests use an independent minute-set occupancy oracle. History tests
  preserve failure rollback, byte limits, out-of-band invalidation and detached
  state ownership. GUI tests cover filtering, sorting, selection and mode restore.
- Snapshot safety copies remain. Separate tracemalloc history peaks stayed roughly
  **12.8 MB**: accepted edit 12,877,192 → 12,765,698 bytes; no-op
  12,760,280 → 12,873,170 bytes. No meaningful memory reduction is claimed.
  These are Python allocations, excluding native Qt and process RSS.
- Resource/quality indexes use additional temporary memory proportional to stored
  memberships/assignments. Genuine shared-resource conflicts still require work.
  Mutable candidate admission is unchanged; only final validation is indexed.
- Native Windows interaction/rendering still needs its own smoke check. No Windows
  speed claim, total import speed claim, or database/storage-speed claim follows
  from these Linux/offscreen measurements. Untouched generation was 217 → 228 ms
  at 5,000 in this bounded fixture; no generation improvement is claimed.

## Reproduce

From `project_root`, use the **same benchmark script** against each source tree:

```bash
QT_QPA_PLATFORM=offscreen XDG_CACHE_HOME=/tmp/sorth-benchmark-cache \
  python tools/benchmark_editor_operations.py --ui-max-size 0 --output core.json
QT_QPA_PLATFORM=offscreen XDG_CACHE_HOME=/tmp/sorth-benchmark-cache \
  python tools/benchmark_editor_operations.py --sizes 100 --ui-max-size 100 --output ui.json
```

Defaults are `--sizes 100 1000 5000 --repeats 3`. Larger candidate UI tests require
explicit `--ui-max-size 5000`; fixtures are capped at 5,000. Use the baseline's
supported dependencies and a writable cache directory. Timing samples never
produce pass/fail assertions. Compare the `correctness` fields only between
algorithm-compatible builds; do not require v1/v2 generation hashes to match.

Raw evidence: [baseline core](editor-operations-before-core.json),
[optimized core](editor-operations-after-core.json),
[baseline UI](editor-operations-before-ui.json),
[optimized UI](editor-operations-after-ui.json).
