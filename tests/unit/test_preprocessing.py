import cv2
import numpy as np

from ai_service.preprocessing import deskew, enhance_image, pdf_to_images


def test_enhance_image_returns_binary_grayscale() -> None:
    image = np.full((80, 160, 3), 255, dtype=np.uint8)
    cv2.putText(image, "TEST", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    result = enhance_image(image)
    assert result.shape == image.shape[:2]
    assert set(np.unique(result)).issubset({0, 255})


def test_deskew_preserves_dimensions() -> None:
    image = np.full((40, 100), 255, dtype=np.uint8)
    cv2.line(image, (10, 20), (90, 25), 0, 2)
    assert deskew(image).shape == image.shape


def test_pdf_to_images_renders_page() -> None:
    import fitz

    document = fitz.open()
    document.new_page(width=100, height=100)
    pages = pdf_to_images(document.tobytes(), dpi=72)
    assert len(pages) == 1
    assert pages[0].shape[:2] == (100, 100)
