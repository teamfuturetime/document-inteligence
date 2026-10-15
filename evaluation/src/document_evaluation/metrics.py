"""Field exact match and non-null PRF; null-null never inflates TP counts."""

import unicodedata

from document_contracts.models import InvoiceValues

FIELDS = tuple(InvoiceValues.model_fields)


def canonical(value):
    return unicodedata.normalize("NFC", " ".join(value.split())) if isinstance(value, str) else value


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def summarize(count):
    tp, fp, fn = (count[key] for key in ("tp", "fp", "fn"))
    return {**count, "exact_match": ratio(count["correct"], count["total"]),
            "precision": ratio(tp, tp + fp), "recall": ratio(tp, tp + fn),
            "f1": ratio(2 * tp, 2 * tp + fp + fn)}


def field_metrics(pairs):
    counts = {field: dict(tp=0, fp=0, fn=0, correct=0, total=0, null_pairs=0, support=0) for field in FIELDS}
    for predicted, expected in pairs:
        for field in FIELDS:
            prediction, truth = canonical(predicted[field]), canonical(expected[field])
            count = counts[field]
            count["total"] += 1
            count["correct"] += prediction == truth
            count["support"] += truth is not None
            count["null_pairs"] += prediction is None and truth is None
            count["tp"] += prediction is not None and prediction == truth
            count["fp"] += prediction is not None and prediction != truth
            count["fn"] += truth is not None and prediction != truth
    fields = {field: summarize(count) for field, count in counts.items()}
    micro = summarize({key: sum(count[key] for count in counts.values()) for key in next(iter(counts.values()))})
    macro = {}
    for metric in ("exact_match", "precision", "recall", "f1"):
        defined = [field[metric] for field in fields.values() if field[metric] is not None]
        macro[metric] = sum(defined) / len(defined) if defined else None
    return {"fields": fields, "micro": micro, "macro": macro}
