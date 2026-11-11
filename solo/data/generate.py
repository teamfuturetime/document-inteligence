"""Create independent synthetic fixtures. Freeze manifest before evaluating."""

import argparse
from datetime import date
import hashlib
from io import BytesIO
import json
from pathlib import Path
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont, __version__

from ai02_solo.contracts import LABELS, TITLES


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(output: Path, font: Path):
    if output.exists() and any(output.iterdir()):
        raise ValueError("Refuse to overwrite frozen data; use a new version/directory")
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"version": "solo-golden-1.0", "schema_version": "solo-1.0", "seed": 20261111,
        "generator": "solo-synthetic-1", "pillow": __version__, "font_sha256": sha(font),
        "ground_truth_review": "author-checked synthetic values; independent review pending", "documents": []}
    rng = random.Random(manifest["seed"])
    body = ImageFont.truetype(str(font), 32)
    small = ImageFont.truetype(str(font), 24)
    heading = ImageFont.truetype(str(font), 46)
    for kind in LABELS:
        for index in range(18):
            identifier = f"{kind}-{index + 1:03d}"
            layout = index // 3 % 3
            condition = ["clean", "blur", "missing"][index % 3]
            when = date(2026, 11, index + 1).isoformat()
            if kind == "invoice":
                truth = dict(invoice_number=f"SOLO-{index + 1:04d}", invoice_date=when,
                    seller_name=f"Cửa hàng Mẫu {['Sen', 'Mây', 'Lá'][layout]}",
                    total_amount=rng.randrange(1, 999) * 1000, currency=None if condition == "missing" else "VND")
            else:
                truth = dict(applicant_name=f"Người Mẫu {['Alpha', 'Beta', 'Gamma'][layout]}",
                    student_id=f"SYN-{index + 1:04d}", recipient="Phòng Đào tạo Mẫu",
                    request=None if condition == "missing" else "Xin cấp giấy xác nhận học tập",
                    submission_date=when)
            image = Image.new("RGB", (1200, 1600), "white")
            draw = ImageDraw.Draw(image)
            draw.text((70, 70), TITLES[kind].upper(), font=heading, fill="black")
            draw.text((70, 150), "DỮ LIỆU TỔNG HỢP - KHÔNG CÓ GIÁ TRỊ THỰC", font=small, fill="black")
            y = 285
            for key, aliases in LABELS[kind].items():
                if truth[key] is None:
                    continue
                value = str(truth[key])
                if key.endswith("_date"):
                    year, month, day = value.split("-")
                    value = f"{day}/{month}/{year}"
                if key == "total_amount":
                    value = f"{truth[key]:,}".replace(",", ".")
                label = aliases[min(layout, len(aliases) - 1)]
                rendered = [f"{label}: {value}"] if layout == 0 else ([f"{label} {value}"] if layout == 1 else [f"{label}:", value])
                for line in rendered:
                    assert draw.textbbox((70, y), line, font=body)[2] < 1150, line
                    draw.text((70, y), line, font=body, fill="black")
                    y += 65 if layout == 2 else 115
            draw.text((70, 1350), f"AI-02 Solo / {identifier} / synthetic", font=small, fill="black")
            if condition == "blur":
                image = image.filter(ImageFilter.GaussianBlur(.65))
            extension = ["png", "jpg", "pdf"][(index // 3 + index % 3) % 3]
            document = output / f"{identifier}.{extension}"
            if extension == "pdf":
                image.save(document, "PDF", resolution=150, quality=95,
                    creationDate="D:20261111000000Z", modDate="D:20261111000000Z")
            elif extension == "jpg":
                image.save(document, "JPEG", quality=88, subsampling=0)
            else:
                image.save(document, "PNG")
            ground_truth = output / f"{identifier}.json"
            ground_truth.write_text(json.dumps(truth, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            manifest["documents"].append({"id": identifier, "kind": kind,
                "split": "dev" if index < 9 else "test", "layout": ["colon", "no-colon", "stacked"][layout],
                "condition": condition, "file": document.name, "sha256": sha(document),
                "truth": ground_truth.name, "truth_sha256": sha(ground_truth)})
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Created {len(manifest['documents'])} synthetic documents; 18 dev / 18 test")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/golden-v1"))
    args = parser.parse_args()
    generate(args.output, args.font)
