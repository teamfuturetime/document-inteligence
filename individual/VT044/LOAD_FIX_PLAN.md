# HTTP load failure investigation - plan before changes (12/11/2026)

User run: 200 simultaneous tasks, 176 successful, 24 fail before any response;
22 ConnectionResetError, one BrokenPipeError, one TCP_NODELAY OSError(22).
The result must remain a failed run even though p95 is below 5 seconds.

## Assumptions to test

1. Failure may be at initial connection establishment rather than the lifecycle
   business rule: every failed task has zero response records. This does not
   prove the server application is uninvolved; collect controlled evidence.
2. macOS reports `kern.ipc.somaxconn=128`, whereas the client opens 200 sockets
   at once. This is a possible connection-burst limit, NOT a proven root cause.
   TCP aggregate counters available here report zero listen overflow.
3. Uvicorn's auto event loop/protocol may contribute. Compare with explicit
   asyncio/h11 before changing the default. Preserve 200 tasks and six steps,
   include initial connection time, and use no retries.

## Plan

- Preserve the student's raw JSON under evidence before further runs.
- First run a controlled asyncio/h11 experiment without editing lifecycle code.
- If cold connections remain unreliable, compare an explicitly labelled warm
  connection mode. Prepare connections before the measured barrier; record all
  warm-up requests separately. Do not report that as a fix for cold connection
  capacity or mix its latency with prior cold runs.
- Keep original cold mode available. No retry, client throttling, fewer tasks,
  sysctl changes, or production authentication changes are authorized/needed.
- Add only the smallest driver change supported by observations, plus useful
  tests of validation/metrics if those logic paths change. Re-run regression.
- Record all outcomes, update README with precise reproduction instructions,
  and preserve failed measurements. Report uncertainty rather than asserting an
  OS/server/library root cause from the exception name alone.

## Observations before the patch

All runs still use 200 cold connections at the common barrier and no retries:

- asyncio/h11: 200 successful, zero errors, task p95 1.207922s.
- asyncio/auto HTTP (resolved to httptools): 200 successful, zero errors,
  task p95 1.148157s.
- auto loop/h11: 194 successful, six errors, task p95 1.116208s.

Installed `auto_loop_setup` selects uvloop on this machine. These observations
support choosing `asyncio` for this local driver; they do NOT prove a universal
uvloop bug or that the OS listen limit is the root cause. Warm-up is unnecessary
and will NOT be introduced. The minimal patch makes the event loop explicit,
defaults to asyncio, records the configuration, and keeps `--server-loop auto`
to reproduce the earlier mode. HTTP protocol, cold connection timing, load,
business code and assertions remain unchanged.

## Repeat check rejects a premature loop-only conclusion

Three preplanned repetitions of asyncio/auto HTTP produced 190/200, 200/200,
200/200 successes. Thus changing the loop alone is NOT a reliable fix and must
not be advertised as one. Preserve those failed/passing outcomes together.

Next controlled change: put Uvicorn in a spawned process with its OWN engine
and Python interpreter/GIL, instead of sharing a process with 200 client
threads. Keep the original auto loop/protocol, all 200 cold connections, the
same barrier, six assertions, no retries and no warm-up. Use a startup queue to
confirm the child is listening (no extra HTTP probe), record both PIDs and the
actual loop/protocol, and retain `--server-mode thread` for legacy comparison.
No kernel limits will be changed. Adopt the process driver only if all three
preplanned repetitions meet correctness and p95; otherwise continue diagnosing.

## Final comparison and scope decision

Separate-process cold runs also failed (131/200, 176/200, 179/200). Both the
process refactor and loop-only default change were therefore discarded.

A controlled preconnected-client profile, retaining the ORIGINAL server
architecture/auto loop and all 200 measured tasks, passed all three planned
runs: 200/200, 1,200 valid measured requests, zero errors, p95 1.119/1.120/1.161s.
Each run separately performed 200 validated setup GETs in 0.170/0.204/0.172s.
No retries, artificial pauses, kernel changes or load reduction were used.

Implement ONLY an optional `--connection-mode preconnected` flag in the stdlib
driver. The default remains `cold` and retains the user's original workload and
failure result. Record setup requests/timing separately and clearly exclude
setup from measured task latency in the new profile. Do not call this a fix for
cold connection capacity or assert that the exact OS/library cause is proven.
Run the actual CLI profile three times plus regression before publishing.
