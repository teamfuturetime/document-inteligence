"""Create deliberately synthetic dev fixtures; no random or personal data."""

import argparse
import hashlib
import json
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, __version__ as pillow_version

ROOT = Path(__file__).resolve().parent
DATE = time.gmtime(0)
SPEC = [
    {
        "id": "synthetic-001", "formats": ["png", "jpg", "pdf"],
        "values": {
            "invoice_number": "SYN-0001", "invoice_date": "2026-10-09",
            "seller_name": "Cửa hàng Mây Việt - dữ liệu giả",
            "total_amount": 125000, "currency": "VND",
        },
    },
    {
        "id": "synthetic-002-missing", "formats": ["png"],
        "values": {
            "invoice_number": "SYN-0002", "invoice_date": "2026-10-08",
            "seller_name": "Cửa hàng Lá Việt - dữ liệu giả",
            "total_amount": 89000, "currency": None,
        },
    },
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def draw_invoice(values, font_path):
    image = Image.new("RGB", (1200, 1600), "white")
    draw = ImageDraw.Draw(image)
    title = ImageFont.truetype(str(font_path), 52)
    body = ImageFont.truetype(str(font_path), 34)
    small = ImageFont.truetype(str(font_path), 26)
    draw.text((70, 70), "HÓA ĐƠN BÁN HÀNG", font=title, fill="black")
    draw.text((70, 150), "MẪU SYNTHETIC - KHÔNG CÓ GIÁ TRỊ THỰC", font=small, fill="black")
    draw.line((70, 210, 1130, 210), fill="black", width=2)
    labels = [
        f"Số hóa đơn: {values['invoice_number']}",
        f"Ngày: {values['invoice_date']}",
        f"Bên bán: {values['seller_name']}",
        f"Tổng tiền: {values['total_amount']:,}".replace(",", "."),
    ]
    if values["currency"] is not None:
        labels.append(f"Tiền tệ: {values['currency']}")
    for index, line in enumerate(labels):
        box = draw.textbbox((70, 280 + 100 * index), line, font=body)
        if box[2] > 1130:
            raise ValueError("Synthetic invoice text exceeds page width")
        draw.text((70, 280 + 100 * index), line, font=body, fill="black")
    draw.line((70, 860, 1130, 860), fill="black", width=2)
    draw.text((70, 910), "Chỉ dùng cho development và kiểm thử contract.", font=small, fill="black")
    draw.text((70, 960), "Tên cửa hàng và mã hóa đơn đều được tự tạo.", font=small, fill="black")
    return image


def create(font, output):
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "dataset_version": "samples-1.0.0", "schema_version": "1.0.0",
        "purpose": "development-only", "generator_version": "1.0.0",
        "seed": None, "randomness": "none",
        "pillow_version": pillow_version, "font_sha256": digest(font),
        "ground_truth_review": "author-checked; independent team review pending",
        "documents": [],
    }
    for spec in SPEC:
        image = draw_invoice(spec["values"], font)
        truth_name = f"{spec['id']}.ground-truth.json"
        (output / truth_name).write_text(
            json.dumps(spec["values"], ensure_ascii=False, indent=2) + "\n"
        )
        variants = []
        for ext in spec["formats"]:
            name = f"{spec['id']}.{ext}"
            path = output / name
            if ext == "png":
                image.save(path, "PNG")
            elif ext == "jpg":
                image.save(path, "JPEG", quality=95, subsampling=0)
            else:
                # Raster PDF intentionally exercises OCR rather than embedded text.
                image.save(path, "PDF", resolution=150.0, quality=95,
                           title=spec["id"], creationDate=DATE, modDate=DATE)
            variants.append({"file": name, "sha256": digest(path), "pages": 1})
        manifest["documents"].append({
            "id": spec["id"], "split": "dev", "layout": "simple-labels-v1",
            "condition": "clean" if spec["values"]["currency"] else "missing-currency",
            "ground_truth": truth_name,
            "ground_truth_sha256": digest(output / truth_name), "variants": variants,
        })
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"Created {len(SPEC)} synthetic invoices in {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, required=True, help="Vietnamese-capable TTF, not bundled")
    parser.add_argument("--output", type=Path, default=ROOT / "samples")
    args = parser.parse_args()
    if not args.font.is_file():
        parser.error("--font must point to an existing font file")
    create(args.font, args.output)


if __name__ == "__main__":
    main()
