"""USB kamera / capture kartı / RTSP / video dosyası kaynağı (OpenCV)."""

from __future__ import annotations

import logging
from typing import Optional, Union

import cv2
import numpy as np

from .base import VideoSource

log = logging.getLogger(__name__)


class CameraSource(VideoSource):
    """cv2.VideoCapture üzerinden kare okur.

    target: cihaz indeksi (int), RTSP adresi veya video dosyası yolu.
    """

    def __init__(self, target: Union[int, str], is_file: bool = False):
        self.target = target
        self.is_file = is_file
        self._cap: Optional[cv2.VideoCapture] = None

    def open(self) -> None:
        self._cap = cv2.VideoCapture(self.target)
        if not self._cap.isOpened():
            raise RuntimeError(f"Görüntü kaynağı açılamadı: {self.target!r}")
        log.info("Kaynak açıldı: %r", self.target)

    def read(self) -> Optional[np.ndarray]:
        if self._cap is None:
            raise RuntimeError("Kaynak açılmadan read() çağrıldı")
        ok, frame = self._cap.read()
        if not ok or frame is None:
            if self.is_file:
                return None  # dosya bitti
            log.warning("Kare okunamadı, kaynak yeniden deneniyor")
            return None
        return frame

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
