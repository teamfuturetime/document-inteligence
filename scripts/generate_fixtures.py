"""Render biểu mẫu tự thiết kế; không phân phối font hệ thống, không chạy OCR."""

import argparse
import hashlib
import json
import random
import textwrap
from pathlib import Path

from docintel.config import ROOT
from docintel.domain.models import FIELD_IDS, SCHEMA_VERSION
from docintel.domain.normalization import normalize_value
from docintel.evaluation.manifest import checksum
from PIL import Image, ImageDraw, ImageFont

LABELS = {
    "full_name": "Họ và tên",
    "student_id": "Mã sinh viên",
    "date_of_birth": "Ngày sinh",
    "class_name": "Lớp",
    "faculty": "Khoa",
    "request_content": "Nội dung đề nghị",
    "request_date": "Ngày làm đơn",
}


def write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser(description="Tạo lại 6 fixture synthetic xác định")
    parser.add_argument("--font", type=Path)
    args = parser.parse_args()
    candidates = (
        [args.font]
        if args.font
        else [
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        ]
    )
    font_path = next((p for p in candidates if p and p.exists()), None)
    if font_path is None:
        parser.error(
            "Cần --font trỏ tới font có dấu tiếng Việt và quyền sử dụng phù hợp"
        )
    font = ImageFont.truetype(str(font_path), 30)
    small_font = ImageFont.truetype(str(font_path), 23)
    title_font = ImageFont.truetype(str(font_path), 44)
    names = [
        "Nguyễn Minh An",
        "Trần Mỹ Linh",
        "Lê Hoàng Bảo",
        "Đặng Thảo Vy",
        "Phạm Khánh Duy",
        "Võ Ngọc Hà",
    ]
    rng = random.Random(20261005)
    manifest = {
        "purpose": "contract_fixture",
        "dataset_version": "synthetic-seed-1.0.0",
        "samples": [],
    }
    predictions, ocr_records = {}, {}
    for index, name in enumerate(names, start=1):
        sample_id = f"fixture_{index:03d}"
        raw = {
            "full_name": name,
            "student_id": "00123456"
            if index == 2
            else f"00{rng.randrange(100000, 999999)}",
            "date_of_birth": "31/02/2005" if index == 5 else "12/03/2005",
            "class_name": "CNTT-K17",
            "faculty": None if index == 4 else "Công nghệ thông tin",
            "request_content": "Đề nghị xác nhận đang theo học"
            if index != 3
            else (
                "Đề nghị xác nhận đang theo học để bổ sung hồ sơ học bổng. "
                "Kính mong nhà trường hỗ trợ cấp giấy xác nhận."
            ),
            "request_date": "20/09/2026",
        }
        image = Image.new("RGB", (1100, 1400), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((30, 30, 1070, 1370), outline="#bac5d3", width=2)
        draw.text(
            (65, 65),
            "DỮ LIỆU GIẢ LẬP — KHÔNG PHẢI HỒ SƠ THẬT",
            fill="#b43f37",
            font=small_font,
        )
        draw.text((325, 150), "ĐƠN ĐỀ NGHỊ", fill="#162c48", font=title_font)
        draw.text(
            (65, 230),
            "Biểu mẫu minh họa AI-02 • nội dung và danh tính hư cấu",
            font=small_font,
            fill="#546479",
        )
        spans, gold_fields = [], {}
        y = 320
        for field_id in FIELD_IDS:
            value = raw[field_id]
            unreadable = index == 6 and field_id == "student_id"
            draw.text((65, y), LABELS[field_id] + ":", font=font, fill="#162c48")
            field_y = y + 45
            if unreadable:
                draw.rectangle((85, field_y + 5, 540, field_y + 34), fill="#424242")
                gold_fields[field_id] = {"status": "unreadable", "value": None}
                lines = []
            elif value is None:
                draw.line(
                    (85, field_y + 34, 980, field_y + 34), fill="#c5ceda", width=1
                )
                gold_fields[field_id] = {"status": "absent", "value": None}
                lines = []
            else:
                lines = textwrap.wrap(value, width=58)
                gold_fields[field_id] = {
                    "status": "present",
                    "value": normalize_value(field_id, value),
                }
            for line_index, line in enumerate(lines):
                line_y = field_y + line_index * 40
                draw.text((85, line_y), line, font=font, fill="#162c48")
                box = draw.textbbox((85, line_y), line, font=font)
                if box[2] > 1015 or box[3] > 1290:
                    raise ValueError("Nội dung tràn trang")
                x0, y0, x1, y1 = map(float, box)
                spans.append(
                    {
                        "span_id": f"{field_id}_{line_index}",
                        "page_index": 0,
                        "text": line,
                        "polygon": [
                            {"x": x0, "y": y0},
                            {"x": x1, "y": y0},
                            {"x": x1, "y": y1},
                            {"x": x0, "y": y1},
                        ],
                        "image_width": 1100,
                        "image_height": 1400,
                        "ocr_score": None,
                        "coordinate_system": "original_pixels_top_left",
                        "transform": "identity",
                    }
                )
            y += max(125, 85 + 40 * len(lines))
        draw.text(
            (65, 1310),
            sample_id + " • synthetic • seed 20261005 • chưa chạy OCR",
            font=small_font,
            fill="#546479",
        )
        image_path = ROOT / f"data/fixtures/images/{sample_id}.png"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(image_path, optimize=False)
        annotation_path = ROOT / f"data/fixtures/annotations/{sample_id}.json"
        write(annotation_path, {"sample_id": sample_id, "fields": gold_fields})
        fields = []
        for field_id in FIELD_IDS:
            value = None if (index == 6 and field_id == "student_id") else raw[field_id]
            # Sai có chủ ý để kiểm tra wrong / missing / extra trong evaluator.
            if index == 2 and field_id == "student_id":
                value = "00123457"
            if index == 3 and field_id == "request_content":
                value = None
            if index == 4 and field_id == "faculty":
                value = "Kinh tế"  # Không có trên ảnh; minh họa UNSUPPORTED_VALUE.
            references = [
                span["span_id"]
                for span in spans
                if span["span_id"].startswith(field_id + "_")
            ]
            fields.append(
                {
                    "field_id": field_id,
                    "raw_value": value,
                    "normalized_value": normalize_value(field_id, value),
                    "observation": "found"
                    if value is not None
                    else (
                        "unreadable"
                        if index == 6 and field_id == "student_id"
                        else "not_found"
                    ),
                    "evidence_status": "available" if references else "unavailable",
                    "evidence_span_ids": references,
                    "confidence": {
                        "method": "unknown",
                        "policy_version": "confidence-draft-1",
                        "score": None,
                        "ocr_score": None,
                        "mapping_signals": {},
                        "reason_codes": ["FIXTURE_NOT_MEASURED"],
                    },
                }
            )
        predictions[sample_id] = {
            "run_id": f"run_{sample_id}",
            "document_id": sample_id,
            "schema_version": SCHEMA_VERSION,
            "provenance": {"data_origin": "synthetic", "prediction_source": "fixture"},
            "fields": fields,
            "spans": spans,
            "status": "succeeded",
        }
        ocr_records[sample_id] = {
            "status": "succeeded",
            "prediction_source": "fixture",
            "spans": spans,
            "engine_package": None,
            "model_artifact": None,
            "error_code": None,
        }
        tags = {
            1: ["clear", "vietnamese"],
            2: ["leading_zero", "intentional_wrong"],
            3: ["multiline", "intentional_missing"],
            4: ["absent", "intentional_extra"],
            5: ["invalid_date_visible"],
            6: ["masked_unreadable"],
        }[index]
        manifest["samples"].append(
            {
                "sample_id": sample_id,
                "parent_document_id": f"parent_{index:03d}",
                "template_id": "request_form_a",
                "document_type": "don_de_nghi",
                "input_path": image_path.relative_to(ROOT).as_posix(),
                "input_sha256": checksum(image_path),
                "annotation_path": annotation_path.relative_to(ROOT).as_posix(),
                "annotation_sha256": checksum(annotation_path),
                "split": "contract_fixture",
                "quality_tags": tags,
                "provenance": {
                    "data_origin": "synthetic",
                    "creator": "scripts/generate_fixtures.py",
                    "template": "Tự thiết kế trong repository",
                    "font": font_path.name,
                    "font_sha256": hashlib.sha256(font_path.read_bytes()).hexdigest(),
                    "font_distribution": "System font; không phân phối trong repository",
                    "seed": "20261005",
                },
                "dataset_version": manifest["dataset_version"],
            }
        )
    write(ROOT / "data/manifests/fixtures.json", manifest)
    write(ROOT / "data/fixtures/predictions.json", predictions)
    write(ROOT / "data/fixtures/ocr.json", ocr_records)
    write(
        ROOT / "evaluation/examples/prediction-fixture.json", predictions["fixture_002"]
    )
    print(
        "Generated 6 synthetic fixtures; verify images/gold after font or generator changes."
    )


if __name__ == "__main__":
    main()
