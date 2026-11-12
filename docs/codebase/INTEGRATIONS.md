# External Integrations

## 1) Integration Inventory
Tesseract5 native CLI: required for actual OCR, no credentials, CPU. Model fetch: official tesseract-ocr/tessdata_fast commit with vie/eng SHA256, explicit setup only. SQLite: local transactional persistence. GitHub Actions: read-only job token, no product API secrets. No paid VLM/OCR.space in selected production app; those remain at solo historical refs.

## 2) Data Stores
SQLite runtime/app with migrations, immutable runs/revisions/events and process lock. Generated file IDs for source/preview under runtime; model weights separate. Backup helper uses SQLite snapshot+file hashes. No automatic migration from another implementation's DB.

## 3) Secrets and Credentials Handling
.env.example is non-secret; .env, weights, DB/uploads/cache ignored. Product requires no credential. No intentionally copied local .env or sensitive invoice used in consolidation. [TODO] Team-approved license/security contact; no fictitious account or CODEOWNERS created.

## 4) Reliability and Failure Behavior
Pipeline30s shared budget, actual image/OCR subprocess timeout, bounded pending queue5, one worker, persisted restart recovery and idempotency key replay. Fixture explicit only; native unavailable fails readiness/upload. No distributed delivery/retry service.

## 5) Observability for Integrations
API request IDs/safe errors; run metadata captures source/engine/model/config/runtime; insights endpoint local counters. No APM/distributed tracing claimed. Quality figures require dataset/run/config/engine provenance.

## 6) Evidence
backend/src/docintel/config.py; repositories/{sqlite.py,locking.py}; services/worker.py; pipeline/src/document_pipeline/{provenance.py,tesseract.py}; scripts/{fetch_ocr_models.py,backup_runtime.py}; .gitignore; ../ml/source-lineage.md.
