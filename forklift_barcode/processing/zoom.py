"""Otomatik dijital zoom: barkod okunana kadar yakınlaştır/uzaklaştır.

Akış:
  1. Kare önce olduğu gibi denenir.
  2. Okunamazsa aday bölgeler bulunur; her bölge kesilip yapılandırılan
     ölçeklerde büyütülür/küçültülür (dijital zoom) ve tekrar denenir.
  3. Başarılı olan bölge+ölçek hatırlanır; sonraki karede önce o denenir
     (barkod sabitken her karede baştan arama yapılmaz).

Koordinatlar her zaman ORİJİNAL kare düzlemine geri çevrilir.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from .decoder import BarcodeDecoder, Decoded
from .locator import Rect, expand_rect, find_barcode_regions

log = logging.getLogger(__name__)


@dataclass
class ZoomResult:
    """Başarılı bir okuma ve hangi zoom ile bulunduğu."""

    decoded: Decoded  # rect orijinal kare koordinatlarındadır
    scale: float  # kullanılan dijital zoom ölçeği
    roi: Optional[Rect]  # zoom yapılan bölge (None = tüm kare)


class AutoZoom:
    def __init__(
        self,
        decoder: BarcodeDecoder,
        zoom_scales: list[float],
        roi_margin: float = 0.2,
        max_regions: int = 3,
        enhance: bool = True,
        full_search_every: int = 1,
    ):
        self.decoder = decoder
        self.zoom_scales = zoom_scales
        self.roi_margin = roi_margin
        self.max_regions = max_regions
        self.enhance = enhance
        # Ağır arama (bölge tespiti + tüm zoom denemeleri) her N karede bir
        # yapılır; aradaki kareler yalnızca hızlı denemelerle geçilir.
        # Böylece barkod görünmediği sürece işlemci boğulmaz (kasma/donma).
        self.full_search_every = max(1, full_search_every)
        self._frame_index = 0
        self._last_hit: Optional[tuple[Rect, float]] = None  # (roi, scale)
        self.last_regions: list[Rect] = []  # önizleme için son aday bölgeler

    def process(self, frame: np.ndarray) -> Optional[ZoomResult]:
        h, w = frame.shape[:2]
        self._frame_index += 1

        # 1) Son başarılı bölge+ölçek varsa önce onu dene (takip modu)
        if self._last_hit is not None:
            roi, scale = self._last_hit
            roi = expand_rect(roi, self.roi_margin, (w, h))
            result = self._try_roi(frame, roi, [scale])
            if result is not None:
                return result
            self._last_hit = None

        # 2) Tüm kareyi zoomsuz dene
        decoded = self.decoder.decode(frame)
        if decoded:
            best = decoded[0]
            self._last_hit = (best.rect, 1.0)
            return ZoomResult(decoded=best, scale=1.0, roi=None)

        # 3) Ağır arama: aday bölgeleri bul, her birini farklı zoom'larla
        #    dene. Yük dengelemek için her N karede bir çalışır (ilk kare dahil).
        if (self._frame_index - 1) % self.full_search_every != 0:
            return None
        self.last_regions = find_barcode_regions(frame, max_regions=self.max_regions)
        for region in self.last_regions:
            roi = expand_rect(region, self.roi_margin, (w, h))
            result = self._try_roi(frame, roi, self.zoom_scales)
            if result is not None:
                return result
        return None

    def _try_roi(
        self, frame: np.ndarray, roi: Rect, scales: list[float]
    ) -> Optional[ZoomResult]:
        x0, y0, rw, rh = roi
        crop = frame[y0 : y0 + rh, x0 : x0 + rw]
        if crop.size == 0:
            return None
        for scale in scales:
            zoomed = self._rescale(crop, scale)
            candidates = [zoomed]
            if self.enhance:
                # Hafif ve güçlü keskinleştirme: bulanık/odaksız kameralarda
                # (özellikle 3x-4x zoom sonrası) okumayı kurtarır
                candidates.append(self._enhance(zoomed))
                candidates.append(self._enhance_strong(zoomed))
            for img in candidates:
                decoded = self.decoder.decode(img)
                if not decoded:
                    continue
                best = decoded[0]
                # Koordinatları orijinal kareye geri çevir
                bx, by, bw_, bh_ = best.rect
                orig_rect = (
                    x0 + int(bx / scale),
                    y0 + int(by / scale),
                    max(1, int(bw_ / scale)),
                    max(1, int(bh_ / scale)),
                )
                best = Decoded(data=best.data, symbol=best.symbol, rect=orig_rect)
                self._last_hit = (orig_rect, scale)
                log.debug("Barkod %.2gx zoom ile okundu: %s", scale, best.data)
                return ZoomResult(decoded=best, scale=scale, roi=roi)
        return None

    @staticmethod
    def _rescale(img: np.ndarray, scale: float) -> np.ndarray:
        if scale == 1.0:
            return img
        interp = cv2.INTER_CUBIC if scale > 1.0 else cv2.INTER_AREA
        return cv2.resize(img, None, fx=scale, fy=scale, interpolation=interp)

    @staticmethod
    def _enhance(img: np.ndarray) -> np.ndarray:
        """Zoom sonrası bulanıklığa karşı keskinleştirme + kontrast açma."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        blur = cv2.GaussianBlur(gray, (0, 0), 3)
        return cv2.addWeighted(gray, 1.5, blur, -0.5, 0)

    @staticmethod
    def _enhance_strong(img: np.ndarray) -> np.ndarray:
        """Agresif keskinleştirme: ciddi bulanıklıkta çizgileri ayırır."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        blur = cv2.GaussianBlur(gray, (0, 0), 3)
        return cv2.addWeighted(gray, 4.0, blur, -3.0, 0)
