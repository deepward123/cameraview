"""Uçtan uca hat testi: sentetik kare -> okuma -> ayıklama -> hedef."""

import numpy as np
import pytest

from forklift_barcode.app import Pipeline, annotate
from forklift_barcode.config import AppConfig, ExtractionConfig, OutputConfig

from .barcode_gen import code128_image, place_on_canvas


class _Capture:
    """Test hedefi: gönderilen okumaları biriktirir."""

    def __init__(self):
        self.readings = []

    def send(self, reading):
        self.readings.append(reading)
        return True

    def close(self):
        pass


def make_pipeline(**extraction_kw) -> tuple[Pipeline, _Capture]:
    cfg = AppConfig(
        extraction=ExtractionConfig(**extraction_kw),
        output=OutputConfig(targets=[], dedupe_seconds=60.0),
    )
    pipe = Pipeline(cfg)
    cap = _Capture()
    pipe.outputs = [cap]
    return pipe, cap


def test_end_to_end_extracts_and_sends():
    frame = place_on_canvas(code128_image("PLT0001234599"), position=(280, 350))
    pipe, cap = make_pipeline(mode="slice", start=4, length=7)
    outcome = pipe.process_frame(frame)
    assert outcome.result is not None
    assert outcome.value == "0001234"
    assert outcome.sent
    assert len(cap.readings) == 1
    r = cap.readings[0]
    assert r.value == "0001234"
    assert r.raw == "PLT0001234599"
    assert r.symbol == "CODE128"


def test_dedupe_prevents_resend():
    frame = place_on_canvas(code128_image("TEKRAR-123456"), position=(280, 350))
    pipe, cap = make_pipeline(mode="slice", start=8, length=6)
    first = pipe.process_frame(frame)
    second = pipe.process_frame(frame)
    assert first.sent and not second.sent
    assert len(cap.readings) == 1


def test_invalid_extraction_not_sent():
    frame = place_on_canvas(code128_image("ABCDEF"), position=(280, 350))
    pipe, cap = make_pipeline(mode="regex", regex=r"(\d{10})", regex_group=1)
    outcome = pipe.process_frame(frame)
    assert outcome.result is not None  # barkod okundu
    assert outcome.value is None  # ama kural eşleşmedi
    assert not outcome.sent
    assert cap.readings == []


def test_annotate_returns_drawable_frame():
    frame = place_on_canvas(code128_image("GORSEL-1"), position=(280, 350))
    pipe, _ = make_pipeline(mode="slice", start=1, length=8)
    outcome = pipe.process_frame(frame)
    shown = annotate(frame, outcome)
    assert shown.shape == frame.shape
    assert not np.array_equal(shown, frame)  # üzerine çizim yapıldı
