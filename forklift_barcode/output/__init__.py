"""Okuma sonuçlarının gönderildiği hedefler: konsol, CSV, SAP."""

from .base import OutputTarget, Reading
from .console import ConsoleOutput
from .csv_out import CsvOutput
from .sap import SapOutput


def create_outputs(cfg) -> list[OutputTarget]:
    """OutputConfig'e göre hedef listesi oluşturur."""
    outputs: list[OutputTarget] = []
    for name in cfg.targets:
        if name == "console":
            outputs.append(ConsoleOutput())
        elif name == "csv":
            outputs.append(CsvOutput(cfg.csv.path))
        elif name == "sap":
            outputs.append(SapOutput(cfg.sap))
        else:
            raise ValueError(f"Bilinmeyen çıkış hedefi: {name}")
    return outputs


__all__ = ["OutputTarget", "Reading", "ConsoleOutput", "CsvOutput", "SapOutput", "create_outputs"]
