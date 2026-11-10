"""Generate labeled, non-sensitive Vietnamese OCR fixtures."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, JpegImagePlugin  # noqa: F401


ROOT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "vietnamese"
FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]
STANDARD_CASES = {
    "don-xin-viec-tong-hop.png": (
        "don_xin_viec",
        "vietnamese_text",
        ["ĐƠN XIN VIỆC", "Kính gửi: Công ty Minh Họa", "Tôi tên là: NGUYỄN VĂN DEMO", "Vị trí ứng tuyển: Nhân viên kiểm thử", "Người làm đơn"],
    ),
    "hop-dong-tong-hop.png": (
        "hop_dong_lao_dong",
        "vietnamese_text",
        ["HỢP ĐỒNG LAO ĐỘNG", "Bên A: CÔNG TY MẪU", "Bên B: TRẦN THỊ THỬ NGHIỆM", "Điều 1: Thời hạn hợp đồng", "Tiền lương: 10.000.000 đồng"],
    ),
    "bieu-mau-hanh-chinh.png": (
        "application_form",
        "administrative_form",
        ["CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", "BIỂU MẪU HÀNH CHÍNH TỔNG HỢP", "Mã hồ sơ: DEMO-0001", "Nội dung chỉ dùng để kiểm thử OCR tiếng Việt."],
    ),
}


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_path = next((path for path in FONT_CANDIDATES if path.exists()), None)
    return ImageFont.truetype(str(font_path), size) if font_path else ImageFont.load_default()


def _base(size=(1654, 2339)) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((80, 80, size[0] - 80, size[1] - 80), outline="#1e3a5f", width=4)
    return image, draw


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    standard_pages: list[Image.Image] = []
    for filename, (expected, category, lines) in STANDARD_CASES.items():
        image, draw = _base()
        font = _font(34)
        for index, line in enumerate(lines):
            draw.text((140, 180 + index * 120), line, fill="#111827", font=font)
        image.save(ROOT / filename, dpi=(200, 200))
        standard_pages.append(image)
        manifest.append({
            "file": filename,
            "expected_document_type": expected,
            "category": category,
            "synthetic": True,
            "ground_truth": "\n".join(lines),
            "reading_order": lines,
        })

    multi_truth = ["\n".join(lines) for _, _, lines in STANDARD_CASES.values()]
    standard_pages[0].save(ROOT / "bo-mau-nhieu-trang.pdf", save_all=True, append_images=standard_pages[1:], resolution=200)
    manifest.append({
        "file": "bo-mau-nhieu-trang.pdf",
        "expected_document_type": "mixed_demo",
        "category": "multi_page_pdf",
        "synthetic": True,
        "pages": 3,
        "ground_truth": "\f".join(multi_truth),
        "reading_order": [line for truth in multi_truth for line in truth.splitlines()],
    })

    invoice_lines = ["HÓA ĐƠN DỊCH VỤ", "MST: 0101234567", "Hạng mục Số lượng Đơn giá Thành tiền", "Dịch vụ A 2 500.000 1.000.000", "TỔNG CỘNG: 1.000.000 đồng"]
    image, draw = _base()
    draw.text((520, 150), invoice_lines[0], fill="#111827", font=_font(40))
    draw.text((140, 250), invoice_lines[1], fill="#111827", font=_font(30))
    columns = [140, 650, 920, 1240]
    rows = [["Hạng mục", "Số lượng", "Đơn giá", "Thành tiền"], ["Dịch vụ A", "2", "500.000", "1.000.000"]]
    for row_index, row in enumerate(rows):
        y = 420 + row_index * 100
        for column_index, value in enumerate(row):
            draw.text((columns[column_index], y), value, fill="#111827", font=_font(28))
    draw.text((900, 680), invoice_lines[-1], fill="#111827", font=_font(30))
    image.save(ROOT / "hoa-don-bang-tong-hop.png", dpi=(200, 200))
    manifest.append({"file": "hoa-don-bang-tong-hop.png", "expected_document_type": "hoa_don", "category": "invoice_table", "synthetic": True, "ground_truth": "\n".join(invoice_lines), "reading_order": invoice_lines, "expected_structure": ["heading", "key_value", "table"], "expected_fields": {"tax_code": "0101234567", "total_amount": "1.000.000"}})

    column_lines = ["VĂN BẢN HAI CỘT", "Cột trái dòng một", "Cột trái dòng hai", "Cột phải dòng một", "Cột phải dòng hai"]
    image, draw = _base()
    draw.text((560, 150), column_lines[0], fill="#111827", font=_font(40))
    for index, line in enumerate(column_lines[1:3]):
        draw.text((140, 350 + index * 120), line, fill="#111827", font=_font(30))
    for index, line in enumerate(column_lines[3:]):
        draw.text((900, 350 + index * 120), line, fill="#111827", font=_font(30))
    image.save(ROOT / "van-ban-hai-cot-tong-hop.png", dpi=(200, 200))
    manifest.append({"file": "van-ban-hai-cot-tong-hop.png", "expected_document_type": "unknown", "category": "multi_column", "synthetic": True, "ground_truth": "\n".join(column_lines), "reading_order": column_lines})

    low_lines = ["ẢNH NGHIÊNG ĐỘ PHÂN GIẢI THẤP", "Ngày: 01/05/2026", "Mã hồ sơ: DEMO-0099"]
    low, draw = _base((900, 1200))
    for index, line in enumerate(low_lines):
        draw.text((70, 170 + index * 100), line, fill="#111827", font=_font(24))
    low = low.rotate(3, resample=Image.Resampling.BICUBIC, expand=False, fillcolor="white")
    low.save(ROOT / "anh-nghieng-do-phan-giai-thap.png", dpi=(120, 120))
    manifest.append({"file": "anh-nghieng-do-phan-giai-thap.png", "expected_document_type": "unknown", "category": "skewed_low_resolution", "synthetic": True, "ground_truth": "\n".join(low_lines), "reading_order": low_lines})

    (ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {len(manifest)} labeled fixtures in {ROOT}")


if __name__ == "__main__":
    main()
