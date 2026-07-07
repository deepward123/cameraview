"""SAP'ye okuma gönderen çıkış hedefi (OData/REST).

Ayıklanan numarayı, yapılandırılan alan eşlemesiyle JSON olarak SAP
Gateway (OData) veya herhangi bir REST uç noktasına POST eder.

- Kimlik bilgileri ortam değişkenlerinden okunur (config'e yazılmaz).
- SAP OData için X-CSRF-Token akışı desteklenir (csrf: true).
- Gönderim başarısız olursa okuma `sap_failed.jsonl` dosyasına kuyruklanır;
  ağ geldiğinde `resend_failed()` ile yeniden gönderilebilir.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import requests

from ..config import SapConfig
from .base import OutputTarget, Reading

log = logging.getLogger(__name__)

_RETRIES = 3
_BACKOFF = 2.0  # saniye; her denemede iki katına çıkar
FAILED_QUEUE = Path("sap_failed.jsonl")


class SapOutput(OutputTarget):
    def __init__(self, cfg: SapConfig):
        self.cfg = cfg
        self._session: Optional[requests.Session] = None
        self._csrf_token: Optional[str] = None

    # -- oturum yönetimi ----------------------------------------------------

    def _get_session(self) -> requests.Session:
        if self._session is None:
            s = requests.Session()
            if self.cfg.auth == "basic":
                user = os.environ.get(self.cfg.user_env, "")
                password = os.environ.get(self.cfg.password_env, "")
                if not user or not password:
                    log.warning(
                        "SAP kimlik bilgileri eksik: %s / %s ortam değişkenlerini ayarlayın",
                        self.cfg.user_env, self.cfg.password_env,
                    )
                s.auth = (user, password)
            elif self.cfg.auth == "token":
                token = os.environ.get(self.cfg.token_env, "")
                if not token:
                    log.warning("SAP token eksik: %s ortam değişkenini ayarlayın",
                                self.cfg.token_env)
                s.headers["Authorization"] = f"Bearer {token}"
            s.headers["Accept"] = "application/json"
            self._session = s
        return self._session

    def _fetch_csrf(self, session: requests.Session) -> Optional[str]:
        """SAP OData yazma işlemleri için CSRF token alır."""
        try:
            resp = session.get(
                self.cfg.url,
                headers={"X-CSRF-Token": "Fetch"},
                timeout=self.cfg.timeout,
                verify=self.cfg.verify_tls,
            )
            return resp.headers.get("X-CSRF-Token")
        except requests.RequestException as exc:
            log.error("CSRF token alınamadı: %s", exc)
            return None

    # -- gönderim ------------------------------------------------------------

    def _build_payload(self, reading: Reading) -> dict:
        values = {
            "value": reading.value,
            "raw": reading.raw,
            "symbol": reading.symbol,
            "zoom": f"{reading.zoom:g}",
            "timestamp": reading.timestamp.isoformat(),
        }
        field_map = self.cfg.field_map or {"Barcode": "{value}"}
        return {key: tmpl.format(**values) for key, tmpl in field_map.items()}

    def send(self, reading: Reading) -> bool:
        payload = self._build_payload(reading)
        if self._post_with_retry(payload):
            return True
        self._queue_failed(payload)
        return False

    def _post_with_retry(self, payload: dict) -> bool:
        session = self._get_session()
        delay = _BACKOFF
        for attempt in range(1, _RETRIES + 1):
            try:
                headers = {"Content-Type": "application/json"}
                if self.cfg.csrf:
                    if self._csrf_token is None:
                        self._csrf_token = self._fetch_csrf(session)
                    if self._csrf_token:
                        headers["X-CSRF-Token"] = self._csrf_token
                resp = session.post(
                    self.cfg.url,
                    json=payload,
                    headers=headers,
                    timeout=self.cfg.timeout,
                    verify=self.cfg.verify_tls,
                )
                if resp.status_code in (200, 201, 204):
                    log.info("SAP'ye gönderildi: %s", payload)
                    return True
                if resp.status_code == 403 and self.cfg.csrf:
                    self._csrf_token = None  # token süresi dolmuş olabilir
                log.warning(
                    "SAP yanıtı %d (deneme %d/%d): %s",
                    resp.status_code, attempt, _RETRIES, resp.text[:300],
                )
            except requests.RequestException as exc:
                log.warning("SAP bağlantı hatası (deneme %d/%d): %s",
                            attempt, _RETRIES, exc)
            if attempt < _RETRIES:
                time.sleep(delay)
                delay *= 2
        return False

    # -- çevrimdışı kuyruk ----------------------------------------------------

    def _queue_failed(self, payload: dict) -> None:
        try:
            with FAILED_QUEUE.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            log.error("SAP'ye gönderilemedi; %s dosyasına kuyruklandı", FAILED_QUEUE)
        except OSError as exc:
            log.critical("Kuyruk dosyası da yazılamadı, kayıt DÜŞTÜ: %s", exc)

    def resend_failed(self) -> int:
        """Kuyruktaki kayıtları yeniden gönderir; başarılı sayısını döndürür."""
        if not FAILED_QUEUE.exists():
            return 0
        lines = FAILED_QUEUE.read_text(encoding="utf-8").splitlines()
        remaining, sent = [], 0
        for line in lines:
            if not line.strip():
                continue
            payload = json.loads(line)
            if self._post_with_retry(payload):
                sent += 1
            else:
                remaining.append(line)
        if remaining:
            FAILED_QUEUE.write_text("\n".join(remaining) + "\n", encoding="utf-8")
        else:
            FAILED_QUEUE.unlink()
        return sent

    def close(self) -> None:
        if self._session is not None:
            self._session.close()
            self._session = None
