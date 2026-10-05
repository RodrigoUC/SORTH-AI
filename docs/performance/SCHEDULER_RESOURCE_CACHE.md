# Reusing resource admission inside one group's search

## Scope

Baseline: `3f1b49abc9bfa5fa963364903a6617f8fe89967a`. Measurements were made on
2026-10-04 using CPython 3.12.14, Linux x86-64, glibc 2.41. They measure only
`Scheduler.schedule`; setup, import, validation, quality analysis, profiling and
memory measurement are outside the wall-time samples. They do not measure GUI
responsiveness, spreadsheet loading, rendering, or Windows performance.

The fixture matrix is synthetic and deterministic. It covers regular/lab rooms,
capacity, soft preferences, course restrictions, all three resource catalog
kinds, unknown/declared availability, shared memberships, exact off-grid split
pins, custom calendar breaks, split families and an intentionally saturated
partial result. No institutional data is included.

## Change and correctness boundary

Resource eligibility is independent of the room. During one group's domain
construction or greedy candidate evaluation, its identity/duration, resources
and current assignments are fixed. A fresh local checker therefore reuses the
result for the same `(day, start)` across rooms. The checker is replaced for the
next group and every later pass/run; no result is reused after assigning a group.
No cache is added to mutable schedule state or the resource catalogs.

The final `ScheduleState.assign` call still performs an uncached resource check.
Candidate traversal, score priorities, tie-break random draws, retries and
per-candidate cancellation checkpoints remain unchanged. The production result
validator is unchanged. Cache storage is proportional to the temporal candidates
for one group, not to the number of rooms or total groups.

The regression module compares against the original uncached resource rule for
36 combinations of data/solver seeds, including assignment insertion order,
domains, unassigned reasons, exact PRNG state, split pins and a manual lab
exception. Further tests cover deny results, exceptions, rebuilding after edits,
reuse across runs, domain and greedy cancellation, and bounded cache entries.

## Reproduction

Run from `project_root`, with the normal development environment (without `-O`):

```sh
python tools/benchmark_scheduler_matrix.py --repeats 5 --out build/reports/scheduler-candidate.json --profile --memory
python tools/benchmark_scheduler_matrix.py --root /path/to/trusted-baseline-checkout --repeats 5 --out build/reports/scheduler-baseline.json --profile --memory
python tools/benchmark_scheduler_pair.py --baseline-root /path/to/trusted-baseline-checkout --repeats 10 --out build/reports/scheduler-paired.json
python -m pytest -c pytest.ini --rootdir=. -q tests/test_scheduling/test_scheduler_resource_cache.py tests/test_scheduling/test_benchmark_matrix.py
```

`--root` intentionally executes scheduling modules from the supplied checkout;
only use a trusted, reviewed source checkout. The paired tool executes both
scheduler classes in one process and rejects the baseline if any other scheduling
module differs; use the separate matrix runs for broader source changes. Both runs use the same fixture
builder and seed 42. The JSON records per-run samples, assignment hashes,
assignment counts, quality results and constraint validation. Each matrix run
rejects nondeterministic assignments. Compare the assignment hashes, quality
results and assigned counts between baseline/candidate before interpreting time.
`--profile` and `--memory` perform separate untimed runs; traced peak allocations
are not process RSS. Avoid concurrent CPU-heavy tests when comparing timings.

## Results

Final paired measurements and exact validation results are recorded in
[scheduler-resource-cache.json](scheduler-resource-cache.json). Wall-time samples
alternate baseline/candidate order ten times per fixture, using fresh objects
and `gc.collect()` before each run, outside the timed region. The collector stays
enabled during scheduling.
The separate five-run matrix also produced identical assignment and quality
results for all eight fixtures. The saturated case remains partial rather than
counting missing sessions as a performance success.

The 120-group, 12-room resource fixture improved from **6.7219 s to 0.9467 s**
(medians), a **7.10× speedup**, with all 120 groups assigned identically. Peak
traced allocations increased from 10,163,422 to 10,178,976 bytes: 15,554 bytes
(about 0.15%). Resource-free cases are not accelerated: medians range from 0.9%
faster to 3.6% slower (small absolute overhead from the local callable wrapper).
The 360-group resource-free fixture remains approximately 1.52 s, and the
saturated case remains exactly 93/180 assigned. These results do not demonstrate
better search quality or feasibility of the unassigned sessions.

The resource fixture's profile identifies the intended cause: calls to
`ScheduleState.resources_allow` fall from 269,996 to 29,379, while the number of
candidates scored and RNG draws remains 94,220. Before the change, resource
admission accounts for 23.45 of 24.45 profiled seconds. Profiling overhead is
substantial; use unprofiled samples for speed comparisons.

Full correctness still requires the documented four-process suite on the final
integrated revision. Linux/offscreen tests are not Windows release acceptance.

## Verification on the candidate

- Independent production-code and benchmark-method review: no correctness blocker.
- New focused modules: 49 passed, including 36 exact seeded differential cases.
- Required complete collection/four-process sequence: 2,998 unique selected tests;
  1,673 GUI + 190 GUI-layout + 24 theme-runtime + 1,099 remaining passed.
  Coverage verification passed with no omitted or duplicate selected tests.
- The base environment has 12 selected skips: 10 native Windows PowerShell cases,
  one optional MCP case, and one live Bandit contract. Two additional optional
  MCP modules are skipped during collection in that base environment.
- Supplemental optional-MCP environment: all 98 MCP tests passed without skips.
  Security contracts passed in the separate security environment, including the
  live analyzer contract omitted by the base environment.
- Bandit static review: completed, no new findings and no baseline suppression
  changes. Architecture boundaries, dependency consistency and diff checks passed.
- Both benchmark CLIs completed smoke runs; ordinary and paired hashes agree.

The final integration must repeat the applicable checks after other branches are
combined. Native Windows-only cases remain unexecuted here; this is not release
acceptance or a claim about native desktop responsiveness.
