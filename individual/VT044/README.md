# BT3 - Nguyễn Công Trí - 23001945 - VT-044

Baseline: `66074f4ecc384b6006ac8b574001a0b4aced86ef` (branch `congtri`).
Individual branch: `bt3/23001945-vt044`, LOCAL ONLY at the user's request.
No GitHub branch or PR has been published. Do not merge before team review.

This is an **executable contract harness**, permitted by the assignment's
fallback, built on the actual `Document`, `Extraction`, `DocumentRepository`,
`LocalStorage` and SQLAlchemy database helpers. It is NOT mounted in the real
API. That API has a shared API key and no document owner identity. Demo tokens
and the sidecar owner/tombstone table are experiment fixtures, not production
security. See `PLAN.md` for the two evidence-based assumption rejections.

## Reproduce

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
validation or OCR. Student/team review is still required; no human sign-off
is claimed by these files.

`REQUIREMENTS.md` maps every assignment item to local evidence and identifies
the outstanding GitHub link, student final review/commitment and Classroom
submission. No remote branch/PR or external submission has been created.

## Report export (optional)

`BT3_23001945.md` contains eight main sections/pages plus two appendix pages.
To export it, install the optional `reportlab` package, then run:

```bash
python individual/VT044/build_report.py individual/VT044/BT3_23001945.md BT3_23001945_VT-044.pdf
```

The exporter uses macOS Arial TrueType fonts for Vietnamese. `VT044_FONT_DIR`
can point to another directory containing the same Arial font filenames.
The application/test dependencies do not require ReportLab.
