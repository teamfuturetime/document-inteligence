"""Readability-focused post-processing for OCR text.

The raw OCR value remains the source of truth.  This module only produces a
presentation-friendly rendering and deliberately avoids document-specific
corrections that could change meaning.
"""

from __future__ import annotations

import re
import unicodedata


_MOJIBAKE_MARKERS = ("Ã", "Â", "Ä", "áº", "á»", "â€", "ðŸ")
_ONLY_NOISE = re.compile(r"^[^\wÀ-ỹ]+$", re.UNICODE)


def _mojibake_score(value: str) -> int:
    return sum(value.count(marker) for marker in _MOJIBAKE_MARKERS)


def _decode_mojibake(value: str) -> str:
    """Repair common UTF-8-as-Windows-1252 text only when confidence is high."""

    if not any(marker in value for marker in _MOJIBAKE_MARKERS):
        return value

    def decode_candidate(fragment: str) -> str:
        if not any(marker in fragment for marker in _MOJIBAKE_MARKERS):
            return fragment
        try:
            candidate = fragment.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return fragment
        return candidate if _mojibake_score(candidate) < _mojibake_score(fragment) else fragment

    try:
        candidate = value.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Mixed correctly decoded and garbled text is safer to repair token-wise.
        return re.sub(r"\S+", lambda match: decode_candidate(match.group()), value)
    return candidate if _mojibake_score(candidate) < _mojibake_score(value) else value


def _is_obvious_noise(line: str) -> bool:
    if not line:
        return False
    if _ONLY_NOISE.fullmatch(line):
        # Only remove repeated scan artifacts; punctuation may be document structure.
        return set(line) <= {"|", "_", "~"}
    return False


def clean_ocr_text(raw_text: str | None) -> str | None:
    """Return a conservative, human-readable rendering of raw OCR text.

    This normalizes encoding and whitespace, removes punctuation-only OCR noise,
    while preserving line boundaries, uppercase tokens and all numeric values.
    """

    if raw_text is None:
        return None

    text = unicodedata.normalize("NFC", raw_text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ").replace("\t", " ").replace("\f", "\n")
    text = _decode_mojibake(text)

    normalized_lines: list[str] = []
    for source_line in text.split("\n"):
        line = re.sub(r"[ \v]+", " ", source_line).strip()
        line = re.sub(r"\s+([,.;:!?])", r"\1", line)
        line = re.sub(r"([:;!?])(?=\S)", r"\1 ", line)
        line = re.sub(r"(?<!\d)([,.])(?=\S)", r"\1 ", line)
        line = re.sub(r"(?<=\d)([,.])(?=[^\s\d])", r"\1 ", line)
        if _is_obvious_noise(line):
            continue
        normalized_lines.append(line)

    output: list[str] = []
    for line in normalized_lines:
        if not line:
            if output and output[-1] != "":
                output.append("")
            continue

        output.append(line)

    while output and output[-1] == "":
        output.pop()
    cleaned = "\n".join(output).strip()
    return cleaned or None
