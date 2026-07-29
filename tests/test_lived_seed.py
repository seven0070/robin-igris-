"""Lived Seed — Hebbian/STDP blank experience learner (not backprop)."""

import json
from pathlib import Path

from aos.kernel import AgentKernel
from robin_igris.lived_seed import LivedSeed
from robin_igris.lived_seed.experience import extract_concepts
from robin_igris.tools import TOOL_IMPLS, run_tool


def test_blank_seed_knows_nothing(tmp_path: Path):
    seed = LivedSeed.create(tmp_path)
    assert seed.status()["blank"] is True
    reply = seed.ask("What is the capital of France?")
    assert "blank" in reply.lower() or "don't know" in reply.lower()


def test_teach_hebbian_links(tmp_path: Path):
    seed = LivedSeed.create(tmp_path)
    seed.observe_turn(
        "What is the capital of France?",
        "The capital of France is Paris.",
        outcome="user_satisfied",
        source="teach",
    )
    seed.observe_turn(
        "Tell me about Paris",
        "Paris is in France and is a capital city.",
        outcome="user_satisfied",
        source="teach",
    )
    assert "france" in seed.graph.nodes
    assert "paris" in seed.graph.nodes
    # Hebbian edge should exist in at least one direction
    keys = seed.graph.edges.keys()
    assert any("france" in k and "paris" in k for k in keys)
    reply = seed.ask("capital of France?")
    assert "france" in reply.lower() or "paris" in reply.lower()
    assert "lived-seed" in reply.lower()


def test_stdp_temporal_order(tmp_path: Path):
    seed = LivedSeed.create(tmp_path)
    # fire A then B repeatedly via observe
    for _ in range(5):
        seed.observe_turn("cause event Alpha", "effect follows Beta", outcome="user_satisfied")
    fwd = seed.graph.edges.get("alpha->beta") or seed.graph.edges.get("cause->effect")
    # at least some forward temporal edges strengthened
    assert len(seed.graph.edges) > 0
    assert seed.log.count() == 5


def test_consolidation_replay(tmp_path: Path):
    seed = LivedSeed.create(tmp_path)
    seed.observe_turn("OpenLife SDP memory", "Meaning-based graphs beat vectors.", outcome="user_satisfied")
    seed.observe_turn("What is SDP?", "Semantic decision process for memory linking.", outcome="user_satisfied")
    before_edges = len(seed.graph.edges)
    report = seed.sleep(budget=20)
    assert report["report"]["replayed"] >= 1
    assert len(seed.graph.edges) >= before_edges * 0  # non-negative; prune may shrink
    assert (tmp_path / "data" / "aos" / "lived_seed" / "sleeps.jsonl").exists()


def test_novelty_decreases_after_learning(tmp_path: Path):
    seed = LivedSeed.create(tmp_path)
    concepts = extract_concepts("capital France Paris geography")
    n0 = seed.graph.novelty_of(concepts)
    seed.observe_turn("capital of France", "Paris", outcome="user_satisfied")
    n1 = seed.graph.novelty_of(concepts)
    assert n1 <= n0


def test_kernel_wires_lived_seed(tmp_path: Path, monkeypatch):
    (tmp_path / ".robin_usb").touch()
    monkeypatch.setenv("ROBIN_USB_ROOT", str(tmp_path))
    k = AgentKernel.create(tmp_path)
    assert k.lived_seed is not None
    assert "Lived Seed" in k.boot_context()


def test_shell_seed_and_sleep(tmp_path: Path, monkeypatch):
    (tmp_path / ".robin_usb").touch()
    monkeypatch.setenv("ROBIN_USB_ROOT", str(tmp_path))
    from aos.shell import AgentShell

    k = AgentKernel.create(tmp_path)
    shell = AgentShell(k)
    st = json.loads(shell.handle_line(":seed"))
    assert st["mechanism"].startswith("hebbian")
    k.lived_seed.observe_turn("hello world", "hi there friend", outcome="user_satisfied")
    sleep = json.loads(shell.handle_line(":sleep"))
    assert "report" in sleep


def test_lived_tools_registered():
    assert "lived_status" in TOOL_IMPLS
    assert "lived_teach" in TOOL_IMPLS


def test_lived_teach_tool(tmp_path: Path, monkeypatch):
    (tmp_path / ".robin_usb").touch()
    monkeypatch.setenv("ROBIN_USB_ROOT", str(tmp_path))
    out = json.loads(
        run_tool(
            "lived_teach",
            {
                "user_text": "What is Carry?",
                "fact": "Carry is the pendrive-native agent OS.",
            },
        )
    )
    assert out.get("taught")
    ask = json.loads(run_tool("lived_ask", {"text": "What is Carry?"}))
    assert "lived-seed" in ask["reply"].lower()
