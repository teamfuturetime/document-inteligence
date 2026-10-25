"""Deterministic, self-designed synthetic documents. No model is run here."""

import argparse
import hashlib
import json
import textwrap
from pathlib import Path

from docintel.config import ROOT
from docintel.domain.documents import DEFINITIONS
from document_pipeline.normalization import normalize
from PIL import Image, ImageDraw, ImageFilter, ImageFont

VERSION = "product-synthetic-1.0.0"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main():
    parser = argparse.ArgumentParser(
        description="Generate 150 parent samples, 90/30/30 split"
    )
    parser.add_argument("--font", type=Path)
    args = parser.parse_args()
    font_path = args.font or next(
        (
            path
            for path in (
                Path("C:/Windows/Fonts/arial.ttf"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            )
            if path.is_file()
        ),
        None,
    )
    if font_path is None:
        parser.error(
            "Pass a permitted Vietnamese-capable --font; font is never copied into Git"
        )
    samples = []
    for kind in DEFINITIONS:
        for index in range(75):
            sample_id = f"{kind}_{index:03}"
            split = (
                "test"
                if index % 5 == 0
                else "validation"
                if index % 5 == 1
                else "development"
            )
            layout = index % 3
            font = ImageFont.truetype(str(font_path), 28 + layout * 2)
            small = ImageFont.truetype(str(font_path), 19)
            image = Image.new("RGB", (1200, 1550), "white")
            draw = ImageDraw.Draw(image)
            draw.text(
                (60, 40),
                "MẪU GIẢ LẬP · KHÔNG PHẢI TÀI LIỆU THẬT",
                font=small,
                fill="#555555",
            )
            draw.text(
                (60, 110),
                "HÓA ĐƠN MẪU" if kind == "hoa_don" else "ĐƠN ĐỀ NGHỊ",
                font=font,
                fill="black",
            )
            if kind == "hoa_don":
                values = {
                    "invoice_number": f"00{41000 + index}",
                    "invoice_date": f"{index % 27 + 1:02}/10/2026",
                    "seller_name": f"Công ty Giả Lập {index + 100}",
                    "total_amount": f"{(index + 1) * 125000:,}".replace(",", "."),
                    "currency": "VND",
                }
            else:
                values = {
                    "full_name": f"Nguyễn Minh An {index + 100}",
                    "student_id": f"00{100000 + index}",
                    "date_of_birth": f"{index % 27 + 1:02}/03/2005",
                    "class_name": f"CNTT-K{index % 5 + 16}",
                    "faculty": "Công nghệ thông tin",
                    "request_content": f"Đề nghị cấp giấy xác nhận đang theo học. Mã hồ sơ mẫu {index + 100}.",
                    "request_date": f"{index % 27 + 1:02}/10/2026",
                }
            gold, tags = {}, [f"layout_{layout}", "typed", "vietnamese"]
            y = 230
            challenge = "seller_name" if kind == "hoa_don" else "student_id"
            for definition in DEFINITIONS[kind]:
                key, value = definition.field_id, values[definition.field_id]
                state = (
                    "unreadable"
                    if index % 19 == 2 and key == challenge
                    else (
                        "absent" if index % 17 == 3 and key == challenge else "present"
                    )
                )
                raw = str(value)
                if key in {"invoice_date", "request_date"} and index % 23 == 4:
                    raw = "31/02/2026"
                    tags.append("invalid_calendar_source")
                x = 60 + layout * 25
                draw.text((x, y), definition.label + ":", font=font, fill="black")
                y += 44
                lines = textwrap.wrap(raw, width=58)
                if state == "present":
                    for line in lines:
                        box = draw.textbbox((x + 20, y), line, font=font)
                        if box[2] > 1140 or box[3] > 1440:
                            raise ValueError("Dataset render overflow")
                        draw.text((x + 20, y), line, font=font, fill="black")
                        y += 39
                    gold[key] = {"status": "present", "value": normalize(key, raw)}
                else:
                    if state == "unreadable":
                        draw.rectangle((x + 20, y + 4, x + 440, y + 35), fill="#333333")
                    y += 39
                    gold[key] = {"status": state, "value": None}
                    tags.append(state)
                y += 40 + layout * 4
            draw.text(
                (60, 1480),
                sample_id + " · synthetic · " + VERSION,
                font=small,
                fill="#666666",
            )
            if index % 13 == 5:
                image = image.filter(ImageFilter.GaussianBlur(0.5))
                tags.append("mild_blur")
            image_path = ROOT / f"data/product/images/{sample_id}.png"
            annotation_path = ROOT / f"data/product/annotations/{sample_id}.json"
            image_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(image_path)
            write(annotation_path, {"sample_id": sample_id, "fields": gold})
            samples.append(
                {
                    "sample_id": sample_id,
                    "parent_document_id": sample_id,
                    "template_id": f"{kind}_layout_{layout}",
                    "document_type": kind,
                    "data_origin": "synthetic",
                    "split": split,
                    "input_path": image_path.relative_to(ROOT).as_posix(),
                    "input_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
                    "annotation_path": annotation_path.relative_to(ROOT).as_posix(),
                    "annotation_sha256": hashlib.sha256(
                        annotation_path.read_bytes()
                    ).hexdigest(),
                    "quality_tags": tags,
                }
            )
    write(
        ROOT / "data/manifests/product.json",
        {
            "purpose": "model_benchmark",
            "dataset_version": VERSION,
            "generator_version": "1.0.0",
            "provenance": {
                "creator": "scripts/generate_product_dataset.py",
                "template": "Self-designed",
                "font": font_path.name,
                "font_sha256": hashlib.sha256(font_path.read_bytes()).hexdigest(),
                "font_distribution": "System font is referenced, never redistributed",
            },
            "samples": samples,
        },
    )
    print(
        f"Generated {len(samples)} self-designed parent documents with separate development/validation/test"
    )


if __name__ == "__main__":
    main()
