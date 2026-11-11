"""Versioned label baseline, OCR evidence alignment and conservative fusion."""

from collections import defaultdict
import re

from .contracts import Extracted, LABELS, Token, clean, folded, validated_value


def lines(tokens: list[Token]) -> list[list[Token]]:
    groups = defaultdict(list)
    for token in tokens:
        groups[token.line].append(token)
    return [sorted(group, key=lambda token: token.box[0]) for group in groups.values()]


def text(group: list[Token]) -> str:
    return clean(" ".join(token.text for token in group))


def field(value=None, source="missing", evidence=(), scores=(), warnings=(), agreement=False):
    score = min(scores) if scores and all(s is not None for s in scores) else None
    if value is None:
        score = None
    return Extracted(value=value, confidence=score,
        confidence_source=("ocr_agreement" if agreement else "ocr_min") if score is not None else "unavailable",
        source=source, evidence=list(evidence), warnings=list(warnings))


def valid_candidate(kind, key, value):
    try:
        return validated_value(kind, key, value)
    except ValueError:
        return None


def match_label(group, kind):
    content = text(group)
    normalized = folded(content)
    aliases = sorted(((alias, key) for key, labels in LABELS[kind].items() for alias in labels),
                     key=lambda pair: len(pair[0]), reverse=True)
    for alias, key in aliases:
        match = re.match(r"^" + re.escape(folded(alias)) + r"(?=$|[\s:：-])\s*[:：-]?\s*(.*)$", normalized)
        if match:
            return key, content[match.start(1):].strip()
    return None


def rule_extract(kind, tokens):
    groups = lines(tokens)
    found = defaultdict(list)
    for index, group in enumerate(groups):
        match = match_label(group, kind)
        if not match:
            continue
        key, raw = match
        evidence = [text(group)]
        scores = [token.confidence for token in group]
        if not raw and index + 1 < len(groups) and not match_label(groups[index + 1], kind):
            following = groups[index + 1]
            raw = text(following)
            evidence.append(raw)
            scores.extend(token.confidence for token in following)
        value = valid_candidate(kind, key, raw)
        found[key].append((value, evidence, scores))
        if key == "total_amount" and re.search(r"(?:VND|VNĐ|đ)\s*$", raw, re.I):
            found["currency"].append(("VND", evidence, scores))
    output = {}
    for key in LABELS[kind]:
        candidates = found[key]
        unique = {candidate[0] for candidate in candidates}
        evidence = [item for _, items, _ in candidates for item in items]
        scores = [score for _, _, items in candidates for score in items]
        if len(unique) == 1 and None not in unique:
            output[key] = field(next(iter(unique)), "rules", evidence, scores)
        else:
            output[key] = field(source="conflict" if len(unique) > 1 else "missing", evidence=evidence,
                                warnings=["Các nhãn mâu thuẫn hoặc giá trị sai định dạng." if candidates else "Không tìm thấy trường trong OCR."])
    return output


def align_vlm(kind, values, tokens):
    output = {}
    for key, raw in values.items():
        value = valid_candidate(kind, key, raw)
        supporting = []
        if value is not None:
            # Contiguous OCR spans only; accent-sensitive exact normalized values.
            for group in lines(tokens):
                for start in range(len(group)):
                    for end in range(start + 1, min(len(group), start + 40) + 1):
                        span = group[start:end]
                        if valid_candidate(kind, key, text(span)) == value:
                            supporting = span
                            break
                    if supporting:
                        break
                if supporting:
                    break
        warnings = (["Giá trị VLM chưa được OCR chứng thực; cần đối chiếu ảnh."] if value is not None and not supporting
                    else (["VLM trả giá trị sai định dạng; cần rà soát."] if raw is not None and value is None else []))
        output[key] = field(value, "vlm" if value is not None else "missing",
            [text(supporting)] if supporting else [], [token.confidence for token in supporting],
            warnings)
    return output


def fuse(baseline, vision):
    output = {}
    for key, rule in baseline.items():
        vlm = vision[key]
        if rule.source == "conflict" or (rule.value is not None and vlm.value is not None and rule.value != vlm.value):
            output[key] = field(source="conflict", evidence=rule.evidence + vlm.evidence,
                                warnings=["OCR + luật và VLM bất đồng; cần người dùng chọn giá trị."])
        elif rule.value is not None and rule.value == vlm.value:
            output[key] = field(rule.value, "agreement", rule.evidence + vlm.evidence,
                [rule.confidence, vlm.confidence], agreement=True)
        elif rule.value is not None:
            output[key] = rule
        elif vlm.evidence and vlm.value is not None:
            output[key] = vlm
        else:
            output[key] = field(warnings=["Thiếu bằng chứng thống nhất; cần rà soát."])
    return output
