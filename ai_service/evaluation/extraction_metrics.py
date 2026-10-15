from dataclasses import dataclass


@dataclass(frozen=True)
class FieldMetrics:
    precision: float
    recall: float
    f1: float


def field_metrics(expected: dict, predicted: dict) -> FieldMetrics:
    expected_pairs = {(key, str(value).strip().casefold()) for key, value in expected.items()}
    predicted_pairs = {(key, str(value).strip().casefold()) for key, value in predicted.items()}
    true_positives = len(expected_pairs & predicted_pairs)
    precision = true_positives / max(len(predicted_pairs), 1)
    recall = true_positives / max(len(expected_pairs), 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)
    return FieldMetrics(precision, recall, f1)
