# Completion review plan - recorded before the follow-up code

Starting commit: `8a776e4` on local branch `bt3/23001945-vt044`.
The user supplied the same VT-044 requirements again and requested all of them.
The earlier explicit instruction to keep the branch/files local still applies.
No push, PR, merge, or Classroom submission is authorized by this follow-up.

## Actual student review

The student answered the agent's assumption-review question on 11/11/2026:

> Bác bỏ: key chung không phân biệt chủ sở hữu tài liệu

This rejects the assumption that the existing shared API key provides per-user
document authorization. Evidence: `require_api_key` returns no user identity;
`Document` has no owner field. This human response occurred during completion
review, after the original harness was written; do not backdate the response or
claim the student reviewed every line of code or approved the final commitment.
The original plan/assumptions preceded the original implementation, as recorded
in `PLAN.md` and commit `911698f`.

## Remaining improvements and assumptions

1. The contract harness remains a valid assignment fallback. Do not expand into
   production authentication, migrations or frontend without a supporting need.
2. Add independent-session contention tests on the SAME document, alongside
   foreign-user attempts. Add meaningful missing-file, missing-extraction and
   active-expiry failure checks; keep existing RED/mutation evidence intact.
3. The two original load runs contain transport failures. Do not call them a
   production-capacity result. Add a stdlib HTTP load transport to isolate the
   async-client stack, keep 200 concurrent tasks and the same six-step workload.
   No retries or reduced concurrency. Preserve both original run artifacts.
4. Include explicit successful/failed task counts, raw per-request results,
   correctness checks, latency method and an exit code that requires both
   correctness AND the p95 target. Confirm all 200 extractions/confirmations
   survive, not merely that no tombstone remains set.
5. Run the suite, coverage, mutation and shuffled order with the new cases;
   update the eight-page report with exact new results and actual human input.
6. Add a requirement-to-artifact audit and a local handoff package. The GitHub
   branch/PR deliverable remains outstanding by the user's explicit choice;
   do not invent a working branch link. Student code review/commitment and
   Classroom submission also cannot be asserted by the agent.

Expected files: `test_lifecycle.py`, `load.py`, `check_order.py`, README,
`evidence/*-completion.*`, `REQUIREMENTS.md`, Markdown report and PDF export.
No production module changes are planned. Reassess transport and p95 from
observations, without selecting a run merely because it passes.

## Adaptive step after the two preplanned stdlib runs

Both stdlib runs still report ConnectionResetError while making the initial
socket connection (199/200 and 195/200 tasks succeed). The async-only exception
is therefore not a sufficient root-cause explanation. Before changing the load
driver again, add an explicitly labelled ASGI in-process mode to isolate the
network boundary, using the SAME 200 tasks and six-step assertions, with no
retries. This is a controlled harness measurement, NOT real network throughput
or production SLA evidence. Retain all four real-HTTP outcomes in the report.
