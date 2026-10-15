"""Unit tests cho tiền xử lý ảnh và tài liệu."""
import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from ai_service.preprocessing.document import (  # noqa: E402
    deskew,
    estimate_skew_angle,
    pdf_to_images,
)
from ai_service.preprocessing.image import (  # noqa: E402
    binarize,
    denoise,
    enhance_contrast,
    preprocess_image,
    resize_to_max_width,
    to_grayscale,
)


@pytest.fixture()
def sample_image() -> np.ndarray:
    """Ảnh xám 200x100 với nền trắng và chữ đen."""
    img = np.full((100, 200), 255, dtype=np.uint8)
    cv2.rectangle(img, (20, 30), (180, 70), 0, -1)  # khối chữ
    return img


def test_to_grayscale_keeps_gray(sample_image):
    result = to_grayscale(sample_image)
    assert result.ndim == 2
    assert result.shape == sample_image.shape


def test_to_grayscale_from_color():
    color = np.zeros((50, 50, 3), dtype=np.uint8)
    gray = to_grayscale(color)
    assert gray.ndim == 2
    assert gray.shape == (50, 50)


def test_enhance_contrast_shape(sample_image):
    result = enhance_contrast(sample_image)
    assert result.shape == sample_image.shape
    assert result.dtype == np.uint8


def test_denoise_shape(sample_image):
    result = denoise(sample_image)
    assert result.shape == sample_image.shape


def test_binarize_otsu(sample_image):
    binary = binarize(sample_image)
    assert set(np.unique(binary)) <= {0, 255}


def test_resize_to_max_width(sample_image):
    small = resize_to_max_width(sample_image, max_width=100)
    assert small.shape[1] == 100
    # Ảnh nhỏ hơn max_width không bị đổi
    unchanged = resize_to_max_width(sample_image, max_width=500)
    assert unchanged.shape == sample_image.shape


def test_preprocess_image_pipeline(sample_image):
    result = preprocess_image(sample_image, binarize_output=True)
    assert result.ndim == 2
    assert set(np.unique(result)) <= {0, 255}


def test_estimate_skew_angle_zero(sample_image):
    angle = estimate_skew_angle(sample_image)
    assert abs(angle) < 1.0


def test_estimate_skew_angle_detects_rotation():
    """Ảnh xoay 5 độ phải cho góc ước lượng gần -5 hoặc 5."""
    img = np.full((200, 400), 255, dtype=np.uint8)
    cv2.line(img, (50, 100), (350, 100), 0, 3)  # đường ngang
    center = (img.shape[1] // 2, img.shape[0] // 2)
    matrix = cv2.getRotationMatrix2D(center, 5.0, 1.0)
    rotated = cv2.warpAffine(img, matrix, (img.shape[1], img.shape[0]))

    angle = estimate_skew_angle(rotated)
    assert abs(angle) > 1.0


def test_deskew_returns_same_shape(sample_image):
    result = deskew(sample_image)
    assert result.shape == sample_image.shape


def test_pdf_to_images_missing_file():
    with pytest.raises(Exception):
        pdf_to_images("khong-ton-tai.pdf")
