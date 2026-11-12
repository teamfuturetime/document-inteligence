from collections import defaultdict
from dataclasses import asdict, dataclass
from statistics import mean

from docintel.domain.models import FIELD_IDS, ExtractionRun, GoldAnnotation
from docintel.domain.normalization import NORMALIZATION_VERSION, normalize_value

EVALUATION_VERSION = "exact-fields-1.0.0"


@dataclass
class Counts:
    support: int = 0
    predicted_non_null: int = 0
    tp: int = 0
    fp: int = 0
    fn: int = 0
    wrong: int = 0
    missing: int = 0
    absent_support: int = 0
    extra: int = 0
    correct_abstention: int = 0
    unreadable_support: int = 0
    unreadable_abstention: int = 0
    unreadable_non_null: int = 0


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def summarized(counts: Counts) -> dict:
    result = asdict(counts)
    result.update(
        precision=ratio(counts.tp, counts.tp + counts.fp),
        recall=ratio(counts.tp, counts.tp + counts.fn),
        f1=ratio(2 * counts.tp, 2 * counts.tp + counts.fp + counts.fn),
        exact_match_accuracy=ratio(counts.tp, counts.support),
        extra_fill_rate=ratio(counts.extra, counts.absent_support),
        unreadable_abstention_rate=ratio(counts.unreadable_abstention, counts.unreadable_support),
    )
    result["undefined_reasons"] = {
        key: "ZERO_DENOMINATOR" for key, value in result.items() if value is None
    }
    return result


def evaluate(gold: list[GoldAnnotation], predictions: list[ExtractionRun], *, source: str) -> dict:
    if source not in {"fixture", "model"}:
        raise ValueError("Nguồn prediction không hợp lệ")
    gold_ids = [item.sample_id for item in gold]
    prediction_ids = [item.document_id for item in predictions]
    if len(set(gold_ids)) != len(gold_ids) or len(set(prediction_ids)) != len(prediction_ids):
        raise ValueError("Document IDs trùng trong gold hoặc prediction")
    if set(prediction_ids) - set(gold_ids):
        raise ValueError("Prediction có tài liệu ngoài manifest gold")
    if any(run.provenance.prediction_source != source for run in predictions):
        raise ValueError("Nguồn prediction không khớp chế độ báo cáo")
    indexed = {
        run.document_id: {field.field_id: field for field in run.fields} for run in predictions
    }
    counts = {field_id: Counts() for field_id in FIELD_IDS}
    buckets = defaultdict(lambda: {"support": 0, "correct": 0})
    documents = {"support": 0, "correct": 0, "excluded": 0, "exclusion_reasons": {}}
    for document in gold:
        fields = indexed.get(document.sample_id, {})
        document_matches = True
        eligible_document = all(
            field_id in document.fields and document.fields[field_id].status == "present"
            for field_id in FIELD_IDS
        )
        for field_id, annotation in document.fields.items():
            count = counts[field_id]
            prediction = fields.get(field_id)
            predicted = (
                normalize_value(field_id, prediction.normalized_value) if prediction else None
            )
            expected = normalize_value(field_id, annotation.value)
            if annotation.status == "unreadable":
                count.unreadable_support += 1
                count.unreadable_abstention += int(predicted is None)
                count.unreadable_non_null += int(predicted is not None)
                continue
            count.predicted_non_null += int(predicted is not None)
            if annotation.status == "absent":
                count.absent_support += 1
                if predicted is None:
                    count.correct_abstention += 1
                else:
                    count.fp += 1
                    count.extra += 1
                continue
            if expected is None:
                raise ValueError("Gold present phải có giá trị sau chuẩn hóa")
            count.support += 1
            correct = predicted == expected
            if correct:
                count.tp += 1
            else:
                count.fn += 1
                document_matches = False
                if predicted is None:
                    count.missing += 1
                else:
                    count.fp += 1
                    count.wrong += 1
            if source == "model" and prediction and prediction.confidence.score is not None:
                confidence = prediction.confidence
                if confidence.method in {"heuristic", "calibrated"}:
                    bucket_id = (
                        "[0,0.5)"
                        if confidence.score < 0.5
                        else ("[0.5,0.8)" if confidence.score < 0.8 else "[0.8,1]")
                    )
                    bucket = buckets[f"{confidence.method}:{bucket_id}"]
                    bucket["support"] += 1
                    bucket["correct"] += int(correct)
        if eligible_document:
            documents["support"] += 1
            documents["correct"] += int(document_matches)
        else:
            documents["excluded"] += 1
            documents["exclusion_reasons"][document.sample_id] = (
                "REQUIRED_FIELD_NOT_PRESENT_READABLE"
            )
    total = Counts(
        **{key: sum(getattr(count, key) for count in counts.values()) for key in asdict(Counts())}
    )
    per_field = {field_id: summarized(count) for field_id, count in counts.items()}
    macro = {}
    for metric in ("precision", "recall", "f1", "exact_match_accuracy"):
        values = [item[metric] for item in per_field.values() if item[metric] is not None]
        macro[metric] = mean(values) if values else None
        macro[f"{metric}_field_support"] = len(values)
    return {
        "report_type": "evaluator_contract_check" if source == "fixture" else "model_benchmark",
        "prediction_source": source,
        "evaluation_version": EVALUATION_VERSION,
        "normalization_version": NORMALIZATION_VERSION,
        "value_source": "machine_pre_review",
        "per_field": per_field,
        "micro": summarized(total),
        "macro": macro,
        "document_exact_match": {
            **documents,
            "accuracy": ratio(documents["correct"], documents["support"]),
        },
        "confidence_buckets": {
            key: {**value, "accuracy": ratio(value["correct"], value["support"])}
            for key, value in buckets.items()
        },
        "confidence_status": "measured" if buckets else "NO_REAL_CONFIDENCE",
        "latency": None,
        "latency_status": "NOT_MEASURED",
    }
