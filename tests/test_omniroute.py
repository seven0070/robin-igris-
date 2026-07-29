"""OmniRoute client helpers (no live gateway required)."""

import os

from robin_igris import omniroute


def test_defaults(monkeypatch):
    monkeypatch.delenv("OMNIROUTE_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OMNIROUTE_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OMNIROUTE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert omniroute.base_url() == "http://127.0.0.1:20128/v1"
    assert omniroute.model() == "auto"
    assert omniroute.api_key() == "omniroute"


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("OMNIROUTE_BASE_URL", "http://10.0.0.2:9/v1")
    monkeypatch.setenv("OMNIROUTE_MODEL", "combo:fast")
    monkeypatch.setenv("OMNIROUTE_API_KEY", "sk-test")
    assert omniroute.base_url() == "http://10.0.0.2:9/v1"
    assert omniroute.model() == "combo:fast"
    assert omniroute.api_key() == "sk-test"


def test_llm_uses_omniroute(monkeypatch):
    monkeypatch.setenv("OMNIROUTE_BASE_URL", "http://example.invalid:20128/v1")
    monkeypatch.setenv("OMNIROUTE_API_KEY", "k")
    from robin_igris import llm

    client = llm.get_client()
    assert str(client.base_url).rstrip("/").endswith("20128/v1") or "20128" in str(
        client.base_url
    )
    assert llm.get_model() in {"auto", os.getenv("OMNIROUTE_MODEL", "auto")}


def test_health_false_when_down(monkeypatch):
    monkeypatch.setenv("OMNIROUTE_BASE_URL", "http://127.0.0.1:1/v1")
    assert omniroute.health(timeout=0.2) is False


def test_chat_text_posts(monkeypatch, httpx_mock=None):
    """Mock httpx via monkeypatch if pytest-httpx absent."""
    import httpx

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{"message": {"content": "pong from omni"}}],
            }

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, headers=None, json=None):
            assert url.endswith("/chat/completions")
            assert json["model"] == "auto"
            return FakeResp()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    monkeypatch.setenv("OMNIROUTE_BASE_URL", "http://127.0.0.1:20128/v1")
    out = omniroute.chat_text([{"role": "user", "content": "hi"}])
    assert out == "pong from omni"
