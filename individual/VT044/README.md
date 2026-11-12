# BT3 - Nguyễn Công Trí - 23001945 - VT-044

Baseline: `66074f4ecc384b6006ac8b574001a0b4aced86ef` (branch `congtri`).
Individual branch: https://github.com/teamfuturetime/document-inteligence/tree/bt3/23001945-vt044
Published at the user's explicit request. Do not merge before team review.

This is an **executable contract harness**, permitted by the assignment's
fallback, built on the actual `Document`, `Extraction`, `DocumentRepository`,
`LocalStorage` and SQLAlchemy database helpers. It is NOT mounted in the real
API. That API has a shared API key and no document owner identity. Demo tokens
and the sidecar owner/tombstone table are experiment fixtures, not production
security. See `PLAN.md` for the two evidence-based assumption rejections.

## Reproduce

Follow `RUN_ORDER.md` to review and reproduce requirements **1 -> 2 -> 3 -> 4 -> 5**
in the teacher's order. The report uses the same five numbered groups, spread
across eight main pages, followed by the permitted appendices.

From the repository root, with Python 3.12:

```bash
python3.12 -m venv .venv-vt044
source .venv-vt044/bin/activate
python -m pip install -r backend/requirements-dev.txt
python -m pytest individual/VT044/test_lifecycle.py --cov=individual.VT044.harness --cov-branch --cov-report=term-missing --cov-report=json:individual/VT044/evidence/coverage-reproduced.json
python -m pytest tests individual/VT044/test_lifecycle.py
python -m individual.VT044.mutate
python -m individual.VT044.check_order
PYTHONPATH=backend:. python -m individual.VT044.load --transport asgi --output individual/VT044/evidence/load-asgi-reproduced.json
PYTHONPATH=backend:. python -m individual.VT044.load --transport stdlib --output individual/VT044/evidence/load-http-reproduced.json
```

The real HTTP load experiment binds **only 127.0.0.1**, uses a temporary SQLite file,
200 synthetic owners/documents, and six sequential requests per task, with all
200 tasks released together. No external service, OCR model or customer data is
used. `--transport asgi` uses the same app/workload in-process without sockets;
it is NOT a real-network measurement. The script saves raw timings, per-request
status/payload-validation records and errors to `--output`, and reports both
request p95 and whole-task p95. A task exception ends that task; consequently
incomplete runs must NOT be reported as 1,200 successful requests. Exit zero
requires every request to be valid, correct final data AND whole-task p95 <= 5s
in the selected transport's scope. It is never a production SLA assertion.
Both new drivers start all task clocks at their common barrier release, so
post-barrier scheduling is included. No retries are used in either driver.

### HTTP connection profiles (12/11/2026)

The default `--connection-mode cold` retains the original experiment: all 200
tasks open NEW connections at the measured barrier. That profile still has
connection errors on this Mac; p95 below 5s does not make it a passing run.

To separately measure 200 concurrent API workflows on established connections:

```bash
PYTHONPATH=backend:. python -m individual.VT044.load --transport stdlib --connection-mode preconnected --output ../output/BT3_23001945_tu_chay/load-http-preconnected.json
```

This profile prepares 200 separate connections with 200 validated GET requests
before the barrier, then starts all 200 measured workflows together. The output
records `setup_requests=200`, `setup_seconds`, `setup_in_task_latency=false`,
`requests=1200` and `total_http_requests=1400`. No retries or concurrency
reduction are used. Setup is excluded from measured latency, so a pass here
does NOT prove cold-connection capacity or replace the previous failing runs.
Three CLI runs passed all 200 workflows, p95 1.337/1.171/1.128s. See
`HTTP_LOAD_NOTES.md`, `LOAD_FIX_PLAN.md` and `evidence/http-diagnostics/` for all
outcomes, including experiments that did not resolve the original failure.

## Evidence and results

- RED commit contains the tests and a deliberate 501 transition scaffold:
  `911698f5b0a8e9942fb33f1bee7d480dae96b0c9`. Check it out in a separate
  worktree and run the contract suite: 21 failed, 7 passed. `red.log` is the
  assertion-failure evidence. `setup-missing-module.log` is an earlier setup
  error and is explicitly NOT the behavioral RED evidence.
- Initial contract suite: 28 passed, regression 127 passed. Completion suite:
  **34 passed**, original plus individual tests: **133 passed**.
- Completion coverage of the harness: **93/93 lines and 18/18 branches**.
  New tests cover missing file/extraction, expired active reads and contention
  with four owner/four foreign requests on the SAME document in each phase.
  Original coverage evidence (91/93, 16/18) is preserved separately.
- Boolean mutation `state.deleted != target` -> `state.deleted == target`
  is killed by the state-cycle test (read returns 200 instead of 404).
  `mutate.py` creates two commits on a disposable temporary Git branch and
  verifies the submission source hash is unchanged. The temporary commits
  are logged, not published or retained as ancestors of this branch.
- Order check: all **34** contracts pass for each seed 44, 1945, 23001945
  (`order-completion.log`). The original 28-case order log is retained.
- Initial HTTP runs fail (37/44 transport errors). The two stdlib HTTP runs
  also fail overall: 199/200 and 195/200 successful tasks; p95 1.118/1.031s;
  one/five connection resets. Low p95 alone is insufficient.
- ASGI controlled run: **200/200 successful tasks, 1,200/1,200 valid requests,
  zero errors, task p95 1.136s <= 5s** (`load-asgi.json`). This isolates the
  app/DB/storage contract; it does not prove error-free network capacity.
- The student personally rejected the shared-key assumption during completion
  review; the exact response and its timing are in `evidence/student-review.md`.

Known gaps: production authentication/authorization, backfilling owners,
migrations, routing all original endpoints through the contract, browser UI,
retention/processing races across the full system, PostgreSQL and sustained
load. Artificial `.png` fixture bytes exercise storage isolation, not image
validation or OCR. The student has confirmed personal review and commitment;
the actual response is recorded in `evidence/student-review.md`. Team review
is still required before merging and has not been claimed.

`REQUIREMENTS.md` maps every assignment item to evidence. The GitHub branch
above contains the tests, patch and logs; no PR or merge is required to use the
branch link for submission. The student has now confirmed personal review and
the responsibility statement. No Classroom submission has been made by the agent.

## Fresh GitHub clone verification

`REMOTE_AUDIT.md` records a fresh clone from GitHub, verification of all four
baseline/RED/patch/completion commits, and re-execution of RED, GREEN, mutation,
coverage, order and load checks. Raw logs are in `evidence/remote-audit/`.
Anonymous GitHub API access returned 404; a successful clone in this session
does not prove a grader has repository read access. Ensure that access before
submission. `REVIEW_GUIDE.md` separates real project modules from demo fixtures.

## Report export (optional)

`BT3_23001945.md` contains five requirement groups across eight main pages,
plus the AI Usage Log and execution-log appendices.
To export it, install the optional `reportlab` package, then run:

```bash
python individual/VT044/build_report.py individual/VT044/BT3_23001945.md BT3_23001945_VT-044.pdf
```

The exporter uses macOS Arial TrueType fonts for Vietnamese. `VT044_FONT_DIR`
can point to another directory containing the same Arial font filenames.
The application/test dependencies do not require ReportLab.
