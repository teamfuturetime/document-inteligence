# BT3 - 23001948 - VT-045

Project AI-02, team SE2026-T11. A small R05 validation-policy change, not a full
upload/OCR/VLM/review implementation. No production endpoint was added.

- Baseline: `52067697c1e4505eb36042e5fbe525ed984d2637`.
- Test-first/red: `6e96e302f3e8c97920e8da660e166357f1ec94fa`.
- Production patch/green: `178cd3abac8af94be089ae45ca15a911d782a5f0`.
- Branch: https://github.com/teamfuturetime/document-inteligence/tree/hw3/23001948-vt045-config-contract
- Final PDF: [BT3_23001948_VT-045.pdf](../../output/pdf/BT3_23001948_VT-045.pdf).
- [Specification / pre-code plan review](spec-and-plan-review.md),
  [test cases / traceability](test-strategy.md), [AI usage](AI_USAGE_LOG.md).

## Run from repository root (PowerShell, CPython 3.13)

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt
./.venv/Scripts/python.exe -m pip install -r homework/VT-045/requirements-tools.txt
./.venv/Scripts/python.exe -m pytest -c backend/pytest.ini backend/tests/test_invoice_policy.py -q
./.venv/Scripts/python.exe homework/VT-045/experiments.py regression
./.venv/Scripts/python.exe homework/VT-045/experiments.py repeat
./.venv/Scripts/python.exe homework/VT-045/experiments.py mutate
./.venv/Scripts/python.exe homework/VT-045/experiments.py load
```

Mutation requires local Git worktree/commit permissions and configured Git name
and email. It creates a detached temporary commit, saves its diff/hash and test
failure, then removes the worktree. It never modifies the submitted source.
Load starts/stops one loopback Uvicorn child on an available port; needs local
socket access, not Internet. Every request is checked against a full outcome oracle.
Optional real OCR regression tests skip if Tesseract/vie is absent; policy tests
do not need OCR, a model, key, database or browser. Evidence files are overwritten
when explicitly rerunning experiments; retain original committed logs as needed.

## Change the policy

Edit ONLY `backend/config/invoice-policy.json`: keep policy_version
`invoice-policy-1`; set integer max_total_amount between 0 and 9007199254740991.
Deploy the file by atomic replacement. Next validation call reads the new policy;
invalid configuration raises InvoicePolicyError, without fallback or success data.
The shipped maximum preserves previous acceptance. Test/example values 100000
and 200000 are synthetic limits, not requirements from an accounting stakeholder.
Keep this file in deployment; missing config intentionally stops validation.

## Evidence and limitations

`evidence/`: baseline531 pass; meaningful red assertion; final561 pass; branch
coverage JSON/text; first fixture mistake; five repeats; temporary mutation patch
and real failed assertions; 3x100 loopback HTTP requests with latencies and outcome
checks. Empty load-server.txt means no warning/error output, not missing evidence.
The first mutation infrastructure failure is retained and NOT counted as a kill.

PDF main body is eight pages; appendices contain AI Usage Log and selected raw
execution logs. Full raw logs and executable tests are in this branch. The report
generator is build_report.py (requires Windows Arial fonts or adjust FONT_DIR).
PDF can be rebuilt with `./.venv/Scripts/python.exe homework/VT-045/build_report.py`.
No merge. Student must read the diff, validate policy intent and review/adopt the
AI-assisted reflection before submitting; no human approval is fabricated.
