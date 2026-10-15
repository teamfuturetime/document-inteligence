"""Conservative invoice label rules over OCRResult; no HTTP or OCR dependency."""

import argparse
from dataclasses import dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from document_contracts.models import (
    Evidence, ExtractionResponse, MAX_SAFE_INTEGER, OCRResult, OCRToken,
)

PIPELINE_VERSION = "invoice-extraction-1.0.0"
RULES = json.loads(Path(__file__).with_name("invoice-rules.json").read_text(encoding="utf-8"))
RULES_SHA256 = hashlib.sha256(json.dumps(RULES, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
MAX_OCR_JSON_BYTES = 10 * 1024 * 1024


def fold_label(text: str) -> str:
    text = unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
    return " ".join("".join(char for char in text if not unicodedata.combining(char)).split())


LABELS = {fold_label(label): field for field, labels in RULES["labels"].items() for label in labels}
LABEL_PATTERN = re.compile(r"(?<!\w)(" + "|".join(
    re.escape(label) for label in sorted(LABELS, key=len, reverse=True)
) + r")\s*:")
CURRENCY_SUFFIX = re.compile(r"(?<![^\W\d])(?P<currency>VND|VNĐ|đồng|đ|₫)$", re.IGNORECASE)


class SourceValueError(ValueError):
    def __init__(self, warning="invalid_source_value"):
        super().__init__(warning)
        self.warning = warning


def normalize_value(field: str, raw: str):
    value = unicodedata.normalize("NFC", " ".join(raw.split()))
    if not value or any(unicodedata.category(char).startswith("C") for char in value):
        raise SourceValueError()
    if field == "invoice_number":
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,99}", value):
            raise SourceValueError()
        return value
    if field == "seller_name":
        if len(value) > 200 or not any(char.isalpha() for char in value):
            raise SourceValueError()
        return value
    if field == "currency":
        if value.casefold() not in {"vnd", "vnđ", "đồng", "đ", "₫"}:
            raise SourceValueError()
        return "VND"
    if field == "invoice_date":
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            year, month, day = map(int, value.split("-"))
        else:
            match = re.fullmatch(r"([0-9]{1,2})([/.-])([0-9]{1,2})\2([0-9]{4})", value)
            if not match:
                raise SourceValueError()
            day, month, year = int(match[1]), int(match[3]), int(match[4])
            # Validate the DMY interpretation; never try swapping or fixing dates.
            try:
                date(year, month, day)
            except ValueError as exc:
                raise SourceValueError() from exc
            if day <= 12 and day != month:
                raise SourceValueError("ambiguous_field")
        try:
            return date(year, month, day).isoformat()
        except ValueError as exc:
            raise SourceValueError() from exc
    if field == "total_amount":
        value = CURRENCY_SUFFIX.sub("", value).strip()
        if re.fullmatch(r"[0-9]+", value):
            digits = value
        elif re.fullmatch(r"[1-9][0-9]{0,2}([., ])[0-9]{3}(?:\1[0-9]{3})*", value):
            digits = re.sub(r"[., ]", "", value)
        else:
            raise SourceValueError()
        # Avoid constructing arbitrarily large integers from OCR text.
        digits = digits.lstrip("0") or "0"
        if len(digits) > 16 or int(digits) > MAX_SAFE_INTEGER:
            raise SourceValueError()
        return int(digits)
    raise ValueError("Unknown invoice field")


def group_lines(tokens: list[OCRToken]) -> list[list[OCRToken]]:
    """Cluster by vertical overlap and centers, then read each row left to right."""
    lines = []
    for token in sorted(tokens, key=lambda token: (
        (token.box.y0 + token.box.y1) / 2, token.box.x0, token.text,
    )):
        box = token.box
        candidates = []
        for index, line in enumerate(lines):
            top = min(item.box.y0 for item in line)
            bottom = max(item.box.y1 for item in line)
            overlap = min(bottom, box.y1) - max(top, box.y0)
            distance = abs((top + bottom - box.y0 - box.y1) / 2)
            if (overlap >= RULES["line_overlap"] * min(bottom - top, box.y1 - box.y0)
                    and distance <= RULES["line_center_distance"] * max(bottom - top, box.y1 - box.y0)):
                candidates.append((distance, index))
        if candidates:
            lines[min(candidates)[1]].append(token)
        else:
            lines.append([token])
    return [sorted(line, key=lambda token: (token.box.x0, token.box.y0, token.text)) for line in lines]


@dataclass
class Candidate:
    value: str | int | None
    tokens: list[OCRToken]
    warning: str | None = None


def resolve_candidates(candidates: list[Candidate]) -> dict:
    evidence = [Evidence(text=token.text, page=1, box=token.box.model_dump()).model_dump()
                for candidate in candidates for token in candidate.tokens]
    warnings = list(dict.fromkeys(item.warning for item in candidates if item.warning))
    values = {item.value for item in candidates}
    if len(values) > 1:
        warnings.append("ambiguous_field")
    if not candidates:
        warnings.append("missing_field")
    if warnings:
        return {"value": None, "confidence": None, "evidence": evidence,
                "warnings": list(dict.fromkeys(warnings))}
    scores = [token.confidence for item in candidates for token in item.tokens]
    confidence = min(scores) if scores and all(score is not None for score in scores) else None
    return {"value": candidates[0].value, "confidence": confidence, "evidence": evidence, "warnings": []}


def extract_invoice(ocr: OCRResult, document_id: str) -> ExtractionResponse:
    """Map explicit same-line labels; preserve input mode and engine provenance."""
    candidates = {field: [] for field in RULES["labels"]}
    for tokens in group_lines(ocr.page.tokens):
        raw = " ".join(token.text for token in tokens)
        matches = list(LABEL_PATTERN.finditer(fold_label(raw)))
        if not matches or matches[0].start() != 0:
            continue
        if len(matches) > 1:
            # Multiple labels on one row need layout handling; do not swallow
            # the next field as seller text or choose a number from a table.
            for field in dict.fromkeys(LABELS[match[1]] for match in matches):
                candidates[field].append(Candidate(None, tokens, "ambiguous_field"))
            continue
        field = LABELS[matches[0][1]]
        value = raw.partition(":")[2].strip()
        try:
            normalized = normalize_value(field, value)
            candidate = Candidate(normalized, tokens)
        except SourceValueError as exc:
            candidate = Candidate(None, tokens, exc.warning if value else "missing_field")
        candidates[field].append(candidate)
        # A VND suffix on an explicitly labelled total is independent evidence.
        # Never infer currency from invoice language, unlabeled prose or a default.
        if field == "total_amount" and (suffix := CURRENCY_SUFFIX.search(value)):
            candidates["currency"].append(Candidate(normalize_value("currency", suffix[0]), tokens))
    fields = {field: resolve_candidates(items) for field, items in candidates.items()}
    warnings = (["mock_data"] if ocr.mode == "mock" else []) + list(dict.fromkeys(
        warning for field in fields.values() for warning in field["warnings"]
    ))
    return ExtractionResponse(
        schema_version="1.0.0", document_id=document_id, mode=ocr.mode,
        pipeline_version=PIPELINE_VERSION, ocr_version=ocr.ocr_version,
        config_version=f"{RULES['version']}:{RULES_SHA256[:12]}", fields=fields, warnings=warnings,
    )


def main():
    parser = argparse.ArgumentParser(description="Extract invoice fields from OCRResult JSON; no OCR or HTTP.")
    parser.add_argument("input", type=Path, help="OCRResult v1.0.0 JSON, real or explicitly mock")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--document-id")
    args = parser.parse_args()
    try:
        report = args.output.with_suffix(".metadata.json")
        if report.resolve() == args.output.resolve() or args.input.resolve() in {
            args.output.resolve(), report.resolve(),
        }:
            raise ValueError("Output và metadata phải khác nhau và khác input")
        with args.input.open("rb") as stream:
            data = stream.read(MAX_OCR_JSON_BYTES + 1)
        if len(data) > MAX_OCR_JSON_BYTES:
            raise ValueError("OCR JSON vượt giới hạn 10 MiB")
        digest = hashlib.sha256(data).hexdigest()
        result = extract_invoice(OCRResult.model_validate_json(data), args.document_id or f"ocr-{digest[:24]}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
        report.write_text(json.dumps({"rules": RULES, "rules_sha256": RULES_SHA256,
                                      "ocr_input_sha256": digest,
                                      "confidence_policy": "minimum-all-evidence-token-scores-or-null"},
                                     ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"result": str(args.output), "metadata": str(report), "mode": result.mode}))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"invalid_input: {exc}\n")


if __name__ == "__main__":
    main()
