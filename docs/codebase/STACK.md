# Technology Stack

## 1) Runtime Summary
Python3.14.5/backend, Node24.16.x/npm11.13.x frontend; uv0.12.22, editable pipeline package. ESM TypeScript frontend, hatchling wheels Python. Evidence: backend/.python-version, backend/pyproject.toml, backend/uv.lock, frontend/package.json/package-lock.json.

## 2) Production Frameworks and Dependencies
FastAPI0.142.2/Pydantic2.13.5/Pydantic-settings2.15.0/Uvicorn0.54.0; SQLite stdlib; Pillow12.3.0; native Tesseract5 external process with pinned vie/eng models. React19.3.0/ReactDOM19.3.0, Vite8.3.6. Exact transitive versions in lockfiles; no PostgreSQL or remote AI service for main app.

## 3) Development Toolchain
pytest9.1.1, httpx2 2.13.1, ruff0.16.10; Vitest5.0.3, TypeScript5.9.3, ESLint10.12.0, Prettier3.9.9; Playwright browser workflow. Backend/pipeline ruff E/F/I/UP/B, line100. Frontend TS strict. Full commands maintained only in README/scripts/dev.py.

## 4) Key Commands
`python scripts/dev.py setup`, `models`, `backend`, `frontend`, `check`, `ocr`, `e2e`. Run from root; README has prerequisites. Docker/compose optional and independently verified, not the default beginner path.

## 5) Environment and Config
.env.example is tesseract; absent config defaults unconfigured. DOCINTEL_* Settings, local runtime/app SQLite/files; model directory runtime/models/tessdata_fast. No secret needed. One worker per DB, loopback single-user. See ../product/runbook.md and ../consolidation-verification.md for measured runtimes.

## 6) Evidence
backend/pyproject.toml; pipeline/pyproject.toml; frontend/package.json; backend/src/docintel/config.py; compose.yaml; README.md.
