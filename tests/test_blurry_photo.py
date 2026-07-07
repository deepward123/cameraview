"""Gerileme testi: kullanıcının forklift kamerası fotoğrafına benzer koşullar.

Gerçek örnek: 778x466 çözünürlük, ~200px genişlikte bulanık barkod
(9001021775), ayna modunda çekilmiş, sensör gürültülü.
"""

import cv2
import numpy as np

from forklift_barcode.app import prepare_frame
from forklift_barcode.processing.decoder import BarcodeDecoder
from forklift_barcode.processing.zoom import AutoZoom

from .barcode_gen import code128_image, place_on_canvas


def build_photo_like_frame(sigma: float = 0.9, mirrored: bool = True) -> np.ndarray:
    """Kullanıcı fotoğrafındaki koşulları taklit eden kare üretir."""
    barcode = code128_image("9001021775", module_width=2, height=40)
    fx = 200.0 / barcode.shape[1]  # ~200px genişliğe küçült
    small = cv2.resize(barcode, None, fx=fx, fy=fx * 2, interpolation=cv2.INTER_AREA)
    blurred = cv2.GaussianBlur(small, (5, 5), sigma)
    frame = place_on_canvas(blurred, canvas_size=(466, 778), position=(120, 280),
                            noise=False)
    rng = np.random.default_rng(3)
    noise = rng.normal(0, 4, frame.shape).astype(np.int16)
    frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return cv2.flip(frame, 1) if mirrored else frame


def make_autozoom():
    return AutoZoom(
        BarcodeDecoder(["CODE128"]),
        zoom_scales=[1.0, 1.5, 2.0, 3.0, 4.0, 0.5],
        full_search_every=1,
    )


def test_blurry_mirrored_photo_is_decoded():
    frame = build_photo_like_frame(sigma=0.9)
    fixed = prepare_frame(frame, flip="horizontal")
    result = make_autozoom().process(fixed)
    assert result is not None, "Bulanık fotoğraf koşulları okunamadı"
    assert result.decoded.data == "9001021775"


def test_blurry_photo_needs_enhancement():
    """Aynı kare, keskinleştirme kapalıyken okunamamalı; bu, güçlü
    keskinleştirmenin gerçekten gerekli olduğunu kanıtlar."""
    frame = build_photo_like_frame(sigma=0.9)
    az = AutoZoom(
        BarcodeDecoder(["CODE128"]),
        zoom_scales=[1.0, 1.5, 2.0, 3.0, 4.0, 0.5],
        enhance=False,
        full_search_every=1,
    )
    assert az.process(frame) is None
