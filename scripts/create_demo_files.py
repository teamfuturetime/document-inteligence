import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "demo_documents"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REGULAR_FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
BOLD_FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def get_font(bold: bool = False, size: int = 24) -> ImageFont.FreeTypeFont:
    path = BOLD_FONT if bold else REGULAR_FONT
    return ImageFont.truetype(path, size)


def draw_red_seal(draw: ImageDraw.ImageDraw, center: tuple[int, int], radius: int, text: str):
    cx, cy = center
    red = (200, 30, 30)
    # Outer circle
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=red, width=4)
    # Inner circle
    r_inner = radius - 10
    draw.ellipse([cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner], outline=red, width=2)
    # 5-point Star in center
    star_r = radius * 0.35
    points = []
    for i in range(10):
        r = star_r if i % 2 == 0 else star_r / 2.5
        angle = i * math.pi / 5 - math.pi / 2
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(points, fill=red)
    # Circular or curved text simulation
    seal_font = get_font(bold=True, size=13)
    draw.text((cx, cy - radius + 20), text[:18], fill=red, font=seal_font, anchor="mm")
    draw.text((cx, cy + radius - 20), text[18:], fill=red, font=seal_font, anchor="mm")


def draw_blue_signature(draw: ImageDraw.ImageDraw, start: tuple[int, int], name: str):
    x, y = start
    blue = (25, 60, 160)
    # Draw cursive-like wavy curves for signature
    points = [
        (x, y + 25), (x + 20, y - 10), (x + 40, y + 20), (x + 65, y - 5),
        (x + 90, y + 15), (x + 120, y - 2), (x + 150, y + 10), (x + 180, y + 5)
    ]
    draw.line(points, fill=blue, width=3, joint="curve")
    draw.line([(x + 10, y + 15), (x + 170, y + 15)], fill=blue, width=2)
    name_font = get_font(bold=True, size=18)
    draw.text((x + 80, y + 55), name, fill=(30, 30, 30), font=name_font, anchor="mm")


