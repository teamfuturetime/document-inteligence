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

Response remains `DocumentDetail`. App API version is 0.3.1; invoice/export
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

Omitted/null `expected_status` now means **draft**, preserving legacy draft
saves while refusing writes to confirmed records. Explicit `confirmed` remains
required to reopen, alongside the latest revision. A rejected legacy write leaves
both the confirmed revision and export unchanged. This intentionally narrows the
old implicit-reopen behavior; old clients must opt in to reopen confirmed records.
No database migration is needed. Generated request descriptions document this rule.

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

Changed fields only are kept in same-origin **localStorage**, keyed by document,
run and a random editor-mount identifier held only in memory;
no token, source image, full OCR or prediction is stored. Draft values are
restricted to known review fields. This remains ADR0008 local single-user,
synthetic/sample scope; auth/multi-user must add user namespacing and logout
cleanup before using this mechanism.

Draft recovery is valid for 24 hours; expired entries for the opened document/run
are removed when recovery runs (there is no background physical deletion of
unopened documents). ACK/discard removes only the **current editor's** entry.
Recovery never transfers ownership of a source key: even an unchanged recovered
source can belong to another live editor. Source entries are left for their owner
or expiry cleanup, so an old draft may appear again after reload until it expires.
The user must compare it with the server; it is never automatically replayed.
Recovery selects the newest available draft for the run; it does not merge
competing browser drafts. All recovery is paused until explicit server comparison.

Reload and normal browser-process restart with the same profile are tested.
Browser data clearing, incognito disposal, storage denial/quota and OS/disk loss
cannot guarantee recovery. Storage is not encrypted. Storage failure warns users
to save/copy before leaving. Already persisted server drafts survive backend
restart independently of browser storage. Existing pre-change session-only draft keys are copied to durable storage before
removal from session storage; migration recovery still requires server comparison.

## Local plan and review

One atomic #7 implementation: API status guard plus contracts/regression test;
frontend autosave plus ordering/recovery tests; then feature documentation and
evidence. Each completed unit is committed separately. No GitHub comments,
push or PR are published by this task. Proposed reviewers remain
`congtri2103` (contract/CAS) and `tuanqtb123-creator` (browser acceptance),
without claiming their confirmation or review.

## Initial verification on 15 November 2026 (before follow-up review)

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

## Follow-up review and final verification ? 15 November 2026

Read the three original commits cc461ce/54f6ecb/bfb7db8 against 921541d,
including generated schema/type changes, revision transactions, Workspace
navigation and confirm/export flows. No changes were made on minhthao.
This section supersedes the initial pending matrix above.

| Severity | Verified finding | Disposition |
| --- | --- | --- |
| Critical | None verified | No speculative fixes |
| High | Omitting or nulling expected_status allows legacy PUT after confirm at the same revision to create a draft | Two regression cases returned 200 instead of 409. Reviewer-only patch prepared; production backend deliberately unchanged pending congtri2103 approval |
| High | A duplicated tab inherited the sessionStorage identifier and overwrote another pending browser draft | Reproduced with window.open; fixed using per-editor in-memory random identifiers, with a browser regression |
| Medium | sessionStorage cannot guarantee unsaved draft recovery after browser process restart | Fixed with bounded, tab-separated changed-field recovery in localStorage; explicit comparison required |
| Low | Expired browser entries were ignored without cleanup on access | Fixed for the opened document/run; no claim of background deletion |

Atomic revision/status checking is inside BEGIN IMMEDIATE; no check/write split
was found. Single-panel manual/autosave requests share an in-flight lock. Browser
checks confirm that typing during a delayed ACK survives, manual save and confirm
are disabled during that write, and export uses persisted confirmed data.
Same-panel response inversion is prevented by serialization. Actual two-tab CAS
returns 409 and retains edits. No additional verified race fix was necessary.

### Backend proposal, not applied

`docs/review/issue-7-legacy-status-proposal.patch` changes omitted/null status to
mean **draft**, preserving legacy draft saves while refusing implicit reopening
of confirmed records. Explicit `expected_status=confirmed` remains the reopen
opt-in. This safely narrows legacy behavior: older clients must update to reopen
confirmed records. It does not claim full semantic backward compatibility for
implicit reopen. No architecture/database change is proposed. The reviewer must
approve rollout/error semantics and update the contract docs/version as needed
before application. No approval has been requested or fabricated on GitHub.

Reproduction on current backend: two legacy omitted/null cases FAIL (actual 200).
Temporarily applied proposal: `python -m pytest backend/tests/test_product.py -q`
passed 16 tests including null, CAS, confirm/export, explicit reopening and both
legacy guard cases. Then restored tracked backend source/tests and saved only the
patch. Thus this High finding is still open on the delivered branch.

### Browser evidence

Locked Playwright 1.64.1 installs Chromium/headless-shell revision 1248,
Chrome 156.0.8078.4 via `npm exec -- playwright install chromium`; dependencies
were not upgraded. Command from frontend:
`npm exec -- playwright test --config playwright.autosave.config.ts`.
Requires the locked backend .venv (Windows launcher in this config) and frontend
node_modules. Separate loopback ports 18812/15174 and disposable SQLite runtime;
server script `backend/tests/browser_autosave_server.py` explicitly seeds
synthetic inference via the existing workflow test double. Browser, production
React App/Workspace/ReviewPanel, HTTP routes, SQLite CAS, confirm and JSON export
are real. This suite is **not native OCR evidence**. No production test endpoints
or fixture fallback were added.

