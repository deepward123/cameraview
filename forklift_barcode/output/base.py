"""Çıkış hedefi arayüzü ve okuma kaydı."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class Reading:
    """Tek bir başarılı barkod okuması."""

    value: str  # ayıklanan numara (SAP'ye gidecek kısım)
    raw: str  # barkodun tam içeriği
    symbol: str  # barkod tipi (CODE128, EAN13 ...)
    zoom: float  # okumayı sağlayan dijital zoom ölçeği
    timestamp: datetime

    @classmethod
    def now(cls, value: str, raw: str, symbol: str, zoom: float) -> "Reading":
        return cls(value=value, raw=raw, symbol=symbol, zoom=zoom,
                   timestamp=datetime.now(timezone.utc))


class OutputTarget(ABC):
    @abstractmethod
    def send(self, reading: Reading) -> bool:
        """Okumayı hedefe iletir; başarı durumunu döndürür.

        Hedefler istisna fırlatmamalı; hata durumunda loglayıp False
        döndürmelidir ki okuma döngüsü kesintiye uğramasın.
        """

    def close(self) -> None:
        """Kaynakları serbest bırakır (varsayılan: bir şey yapma)."""
