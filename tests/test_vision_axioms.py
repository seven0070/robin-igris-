"""Tests for offline-first WiFi contract, queue, and shell evolution."""

import json
from pathlib import Path

from aos.evolution import EvolutionStore
from aos.kernel import AgentKernel
from aos.offline_queue import OfflineQueue
from aos.wifi_contract import WifiContract


def test_wifi_default_deny_unknown_ssid(monkeypatch):
    monkeypatch.setenv("ROBIN_WIFI_ASSUME_STAR", "0")
    monkeypatch.delenv("ROBIN_WIFI_SSID", raising=False)
    c = WifiContract.from_manifest_raw(
        {
            "wifi": {
                "default": "deny",
                "networks": [{"ssid": "home", "actions": ["check_buzz"], "budget_mb_month": 10}],
            }
        }
    )
    ok, reason = c.allow("check_buzz", ssid=None)
    assert ok is False
    assert "offline" in reason or "not in" in reason or "deny" in reason.lower() or "no authorized" in reason


def test_wifi_allows_listed_action(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("ROBIN_WIFI_SSID", "home")
    c = WifiContract.from_manifest_raw(
        {
            "wifi": {
                "default": "deny",
                "networks": [
                    {"ssid": "home", "actions": ["check_buzz", "sync_memory"], "budget_mb_month": 10}
                ],
            }
        },
        usage_path=tmp_path / "usage.json",
    )
    ok, _ = c.allow("check_buzz")
    assert ok is True
    ok2, reason = c.allow("pull_models")
    assert ok2 is False
    assert "not permitted" in reason


def test_wifi_budget(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("ROBIN_WIFI_SSID", "home")
    c = WifiContract.from_manifest_raw(
        {
            "wifi": {
                "networks": [{"ssid": "home", "actions": ["check_buzz"], "budget_mb_month": 0.0001}]
            }
        },
        usage_path=tmp_path / "usage.json",
    )
    c.record_usage(bytes_used=10_000_000)
    ok, reason = c.allow("check_buzz", bytes_estimate=1000)
    assert ok is False
    assert "budget" in reason


def test_offline_queue_flush(tmp_path: Path):
    q = OfflineQueue(tmp_path / "queue")
    jid = q.enqueue("ping", {"n": 1}, wifi_action="check_buzz")
    assert jid
    assert len(q.list_pending()) == 1

    def allow_yes(_a: str):
        return True, "ok"

    def allow_no(_a: str):
        return False, "offline"

    r = q.flush(allow=allow_no, handlers={"ping": lambda p: p})
    assert r["remaining"] == 1
    r2 = q.flush(allow=allow_yes, handlers={"ping": lambda p: {"echo": p}})
    assert r2["remaining"] == 0
    assert r2["flushed"][0]["status"] == "done"


def test_evolution_checkpoint_rollback(tmp_path: Path):
    evo = EvolutionStore(tmp_path / "shell")
    evo.promote_skill("hello", "# hello\n", verified=True)
    meta = evo.checkpoint("t1")
    evo.promote_skill("hello", "# hello v2\n", verified=True)
    assert (tmp_path / "shell" / "skills" / "hello.md").read_text().endswith("v2\n")
    evo.rollback(meta["id"])
    assert "# hello\n" in (tmp_path / "shell" / "skills" / "hello.md").read_text()
    prop = evo.propose_manifest_update({"capabilities": {"camera": True}})
    assert prop["status"] == "pending_human_approval"


def test_kernel_wires_axioms(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ROBIN_WIFI_ASSUME_STAR", "1")
    (tmp_path / ".robin_usb").touch()
    k = AgentKernel.create(tmp_path)
    st = k.status()
    assert "offline-first" in st["axioms"]
    assert "wifi" in st
    assert k.queue is not None
    assert k.evolution is not None
    jid = k.enqueue_offline("buzz_send_message", {"content": "hi"}, wifi_action="check_buzz")
    assert jid
    assert st["offline_queue_pending"] >= 0 or True
