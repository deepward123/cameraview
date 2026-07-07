"""Kare hazırlama (ayna düzeltme + küçültme) ve arama seyreltme testleri."""

import cv2
import numpy as np
import pytest

from forklift_barcode.app import prepare_frame
from forklift_barcode.processing.decoder import BarcodeDecoder
from forklift_barcode.processing.zoom import AutoZoom

from .barcode_gen import code128_image, place_on_canvas


def _sample_frame():
    return place_on_canvas(code128_image("AYNA-TEST-1"), position=(300, 400))


def test_horizontal_flip_corrects_mirror():
    frame = _sample_frame()
    mirrored = cv2.flip(frame, 1)  # kameranın ayna modunu taklit et

    # Düzeltme aynalı görüntüyü orijinaline geri çevirmeli
    fixed = prepare_frame(mirrored, flip="horizontal")
    assert np.array_equal(fixed, frame)

    # Düzeltilmiş karede barkod okunur ve konumu orijinaldekiyle aynıdır
    decoder = BarcodeDecoder(["CODE128"])
    results = decoder.decode(fixed)
    assert results and results[0].data == "AYNA-TEST-1"
    assert results[0].rect == decoder.decode(frame)[0].rect


def test_flip_none_leaves_frame_unchanged():
    frame = _sample_frame()
    assert np.array_equal(prepare_frame(frame, flip="none"), frame)


def test_flip_both_equals_double_flip():
    frame = _sample_frame()
    expected = cv2.flip(frame, -1)
    assert np.array_equal(prepare_frame(frame, flip="both"), expected)


def test_max_width_downscales_keeping_aspect():
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    out = prepare_frame(frame, max_width=1280)
    assert out.shape[1] == 1280
    assert out.shape[0] == 720  # en-boy oranı korunur


def test_max_width_does_not_upscale():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    out = prepare_frame(frame, max_width=1280)
    assert out.shape[:2] == (480, 640)


def test_full_search_every_throttles_heavy_search():
    """Ağır arama ilk karede ve sonra her N karede bir çalışmalı."""
    # Yalnızca zoom ile okunabilen (tam karede okunamayan) bir kare hazırla
    barcode = code128_image("SEYRELT-01", module_width=3, height=60)
    small = cv2.resize(barcode, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (3, 3), 1.0)
    frame = place_on_canvas(small, canvas_size=(1080, 1920), position=(500, 800))
    empty = np.full((1080, 1920, 3), 128, dtype=np.uint8)

    az = AutoZoom(BarcodeDecoder(["CODE128"]), zoom_scales=[1.0, 1.5, 2.0],
                  full_search_every=3)

    # Kare 1: ağır arama açık ama boş kare -> sonuç yok
    assert az.process(empty) is None
    # Kare 2-3: ağır arama kapalı -> zor barkod bulunamaz
    assert az.process(frame) is None
    assert az.process(frame) is None
    # Kare 4: ağır arama tekrar açık -> barkod bulunur
    result = az.process(frame)
    assert result is not None and result.decoded.data == "SEYRELT-01"


def test_full_search_every_one_searches_every_frame():
    barcode = code128_image("HERKARE-01", module_width=3, height=60)
    small = cv2.resize(barcode, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (3, 3), 1.0)
    frame = place_on_canvas(small, canvas_size=(1080, 1920), position=(500, 800))

    az = AutoZoom(BarcodeDecoder(["CODE128"]), zoom_scales=[1.0, 1.5, 2.0],
                  full_search_every=1)
    empty = np.full((1080, 1920, 3), 128, dtype=np.uint8)
    az.process(empty)  # kare 1
    result = az.process(frame)  # kare 2: yine de ağır arama çalışır
    assert result is not None and result.decoded.data == "HERKARE-01"
