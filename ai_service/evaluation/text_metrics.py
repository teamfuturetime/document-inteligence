def edit_distance(reference: list[str], hypothesis: list[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for row, expected in enumerate(reference, start=1):
        current = [row]
        for column, actual in enumerate(hypothesis, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (expected != actual),
                )
            )
        previous = current
    return previous[-1]


def character_error_rate(reference: str, hypothesis: str) -> float:
    return edit_distance(list(reference), list(hypothesis)) / max(len(reference), 1)


def word_error_rate(reference: str, hypothesis: str) -> float:
    reference_words = reference.split()
    return edit_distance(reference_words, hypothesis.split()) / max(len(reference_words), 1)
