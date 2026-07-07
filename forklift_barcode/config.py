"""YAML yapılandırmasını yükleyip doğrulayan veri sınıfları."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class ScreenConfig:
    monitor: int = 1
    region: Optional[dict] = None  # {left, top, width, height}


@dataclass
class SourceConfig:
    type: str = "camera"  # camera | screen | rtsp | file
    camera_index: int = 0
    rtsp_url: str = ""
    file_path: str = ""
    screen: ScreenConfig = field(default_factory=ScreenConfig)
    fps_limit: float = 15.0


@dataclass
class ProcessingConfig:
    zoom_scales: list[float] = field(
        default_factory=lambda: [1.0, 1.5, 2.0, 3.0, 4.0, 0.75, 0.5]
    )
    roi_margin: float = 0.20
    max_regions: int = 3
    enhance: bool = True
    symbologies: list[str] = field(default_factory=list)


@dataclass
class ExtractionConfig:
    mode: str = "full"  # full (barkodun tamamı) | slice | regex
    start: int = 1  # 1 tabanlı
    length: int = 10
    regex: str = ""
    regex_group: int = 1
    digits_only: bool = False
    min_length: int = 1


@dataclass
class CsvConfig:
    path: str = "readings.csv"


@dataclass
class OutputConfig:
    targets: list[str] = field(default_factory=lambda: ["console"])
    dedupe_seconds: float = 5.0
    csv: CsvConfig = field(default_factory=CsvConfig)


@dataclass
class PreviewConfig:
    enabled: bool = True
    window_name: str = "Forklift Barkod"
    draw_regions: bool = True


@dataclass
class AppConfig:
    source: SourceConfig = field(default_factory=SourceConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    preview: PreviewConfig = field(default_factory=PreviewConfig)


def _merge(dc_cls, data: Any):
    """dict verisini dataclass'a, bilinmeyen anahtarları yok sayarak aktarır."""
    if data is None:
        return dc_cls()
    if not isinstance(data, dict):
        raise ValueError(f"{dc_cls.__name__} için sözlük bekleniyordu: {data!r}")
    kwargs = {}
    for f in dc_cls.__dataclass_fields__.values():
        if f.name not in data:
            continue
        value = data[f.name]
        nested = {
            "screen": ScreenConfig,
            "csv": CsvConfig,
        }.get(f.name)
        kwargs[f.name] = _merge(nested, value) if nested else value
    return dc_cls(**kwargs)


def load_config(path: str | Path) -> AppConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    cfg = AppConfig(
        source=_merge(SourceConfig, raw.get("source")),
        processing=_merge(ProcessingConfig, raw.get("processing")),
        extraction=_merge(ExtractionConfig, raw.get("extraction")),
        output=_merge(OutputConfig, raw.get("output")),
        preview=_merge(PreviewConfig, raw.get("preview")),
    )
    _validate(cfg)
    return cfg


def _validate(cfg: AppConfig) -> None:
    if cfg.source.type not in ("camera", "screen", "rtsp", "file"):
        raise ValueError(f"Geçersiz kaynak tipi: {cfg.source.type}")
    if cfg.extraction.mode not in ("full", "slice", "regex"):
        raise ValueError(f"Geçersiz ayıklama modu: {cfg.extraction.mode}")
    if cfg.extraction.mode == "slice" and cfg.extraction.start < 1:
        raise ValueError("extraction.start 1 veya daha büyük olmalı (1 tabanlı)")
    if cfg.extraction.mode == "regex" and not cfg.extraction.regex:
        raise ValueError("extraction.mode=regex için 'regex' alanı gerekli")
    for target in cfg.output.targets:
        if target not in ("console", "csv"):
            raise ValueError(f"Geçersiz çıkış hedefi: {target}")
    if not cfg.processing.zoom_scales:
        raise ValueError("processing.zoom_scales boş olamaz")
