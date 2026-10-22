"""Generate non-sensitive Vietnamese demo documents; no personal data is used."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, JpegImagePlugin  # noqa: F401

ROOT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "vietnamese"
FONT_CANDIDATES = [Path("C:/Windows/Fonts/arial.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]

CASES = {
    "don-xin-viec-tong-hop.png": ("don_xin_viec", ["ĐƠN XIN VIỆC", "Kính gửi: Công ty Minh Họa", "Tôi tên là: NGUYỄN VĂN DEMO", "Vị trí ứng tuyển: Nhân viên kiểm thử", "Người làm đơn"]),
    "hop-dong-tong-hop.png": ("hop_dong_lao_dong", ["HỢP ĐỒNG LAO ĐỘNG", "Bên A: CÔNG TY MẪU", "Bên B: TRẦN THỊ THỬ NGHIỆM", "Điều 1: Thời hạn hợp đồng", "Tiền lương: 10.000.000 đồng"]),
    "bieu-mau-hanh-chinh.png": ("unknown", ["CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", "BIỂU MẪU HÀNH CHÍNH TỔNG HỢP", "Mã hồ sơ: DEMO-0001", "Nội dung chỉ dùng để kiểm thử OCR tiếng Việt."]),
}

def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    font_path = next((path for path in FONT_CANDIDATES if path.exists()), None)
    font = ImageFont.truetype(str(font_path), 34) if font_path else ImageFont.load_default()
    manifest = []
    pages = []
    for filename, (expected, lines) in CASES.items():
        image = Image.new("RGB", (1654, 2339), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((80, 80, 1574, 2259), outline="#1e3a5f", width=4)
        for index, line in enumerate(lines):
            draw.text((140, 180 + index * 120), line, fill="#111827", font=font)
        image.save(ROOT / filename, dpi=(200, 200))
        pages.append(image)
        manifest.append({"file": filename, "expected_document_type": expected, "synthetic": True})
    pages[0].save(ROOT / "bo-mau-nhieu-trang.pdf", save_all=True, append_images=pages[1:], resolution=200)
    manifest.append({"file": "bo-mau-nhieu-trang.pdf", "expected_document_type": "mixed_demo", "synthetic": True, "pages": 3})
    (ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {len(manifest)} fixtures in {ROOT}")

if __name__ == "__main__":
    main()
