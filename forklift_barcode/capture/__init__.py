"""Görüntü kaynakları: kamera, ekran yakalama, RTSP, video dosyası."""

from .base import VideoSource
from .camera import CameraSource
from .screen import ScreenSource


def create_source(cfg) -> VideoSource:
    """SourceConfig'e göre uygun görüntü kaynağını oluşturur."""
    if cfg.type == "camera":
        return CameraSource(cfg.camera_index)
    if cfg.type == "rtsp":
        return CameraSource(cfg.rtsp_url)
    if cfg.type == "file":
        return CameraSource(cfg.file_path, is_file=True)
    if cfg.type == "screen":
        return ScreenSource(monitor=cfg.screen.monitor, region=cfg.screen.region)
    raise ValueError(f"Bilinmeyen kaynak tipi: {cfg.type}")


__all__ = ["VideoSource", "CameraSource", "ScreenSource", "create_source"]