def create_id_card():
    """Tạo Căn cước công dân chuẩn."""
    width, height = 1000, 630
    img = Image.new("RGB", (width, height), color=(240, 246, 252))
    draw = ImageDraw.Draw(img)

    # Viền thẻ và dải nền trang trí
    draw.rounded_rectangle([15, 15, width - 15, height - 15], radius=24, outline=(70, 130, 180), width=4)
    draw.rectangle([25, 25, width - 25, 110], fill=(225, 238, 250))

    # Quốc hiệu
    draw.text((width // 2, 45), "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", fill=(180, 20, 20), font=get_font(True, 22), anchor="mm")
    draw.text((width // 2, 72), "Độc lập - Tự do - Hạnh phúc", fill=(20, 20, 20), font=get_font(True, 16), anchor="mm")
    draw.line([(width // 2 - 110, 85), (width // 2 + 110, 85)], fill=(20, 20, 20), width=2)

    # Tiêu đề thẻ
    draw.text((width // 2 + 60, 135), "CĂN CƯỚC CÔNG DÂN", fill=(10, 50, 120), font=get_font(True, 28), anchor="mm")
    draw.text((width // 2 + 60, 165), "IDENTITY CARD", fill=(100, 116, 139), font=get_font(False, 15), anchor="mm")

    # Khung ảnh chân dung
    draw.rectangle([45, 180, 245, 450], outline=(148, 163, 184), width=3, fill=(230, 235, 245))
    # Silhouette chân dung
    draw.ellipse([110, 230, 180, 300], fill=(160, 175, 195))
    draw.polygon([(80, 420), (145, 330), (210, 420)], fill=(160, 175, 195))
    draw.text((145, 430), "ẢNH 3x4", fill=(100, 116, 139), font=get_font(True, 14), anchor="mm")

    # Biểu tượng Chip điện tử
    draw.rounded_rectangle([45, 480, 120, 535], radius=8, fill=(212, 175, 55), outline=(180, 140, 30), width=2)
    draw.line([(70, 480), (70, 535)], fill=(160, 120, 20), width=2)
    draw.line([(95, 480), (95, 535)], fill=(160, 120, 20), width=2)

    # Các trường thông tin (khớp đúng keywords và patterns của hệ thống)
    left_x = 280
    info = [
        ("Số / No.:", "079098012345", True, 26, (180, 20, 20)),
        ("Họ và tên / Full name:", "NGUYỄN VĂN AN", True, 24, (20, 30, 80)),
        ("Ngày sinh / Date of birth:", "15/08/1998", False, 20, (30, 30, 30)),
        ("Giới tính / Sex:", "Nam          Quốc tịch / Nationality: Việt Nam", False, 18, (30, 30, 30)),
        ("Quê quán / Place of origin:", "Xã Tân Triều, Huyện Thanh Trì, TP. Hà Nội", False, 19, (30, 30, 30)),
        ("Nơi thường trú / Place of residence:", "123 Đường Nguyễn Trãi, Phường 2, Quận 5, TP.HCM", False, 19, (30, 30, 30)),
        ("Có giá trị đến / Date of expiry:", "15/08/2038", False, 18, (30, 30, 30)),
    ]

    curr_y = 190
    for label, val, is_bold, sz, col in info:
        draw.text((left_x, curr_y), label, fill=(100, 116, 139), font=get_font(False, 15))
        draw.text((left_x, curr_y + 22), val, fill=col, font=get_font(is_bold, sz))
        curr_y += 58

    # Xuất ra PNG và PDF
    png_path = OUTPUT_DIR / "01_can_cuoc_cong_dan.png"
    pdf_path = OUTPUT_DIR / "01_can_cuoc_cong_dan.pdf"
    img.save(png_path)
    img.save(pdf_path, "PDF", resolution=150.0)
    print(f"Generated: {png_path.name} & {pdf_path.name}")


def create_birth_certificate():
    """Tạo Giấy khai sinh chuẩn."""
    width, height = 1200, 1700
    img = Image.new("RGB", (width, height), color=(253, 252, 247))
    draw = ImageDraw.Draw(img)

    # Khung viền đôi trang trọng
    draw.rectangle([40, 40, width - 40, height - 40], outline=(160, 120, 60), width=4)
    draw.rectangle([52, 52, width - 52, height - 52], outline=(200, 160, 100), width=2)

    # Cơ quan cấp & Quốc hiệu
    draw.text((80, 80), "UBND PHƯỜNG BẾN THÀNH", fill=(40, 40, 40), font=get_font(True, 22))
    draw.text((80, 110), "QUẬN 1, TP. HỒ CHÍ MINH", fill=(60, 60, 60), font=get_font(False, 18))
    draw.text((80, 140), "Số: 156/TLKS-BS", fill=(160, 40, 40), font=get_font(True, 18))

    draw.text((width - 80, 80), "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", fill=(20, 20, 20), font=get_font(True, 22), anchor="ra")
    draw.text((width - 80, 115), "Độc lập - Tự do - Hạnh phúc", fill=(20, 20, 20), font=get_font(True, 18), anchor="ra")
    draw.line([(width - 380, 135), (width - 80, 135)], fill=(20, 20, 20), width=2)

    # Tiêu đề
    draw.text((width // 2, 230), "GIẤY KHAI SINH", fill=(180, 20, 20), font=get_font(True, 42), anchor="mm")
    draw.text((width // 2, 280), "(BẢN SAO TRÍCH LỤC)", fill=(70, 70, 70), font=get_font(True, 22), anchor="mm")

    # Danh sách các trường
    left = 120
    fields = [
        ("Họ và tên:", "TRẦN THỊ BÌNH", True, 26, (10, 30, 100)),
        ("Giới tính:", "Nữ                 Dân tộc: Kinh               Quốc tịch: Việt Nam", False, 22, (30, 30, 30)),
        ("Ngày sinh:", "20/11/2005", True, 24, (160, 20, 20)),
        ("Ghi bằng chữ:", "Ngày hai mươi tháng mười một năm hai nghìn không trăm lẻ năm", False, 20, (60, 60, 60)),
        ("Nơi sinh:", "Bệnh viện Phụ sản Từ Dũ, Quận 1, TP. Hồ Chí Minh", False, 22, (30, 30, 30)),
        ("Quê quán:", "Phường Tân Định, Quận 1, TP. Hồ Chí Minh", False, 22, (30, 30, 30)),
        ("Số định danh cá nhân:", "079305009876", False, 22, (30, 30, 30)),
        ("Họ và tên cha:", "TRẦN VĂN HÙNG", True, 24, (20, 20, 20)),
        ("Năm sinh cha:", "1978               Dân tộc: Kinh               Quốc tịch: Việt Nam", False, 20, (50, 50, 50)),
        ("Họ và tên mẹ:", "LÊ THỊ MAI", True, 24, (20, 20, 20)),
        ("Năm sinh mẹ:", "1982               Dân tộc: Kinh               Quốc tịch: Việt Nam", False, 20, (50, 50, 50)),
        ("Người đi khai sinh:", "Trần Văn Hùng (Quan hệ: Cha đẻ)", False, 22, (30, 30, 30)),
    ]

    y = 360
    for label, val, is_bold, sz, col in fields:
        draw.text((left, y), label, fill=(100, 100, 100), font=get_font(False, 20))
        draw.text((left + 260, y), val, fill=col, font=get_font(is_bold, sz))
        draw.line([(left, y + 36), (width - 120, y + 36)], fill=(230, 225, 215), width=1)
        y += 70

    # Phần chữ ký, dấu mộc
    y_sign = height - 320
    draw.text((width - 320, y_sign), "TP. Hồ Chí Minh, ngày 25 tháng 11 năm 2005", fill=(40, 40, 40), font=get_font(False, 19), anchor="mm")
    draw.text((width - 320, y_sign + 35), "CHỦ TỊCH ỦY BAN NHÂN DÂN", fill=(20, 20, 20), font=get_font(True, 20), anchor="mm")
    draw_blue_signature(draw, (width - 410, y_sign + 80), "Lê Hoàng Quân")
    draw_red_seal(draw, (width - 450, y_sign + 120), 85, "UBND PHUONG BEN THANH*QUAN 1*")

    png_path = OUTPUT_DIR / "02_giay_khai_sinh.png"
    pdf_path = OUTPUT_DIR / "02_giay_khai_sinh.pdf"
    img.save(png_path)
    img.save(pdf_path, "PDF", resolution=150.0)
    print(f"Generated: {png_path.name} & {pdf_path.name}")


def create_application_form():
    """Tạo Đơn đề nghị chuẩn."""
    width, height = 1200, 1700
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Khung nhẹ
    draw.rectangle([50, 50, width - 50, height - 50], outline=(200, 210, 220), width=2)

    # Quốc hiệu
    draw.text((width // 2, 100), "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", fill=(20, 20, 20), font=get_font(True, 26), anchor="mm")
    draw.text((width // 2, 140), "Độc lập - Tự do - Hạnh phúc", fill=(20, 20, 20), font=get_font(True, 21), anchor="mm")
    draw.line([(width // 2 - 160, 160), (width // 2 + 160, 160)], fill=(20, 20, 20), width=2)

    # Tiêu đề đơn
    draw.text((width // 2, 240), "ĐƠN ĐỀ NGHỊ", fill=(10, 40, 110), font=get_font(True, 38), anchor="mm")
    draw.text((width // 2, 290), "Về việc: Cấp lại thẻ sinh viên và bảng điểm rèn luyện", fill=(180, 30, 30), font=get_font(True, 22), anchor="mm")

    # Kính gửi
    left = 130
    draw.text((left, 360), "Kính gửi:", fill=(50, 50, 50), font=get_font(True, 22))
    draw.text((left + 120, 360), "Ban Giám hiệu Trường Đại học Khoa học Tự nhiên", fill=(20, 20, 20), font=get_font(False, 22))
    draw.text((left + 120, 400), "Phòng Công tác Sinh viên", fill=(20, 20, 20), font=get_font(False, 22))

    # Thông tin người làm đơn
    lines = [
        ("Người làm đơn:", "PHẠM MINH ĐỨC", True, (10, 40, 120)),
        ("Sinh ngày:", "10/05/2003", False, (30, 30, 30)),
        ("Mã số sinh viên:", "21120001", False, (30, 30, 30)),
        ("Địa chỉ:", "Ký túc xá Khu B, Đại học Quốc gia, TP. Thủ Đức, TP.HCM", False, (30, 30, 30)),
        ("Số điện thoại:", "0908123456", False, (30, 30, 30)),
    ]

    y = 470
    for label, val, is_bold, col in lines:
        draw.text((left, y), label, fill=(90, 90, 90), font=get_font(False, 21))
        draw.text((left + 220, y), val, fill=col, font=get_font(is_bold, 22))
        y += 50

    # Nội dung đề nghị
    draw.text((left, y + 20), "Nội dung đề nghị:", fill=(50, 50, 50), font=get_font(True, 22))
    content_lines = [
        "Trong thời gian tham gia thực tập doanh nghiệp vừa qua, tôi đã sơ ý đánh rơi ví",
        "trong đó có chứa thẻ sinh viên của nhà trường.",
        "Nay tôi làm đơn này kính đề nghị Phòng Công tác Sinh viên xem xét và cấp lại",
        "thẻ sinh viên cho tôi để thuận tiện cho việc tham gia kỳ thi học kỳ sắp tới.",
        "",
        "Tôi xin cam đoan những thông tin khai trên là hoàn toàn đúng sự thật và chịu",
        "hoàn toàn trách nhiệm trước nhà trường nếu có điều gì gian dối."
    ]
    cy = y + 70
    for cl in content_lines:
        draw.text((left + 20, cy), cl, fill=(40, 40, 40), font=get_font(False, 21))
        cy += 40

    # Chữ ký
    y_sign = height - 320
    draw.text((width - 320, y_sign), "ngày 15 tháng 10 năm 2026", fill=(60, 60, 60), font=get_font(False, 20), anchor="mm")
    draw.text((width - 320, y_sign + 40), "Người làm đơn", fill=(20, 20, 20), font=get_font(True, 22), anchor="mm")
    draw.text((width - 320, y_sign + 70), "(Ký và ghi rõ họ tên)", fill=(120, 120, 120), font=get_font(False, 17), anchor="mm")
    draw_blue_signature(draw, (width - 410, y_sign + 130), "Phạm Minh Đức")

    png_path = OUTPUT_DIR / "03_don_de_nghi.png"
    pdf_path = OUTPUT_DIR / "03_don_de_nghi.pdf"
    img.save(png_path)
    img.save(pdf_path, "PDF", resolution=150.0)
    print(f"Generated: {png_path.name} & {pdf_path.name}")


def create_unknown_document():
    """Tạo Biên bản họp (Tài liệu khác / unknown) để demo phân loại."""
    width, height = 1200, 1700
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.rectangle([50, 50, width - 50, height - 50], outline=(220, 220, 220), width=2)
    draw.text((width // 2, 100), "CÔNG TY CỔ PHẦN CÔNG NGHỆ TƯƠNG LAI", fill=(20, 20, 20), font=get_font(True, 24), anchor="mm")
    draw.text((width // 2, 140), "Số: 45/BB-CT", fill=(100, 100, 100), font=get_font(False, 18), anchor="mm")

    draw.text((width // 2, 230), "BIÊN BẢN HỌP GIAO BAN TUẦN", fill=(20, 50, 120), font=get_font(True, 34), anchor="mm")
    left = 140
    y = 320
    content = [
        "Thời gian: 09 giờ 00 ngày 15 tháng 10 năm 2026",
        "Địa điểm: Phòng họp A, Tầng 3",
        "Chủ trì: Ông Vũ Đình Nam - Giám đốc điều hành",
        "Thư ký: Bà Hoàng Mỹ Linh",
        "",
        "Nội dung cuộc họp:",
        "1. Đánh giá tiến độ triển khai hệ thống Document Intelligence AI-02.",
        "2. Thảo luận phương án thử nghiệm hiệu năng tải 421 người dùng.",
        "3. Kế hoạch demo nghiệm thu giai đoạn 1 của nhóm SE2026-T11.",
        "",
        "Kết luận:",
        "- Bộ phận kỹ thuật hoàn thiện bộ tài liệu kiểm thử trước ngày 20/10.",
        "- Chuẩn bị môi trường staging đảm bảo tiêu chuẩn bảo mật RE-044.",
    ]
    for line in content:
        draw.text((left, y), line, fill=(30, 30, 30), font=get_font(True if line.startswith(("Nội dung", "Kết luận")) else False, 22))
        y += 45

    png_path = OUTPUT_DIR / "04_bien_ban_hop.png"
    pdf_path = OUTPUT_DIR / "04_bien_ban_hop.pdf"
    img.save(png_path)
    img.save(pdf_path, "PDF", resolution=150.0)
    print(f"Generated: {png_path.name} & {pdf_path.name}")


if __name__ == "__main__":
    create_id_card()
    create_birth_certificate()
    create_application_form()
    create_unknown_document()
    print("All demo files created in:", OUTPUT_DIR)

