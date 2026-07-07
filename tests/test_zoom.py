"""Otomatik zoom testleri: küçük/büyük barkodlar ve koordinat eşleme."""

import cv2
import numpy as np
import pytest

from forklift_barcode.processing.decoder import BarcodeDecoder
from forklift_barcode.processing.zoom import AutoZoom

from .barcode_gen import code128_image, place_on_canvas

SCALES = [1.0, 1.5, 2.0, 3.0, 4.0, 0.75, 0.5]


def make_autozoom(symbologies=None, **kw):
    return AutoZoom(BarcodeDecoder(symbologies), zoom_scales=SCALES, **kw)


def test_reads_normal_barcode_without_zoom():
    frame = place_on_canvas(code128_image("ZOOM-TEST-01"), position=(300, 400))
    result = make_autozoom().process(frame)
    assert result is not None
    assert result.decoded.data == "ZOOM-TEST-01"
    assert result.scale == 1.0
    assert result.roi is None


def test_reads_small_barcode_with_zoom_in():
    """Küçük/uzak barkod: tam karede okunamaz, yakınlaştırmayla okunur."""
    barcode = code128_image("KUCUK-BARKOD-42", module_width=3, height=60)
    # Barkodu küçültüp bulanıklaştırarak "uzaktaki" barkodu taklit et
    small = cv2.resize(barcode, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (3, 3), 1.0)
    frame = place_on_canvas(small, canvas_size=(1080, 1920), position=(500, 800))

    # Gürültülü/bozuk karede yanlış pozitifleri önlemek için sahadaki gibi
    # beklenen semboloji ile filtrelenir
    decoder = BarcodeDecoder(["CODE128"])
    assert decoder.decode(frame) == [], "Tam karede okunmamalıydı (test kurgusu)"

    result = make_autozoom(symbologies=["CODE128"]).process(frame)
    assert result is not None
    assert result.decoded.data == "KUCUK-BARKOD-42"
    assert result.scale > 1.0  # yakınlaştırma ile okundu


def test_result_rect_is_in_frame_coordinates():
    pos_y, pos_x = (350, 600)
    barcode = code128_image("KOORDINAT-1")
    frame = place_on_canvas(barcode, position=(pos_y, pos_x))
    result = make_autozoom().process(frame)
    assert result is not None
    x, y, w, h = result.decoded.rect
    bh, bw = barcode.shape[:2]
    # Kutu barkodun yerleştirildiği alanın içinde kalmalı
    assert pos_x <= x <= pos_x + bw
    assert pos_y - 10 <= y <= pos_y + bh
    assert w <= bw and h <= bh + 10


def test_tracking_reuses_last_hit():
    """İkinci karede tam arama yerine son bölge+ölçek kullanılmalı."""
    frame = place_on_canvas(code128_image("TAKIP-77"), position=(300, 400))
    az = make_autozoom()
    first = az.process(frame)
    assert first is not None
    assert az._last_hit is not None
    second = az.process(frame)
    assert second is not None
    assert second.decoded.data == "TAKIP-77"
    assert second.roi is not None  # takip modunda ROI üzerinden okundu


def test_returns_none_when_no_barcode():
    empty = np.full((720, 1280, 3), 128, dtype=np.uint8)
    assert make_autozoom().process(empty) is None
