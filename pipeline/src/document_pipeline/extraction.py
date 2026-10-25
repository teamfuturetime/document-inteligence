"""Literal-label baseline with candidate conflicts and source-token evidence."""

import hashlib
import json
import re
from collections import OrderedDict
from importlib.resources import files

from document_pipeline.models import DocumentType, Prediction, Token
from document_pipeline.normalization import fold_label, folded_offsets, normalize

RULE_BYTES = files("document_pipeline").joinpath("resources/fields.json").read_bytes()
RULES = json.loads(RULE_BYTES)
RULES_SHA256 = hashlib.sha256(RULE_BYTES).hexdigest()
CONFIDENCE_VERSION = "evidence-minimum-ocr-abstain-1.1.0"


def extract(
    tokens: tuple[Token, ...], document_type: DocumentType, *, minimum_ocr_score: float = 0.0
) -> tuple[Prediction, ...]:
    definitions = RULES[document_type]
    grouped: dict[str, list[Token]] = OrderedDict()
    for token in tokens:
        grouped.setdefault(token.line_id, []).append(token)
    lines = []
    for line_tokens in grouped.values():
        text = " ".join(token.text for token in line_tokens)
        folded, raw_offsets = folded_offsets(text)
        matches = []
        for field, aliases in definitions.items():
            for alias in aliases:
                pattern = r"(?<!\w)" + re.escape(fold_label(alias)) + r"(?!\w)"
                for match in re.finditer(pattern, folded):
                    if match.start() != 0 and not re.match(r"\s*[:：]", folded[match.end() :]):
                        continue
                    raw_start = raw_offsets[match.start()]
                    raw_end = (
                        raw_offsets[match.end()] if match.end() < len(raw_offsets) else len(text)
                    )
                    matches.append((raw_start, raw_end, field))
        chosen = []
        for match in sorted(matches, key=lambda item: (item[0], -(item[1] - item[0]))):
            if not any(match[0] < old[1] and match[1] > old[0] for old in chosen):
                chosen.append(match)
        offsets, offset = [], 0
        for token in line_tokens:
            offsets.append((offset, offset + len(token.text), token))
            offset += len(token.text) + 1
        lines.append((text, sorted(chosen), offsets))
    candidates: dict[str, list[tuple[str, tuple[Token, ...]]]] = {
        field: [] for field in definitions
    }
    for line_index, (text, matches, offsets) in enumerate(lines):
        for match_index, (start, end, field) in enumerate(matches):
            boundary = matches[match_index + 1][0] if match_index + 1 < len(matches) else len(text)
            raw = text[end:boundary].strip(" :：;\t")
            evidence = [
                token for left, right, token in offsets if right > start and left < boundary
            ]
            if field in {"request_content", "seller_name"} or not raw:
                for next_text, next_matches, next_offsets in lines[line_index + 1 : line_index + 7]:
                    if next_matches or re.search(
                        r"nguoi lam don|ky va ghi|tran trong|ngay \d+ thang", fold_label(next_text)
                    ):
                        break
                    if raw and field != "request_content":
                        break
                    raw = (raw + "\n" + next_text).strip()
                    evidence.extend(item[2] for item in next_offsets)
                    if field != "request_content":
                        break
            if raw and not re.fullmatch(r"[\s._…-]+", raw):
                candidates[field].append((raw, tuple(evidence)))
    # Currency must be visible; an explicit suffix in the total is evidence, not a locale guess.
    if document_type == "hoa_don" and not candidates["currency"]:
        for raw, evidence in candidates["total_amount"]:
            suffix = re.search(r"(?i)(VND|VNĐ|đồng|đ)\s*$", raw)
            if suffix:
                candidates["currency"].append((suffix[1], evidence))
    predictions = []
    for field, options in candidates.items():
        values = {normalize(field, raw) for raw, _ in options}
        if len(values) != 1:
            predictions.append(
                Prediction(
                    field_id=field,
                    raw_value=None,
                    normalized_value=None,
                    observation="unknown" if options else "not_found",
                    candidate_count=len(values),
                    reason_codes=("AMBIGUOUS_CANDIDATES" if options else "NO_SUPPORTED_EVIDENCE",),
                )
            )
            continue
        raw, _ = options[0]
        evidence_by_id = {token.token_id: token for _, evidence in options for token in evidence}
        evidence = tuple(evidence_by_id.values())
        scores = [token.confidence for token in evidence]
        score = min(scores) if scores and all(item is not None for item in scores) else None
        if score is not None and score < minimum_ocr_score:
            predictions.append(
                Prediction(
                    field_id=field,
                    raw_value=None,
                    normalized_value=None,
                    observation="unknown",
                    evidence_token_ids=tuple(evidence_by_id),
                    ocr_score=score,
                    candidate_count=1,
                    reason_codes=("LOW_OCR_EVIDENCE", "HEURISTIC_NOT_CALIBRATED"),
                )
            )
            continue
        predictions.append(
            Prediction(
                field_id=field,
                raw_value=raw,
                normalized_value=next(iter(values)),
                observation="found",
                evidence_token_ids=tuple(evidence_by_id),
                ocr_score=score,
                candidate_count=1,
                reason_codes=("LITERAL_LABEL_AND_SOURCE_TOKENS", "HEURISTIC_NOT_CALIBRATED")
                + (() if score is not None else ("OCR_SCORE_UNAVAILABLE",)),
            )
        )
    return tuple(predictions)
