"""Cheap live DB/worker checks; provider availability is a bounded startup snapshot."""

import sqlite3
import time
from contextlib import closing

from document_pipeline.errors import PipelineError
from document_pipeline.tesseract import probe

from docintel import __version__
from docintel.config import Settings
from docintel.domain.operations import Readiness
from docintel.repositories.schema import SCHEMA_VERSION


def provider_at_startup(settings: Settings):
    if settings.provider_mode != "tesseract":
        return settings.provider_mode
    try:
        probe(settings.tesseract_executable, settings.tessdata_dir, timeout=3)
    except PipelineError:
        return "unavailable"
    return "ready"


def database_status(runtime):
    deadline = time.monotonic() + 0.1
    try:
        # mode=ro never creates a missing database. The app owns WAL/recovery; no
        # repository initialize, migration, integrity scan or document query here.
        with closing(
            sqlite3.connect(
                (runtime / "documents.sqlite3").resolve().as_uri() + "?mode=ro",
                uri=True,
                timeout=0.05,
            )
        ) as db:
            db.set_progress_handler(lambda: int(time.monotonic() >= deadline), 100)
            db.execute("PRAGMA query_only=ON")
            version = db.execute("SELECT max(version) FROM schema_migrations").fetchone()[0]
            return (
                "ready"
                if type(version) is int and version == SCHEMA_VERSION
                else "unsupported_schema"
            )
    except sqlite3.Error, OSError, ValueError:
        return "unavailable"


def inspect_readiness(state, settings: Settings):
    lifecycle = getattr(state, "runtime_lifecycle", "not_started")
    provider = getattr(state, "provider_readiness", "not_checked")
    worker = getattr(state, "inference_worker", None)
    worker_status = "not_started"
    if worker is not None:
        worker_status = (
            "ready" if worker.thread.is_alive() and not worker.stop.is_set() else "stopped"
        )
    elif settings.provider_mode != "tesseract":
        worker_status = "disabled"
    database = database_status(settings.runtime_dir) if lifecycle == "running" else "not_checked"
    ready = (
        lifecycle == "running"
        and database == "ready"
        and worker_status == "ready"
        and provider == "ready"
    )
    return Readiness(
        status="ready" if ready else "not_ready",
        app_version=__version__,
        lifecycle=lifecycle,
        database=database,
        worker=worker_status,
        provider=provider,
        provider_mode=settings.provider_mode,
        auth_mode=settings.auth_mode,
    )
