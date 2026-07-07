"""SAP çıkış hedefi testleri (ağ yok; requests monkeypatch edilir)."""

import json

import pytest

import forklift_barcode.output.sap as sap_mod
from forklift_barcode.config import SapConfig
from forklift_barcode.output.base import Reading
from forklift_barcode.output.sap import SapOutput


class _FakeResponse:
    def __init__(self, status_code=201, headers=None, text=""):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text


class _FakeSession:
    def __init__(self, post_status=201):
        self.post_status = post_status
        self.posts = []
        self.gets = []
        self.headers = {}
        self.auth = None

    def get(self, url, **kw):
        self.gets.append((url, kw))
        return _FakeResponse(200, headers={"X-CSRF-Token": "test-token"})

    def post(self, url, **kw):
        self.posts.append((url, kw))
        return _FakeResponse(self.post_status)

    def close(self):
        pass


@pytest.fixture()
def reading():
    return Reading.now(value="0012345", raw="PLT0012345XX", symbol="CODE128", zoom=2.0)


def make_output(session, **cfg_kw):
    cfg = SapConfig(
        url="https://sap.test/odata/Readings",
        field_map={"Barcode": "{value}", "Raw": "{raw}", "At": "{timestamp}"},
        **cfg_kw,
    )
    out = SapOutput(cfg)
    out._session = session
    return out


def test_send_posts_mapped_payload(reading):
    session = _FakeSession()
    out = make_output(session, csrf=False)
    assert out.send(reading) is True
    assert len(session.posts) == 1
    _, kwargs = session.posts[0]
    assert kwargs["json"]["Barcode"] == "0012345"
    assert kwargs["json"]["Raw"] == "PLT0012345XX"


def test_csrf_token_fetched_and_sent(reading):
    session = _FakeSession()
    out = make_output(session, csrf=True)
    assert out.send(reading) is True
    assert len(session.gets) == 1  # token Fetch çağrısı
    _, kwargs = session.posts[0]
    assert kwargs["headers"]["X-CSRF-Token"] == "test-token"


def test_failure_queues_to_file(reading, tmp_path, monkeypatch):
    monkeypatch.setattr(sap_mod, "FAILED_QUEUE", tmp_path / "failed.jsonl")
    monkeypatch.setattr(sap_mod, "_RETRIES", 1)
    monkeypatch.setattr(sap_mod, "_BACKOFF", 0.0)
    session = _FakeSession(post_status=500)
    out = make_output(session, csrf=False)
    assert out.send(reading) is False
    queued = (tmp_path / "failed.jsonl").read_text().strip().splitlines()
    assert len(queued) == 1
    assert json.loads(queued[0])["Barcode"] == "0012345"


def test_resend_failed_clears_queue(reading, tmp_path, monkeypatch):
    monkeypatch.setattr(sap_mod, "FAILED_QUEUE", tmp_path / "failed.jsonl")
    (tmp_path / "failed.jsonl").write_text(
        json.dumps({"Barcode": "111"}) + "\n" + json.dumps({"Barcode": "222"}) + "\n"
    )
    session = _FakeSession(post_status=201)
    out = make_output(session, csrf=False)
    assert out.resend_failed() == 2
    assert not (tmp_path / "failed.jsonl").exists()
