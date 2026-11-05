from dataclasses import dataclass

import numpy as np

from ai_service.ocr.engines import OcrEngine
from ai_service.ocr.geometry import TextBlock, extract_blocks
from ai_service.ocr.normalization import normalize_vietnamese_text
from ai_service.preprocessing import deskew, enhance_image


@dataclass(frozen=True)
class OcrPage:
    page_number: int
    width: int
    height: int
    lines: list[TextBlock]

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)


class OcrService:
    def __init__(self, engine: OcrEngine):
        self.engine = engine

    def process_pages(self, pages: list[np.ndarray]) -> list[OcrPage]:
        results: list[OcrPage] = []
        for index, page in enumerate(pages, start=1):
            prepared = (
                enhance_image(deskew(page))
                if getattr(self.engine, "uses_preprocessing", True)
                else page
            )
            height, width = prepared.shape[:2]
            lines = [
                TextBlock(normalize_vietnamese_text(line.text), line.confidence, line.box)
                for line in extract_blocks(self.engine.recognize(prepared), width, height)
            ]
            results.append(OcrPage(index, width, height, lines))
        return results
