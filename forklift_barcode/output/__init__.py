"""Okuma sonuçlarının gösterildiği hedefler: konsol ve isteğe bağlı CSV kaydı."""

from .base import OutputTarget, Reading
from .console import ConsoleOutput
from .csv_out import CsvOutput


def create_outputs(cfg) -> list[OutputTarget]:
    """OutputConfig'e göre hedef listesi oluşturur."""
    outputs: list[OutputTarget] = []
    for name in cfg.targets:
        if name == "console":
            outputs.append(ConsoleOutput())
        elif name == "csv":
            outputs.append(CsvOutput(cfg.csv.path))
        else:
            raise ValueError(f"Bilinmeyen çıkış hedefi: {name}")
    return outputs


__all__ = ["OutputTarget", "Reading", "ConsoleOutput", "CsvOutput", "create_outputs"]
