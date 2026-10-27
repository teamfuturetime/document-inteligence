"""OCR evaluation metrics computed only against independently authored truth."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from typing import TypeVar


T = TypeVar("T")


def normalize_for_evaluation(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "")
    return re.sub(r"\s+", " ", text).strip()


def edit_distance(reference: Sequence[T], hypothesis: Sequence[T]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for ref_index, ref_item in enumerate(reference, start=1):
        current = [ref_index]
        for hyp_index, hyp_item in enumerate(hypothesis, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[hyp_index] + 1,
                    previous[hyp_index - 1] + (ref_item != hyp_item),
                )
            )
        previous = current
    return previous[-1]


def character_error_rate(reference: str, hypothesis: str) -> float:
    expected = normalize_for_evaluation(reference)
    actual = normalize_for_evaluation(hypothesis)
    if not expected:
        return 0.0 if not actual else 1.0
    return edit_distance(expected, actual) / len(expected)


def word_error_rate(reference: str, hypothesis: str) -> float:
    expected = normalize_for_evaluation(reference).split()
    actual = normalize_for_evaluation(hypothesis).split()
    if not expected:
        return 0.0 if not actual else 1.0
    return edit_distance(expected, actual) / len(expected)


def reading_order_score(expected_lines: list[str], hypothesis: str) -> float:
    """LCS ratio of labeled lines in the recognized reading sequence."""

    expected = [normalize_for_evaluation(line) for line in expected_lines if line.strip()]
    actual = [normalize_for_evaluation(line) for line in hypothesis.splitlines() if line.strip()]
    if not expected:
        return 0.0
    previous = [0] * (len(actual) + 1)
    for expected_line in expected:
        current = [0]
        for index, actual_line in enumerate(actual, start=1):
            if expected_line == actual_line:
                current.append(previous[index - 1] + 1)
            else:
                current.append(max(current[-1], previous[index]))
        previous = current
    return previous[-1] / len(expected)


def exact_field_accuracy(expected: dict[str, str], actual: dict[str, str]) -> float | None:
    if not expected:
        return None
    return sum(actual.get(key) == value for key, value in expected.items()) / len(expected)
