"""Compare the previous OCR recipe with the layout-aware pipeline on labeled fixtures."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_service.evaluation.metrics import (  # noqa: E402
    character_error_rate,
    exact_field_accuracy,
    reading_order_score,
    word_error_rate,
)
from ai_service.ocr.engine import VietnameseOCREngine, available_tesseract_languages  # noqa: E402
from ai_service.pipeline import DocumentPipeline  # noqa: E402
from ai_service.preprocessing.image import preprocess_image  # noqa: E402


def evaluate_case(path: Path, case: dict, language: str) -> dict:
    engine = VietnameseOCREngine(tesseract_lang=language)
    pipeline = DocumentPipeline(engine)
    pages = pipeline._load_pages(path)
    baseline_text = "\n\f\n".join(
        engine.recognize(
            preprocess_image(page, max_width=2000, denoise_strength=10),
            page_number=index,
            psm=6,
        ).text
        for index, page in enumerate(pages, start=1)
    )
    improved = pipeline.process(path)
    improved_text = improved["ocr"]["text"]
    truth = case["ground_truth"]
    expected_lines = case.get("reading_order", truth.replace("\f", "\n").splitlines())
    detected_blocks = [
        block["type"]
        for page in improved["ocr"]["pages"]
        for block in page["blocks"]
    ]
    expected_structure = case.get("expected_structure", [])
    structure_recall = (
        len(set(expected_structure) & set(detected_blocks)) / len(set(expected_structure))
        if expected_structure
        else None
    )
    return {
        "file": case["file"],
        "language": language,
        "baseline": {
            "cer": round(character_error_rate(truth, baseline_text), 4),
            "wer": round(word_error_rate(truth, baseline_text), 4),
            "reading_order": round(reading_order_score(expected_lines, baseline_text), 4),
        },
        "improved": {
            "cer": round(character_error_rate(truth, improved_text), 4),
            "wer": round(word_error_rate(truth, improved_text), 4),
            "reading_order": round(reading_order_score(expected_lines, improved_text), 4),
            "mean_confidence": improved["ocr"]["mean_confidence"],
            "quality": improved["ocr"]["quality"],
            "detected_blocks": detected_blocks,
            "structure_recall": structure_recall,
            "field_accuracy": exact_field_accuracy(
                case.get("expected_fields", {}), improved["extraction"]["data"]
            ),
        },
    }


def aggregate(results: list[dict]) -> dict:
    summary = {}
    for language in sorted({result["language"] for result in results}):
        selected = [result for result in results if result["language"] == language]
        language_summary = {}
        for variant in ("baseline", "improved"):
            language_summary[variant] = {
                metric: round(sum(result[variant][metric] for result in selected) / len(selected), 4)
                for metric in ("cer", "wer", "reading_order")
            }
        optional = {
            metric: [result["improved"][metric] for result in selected if result["improved"].get(metric) is not None]
            for metric in ("structure_recall", "field_accuracy")
        }
        language_summary["improved"].update(
            {metric: round(sum(values) / len(values), 4) for metric, values in optional.items() if values}
        )
        summary[language] = language_summary
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, default=ROOT / "tests/fixtures/vietnamese")
    parser.add_argument("--languages", nargs="*", default=None)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = json.loads((args.fixtures / "manifest.json").read_text(encoding="utf-8"))
    installed = set(available_tesseract_languages())
    requested = args.languages or [language for language in ("vie", "vie+eng") if all(part in installed for part in language.split("+"))]
    if not requested:
        raise SystemExit("Không có language pack Tesseract phù hợp để đánh giá")

    results = [
        evaluate_case(args.fixtures / case["file"], case, language)
        for language in requested
        for case in manifest
        if case.get("ground_truth")
    ]
    report = {"dataset": str(args.fixtures), "summary": aggregate(results), "results": results}
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
