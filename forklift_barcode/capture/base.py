"""Görüntü kaynağı arayüzü."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import numpy as np


class VideoSource(ABC):
    """Tüm görüntü kaynaklarının ortak arayüzü (BGR kare üretir)."""

    @abstractmethod
    def open(self) -> None:
        """Kaynağı açar; başarısızsa RuntimeError fırlatır."""

    @abstractmethod
    def read(self) -> Optional[np.ndarray]:
        """Bir sonraki kareyi döndürür; akış bittiyse/koptuysa None."""

    @abstractmethod
    def close(self) -> None:
        """Kaynağı serbest bırakır."""

    def __enter__(self) -> "VideoSource":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()
