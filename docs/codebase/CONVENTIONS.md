# Coding Conventions

## 1) Naming Rules
Python snake_case functions/modules, PascalCase Pydantic/service classes, uppercase constants/env DOCINTEL_*. React PascalCase TSX, camelCase hooks/callbacks. Example files: services/documents.py, domain/documents.py, features/documents/ReviewPanel.tsx and SourcePreview.tsx.

## 2) Formatting and Linting
Ruff configuration in backend/pipeline pyproject.toml (E/F/I/UP/B, target py314/py311 respectively); frontend eslint.config.js + Prettier. `python scripts/dev.py check` runs configured checks; don't add broad skip/continue-on-error to make them pass.

## 3) Import and Module Conventions
Ruff I sorts Python imports. Use installed editable docintel/document_pipeline modules; run tools from root, not ad-hoc sys.path copies. Frontend contracts are generated; DTO->domain conversion is only at adapter. Generated files not manually edited.

## 4) Error and Logging Conventions
ProductError has safe code/status/message; API wraps request ID. No raw OCR/source/error stderr in application logs. Invalid drafts can persist; confirm/export require valid latest revision. is_reviewed=true + reviewed_value=null means clear, never fallback with `or`.

## 5) Testing Conventions
backend/tests/test_*.py and pipeline/tests/test_*.py; frontend src/**/*.test.tsx; browser e2e separately. pytest monkeypatch/tmp_path and explicit fixture mode. No fixture fallback on provider failure. No newly declared arbitrary coverage threshold. Git rules in AGENTS/CONTRIBUTING; preserve attribution when porting.

## 6) Evidence
AGENTS.md; CONTRIBUTING.md; backend/pyproject.toml; frontend/eslint.config.js; backend/src/docintel/api/app.py; backend/tests/test_product.py; frontend/src/features/documents/ReviewPanel.test.tsx.
