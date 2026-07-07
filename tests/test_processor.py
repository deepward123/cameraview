"""Arka plan işlemcisi (FrameProcessor) testleri."""

import time

import numpy as np

from forklift_barcode.app import FrameProcessor, Pipeline
from forklift_barcode.config import AppConfig, ExtractionConfig, OutputConfig

from .barcode_gen import code128_image, place_on_canvas


def wait_until(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def make_processor():
    cfg = AppConfig(
        extraction=ExtractionConfig(mode="full"),
        output=OutputConfig(targets=[], dedupe_seconds=0.0),
    )
    return FrameProcessor(Pipeline(cfg))


def test_processor_produces_outcome_in_background():
    proc = make_processor()
    proc.start()
    try:
        frame = place_on_canvas(code128_image("ISLEMCI-1"), position=(300, 400))
        proc.submit(frame)
        assert wait_until(lambda: proc.latest.value == "ISLEMCI-1"), \
            "İşlemci sonucu zamanında üretmedi"
    finally:
        proc.stop()
        proc.join(timeout=5.0)
        assert not proc.is_alive()


def test_processor_skips_stale_frames():
    """İşleme yetişemezse hep en yeni kare işlenmeli (kuyruk birikmemeli)."""
    proc = make_processor()
    frames = [
        place_on_canvas(code128_image(f"KARE-{i}"), position=(300, 400), seed=i)
        for i in range(5)
    ]
    # İşlemci başlamadan hepsini bırak: yalnızca sonuncusu bekliyor olmalı
    for f in frames:
        proc.submit(f)
    proc.start()
    try:
        assert wait_until(lambda: proc.latest.value is not None)
        assert proc.latest.value == "KARE-4"
    finally:
        proc.stop()
        proc.join(timeout=5.0)


def test_processor_survives_bad_frame():
    proc = make_processor()
    proc.start()
    try:
        proc.submit(np.zeros((2, 2), dtype=np.uint8))  # bozuk/küçücük kare
        frame = place_on_canvas(code128_image("SAGLAM-1"), position=(300, 400))
        proc.submit(frame)
        assert wait_until(lambda: proc.latest.value == "SAGLAM-1")
    finally:
        proc.stop()
        proc.join(timeout=5.0)
