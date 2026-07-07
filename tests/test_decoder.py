"""Barkod çözümleme round-trip testleri."""

import pytest

from forklift_barcode.processing.decoder import BarcodeDecoder

from .barcode_gen import code128_image, place_on_canvas


@pytest.fixture()
def decoder():
    return BarcodeDecoder()


def test_decodes_plain_code128(decoder):
    img = code128_image("PALET-1234567890")
    results = decoder.decode(img)
    assert len(results) == 1
    assert results[0].data == "PALET-1234567890"
    assert results[0].symbol == "CODE128"


def test_decodes_barcode_inside_frame(decoder):
    barcode = code128_image("00340012345678901234")
    frame = place_on_canvas(barcode, position=(200, 300))
    results = decoder.decode(frame)
    assert results, "Kare içindeki barkod çözülemedi"
    assert results[0].data == "00340012345678901234"


def test_rect_matches_barcode_position(decoder):
    barcode = code128_image("ABC123")
    frame = place_on_canvas(barcode, position=(150, 500))
    results = decoder.decode(frame)
    assert results
    x, y, w, h = results[0].rect
    # Kutu, yerleştirilen konumla örtüşmeli (quiet zone payıyla)
    assert abs(y - 150) < 30
    assert 400 < x < 700


def test_symbology_filter(decoder_cls=BarcodeDecoder):
    only_ean = decoder_cls(["EAN13"])
    img = code128_image("FILTRE-TEST")
    assert only_ean.decode(img) == []

    only_code128 = decoder_cls(["CODE128"])
    results = only_code128.decode(img)
    assert results and results[0].data == "FILTRE-TEST"


def test_no_barcode_returns_empty(decoder):
    frame = place_on_canvas(code128_image("X"), noise=True)[..., :]
    empty = frame.copy()
    empty[:] = 128
    assert decoder.decode(empty) == []
