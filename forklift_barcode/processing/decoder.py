"""Barkod çözümleme: pyzbar (birincil) + OpenCV (yedek) tek arayüzde."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

log = logging.getLogger(__name__)

try:
    from pyzbar import pyzbar as _zbar
    from pyzbar.pyzbar import ZBarSymbol as _ZBarSymbol

    _HAS_ZBAR = True
except Exception:  # libzbar kurulu değilse OpenCV ile devam edilir
    _zbar = None
    _ZBarSymbol = None
    _HAS_ZBAR = False
    log.warning("pyzbar kullanılamıyor (libzbar eksik olabilir); OpenCV kullanılacak")


@dataclass
class Decoded:
    """Çözülen tek bir barkod."""

    data: str
    symbol: str  # CODE128, EAN13, QRCODE ...
    rect: tuple[int, int, int, int]  # verilen görüntüde (x, y, w, h)


class BarcodeDecoder:
    """Verilen görüntüdeki barkodları çözer.

    symbologies: yalnızca bu tiplere bak (boş liste = tümü). İsimler
    pyzbar ZBarSymbol isimleriyle uyumludur (CODE128, EAN13, QRCODE...).
    """

    def __init__(self, symbologies: Optional[list[str]] = None):
        self.symbologies = [s.upper() for s in (symbologies or [])]
        self._zbar_symbols = None
        if _HAS_ZBAR and self.symbologies:
            self._zbar_symbols = [
                getattr(_ZBarSymbol, name)
                for name in self.symbologies
                if hasattr(_ZBarSymbol, name)
            ]
        self._cv_bar = None
        self._cv_qr = None

    def decode(self, image: np.ndarray) -> list[Decoded]:
        gray = self._to_gray(image)
        results = self._decode_zbar(gray) if _HAS_ZBAR else []
        if not results:
            results = self._decode_opencv(gray)
        return results

    @staticmethod
    def _to_gray(image: np.ndarray) -> np.ndarray:
        if image.ndim == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image

    def _decode_zbar(self, gray: np.ndarray) -> list[Decoded]:
        kwargs = {"symbols": self._zbar_symbols} if self._zbar_symbols else {}
        results = []
        for sym in _zbar.decode(gray, **kwargs):
            try:
                data = sym.data.decode("utf-8")
            except UnicodeDecodeError:
                data = sym.data.decode("latin-1")
            r = sym.rect
            results.append(
                Decoded(data=data, symbol=sym.type, rect=(r.left, r.top, r.width, r.height))
            )
        return results

    def _decode_opencv(self, gray: np.ndarray) -> list[Decoded]:
        results: list[Decoded] = []
        results.extend(self._decode_cv_1d(gray))
        results.extend(self._decode_cv_qr(gray))
        if self.symbologies:
            results = [r for r in results if r.symbol in self.symbologies]
        return results

    def _decode_cv_1d(self, gray: np.ndarray) -> list[Decoded]:
        try:
            if self._cv_bar is None:
                self._cv_bar = cv2.barcode.BarcodeDetector()
            ok, infos, types, points = self._cv_bar.detectAndDecodeWithType(gray)
        except Exception:
            return []
        if not ok or points is None:
            return []
        out = []
        for info, typ, quad in zip(infos, types, points):
            if not info:
                continue
            out.append(Decoded(data=info, symbol=str(typ).upper().replace("_", ""),
                               rect=_quad_to_rect(quad)))
        return out

    def _decode_cv_qr(self, gray: np.ndarray) -> list[Decoded]:
        try:
            if self._cv_qr is None:
                self._cv_qr = cv2.QRCodeDetector()
            ok, infos, points, _ = self._cv_qr.detectAndDecodeMulti(gray)
        except Exception:
            return []
        if not ok or points is None:
            return []
        return [
            Decoded(data=info, symbol="QRCODE", rect=_quad_to_rect(quad))
            for info, quad in zip(infos, points)
            if info
        ]


def _quad_to_rect(quad: np.ndarray) -> tuple[int, int, int, int]:
    """4 köşe noktasını (x, y, w, h) kutusuna çevirir."""
    pts = np.asarray(quad).reshape(-1, 2)
    x0, y0 = pts.min(axis=0)
    x1, y1 = pts.max(axis=0)
    return int(x0), int(y0), int(x1 - x0), int(y1 - y0)
