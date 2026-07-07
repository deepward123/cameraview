"""Konsola yazan basit çıkış hedefi."""

from __future__ import annotations

import logging

from .base import OutputTarget, Reading

log = logging.getLogger(__name__)


class ConsoleOutput(OutputTarget):
    def send(self, reading: Reading) -> bool:
        detail = f"tip: {reading.symbol}, zoom: {reading.zoom:g}x"
        if reading.value != reading.raw:
            detail = f"barkodun tamamı: {reading.raw}, {detail}"
        print(
            f"[{reading.timestamp.astimezone().strftime('%H:%M:%S')}] "
            f"BARKOD: {reading.value}  ({detail})"
        )
        return True
