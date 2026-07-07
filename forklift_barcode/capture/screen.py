"""Ekran yakalama kaynağı: kameranın yansıdığı monitörü okur (mss)."""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from .base import VideoSource

log = logging.getLogger(__name__)


class ScreenSource(VideoSource):
    """Monitörün tamamını veya belirli bir bölgesini kare olarak yakalar.

    Forklift ekranında kamera görüntüsü bir pencerede/monitörde
    gösteriliyorsa, region ile yalnızca o bölge yakalanabilir.
    """

    def __init__(self, monitor: int = 1, region: Optional[dict] = None):
        self.monitor = monitor
        self.region = region
        self._sct = None

    def open(self) -> None:
        import mss  # yalnızca ekran kaynağı kullanılırsa gereklidir

        self._sct = mss.mss()
        monitors = self._sct.monitors
        if self.monitor >= len(monitors):
            raise RuntimeError(
                f"Monitör {self.monitor} bulunamadı (mevcut: {len(monitors) - 1})"
            )
        self._grab_area = dict(self.region) if self.region else monitors[self.monitor]
        log.info("Ekran yakalama başladı: %s", self._grab_area)

    def read(self) -> Optional[np.ndarray]:
        if self._sct is None:
            raise RuntimeError("Kaynak açılmadan read() çağrıldı")
        shot = self._sct.grab(self._grab_area)
        frame = np.asarray(shot)  # BGRA
        return frame[:, :, :3].copy()  # BGR

    def close(self) -> None:
        if self._sct is not None:
            self._sct.close()
            self._sct = None
