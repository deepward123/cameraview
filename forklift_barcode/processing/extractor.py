"""Barkod içeriğinden istenen kısmı (numarayı) ayıklar."""

from __future__ import annotations

import logging
import re
from typing import Optional

from ..config import ExtractionConfig

log = logging.getLogger(__name__)


class Extractor:
    """Barkod içeriğinden, yapılandırılan kurala göre yazılacak numarayı çıkarır.

    - full : barkodun tamamı olduğu gibi kullanılır (varsayılan)
    - slice: 1 tabanlı start + length ile karakter aralığı
    - regex: düzenli ifadenin verilen yakalama grubu
    - digits_only: kural uygulanmadan önce rakam dışı karakterleri at
    """

    def __init__(self, cfg: ExtractionConfig):
        self.cfg = cfg
        self._pattern = re.compile(cfg.regex) if cfg.mode == "regex" else None

    def extract(self, raw: str) -> Optional[str]:
        text = raw
        if self.cfg.digits_only:
            text = "".join(ch for ch in text if ch.isdigit())

        if self.cfg.mode == "full":
            value = text
        elif self.cfg.mode == "slice":
            start = self.cfg.start - 1
            value = text[start : start + self.cfg.length]
        else:
            match = self._pattern.search(text)
            if match is None:
                log.debug("Regex eşleşmedi: %r", raw)
                return None
            try:
                value = match.group(self.cfg.regex_group)
            except IndexError:
                log.error("Regex grubu %d yok: %s", self.cfg.regex_group, self.cfg.regex)
                return None

        if value is None or len(value) < self.cfg.min_length:
            log.debug("Ayıklanan değer çok kısa: %r (barkod: %r)", value, raw)
            return None
        return value
