"""Extract invoice values from nearby OCR blocks, preserving original text."""
import re
from datetime import date

from ai_service.extraction.schemas import ExtractedField
from ai_service.ocr.normalization import fold_vietnamese_for_matching


def invoice_fields(pages):
    fields = {name: ExtractedField(value=None, confidence=0) for name in
              ("customer", "payment_recipient", "date", "total_amount")}
    for page in pages:
        blocks = page.lines
        for block in blocks:
            folded = fold_vietnamese_for_matching(block.text)
            match = re.search(r"ngay\s+(\d{1,2})\s+thang\s+(\d{1,2})\s+nam\s+(\d{4})", folded)
            if match:
                try:
                    value = date(int(match[3]), int(match[2]), int(match[1])).isoformat()
                    fields["date"] = ExtractedField(value=value, confidence=block.confidence, source_text=block.text)
                except ValueError:
                    pass
            for name, labels in {
                "customer": ("gui cho", "khach hang"),
                "payment_recipient": ("thanh toan cho",),
                "total_amount": ("tong cong", "tong thanh toan"),
            }.items():
                label = next((label for label in labels if label in folded), None)
                if not label:
                    continue
                end = folded.index(label) + len(label)
                value = block.text[end:].strip(" :.|\t")
                source = block
                if name == "total_amount":
                    amount = re.search(r"\d[\d.,]*\s*(?:đ|vnd)?", value, re.I)
                    if not amount:
                        candidates = [b for b in blocks if b.box[0] >= block.box[2] - .01
                                      and abs(b.box[1] - block.box[1]) < .015
                                      and re.search(r"\d[\d.,]+", b.text)]
                        if not candidates:
                            continue
                        source = min(candidates, key=lambda b: b.box[0])
                        amount = re.search(r"\d[\d.,]*\s*(?:đ|vnd)?", source.text, re.I)
                    value = amount[0].strip()
                elif not value:
                    candidates = [b for b in blocks if b.box[1] >= block.box[3] - .003
                                  and b.box[1] - block.box[3] < .065
                                  and abs(b.box[0] - block.box[0]) < .05]
                    if not candidates:
                        continue
                    source = min(candidates, key=lambda b: b.box[1])
                    value = source.text.strip()
                    if any(word in fold_vietnamese_for_matching(value) for word in
                           ("hang muc", "don gia", "tong cong", "so dien thoai")):
                        continue
                if value:
                    fields[name] = ExtractedField(value=value, confidence=min(block.confidence, source.confidence),
                                                  source_text=source.text)
    return fields
