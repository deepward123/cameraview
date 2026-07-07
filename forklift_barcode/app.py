"""Ana uygulama: kare al -> otomatik zoom ile barkod oku -> numarayı ayıkla
-> hedeflere (konsol/CSV/SAP) gönder -> önizlemede göster."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from .capture import create_source
from .config import AppConfig
from .output import Reading, create_outputs
from .processing import AutoZoom, BarcodeDecoder, Extractor, ZoomResult

log = logging.getLogger(__name__)


@dataclass
class FrameOutcome:
    """Tek karenin işlenme sonucu (önizleme ve test için)."""

    result: Optional[ZoomResult]  # barkod bulunduysa
    value: Optional[str]  # ayıklanan numara (geçerliyse)
    sent: bool  # bu karede hedeflere gönderim yapıldı mı
    regions: list  # denenen aday bölgeler


class Pipeline:
    """Görüntü işleme hattı; kaynak ve pencere yönetiminden bağımsızdır."""

    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        decoder = BarcodeDecoder(cfg.processing.symbologies)
        self.autozoom = AutoZoom(
            decoder,
            zoom_scales=cfg.processing.zoom_scales,
            roi_margin=cfg.processing.roi_margin,
            max_regions=cfg.processing.max_regions,
            enhance=cfg.processing.enhance,
        )
        self.extractor = Extractor(cfg.extraction)
        self.outputs = create_outputs(cfg.output)
        self._last_sent: dict[str, float] = {}  # değer -> son gönderim zamanı

    def process_frame(self, frame: np.ndarray) -> FrameOutcome:
        result = self.autozoom.process(frame)
        if result is None:
            return FrameOutcome(None, None, False, self.autozoom.last_regions)

        value = self.extractor.extract(result.decoded.data)
        if value is None:
            return FrameOutcome(result, None, False, self.autozoom.last_regions)

        sent = False
        if self._should_send(value):
            reading = Reading.now(
                value=value,
                raw=result.decoded.data,
                symbol=result.decoded.symbol,
                zoom=result.scale,
            )
            for target in self.outputs:
                target.send(reading)
            sent = True
        return FrameOutcome(result, value, sent, self.autozoom.last_regions)

    def _should_send(self, value: str) -> bool:
        now = time.monotonic()
        last = self._last_sent.get(value)
        if last is not None and now - last < self.cfg.output.dedupe_seconds:
            return False
        self._last_sent[value] = now
        return True

    def close(self) -> None:
        for target in self.outputs:
            target.close()


def annotate(frame: np.ndarray, outcome: FrameOutcome, draw_regions: bool = True) -> np.ndarray:
    """Önizleme karesine barkod kutusu, zoom bilgisi ve numarayı çizer."""
    out = frame.copy()
    if draw_regions:
        for x, y, w, h in outcome.regions:
            cv2.rectangle(out, (x, y), (x + w, y + h), (80, 80, 255), 1)
    if outcome.result is not None:
        x, y, w, h = outcome.result.decoded.rect
        cv2.rectangle(out, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(out, f"zoom {outcome.result.scale:g}x", (x, max(20, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    if outcome.value is not None:
        text = f"NUMARA: {outcome.value}"
        color = (0, 255, 0) if outcome.sent else (0, 200, 255)
        cv2.rectangle(out, (0, 0), (out.shape[1], 44), (0, 0, 0), -1)
        cv2.putText(out, text, (10, 32), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
    return out


def run(cfg: AppConfig) -> None:
    """Canlı okuma döngüsü: kaynaktan kare alır, işler, önizler."""
    pipeline = Pipeline(cfg)
    preview = cfg.preview.enabled
    frame_interval = 1.0 / cfg.source.fps_limit if cfg.source.fps_limit > 0 else 0.0

    try:
        with create_source(cfg.source) as source:
            log.info("Okuma döngüsü başladı (çıkmak için q / ESC)")
            while True:
                started = time.monotonic()
                frame = source.read()
                if frame is None:
                    if cfg.source.type == "file":
                        log.info("Video dosyası bitti")
                        break
                    time.sleep(0.5)  # kaynak koptu; kısa bekleyip yeniden dene
                    continue

                outcome = pipeline.process_frame(frame)

                if preview:
                    try:
                        shown = annotate(frame, outcome, cfg.preview.draw_regions)
                        cv2.imshow(cfg.preview.window_name, shown)
                        key = cv2.waitKey(1) & 0xFF
                        if key in (ord("q"), 27):
                            break
                    except cv2.error:
                        log.warning(
                            "Önizleme açılamadı (başsız OpenCV kurulu olabilir); "
                            "önizlemesiz devam ediliyor"
                        )
                        preview = False

                # FPS sınırı
                elapsed = time.monotonic() - started
                if frame_interval > elapsed:
                    time.sleep(frame_interval - elapsed)
    finally:
        pipeline.close()
        if preview:
            try:
                cv2.destroyAllWindows()
            except cv2.error:
                pass


def process_image(cfg: AppConfig, image_path: str) -> FrameOutcome:
    """Tek bir görüntü dosyasını işler (test/deneme için)."""
    frame = cv2.imread(image_path)
    if frame is None:
        raise FileNotFoundError(f"Görüntü okunamadı: {image_path}")
    pipeline = Pipeline(cfg)
    try:
        return pipeline.process_frame(frame)
    finally:
        pipeline.close()
