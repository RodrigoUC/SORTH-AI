# Cooperative generation cancellation

Cancellation is always-on internal safety, not an optional tool. `SchedulingCancelled`
is separate from algorithm/data errors. Checkpoints cover domain rooms/days/start
candidates, groups, candidate filtering/scoring, retry passes and result publication.
The service builds isolated copies; no cancelled intermediate result reaches persistence.
The GUI also rejects queued results after cancellation and from superseded workers.
Close requests cancel cooperatively and defer destruction until the worker finishes;
the event loop is never synchronously blocked and threads are never force-terminated.

Evidence: deterministic checkpoints 1, 2, 4, 10, 50, 100, 200 and 500; late
publication cancellation; actual Qt worker cancellation on 3,000 synthetic sessions;
prior schedule, pins and persisted bytes preserved; subsequent runs work. The actual
worker test has a two-second watchdog on this Linux development fixture. This is a
regression budget, not a measured promise for Windows, file import or arbitrary data.
File-reader calls and Python deepcopy are not preempted inside external library work.
Native Windows cancellation latency remains a release-acceptance measurement.
