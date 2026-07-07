"""Konsola yazan basit çıkış hedefi."""

from __future__ import annotations

import logging

from .base import OutputTarget, Reading

log = logging.getLogger(__name__)


class ConsoleOutput(OutputTarget):
    def send(self, reading: Reading) -> bool:
        print(
            f"[{reading.timestamp.astimezone().strftime('%H:%M:%S')}] "
            f"NUMARA: {reading.value}  "
            f"(barkod: {reading.raw}, tip: {reading.symbol}, zoom: {reading.zoom:g}x)"
        )
        return True
