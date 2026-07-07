"""Testler için Code128-B barkod görüntüsü üretir (harici bağımlılık yok).

Üretilen görüntülerin doğruluğu, testlerdeki çözümleme (pyzbar/OpenCV)
round-trip'iyle kanıtlanır.
"""

from __future__ import annotations

import numpy as np

# Code128 modül desenleri (değer 0-106): bar/boşluk genişlikleri
_PATTERNS = [
    "212222", "222122", "222221", "121223", "121322", "131222", "122213",
    "122312", "132212", "221213", "221312", "231212", "112232", "122132",
    "122231", "113222", "123122", "123221", "223211", "221132", "221231",
    "213212", "223112", "312131", "311222", "321122", "321221", "312212",
    "322112", "322211", "212123", "212321", "232121", "111323", "131123",
    "131321", "112313", "132113", "132311", "211313", "231113", "231311",
    "112133", "112331", "132131", "113123", "113321", "133121", "313121",
    "211331", "231131", "213113", "213311", "213131", "311123", "311321",
    "331121", "312113", "312311", "332111", "314111", "221411", "431111",
    "111224", "111422", "121124", "121421", "141122", "141221", "112214",
    "112412", "122114", "122411", "142112", "142211", "241211", "221114",
    "413111", "241112", "134111", "111242", "121142", "121241", "114212",
    "124112", "124211", "411212", "421112", "421211", "212141", "214121",
    "412121", "111143", "111341", "131141", "114113", "114311", "411113",
    "411311", "113141", "114131", "311141", "411131", "211412", "211214",
    "211232",
]
_STOP = "2331112"
_START_B = 104


def _encode_values(text: str) -> list[int]:
    """Metni Code128-B değer dizisine (start + veri + checksum) çevirir."""
    values = [_START_B]
    for ch in text:
        code = ord(ch)
        if not 32 <= code <= 126:
            raise ValueError(f"Code128-B dışı karakter: {ch!r}")
        values.append(code - 32)
    checksum = values[0]
    for pos, val in enumerate(values[1:], start=1):
        checksum += pos * val
    values.append(checksum % 103)
    return values


def code128_image(
    text: str,
    module_width: int = 3,
    height: int = 80,
    quiet: int = 10,
) -> np.ndarray:
    """Verilen metin için gri tonlamalı Code128-B görüntüsü (uint8) üretir."""
    widths: list[int] = []
    for value in _encode_values(text):
        widths.extend(int(d) for d in _PATTERNS[value])
    widths.extend(int(d) for d in _STOP)

    total = (sum(widths) + 2 * quiet) * module_width
    img = np.full((height, total), 255, dtype=np.uint8)
    x = quiet * module_width
    dark = True
    for w in widths:
        px = w * module_width
        if dark:
            img[:, x : x + px] = 0
        x += px
        dark = not dark
    return img


def place_on_canvas(
    barcode: np.ndarray,
    canvas_size: tuple[int, int] = (720, 1280),
    position: tuple[int, int] = (300, 400),
    noise: bool = True,
    seed: int = 42,
) -> np.ndarray:
    """Barkodu daha büyük bir 'kamera karesi' üzerine yerleştirir (BGR)."""
    ch, cw = canvas_size
    rng = np.random.default_rng(seed)
    if noise:
        canvas = rng.integers(90, 150, size=(ch, cw), dtype=np.uint8)
    else:
        canvas = np.full((ch, cw), 120, dtype=np.uint8)
    y, x = position
    bh, bw = barcode.shape[:2]
    if y + bh > ch or x + bw > cw:
        raise ValueError("Barkod tuvale sığmıyor")
    canvas[y : y + bh, x : x + bw] = barcode
    return np.stack([canvas] * 3, axis=-1)
