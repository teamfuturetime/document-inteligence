# Field review autosave — Issue #7

Implementation base: main `921541d`; `git merge-base --is-ancestor fb24bc1 HEAD`
succeeded, verifying CONS-01 ancestry rather than relying on issue closure.
Worktree branch: `feat/7-field-review-autosave`. Original `minhthao@760ccdc`
and its uncommitted changes are preserved.

## Mapping and source lineage

PR #2 / `bt3-vt043-autosave@55e9c74`, particularly `OCRTextCard.tsx`,
informed request serialization, retained draft and explicit recovery. That work
edits readable OCR text (`ocr_revision`, `ocr_text_cleaned`) on `minhthao`.
No second application or raw-text schema was copied into this product.

Here `run.spans` is raw OCR evidence and `run.fields` is immutable machine
prediction. `review.fields` contains user decisions; `review.effective_data`
is computed by the backend. Autosave writes only changed review fields.
Omitted field means retain its saved decision. `{is_reviewed:true,
reviewed_value:null}` means deliberately clear it. `is_reviewed:false` restores
the machine prediction; it does not modify OCR or extraction.

## Contract and concurrency

`PUT /api/v1/documents/{id}/review` receives `run_id`, `expected_revision`,
`expected_status` and `fields`. Example:

```json
{"run_id":"run-id","expected_revision":2,"expected_status":"draft","fields":{"seller_name":{"is_reviewed":true,"reviewed_value":null}}}
```

Response remains `DocumentDetail`. App API version is 0.3.0; invoice/export
schema 1.0.0 is unchanged. Generated OpenAPI, ReviewRequest schema and TS types
come from backend models. No database migration is required; rollback reverts
the code and generated contracts, without rewriting revisions.

The existing SQLite `BEGIN IMMEDIATE` transaction protects latest-run,
revision and now status checks plus revision insertion as one operation.
409 `REVISION_CONFLICT` / `STALE_RUN` / `REVIEW_STATE_CONFLICT` preserves
local edits and requires comparison. Status CAS is needed because confirm
updates the same revision in place. A delayed draft autosave must not reopen
a confirmed revision. Explicit manual save from a confirmed view supplies
`expected_status=confirmed`, creating the next draft revision.

For compatibility, omitted/null `expected_status` preserves the legacy manual
save contract. Old API clients therefore do not receive the additional status
guard. All writes from this UI supply status. Trí should review this additive
contract and decide whether a future API version must require status for every
external client; this patch does not claim to enforce that on legacy clients.

## State and recovery

- Editing/pending: changes are stored immediately; debounce is 800 ms.
- Saving: one write at a time, typing remains enabled; manual save shares the
  same lock. ACK removes only captured field objects, preserving subsequent
  edits even to the same field. New edits save against the acknowledged revision.
  Serializing requests prevents same-panel response inversion by construction.
- Saved: no pending changes. Confirm/export stay disabled while dirty/saving.
- Failed: network error, 15-second abort or rejected HTTP response retains edits;
  no automatic retry loop. Manual retry can discover 409 after an ambiguous ACK.
- Conflict: fetch server detail, compare values, then explicitly keep local edits
  using that revision or discard them. A server reprocess cannot be rebased onto
  another run. Comparison itself does not apply local edits.
- Confirmed: no background autosave; explicit manual save reopens review.
  Confirm and export use persisted server revision, never the browser draft.
- Navigation/unmount cancels debounce, not an already accepted server write.
  Late callbacks do not update the unmounted component; recovery must compare
  the server because a disconnected request might already have committed.

Changed fields only are kept in same-origin **sessionStorage**, keyed by
document and run, with a 24-hour recovery validity window. No token, source
image, full OCR or prediction is stored. This is the ADR0008 local single-user,
synthetic/sample scope: there is no authenticated user identity to key by.
Auth/multi-user work must redesign the namespace and cleanup on logout.
ACK/discard removes the entry. Expired entries are ignored; session storage is
not encrypted and expired bytes can remain until the tab/session closes.
Storage failure displays a warning. Recovery always pauses writes until server
comparison. Reload in the same tab can recover; browser/OS restart and closing
the tab are not guaranteed. Persisted server drafts survive backend restart.

