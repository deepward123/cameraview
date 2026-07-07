"""Ana uygulama: kare al -> otomatik zoom ile barkod oku -> numarayı ayıkla
-> bilgisayarda yaz (konsol + önizleme, istenirse CSV kaydı).

Görüntü akışı ile barkod işleme ayrı iş parçacıklarında çalışır: ağır
arama sürerken bile önizleme akıcı kalır (kesik kesik donma olmaz)."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
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

    result: Optional[ZoomResult] = None  # barkod bulunduysa
    value: Optional[str] = None  # ayıklanan numara (geçerliyse)
    sent: bool = False  # bu karede hedeflere gönderim yapıldı mı
    regions: list = field(default_factory=list)  # denenen aday bölgeler


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
            full_search_every=cfg.processing.full_search_every,
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


class FrameProcessor(threading.Thread):
    """Kareleri arka planda işleyen iş parçacığı.

    Ana döngü kareleri `submit` ile bırakır ve beklemeden devam eder;
    işleme yetişemezse aradaki kareler atlanır (her zaman en yeni kare
    işlenir). Son sonuç `latest` ile okunur. OpenCV/zbar çağrıları GIL'i
    bıraktığı için işleme gerçekten paralel yürür.
    """

    def __init__(self, pipeline: Pipeline):
        super().__init__(daemon=True, name="frame-processor")
        self.pipeline = pipeline
        self._cond = threading.Condition()
        self._pending: Optional[np.ndarray] = None
        self._latest = FrameOutcome()
        self._stopped = False

    def submit(self, frame: np.ndarray) -> None:
        with self._cond:
            self._pending = frame  # önceki bekleyen kare varsa üzerine yazılır
            self._cond.notify()

    @property
    def latest(self) -> FrameOutcome:
        with self._cond:
            return self._latest

    def run(self) -> None:
        while True:
            with self._cond:
                while self._pending is None and not self._stopped:
                    self._cond.wait()
                if self._stopped:
                    return
                frame, self._pending = self._pending, None
            try:
                outcome = self.pipeline.process_frame(frame)
            except Exception:
                log.exception("Kare işlenirken hata")
                continue
            with self._cond:
                self._latest = outcome

    def stop(self) -> None:
        with self._cond:
            self._stopped = True
            self._cond.notify()


_FLIP_CODES = {"horizontal": 1, "vertical": 0, "both": -1}


def prepare_frame(frame: np.ndarray, flip: str = "none", max_width: int = 0) -> np.ndarray:
    """Kareyi işlemeye hazırlar: ayna/ters görüntüyü düzeltir ve performans
    için yapılandırılan genişliğe küçültür."""
    code = _FLIP_CODES.get(flip)
    if code is not None:
        frame = cv2.flip(frame, code)
    h, w = frame.shape[:2]
    if max_width and w > max_width:
        new_h = int(h * max_width / w)
        frame = cv2.resize(frame, (max_width, new_h), interpolation=cv2.INTER_AREA)
    return frame


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
        text = f"BARKOD: {outcome.value}"
        color = (0, 255, 0) if outcome.sent else (0, 200, 255)
        cv2.rectangle(out, (0, 0), (out.shape[1], 44), (0, 0, 0), -1)
        cv2.putText(out, text, (10, 32), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
    return out


def run(cfg: AppConfig) -> None:
    """Canlı okuma döngüsü: kareyi alıp arka plandaki işlemciye bırakır,
    en son sonucu üzerine çizip gösterir. İşleme uzun sürse bile görüntü
    akışı takılmaz."""
    pipeline = Pipeline(cfg)
    processor = FrameProcessor(pipeline)
    processor.start()
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

                frame = prepare_frame(frame, cfg.source.flip, cfg.processing.max_width)
                processor.submit(frame)  # beklemeden devam et

                if preview:
                    try:
                        shown = annotate(frame, processor.latest, cfg.preview.draw_regions)
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
        processor.stop()
        processor.join(timeout=5.0)
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
    frame = prepare_frame(frame, cfg.source.flip, cfg.processing.max_width)
    pipeline = Pipeline(cfg)
    try:
        return pipeline.process_frame(frame)
    finally:
        pipeline.close()
