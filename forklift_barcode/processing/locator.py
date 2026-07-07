"""Karede barkod olması muhtemel bölgeleri bulur (gradyan + morfoloji).

Barkodlar yatay yönde yoğun dikey çizgi geçişleri içerir; x-yönü gradyanının
y-yönüne baskın olduğu, morfolojik kapamayla birleşen bloklar aday bölgedir.
"""

from __future__ import annotations

import cv2
import numpy as np

Rect = tuple[int, int, int, int]  # x, y, w, h


def find_barcode_regions(
    frame: np.ndarray,
    max_regions: int = 3,
    min_area_ratio: float = 0.0005,
    max_area_ratio: float = 0.5,
) -> list[Rect]:
    """Barkod adayı dikdörtgenleri (büyükten küçüğe) döndürür."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    h, w = gray.shape[:2]
    frame_area = float(h * w)

    # Yüksek çözünürlükte hız için küçült, sonuçları geri ölçekle
    scale = 1.0
    if max(h, w) > 1000:
        scale = 1000.0 / max(h, w)
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=-1)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=-1)
    grad = cv2.convertScaleAbs(cv2.subtract(np.abs(grad_x), np.abs(grad_y)))

    blurred = cv2.blur(grad, (9, 9))
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 7))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    closed = cv2.erode(closed, None, iterations=3)
    closed = cv2.dilate(closed, None, iterations=6)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions: list[Rect] = []
    for c in sorted(contours, key=cv2.contourArea, reverse=True):
        x, y, cw, ch = cv2.boundingRect(c)
        if scale != 1.0:
            x, y = int(x / scale), int(y / scale)
            cw, ch = int(cw / scale), int(ch / scale)
        area = cw * ch
        if area < frame_area * min_area_ratio or area > frame_area * max_area_ratio:
            continue
        regions.append((x, y, cw, ch))
        if len(regions) >= max_regions:
            break
    return regions


def expand_rect(rect: Rect, margin: float, bounds: tuple[int, int]) -> Rect:
    """Dikdörtgeni orana göre büyütür ve kare sınırlarına kırpar."""
    x, y, w, h = rect
    bw, bh = bounds
    dx, dy = int(w * margin), int(h * margin)
    x0 = max(0, x - dx)
    y0 = max(0, y - dy)
    x1 = min(bw, x + w + dx)
    y1 = min(bh, y + h + dy)
    return x0, y0, max(1, x1 - x0), max(1, y1 - y0)
