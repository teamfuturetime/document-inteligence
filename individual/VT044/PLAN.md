# Plan recorded before implementation — 23001945 / VT-044

Baseline: `66074f4ecc384b6006ac8b574001a0b4aced86ef`; branch: `bt3/23001945-vt044`.

## Prompt and initial assumptions

User supplied the personalized assignment and requested a completed Vietnamese
report in `BT3_23001945.md`. Coding-agent prompt used for the experiment:

> Inspect the real AI-02 repository. Plan before coding. Use test-first state
> transition testing for soft delete/restore, protect against cross-user access,
> preserve related data, invert a boolean business rule temporarily, and measure
> 200 concurrent tasks against p95 <= 5 seconds. Record actual evidence only.

Initial AI assumptions, stated before reading the implementation:

1. Documents already have an owner identity; reuse it for authorization.
2. Deletion affects database records only; a soft-delete flag should suffice.

## Repository review and corrections

1. **Reject assumption 1**: `backend/app/models/document.py::Document` has no
   owner column; `backend/app/core/security.py::require_api_key` uses one shared
   key and returns no identity. `docs/security.md` explicitly defers per-user
   authorization to a gateway. Never trust a request's arbitrary user ID.
   Introduce an isolated harness with a server-side demo token-to-identity map
   and an owner/tombstone sidecar table referencing the real Document model.
   This is NOT a production authentication patch or a secure deployment.
2. **Reject assumption 2**: `scripts/retention.py::purge_expired` unlinks files
   and deletes metadata at expiry. `Document.extractions` cascades delete-orphan.
   Keep document, extraction, status, expiry and file unchanged on soft delete;
   refuse expired-document restore. Production retention coordination remains
   outside this slice and must be integrated before release.
3. Do not add ownership/auth migrations, JWT, or UI to this small assignment.
   The assignment explicitly permits an executable harness when the repository
   cannot support the request yet. Do not claim harness endpoints replace the
   application's existing unscoped endpoints.

These are coding-agent corrections; the student must independently review
and endorse/reject them before submission. No human review is fabricated.

## Final plan and intended files

1. Add this plan and failing tests in `individual/VT044/test_lifecycle.py`.
   Exercise real SQLAlchemy Document/Extraction, LocalStorage and repository.
2. Add `individual/VT044/harness.py`: owner-scoped access; active/deleted sidecar;
   transactional delete/restore; repeatable commands; processing/expiry guards;
   sanitized database failure. No modification to production entrypoints.
3. Add deterministic failure injection, fixed clock, independent temporary DBs
   and a complete API workflow. Review diff and run original regression suite.
4. Add `individual/VT044/mutate.py`: invert `if state.deleted != target` to `==`
   in a temporary copy, capture a killed mutant, preserve submission source.
5. Add `individual/VT044/load.py`: real loopback HTTP, file SQLite, 200 tasks
   released by a barrier; report task and request p95 and correctness/errors.
6. Save raw evidence in `individual/VT044/evidence/`, README reproduction steps,
   and report `/Users/nguyencongtri/Documents/SE/BT3_23001945.md`.

Acceptance: owner-only read/list/content/extraction/delete/restore; active ->
deleted -> active with children and bytes preserved; idempotence; processing and
expiry conflict rules; rollback; honest load scope. No merge before team review.
