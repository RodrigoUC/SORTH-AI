# Placement suggestions (optional)

Enable **Opciones de ubicación / Placement options** in Settings. Select a pending
session and choose **Ver opciones / View options**. Suggestions use the current
schedule, room restrictions/capacity/type, split-session rules, current project
calendar and stored resource memberships/availability. Existing sessions do not
move; pinned sessions cannot be reassigned and no LAB exception is created.

The pure service reuses scheduler domains on the calendar's 30-minute grid plus exact preferred/split-sibling starts, then
independently validates every candidate against the full schedule. It examines at
most 2,000 domain candidates and shows at most 100 options by default. The UI
explicitly reports limited results. Other exact times remain available through
manual assignment. Empty results do not prove global infeasibility or optimality.

Assignment requires a selected row and rechecks a fingerprint of all validity
inputs. A stale review recalculates and requires a new selection. The final apply
validates again and commits through persistence-first edit history. Cancel,
disable, I/O failure and stale inputs never assign or move a session.

Tests cover domain/independent-validator equivalence on the declared grid, bounds,
no results, lab restrictions, split sessions, pins, custom time models, teaching
resource availability/conflicts, stale revisions, forged choices, Qt review,
persistence failure, undo/redo, feature restart and ES/EN names. Screenshots and
latency samples are development evidence; native Windows QA remains outstanding.
