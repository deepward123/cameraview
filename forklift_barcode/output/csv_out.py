"""Okumaları yerel CSV dosyasına ekleyen çıkış hedefi."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from .base import OutputTarget, Reading

log = logging.getLogger(__name__)

_HEADER = ["timestamp", "value", "raw", "symbol", "zoom"]


class CsvOutput(OutputTarget):
    def __init__(self, path: str):
        self.path = Path(path)

    def send(self, reading: Reading) -> bool:
        try:
            new_file = not self.path.exists()
            with self.path.open("a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if new_file:
                    writer.writerow(_HEADER)
                writer.writerow([
                    reading.timestamp.isoformat(),
                    reading.value,
                    reading.raw,
                    reading.symbol,
                    reading.zoom,
                ])
            return True
        except OSError as exc:
            log.error("CSV yazılamadı (%s): %s", self.path, exc)
            return False
