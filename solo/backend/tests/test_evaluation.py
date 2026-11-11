import json

import pytest

from ai02_solo.evaluate import load_dataset, metric
from ai02_solo.settings import ROOT


def test_field_metrics_wrong_nonnull_counts_fp_and_fn_and_null_is_not_tp():
    result = metric([("A", "A"), ("B", "C"), ("D", None), (None, "E"), (None, None)])
    assert result["tp"] == 1
    assert result["fp"] == 2
    assert result["fn"] == 2
    assert result["null_pairs"] == 1
    assert result["exact_match"] == .4
    assert result["precision"] == result["recall"] == result["f1"] == 1 / 3
    assert metric([(None, None)])["f1"] is None
    assert metric([])["exact_match"] is None


def test_frozen_manifest_balances_splits_schemas_layouts_and_formats():
    manifest, _, documents = load_dataset(ROOT / "data/golden-v1")
    assert len(documents) == 36
    for kind in ["invoice", "application"]:
        for split in ["dev", "test"]:
            subset = [item for item in manifest["documents"] if item["kind"] == kind and item["split"] == split]
            assert len(subset) == 9
            assert {item["layout"] for item in subset} == {"colon", "no-colon", "stacked"}
            assert {item["condition"] for item in subset} == {"clean", "blur", "missing"}
            assert {item["file"].split(".")[-1] for item in subset} == {"png", "jpg", "pdf"}


def test_modified_truth_is_rejected_before_pipeline(tmp_path):
    manifest = json.loads((ROOT / "data/golden-v1/manifest.json").read_text())
    item = manifest["documents"][0]
    manifest["documents"] = [item]
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    (tmp_path / item["file"]).write_bytes((ROOT / "data/golden-v1" / item["file"]).read_bytes())
    (tmp_path / item["truth"]).write_text("{}")
    with pytest.raises(ValueError, match="integrity"):
        load_dataset(tmp_path)
