"""Generate the frozen 30-document synthetic baseline before running evaluation."""

import argparse
from datetime import date
import hashlib
from io import BytesIO
import json
from pathlib import Path
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont, __version__ as pillow_version

SEED = 20261015
FONT_SHA256 = "525979822591a3447cfc49d943d6f7683508e25543407871c0ed8fed05fd2bd9"
LAYOUTS = [
    ["Số hóa đơn", "Ngày", "Bên bán", "Tổng tiền", "Tiền tệ"],
    ["Mã hóa đơn", "Ngày lập", "Người bán", "Tổng cộng", "Đơn vị tiền tệ"],
    ["Số hóa đơn", "Ngày hóa đơn", "Tên bên bán", "Tổng thanh toán", "Tiền tệ"],
]
FIELDS = ["invoice_number", "invoice_date", "seller_name", "total_amount", "currency"]
CONDITIONS = ["clean", "compression", "blur", "rotation", "missing-currency"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create(font: Path, output: Path):
    if sha(font) != FONT_SHA256:
        raise ValueError("Font hash differs from the frozen Arial baseline")
    if pillow_version != "12.3.0":
        raise ValueError("Use locked workspace Pillow 12.3.0")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output must be empty; never overwrite a frozen dataset")
    output.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    manifest = {"dataset_version": "golden-1.0.0", "schema_version": "1.0.0",
                "generator_version": "1.0.0", "seed": SEED, "pillow_version": pillow_version,
                "font_sha256": FONT_SHA256, "font": "macOS Supplemental Arial.ttf; not bundled",
                "ground_truth_review": "author-checked; independent team review pending",
                "target_macro_exact_match": .85, "documents": []}
    title = ImageFont.truetype(str(font), 48)
    body = ImageFont.truetype(str(font), 34)
    small = ImageFont.truetype(str(font), 25)
    for index in range(1, 31):
        identifier = f"golden-{index:03d}"
        layout = (index - 1) % 3
        condition = CONDITIONS[(index - 1) % 5]
        values = {"invoice_number": f"GH-{index:04d}",
                  "invoice_date": date(2026, (index - 1) % 12 + 1, 15 + index % 13).isoformat(),
                  "seller_name": f"Cửa hàng {['Sen', 'Mây', 'Lá'][layout]} Việt",
                  "total_amount": 0 if index == 6 else rng.randint(10, 9999) * 1000,
                  "currency": None if condition == "missing-currency" else "VND"}
        image = Image.new("RGB", (1200, 1600), "white")
        draw = ImageDraw.Draw(image)
        margin = [70, 100, 85][layout]
        draw.text((margin, 70), "HÓA ĐƠN BÁN HÀNG", font=title, fill="black")
        draw.text((margin, 145), "DỮ LIỆU GIẢ - KHÔNG CÓ GIÁ TRỊ THỰC", font=small, fill="black")
        order = [0, 1, 2, 3, 4] if layout != 1 else [2, 0, 1, 4, 3]
        row = 0
        for position in order:
            field = FIELDS[position]
            if values[field] is None:
                continue
            value = str(values[field])
            if field == "total_amount":
                separator = "," if layout == 2 else "."
                value = f"{values[field]:,}".replace(",", separator)
            text = f"{LAYOUTS[layout][position]}: {value}"
            point = (margin, 280 + row * [100, 110, 95][layout])
            assert draw.textbbox(point, text, font=body)[2] < 1150
            draw.text(point, text, font=body, fill="black")
            row += 1
        draw.text((margin, 1000), f"Mẫu synthetic độc lập {identifier}", font=small, fill="black")
        if condition == "blur":
            image = image.filter(ImageFilter.GaussianBlur(1.0))
        elif condition == "rotation":
            image = image.rotate(1.1, Image.Resampling.BICUBIC, fillcolor="white")
        elif condition == "compression":
            stream = BytesIO()
            image.save(stream, "JPEG", quality=35)
            stream.seek(0)
            with Image.open(stream) as encoded:
                image = encoded.convert("RGB")
        extension = ["png", "jpg", "pdf"][layout]
        filename = f"{identifier}.{extension}"
        document = output / filename
        if extension == "pdf":
            image.save(document, "PDF", resolution=150, quality=95, title=identifier,
                       creationDate="D:20261015000000Z", modDate="D:20261015000000Z")
        elif extension == "jpg":
            image.save(document, "JPEG", quality=90, subsampling=0)
        else:
            image.save(document, "PNG")
        truth = output / f"{identifier}.ground-truth.json"
        truth.write_text(json.dumps(values, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest["documents"].append({
            "id": identifier, "split": "dev" if index <= 18 else "test", "layout": f"labels-{layout + 1}",
            "condition": condition, "file": filename, "sha256": sha(document),
            "ground_truth": truth.name, "ground_truth_sha256": sha(truth),
        })
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Created 30 independent invoices, 18 dev / 12 test: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    create(args.font, args.output)
