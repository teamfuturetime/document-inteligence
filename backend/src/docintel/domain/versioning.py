from datetime import datetime
from typing import Literal

from pydantic import Field

from docintel.domain.models import Contract


class ComponentVersion(Contract):
    component: str
    package_version: str | None
    model_revision: str | None
    artifact_sha256: str | None


class RunManifest(Contract):
    run_id: str
    started_at: datetime
    status: Literal["succeeded", "failed", "unavailable"]
    report_type: Literal["evaluator_contract_check", "model_benchmark"]
    prediction_source: Literal["fixture", "model"]
    git_commit: str
    git_dirty: bool
    dataset_version: str
    manifest_sha256: str
    split: str
    ocr: ComponentVersion
    extraction: ComponentVersion
    versions: dict[str, str]
    hashes: dict[str, str]
    resolved_config: dict[str, str | int | bool]
    runtime: dict[str, str]
    hardware: dict[str, str]
    seed: int | None
    prediction_artifact: str
    report_artifact: str
    reproducibility_limitations: list[str] = Field(default_factory=list)
