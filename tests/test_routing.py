"""Offline-first OmniRoute routing policy."""

from robin_igris.routing import classify_task, from_capsule, resolve_route


def test_offline_forces_local():
    d = resolve_route(has_network=False, user_text="refactor this python module")
    assert d.mode == "local"
    assert d.allow_cloud is False
    assert d.model  # non-empty


def test_online_coding_spillover():
    d = resolve_route(has_network=True, user_text="Please refactor this Python bug")
    assert d.mode == "cloud"
    assert d.allow_cloud is True
    assert classify_task("refactor this Python bug") == "coding"


def test_budget_blocks_cloud():
    d = resolve_route(has_network=True, user_text="hello", budget_usd=0.01, cloud_min_budget=0.05)
    assert d.mode == "local"
    assert "budget" in d.reason


def test_from_capsule_respects_network_cap():
    d = from_capsule({"network": False, "local_llm": True}, user_text="plan architecture")
    assert d.mode == "local"


def test_from_capsule_manifest_budget():
    d = from_capsule(
        {"network": True, "local_llm": True},
        user_text="hi",
        manifest_raw={"budget": {"balance_usd": 0.01, "cloud_min_usd": 0.05}},
    )
    assert d.mode == "local"