## Local plan and review

One atomic #7 implementation: API status guard plus contracts/regression test;
frontend autosave plus ordering/recovery tests; then feature documentation and
evidence. Each completed unit is committed separately. No GitHub comments,
push or PR are published by this task. Proposed reviewers remain
`congtri2103` (contract/CAS) and `tuanqtb123-creator` (browser acceptance),
without claiming their confirmation or review.

## Verification on 15 November 2026

Windows, Python 3.14.5 installed through uv 0.12.22 in ignored runtime tooling;
locked backend environment. Node 26.13.0/npm 11.20.0 differ from repository pins
24.16.x/11.13.x; locked `npm ci --ignore-scripts --no-audit --no-fund` succeeded.

- Baseline frontend: 12 tests passed and typecheck passed.
- Red phase: three new frontend tests failed before implementation (debounce,
  pending edits across ACK, recovery). Backend status-race regression failed
  with the guard disabled: late save returned 200 instead of 409.
- `backend/.venv/Scripts/python.exe -m pytest backend/tests pipeline/tests -q`:
  132 passed, zero skips/failures. Includes real SQLite concurrent save CAS,
  null, export authority, persistence and reprocess regressions; OCR is a test
  double here, not native inference evidence.
- `npm --prefix frontend test`: 21 passed. New cases include debounce,
  serialized pending edits, unmount recovery, HTTP 401/403/422/500 retention,
  network failure/manual retry and explicit confirmed reopening.
- Typecheck, ESLint, production build, Prettier, frontend contracts check:
  passed. Ruff check/format passed across backend/scripts/pipeline.
- Contract generator check: 25 passed; repository/docs checker, data manifests
  and six fixture evaluator contract cases passed. Generated evaluator reports
  were restored to baseline; no new benchmark is claimed.
- Native `scripts/verify_product.py`: failed at `ocr_ready` assertion before
  upload. No native success or new model accuracy claim.
- `npm --prefix frontend run test:e2e` (uv available on PATH, loopback servers
  started with disposable runtime): 1 failed before test steps because the pinned
  Playwright Chromium executable is absent. No browser scenario passed.

Pending acceptance: real browser/native flow on the final commit; sustained
two-tab interaction, timeout behavior, recovery after full browser restart,
and review by Trí/Tuấn. Session recovery tests are component tests, not proof
of browser restart durability. Auth enforcement is outside the single-user
platform; mocked 401/403 tests verify retention only. Do not propose `Closes #7`
until remaining acceptance and reviewer decisions are resolved; use `Refs #7`.

| Requested cases | Evidence / remaining work |
| --- | --- |
| TC01–03 | Component tests: debounce, continuous edits, pending snapshot after ACK |
| TC04 | One in-flight request prevents concurrent same-panel writes; late unmounted ACK is ignored in code; browser response-delay scenario pending |
| TC05 | Existing SQLite concurrent CAS test and component 409 comparison; real two-tab browser test pending |
| TC06 | Network rejection/controlled retry tested; actual 15-second timeout browser case pending |
| TC07 | Component remount recovery and existing persisted backend restart test; no full browser restart guarantee |
| TC08 | Existing explicit-null component and backend immutable-prediction/null tests |
| TC09 | Shared in-flight ref and disabled manual save while saving; dedicated simultaneous browser interaction pending |
| TC10–12 | New backend confirm/delayed-autosave/export/reopen regression plus existing workflow tests; browser acceptance pending |
| TC13 | Rejected HTTP retention component tests; backend latest-run/transition checks; no auth is implemented by this platform |
| TC14 | Debounce cancelled on unmount and draft recovered in component test; navigation guards retained |
| TC15 | 132 backend/pipeline and 21 frontend regressions pass; native/browser run blocked as recorded above |