Final uninterrupted run: **10 passed in 42.7s; 0 failed, 0 skipped**.
An earlier run used the wrong test-server origin and was corrected without
changing production middleware. A subsequent run overlapped config edits/native
artifact cleanup and failed one timeout case; final run used stable files and
separate artifact output, without retries or weakened assertions.

| Scenario | Final result |
| --- | --- |
| 1 Debounce, no repeated saves | PASS |
| 2 Two tabs edit same document | PASS |
| 3 Real HTTP409, retained draft and comparison | PASS (combined with scenario 2) |
| 4 Actual 15-second fetch timeout and explicit retry | PASS |
| 5 Navigation with unsaved changes | PASS |
| 6 Confirm/manual-save during in-flight autosave; newer edit across ACK | PASS |
| 7 Reload recovery | PASS |
| Browser process close/relaunch, same persistent profile | PASS |
| Duplicated tab preserves both independent drafts | PASS |
| Stale recovered draft versus newer persisted server data | PASS |
| 8 Export after autosave and confirm | PASS |

### Native diagnosis and remaining acceptance

Native readiness probe with provider_mode=tesseract shows executable `tesseract`
not resolved on PATH/default install path, and both pinned files
`runtime/models/tessdata_fast/vie.traineddata` and `eng.traineddata` absent.
`probe` raises PROVIDER_UNAVAILABLE at model verification before executable launch.
`git diff 921541d -- pipeline backend/src/docintel/api/app.py
backend/src/docintel/config.py` is empty: readiness/config/pipeline unchanged.
This is evidence of missing environment prerequisites, not an autosave pipeline
regression. No OCR engine/model or pipeline change was made outside #7.

After installing Chromium, original `npm run test:e2e`: **1 FAIL, 0 PASS, 0 SKIP**
at invoice.spec.ts readiness assertion (ocr_ready=false), before upload. Native
`scripts/verify_product.py` likewise stops at readiness. These are actual failed
runs, not skipped tests; native scenarios remain blocked.

Final standard checks:

- `backend/.venv/Scripts/python.exe -m pytest backend/tests pipeline/tests -q`:
  **132 PASS**, zero failures/skips on the delivered backend (proposal not applied).
- Ruff check and format check for backend/scripts/pipeline: PASS.
- `npm test`: **23 PASS**, including stale/expired recovery and legacy session migration; zero failures/skips.
- `npm run typecheck`, `lint`, `format:check`, `contracts:check`, `build`: PASS.
- `python scripts/generate_contracts.py --check`: PASS, 25 contracts unchanged.
- `python scripts/check_repository.py`: PASS; final docs/diff checks rerun before commit.

Issue #7 is **not fully accepted**: legacy status bypass awaits backend review,
native upload/OCR/browser regression awaits Tesseract+models, and independent
review by the assigned teammates remains outstanding. A Draft PR using Refs #7
can be reviewed with these explicit blockers; it is not ready to merge/Closes #7.
No push, merge, PR, or GitHub message was performed.

## PR #23 review fixes (supersedes earlier pending conclusions)

Reviewer reproduced three findings at 1f43e11. All three now have runtime fixes:

| Finding | Fix and regression evidence |
| --- | --- |
| P1 Legacy omitted/null status can reopen Confirm | Apply the previously proposed guard to DocumentService inside BEGIN IMMEDIATE. Both missing and null status return 409 after confirm; the persisted status, original data and export stay confirmed/200. Explicit reopen remains tested. API 0.3.1 and generated contracts updated. |
| P2 Tab B discard deletes A's source draft | Remove source-key deletion on ACK/discard. Component regression failed before the fix. Browser test covers ordinary discard, server-comparison discard, closing A, and recovery by a new tab. |
| P2 Windows-only browser launcher | Replace the hardcoded executable with `uv run --project backend --locked python backend/tests/browser_autosave_server.py`. Uses the repository's pinned uv environment on Windows/macOS/Linux. Add this suite to the Ubuntu Browser E2E job, under the existing Product checks gate. |

The old reviewer-only proposal file was removed after applying it. Its historical
content remains at commit 1f43e11; it is no longer a pending patch to apply.
Local commits for code fixes: a567ce1 (status CAS), eb23c08 (draft ownership),
plus the cross-platform launcher/CI commit in this PR. The earlier sections record
historical verification and blockers; this section describes current disposition.

Final local verification on Windows, same pinned dependencies as above:

- Backend/pipeline: **134 passed**, 0 failed/skipped; focused final product tests
  **16 passed** after adding export-preservation assertions.
- Frontend: **24 passed**, 0 failed/skipped; typecheck, lint, format, build and
  generated contracts check PASS.
- Autosave browser suite using the uv launcher: **11 passed in 46.4s**, no retries,
  failures or skips. Uses real UI/HTTP/SQLite with explicit synthetic OCR doubles.
- Ruff lint/format, 25 backend generated contracts and repository/docs checks PASS.
- macOS execution is not available on this Windows machine; new Ubuntu CI provides
  Linux coverage after push. Do not label macOS as locally tested.

Reviewer reported 14 native OCR checks and all six CI checks passed at 1f43e11.
That is reviewer evidence for the old head, not a native run on this Windows host
or verification of the new commits. This machine still lacks native OCR prerequisites;
no pipeline changes were made. Updated CI and independent re-review must be checked
on the new head before merge. Keep PR #23 Draft; no merge or issue closure.
