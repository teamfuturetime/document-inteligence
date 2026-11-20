"""Operational state without document, identity or filesystem details."""

from typing import Literal

from docintel.domain.models import Contract


class Readiness(Contract):
    status: Literal["ready", "not_ready"]
    app_version: str
    lifecycle: Literal["not_started", "starting", "running", "stopping", "stopped"]
    database: Literal["not_checked", "ready", "unavailable", "unsupported_schema"]
    worker: Literal["not_started", "disabled", "ready", "stopped"]
    provider: Literal["not_checked", "ready", "unconfigured", "fixture", "unavailable"]
    provider_check: Literal["startup_snapshot"] = "startup_snapshot"
    provider_mode: Literal["unconfigured", "fixture", "tesseract"]
    auth_mode: Literal["local", "session"]
