# Architecture

## 1) Architectural Style
Modular backend with in-process persisted queue worker plus one React client, not distributed microservices. SQLite transaction is authority for review/confirm/export; native subprocesses bound image/OCR work. Single local user, one worker/DB, PNG/JPEG one page shape the design.

## 2) System Flow
Browser bytes -> API streamed byte cap -> DocumentService upload/key/admission -> SQLite queued run + immutable source/preview -> LocalInferenceWorker -> DocumentPipeline preprocess/Tesseract/extract -> immutable machine fields/evidence -> UI review -> CAS revision/save -> final domain validation/confirm -> server export latest persisted confirmed revision.

## 3) Layer/Module Responsibilities
api/documents.py: route I/O, no OCR/SQL inline. services/documents.py: use cases and result authority. repositories/sqlite.py: atomic writes/migrations. adapters/pipeline.py: inference DTO to domain. pipeline: bounded CPU inference independent of labels. domain/documents.py is public product schema source; domain/models.py foundation contracts remain separate by purpose.

## 4) Reused Patterns
App factory+lifespan; repository transaction context; Protocol adapters; immutable runs; explicit review-null; compare-and-swap expected_revision; process lock. Read actual code before adding retry/autosave, do not merge competing public models.

## 5) Known Architectural Risks
No auth/tenant boundary; do not expose publicly. Body cap does not add a total upload receive deadline/admission limit for slow sockets. Cooperative worker/thread shutdown depends on native timeout. Manual draft save is not autosave; request replay keys do not replace distributed queue semantics.

## 6) Evidence
backend/src/docintel/{api/app.py,api/documents.py,services/documents.py,services/worker.py,repositories/sqlite.py,domain/documents.py}; pipeline/src/document_pipeline/service.py; ../product/architecture.md.
