"""Donanımsız demo: sentetik 'forklift kamerası' kareleri üretip hattı çalıştırır.

Kullanım (depo kökünden):
    python3 tools/demo.py

Farklı uzaklık/konumlarda barkodlu kareler üretir, her birini işler ve
işaretlenmiş sonuç görüntülerini demo_out/ klasörüne yazar.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forklift_barcode.app import Pipeline, annotate
from forklift_barcode.config import AppConfig, ExtractionConfig, OutputConfig, ProcessingConfig
from tests.barcode_gen import code128_image, place_on_canvas

OUT_DIR = Path(__file__).resolve().parent.parent / "demo_out"

# (isim, barkod, küçültme oranı, bulanıklık, konum)
SCENES = [
    ("yakin", "PLT0012345678TR", 1.0, 0.0, (280, 350)),
    ("orta", "PLT0098765432TR", 0.7, 0.6, (400, 700)),
    ("uzak", "PLT0055555555TR", 0.5, 1.0, (500, 900)),
]


def build_frame(code: str, shrink: float, blur: float, pos: tuple[int, int]):
    barcode = code128_image(code, module_width=3, height=70)
    if shrink != 1.0:
        barcode = cv2.resize(barcode, None, fx=shrink, fy=shrink,
                             interpolation=cv2.INTER_AREA)
    if blur > 0:
        barcode = cv2.GaussianBlur(barcode, (3, 3), blur)
    return place_on_canvas(barcode, canvas_size=(1080, 1920), position=pos, seed=7)


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    cfg = AppConfig(
        processing=ProcessingConfig(symbologies=["CODE128"]),
        extraction=ExtractionConfig(mode="full"),
        output=OutputConfig(targets=["console"], dedupe_seconds=0.0),
    )
    pipeline = Pipeline(cfg)

    ok = 0
    for name, code, shrink, blur, pos in SCENES:
        frame = build_frame(code, shrink, blur, pos)
        outcome = pipeline.process_frame(frame)
        shown = annotate(frame, outcome)
        out_path = OUT_DIR / f"{name}.png"
        cv2.imwrite(str(out_path), shown)
        if outcome.value is not None:
            ok += 1
            print(f"[{name}] OK  barkod={outcome.result.decoded.data} "
                  f"numara={outcome.value} zoom={outcome.result.scale:g}x -> {out_path}")
        else:
            print(f"[{name}] BAŞARISIZ -> {out_path}")

    pipeline.close()
    print(f"\n{ok}/{len(SCENES)} sahne başarıyla okundu. Görseller: {OUT_DIR}/")
    return 0 if ok == len(SCENES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
