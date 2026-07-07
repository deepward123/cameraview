"""Komut satırı girişi: python -m forklift_barcode [--config config.yaml]"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .app import process_image, run
from .config import AppConfig, load_config


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="forklift_barcode",
        description="Forklift kamera görüntüsünden barkod okuyup numarayı SAP'ye gönderir.",
    )
    parser.add_argument("--config", "-c", default="config.yaml",
                        help="YAML yapılandırma dosyası (varsayılan: config.yaml)")
    parser.add_argument("--source", choices=["camera", "screen", "rtsp", "file"],
                        help="Yapılandırmadaki kaynak tipini geçersiz kıl")
    parser.add_argument("--image", help="Canlı döngü yerine tek bir görüntü dosyasını işle")
    parser.add_argument("--no-preview", action="store_true", help="Önizleme penceresini kapat")
    parser.add_argument("--verbose", "-v", action="store_true", help="Ayrıntılı log")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if Path(args.config).exists():
        cfg = load_config(args.config)
    else:
        if args.config != "config.yaml":
            print(f"Yapılandırma dosyası bulunamadı: {args.config}", file=sys.stderr)
            return 2
        cfg = AppConfig()  # varsayılanlarla çalış

    if args.source:
        cfg.source.type = args.source
    if args.no_preview:
        cfg.preview.enabled = False

    if args.image:
        outcome = process_image(cfg, args.image)
        if outcome.result is None:
            print("Barkod bulunamadı")
            return 1
        print(f"Barkod : {outcome.result.decoded.data} ({outcome.result.decoded.symbol})")
        print(f"Zoom   : {outcome.result.scale:g}x")
        print(f"Numara : {outcome.value if outcome.value is not None else '(kural eşleşmedi)'}")
        return 0

    run(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
