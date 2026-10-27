"""Build conservative document structure from Tesseract word coordinates."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean, median
from typing import Any, Iterable


LOW_CONFIDENCE = 50.0


def _union_bbox(items: Iterable[Any]) -> list[int]:
    items = list(items)
    if not items:
        return [0, 0, 0, 0]
    left = min(item.bbox[0] for item in items)
    top = min(item.bbox[1] for item in items)
    right = max(item.bbox[0] + item.bbox[2] for item in items)
    bottom = max(item.bbox[1] + item.bbox[3] for item in items)
    return [left, top, right - left, bottom - top]


def _line_cells(words: list[Any]) -> list[dict]:
    """Split a line only at visually large gaps; never infer missing cell text."""

    if len(words) < 2:
        return []
    ordered = sorted(words, key=lambda word: word.bbox[0])
    typical_height = max(median(word.bbox[3] for word in ordered), 1)
    groups: list[list[Any]] = [[ordered[0]]]
    for word in ordered[1:]:
        previous = groups[-1][-1]
        gap = word.bbox[0] - (previous.bbox[0] + previous.bbox[2])
        if gap > typical_height * 2.5:
            groups.append([word])
        else:
            groups[-1].append(word)
    if len(groups) < 2:
        return []
    return [
        {
            "text": " ".join(word.text for word in group),
            "confidence": round(mean(max(0.0, word.confidence) for word in group) / 100, 3),
            "bbox": _union_bbox(group),
        }
        for group in groups
    ]


def _looks_like_table(lines: list[dict]) -> bool:
    cell_lines = [line for line in lines if len(line["cells"]) >= 2]
    if len(cell_lines) < 2:
        return False
    column_counts = [len(line["cells"]) for line in cell_lines]
    expected = max(set(column_counts), key=column_counts.count)
    aligned = [line for line in cell_lines if len(line["cells"]) == expected]
    if len(aligned) < 2:
        return False
    starts = [[cell["bbox"][0] for cell in line["cells"]] for line in aligned]
    tolerance = max(median(line["bbox"][3] for line in aligned) * 2.5, 20)
    return all(
        max(row[index] for row in starts) - min(row[index] for row in starts) <= tolerance
        for index in range(expected)
    )


def _block_type(text: str, lines: list[dict]) -> str:
    if _looks_like_table(lines):
        return "table"
    if len(lines) == 1 and ":" in text:
        return "key_value"
    letters = [character for character in text if character.isalpha()]
    if len(lines) <= 2 and letters and all(character.isupper() for character in letters):
        return "heading"
    if all(line["text"].lstrip().startswith(("-", "•", "*")) for line in lines):
        return "list"
    if text:
        return "paragraph"
    return "unknown"


def _aligned_cell_lines(blocks: list[dict], minimum_cells: int) -> list[dict]:
    return [
        block
        for block in blocks
        if len(block["lines"]) == 1 and len(block["lines"][0]["cells"]) >= minimum_cells
    ]


def _merge_page_table_rows(blocks: list[dict]) -> list[dict]:
    """Merge separately segmented rows only when 3+ columns repeatedly align."""

    candidates = _aligned_cell_lines(blocks, 3)
    if len(candidates) < 2:
        return blocks
    template = max(candidates, key=lambda block: len(block["lines"][0]["cells"]))
    template_starts = [cell["bbox"][0] for cell in template["lines"][0]["cells"]]
    tolerance = max(median(block["bbox"][3] for block in candidates) * 2.5, 20)
    rows = [
        block
        for block in candidates
        if all(
            any(abs(cell["bbox"][0] - expected) <= tolerance for expected in template_starts)
            for cell in block["lines"][0]["cells"]
        )
    ]
    if len(rows) < 2:
        return blocks
    ordered_rows = sorted(rows, key=lambda block: block["bbox"][1])
    table = {
        "type": "table",
        "text": "\n".join(block["text"] for block in ordered_rows),
        "confidence": round(mean(block["confidence"] for block in ordered_rows), 3),
        "bbox": _union_bbox(
            type("Box", (), {"bbox": tuple(block["bbox"])}) for block in ordered_rows
        ),
        "block_number": min(block["block_number"] for block in ordered_rows),
        "needs_review": any(block["needs_review"] for block in ordered_rows)
        or any(
            len(block["lines"][0]["cells"]) != len(template_starts)
            for block in ordered_rows
        ),
        "lines": [block["lines"][0] for block in ordered_rows],
        "rows": [block["lines"][0]["cells"] for block in ordered_rows],
    }
    return [block for block in blocks if block not in rows] + [table]


def _split_page_columns(blocks: list[dict], page_width: int) -> list[dict]:
    """Split clear repeated two-column lines into independent text streams."""

    candidates = [
        block
        for block in _aligned_cell_lines(blocks, 2)
        if len(block["lines"][0]["cells"]) == 2
        and block["lines"][0]["cells"][1]["bbox"][0]
        - block["lines"][0]["cells"][0]["bbox"][0]
        > page_width * 0.3
    ]
    if len(candidates) < 2:
        return blocks
    starts = [[cell["bbox"][0] for cell in block["lines"][0]["cells"]] for block in candidates]
    tolerance = max(median(block["bbox"][3] for block in candidates) * 2.5, 20)
    if any(max(row[index] for row in starts) - min(row[index] for row in starts) > tolerance for index in (0, 1)):
        return blocks

    split_blocks: list[dict] = []
    for block in candidates:
        for column_index, cell in enumerate(block["lines"][0]["cells"]):
            split_blocks.append(
                {
                    "type": "paragraph",
                    "text": cell["text"],
                    "confidence": cell["confidence"],
                    "bbox": cell["bbox"],
                    "block_number": block["block_number"] * 10 + column_index,
                    "needs_review": cell["confidence"] * 100 < LOW_CONFIDENCE,
                    "lines": [
                        {
                            "text": cell["text"],
                            "confidence": cell["confidence"],
                            "bbox": cell["bbox"],
                            "paragraph_number": block["lines"][0]["paragraph_number"],
                            "line_number": block["lines"][0]["line_number"],
                            "needs_review": cell["confidence"] * 100 < LOW_CONFIDENCE,
                            "cells": [],
                        }
                    ],
                }
            )
    return [block for block in blocks if block not in candidates] + split_blocks


def _reading_order(blocks: list[dict], page_width: int) -> list[dict]:
    """Order clear two-column layouts without mixing their vertical streams."""

    if len(blocks) < 4 or page_width <= 0:
        return sorted(blocks, key=lambda block: (block["bbox"][1], block["bbox"][0]))

    content_tops = [block["bbox"][1] for block in blocks if block["type"] != "heading"]
    content_top = min(content_tops, default=0)
    spanning = [
        block
        for block in blocks
        if block["bbox"][2] >= page_width * 0.68
        or (block["type"] == "heading" and block["bbox"][1] < content_top)
    ]
    narrow = [block for block in blocks if block not in spanning]
    centers = sorted(
        (
            block["bbox"][0] + block["bbox"][2] / 2,
            index,
            block,
        )
        for index, block in enumerate(narrow)
    )
    if len(centers) < 4:
        return sorted(blocks, key=lambda block: (block["bbox"][1], block["bbox"][0]))

    gaps = [(centers[index + 1][0] - centers[index][0], index) for index in range(len(centers) - 1)]
    largest_gap, split_index = max(gaps, default=(0, 0))
    left = [block for _, _, block in centers[: split_index + 1]]
    right = [block for _, _, block in centers[split_index + 1 :]]
    if largest_gap < page_width * 0.18 or len(left) < 2 or len(right) < 2:
        return sorted(blocks, key=lambda block: (block["bbox"][1], block["bbox"][0]))

    ordered_spanning = sorted(spanning, key=lambda block: (block["bbox"][1], block["bbox"][0]))
    ordered_columns = sorted(left, key=lambda block: block["bbox"][1]) + sorted(
        right, key=lambda block: block["bbox"][1]
    )
    top_of_columns = min(block["bbox"][1] for block in ordered_columns)
    header = [block for block in ordered_spanning if block["bbox"][1] < top_of_columns]
    footer = [block for block in ordered_spanning if block not in header]
    return header + ordered_columns + footer


def build_page_structure(
    words: list[Any], *, page_number: int, width: int, height: int
) -> dict:
    """Create serializable blocks while retaining every recognized word."""

    grouped_lines: dict[tuple[int, int, int], list[Any]] = defaultdict(list)
    for word in words:
        grouped_lines[(word.block_number, word.paragraph_number, word.line_number)].append(word)

    grouped_blocks: dict[int, list[dict]] = defaultdict(list)
    for (block_number, paragraph_number, line_number), line_words in grouped_lines.items():
        ordered_words = sorted(line_words, key=lambda word: word.word_number or word.bbox[0])
        confidence = mean(max(0.0, word.confidence) for word in ordered_words) / 100
        grouped_blocks[block_number].append(
            {
                "text": " ".join(word.text for word in ordered_words),
                "confidence": round(confidence, 3),
                "bbox": _union_bbox(ordered_words),
                "paragraph_number": paragraph_number,
                "line_number": line_number,
                "needs_review": confidence * 100 < LOW_CONFIDENCE,
                "cells": _line_cells(ordered_words),
            }
        )

    blocks: list[dict] = []
    for block_number, lines in grouped_blocks.items():
        ordered_lines = sorted(lines, key=lambda line: (line["bbox"][1], line["bbox"][0]))
        text = "\n".join(line["text"] for line in ordered_lines)
        block_confidence = mean(line["confidence"] for line in ordered_lines)
        block = {
            "type": _block_type(text, ordered_lines),
            "text": text,
            "confidence": round(block_confidence, 3),
            "bbox": _union_bbox(
                type("Box", (), {"bbox": tuple(line["bbox"])}) for line in ordered_lines
            ),
            "block_number": block_number,
            "needs_review": block_confidence * 100 < LOW_CONFIDENCE,
            "lines": ordered_lines,
        }
        if block["type"] == "key_value":
            key, value = text.split(":", 1)
            block["key"] = key.strip()
            block["value"] = value.strip()
        if block["type"] == "table":
            block["rows"] = [line["cells"] for line in ordered_lines if line["cells"]]
        blocks.append(block)

    blocks = _merge_page_table_rows(blocks)
    blocks = _split_page_columns(blocks, width)
    ordered_blocks = _reading_order(blocks, width)
    return {
        "page_number": page_number,
        "width": width,
        "height": height,
        "blocks": ordered_blocks,
    }


def render_page_text(page: dict) -> str:
    """Render blocks in the established reading order without rewriting content."""

    return "\n\n".join(block["text"] for block in page["blocks"] if block["text"])
