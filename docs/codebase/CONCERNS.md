# Codebase Concerns

## 1) Top Risks (Prioritized)
P0: main lacks product until PRs reviewed/merged; latest check only after approved push. P0: no auth, run loopback and synthetic data. P1: PNG/JPEG-only breaks expectations from older PDF branches; README/capabilities define actual support. P1: slow upload receive deadline/admission not implemented at HTTP ingress. P1: automatic draft save absent; manual save/conflict protection exists. Evidence: api/documents.py, config.py, branch-inventory.md.

## 2) Technical Debt
Historical foundation docs mixed with product; root/docs index and banners now distinguish them. External branch features require semantic adapters, not full merges. Existing scopes/old deadlines/roles are historical, no CODEOWNERS inferred. Main regression on recorded predictions is evaluator behavior, not a native engine-version-independent accuracy gate.

## 3) Security Concerns
No identity -> no public or multi-tenant deployment. Origin allowlist is not authentication. Runtime paths generated and source-only sample data used. [.env/DB/model ignore] is preventive, not a claim of exhaustive secret audit. Minhthao's Windows path portability test failed on macOS; record in audit/backlog, no silent patch to another branch.

## 4) Performance and Scaling Concerns
Single pending queue+worker intentionally bounded; no claim of concurrency SLA. HTTP upload cap5MiB and decoded pixel16M bound work but socket/slowloris/large server-chunk allocations need ingress policy. SQLite process lock prevents multiple workers per DB; cannot scale by adding uvicorn workers.

## 5) Fragile/High-Churn Areas
In nhatquang's six recent commits, frontend/features/documents/Workspace.tsx changed in polling/retry fixes a03ea30/96ce73d and product introduction db72749. API/SQLite upload admission changed at 2805672 after product commit. These are churn signals (not proof of bugs); keep Workspace component checks and forced-race retry tests; don't merge older VT-042 UI over them. Large services/documents.py and repositories/sqlite.py combine multiple workflow transitions; split only with behavior tests, not as cosmetic consolidation.

## 6) [ASK USER] Questions
None outstanding about product scope: user explicitly selected local single-user invoice on 2026-11-12. GitHub writes/required protection remain a concrete approval package at end; do not ask the same scope again. [TODO] Confirm owner volunteers/license/security contact separately before any CODEOWNERS/license activation, not a blocker for local consolidation.

## 7) Evidence
../repository-audit.md; ../branch-inventory.md; ../decisions/0008-primary-invoice-platform.md; backend/src/docintel/{config.py,api/documents.py,services/documents.py}; frontend/src/features/documents/Workspace.tsx; Git log a03ea30/96ce73d/2805672/db72749.
