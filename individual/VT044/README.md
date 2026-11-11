# BT3 - Nguyễn Công Trí - 23001945 - VT-044

Baseline: `66074f4ecc384b6006ac8b574001a0b4aced86ef` (branch `congtri`).
Individual branch: `bt3/23001945-vt044`. Do not merge before team review.

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
python -m pytest individual/VT044/test_lifecycle.py --cov=individual.VT044.harness --cov-branch --cov-report=term-missing --cov-report=json:individual/VT044/evidence/coverage.json
python -m pytest tests individual/VT044/test_lifecycle.py
python -m individual.VT044.mutate
python -m individual.VT044.check_order
PYTHONPATH=backend:. python -m individual.VT044.load
```

The HTTP load experiment binds **only 127.0.0.1**, uses a temporary SQLite file,
200 synthetic owners/documents, and six sequential requests per task, with all
200 tasks released together. No external service, OCR model or customer data is
used. It saves raw timings and errors to `evidence/load.json` and reports both
request p95 and whole-task p95. A task exception ends that task; consequently
incomplete runs must NOT be reported as 1,200 successful requests. Nonzero exit
indicates errors or incorrect final state. Evaluate the separate
`task_p95_meets_target` field as well; exit zero alone is NOT an SLA assertion.

## Evidence and results

- RED commit contains the tests and a deliberate 501 transition scaffold:
  `911698f5b0a8e9942fb33f1bee7d480dae96b0c9`. Check it out in a separate
  worktree and run the contract suite: 21 failed, 7 passed. `red.log` is the
  assertion-failure evidence. `setup-missing-module.log` is an earlier setup
  error and is explicitly NOT the behavioral RED evidence.
- Final contract suite: 28 passed. Original plus individual suite: 127 passed.
- Coverage of the harness: 91/93 lines; 16/18 branches; combined display 96%.
  Missing branches: absent file and absent extraction.
- Boolean mutation `state.deleted != target` -> `state.deleted == target`
  is killed by the state-cycle test (read returns 200 instead of 404).
  `mutate.py` creates two commits on a disposable temporary Git branch and
  verifies the submission source hash is unchanged. The temporary commits
  are logged, not published or retained as ancestors of this branch.
- Order check: all 28 contracts pass for each seed 44, 1945, 23001945.
- Load: the first and diagnostic run both fail. Do not infer production
  capacity from their request p95 or from final row counts. Raw logs retain
  incomplete request counts and client transport exceptions.

Known gaps: production authentication/authorization, backfilling owners,
migrations, routing all original endpoints through the contract, browser UI,
retention/processing races across the full system, PostgreSQL and sustained
load. Artificial `.png` fixture bytes exercise storage isolation, not image
validation or OCR. Student/team review is still required; no human sign-off
is claimed by these files.
