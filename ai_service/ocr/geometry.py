from dataclasses import dataclass

from ai_service.ocr.engines import RawOcrLine


@dataclass(frozen=True)
class TextBlock:
    text: str
    confidence: float
    box: tuple[float, float, float, float]


def to_text_block(line: RawOcrLine, width: int, height: int) -> TextBlock:
    if width <= 0 or height <= 0 or not line.polygon:
        raise ValueError("Invalid page geometry")
    xs = [point[0] for point in line.polygon]
    ys = [point[1] for point in line.polygon]
    clamp = lambda value: min(max(value, 0.0), 1.0)
    box = (
        clamp(min(xs) / width),
        clamp(min(ys) / height),
        clamp(max(xs) / width),
        clamp(max(ys) / height),
    )
    return TextBlock(line.text, min(max(line.confidence, 0.0), 1.0), box)


def extract_blocks(lines: list[RawOcrLine], width: int, height: int) -> list[TextBlock]:
    return [to_text_block(line, width, height) for line in lines]
