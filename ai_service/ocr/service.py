from dataclasses import dataclass

import numpy as np

from ai_service.ocr.engines import OcrEngine
from ai_service.preprocessing import deskew, enhance_image


@dataclass(frozen=True)
class OcrPage:
    page_number: int
    width: int
    height: int
    lines: list

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)


class OcrService:
    def __init__(self, engine: OcrEngine):
        self.engine = engine

    def process_pages(self, pages: list[np.ndarray]) -> list[OcrPage]:
        results: list[OcrPage] = []
        for index, page in enumerate(pages, start=1):
            prepared = enhance_image(deskew(page))
            lines = self.engine.recognize(prepared)
            height, width = prepared.shape[:2]
            results.append(OcrPage(index, width, height, lines))
        return results
