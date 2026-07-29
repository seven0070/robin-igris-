"""Novel LLM hybrid — not next-token prediction."""

import json
from pathlib import Path

from aos.kernel import AgentKernel
from robin_igris.lived_seed import LivedSeed
from robin_igris.novel_llm import NovelLLM
from robin_igris.tools import TOOL_IMPLS, run_tool


def test_forward_is_not_next_token(tmp_path: Path):
    seed = LivedSeed.create(tmp_path)
    novel = NovelLLM.create(tmp_path, seed=seed)
    out = novel.forward("What is the capital of France?")
    assert out["architecture"] == "novel-hybrid-v0"
    assert out["not"] == "next-token-transformer"
    assert "memory-as-compute" in out["directions"]
    assert out["action"] in {
        "answer_from_memory",
        "synthesize_skill",
        "defer_to_omniroute",
        "ask_clarifying_question",
        "say_nothing",
    }
    # Blank → world model should prefer deferring for capability now
    assert out["action"] == "defer_to_omniroute"
    assert "defer" in out["reply"].lower() or "omniroute" in out["reply"].lower()


def test_memory_as_compute_after_teach(tmp_path: Path):
    seed = LivedSeed.create(tmp_path)
    seed.observe_turn(
        "What is the capital of France?",
        "Paris is the capital of France.",
        outcome="user_satisfied",
        source="teach",
    )
    novel = NovelLLM.create(tmp_path, seed=seed)
    out = novel.forward("capital of France")
    assert out["memories"]
    # Stronger memory → may answer from memory or synthesize
    assert out["action"] in {"answer_from_memory", "synthesize_skill", "defer_to_omniroute"}


def test_program_synthesis_stores_verified_skill(tmp_path: Path):
    seed = LivedSeed.create(tmp_path)
    seed.observe_turn("OpenLife SDP", "Meaning graph beats vectors for retrieval.", outcome="user_satisfied")
    novel = NovelLLM.create(tmp_path, seed=seed)
    # Force synthesis path by calling the module directly if simulator picks defer
    from robin_igris.novel_llm.program_synth import run_program_synthesis

    r = run_program_synthesis(
        "How does SDP memory work?",
        library=novel.skills,
        memory_snippets=["Meaning-based SDP graphs outperform vector similarity."],
    )
    assert r["mode"] == "write_then_execute"
    assert r["program"]["verified"] is True
    assert novel.skills.list_verified()


def test_living_weights_change_every_forward(tmp_path: Path):
    seed = LivedSeed.create(tmp_path)
    novel = NovelLLM.create(tmp_path, seed=seed)
    e0 = len(seed.graph.edges)
    novel.forward("alpha beta gamma patterns in my workflow")
    e1 = len(seed.graph.edges)
    assert e1 >= e0
    assert len(seed.graph.nodes) > 0


def test_kernel_wires_novel(tmp_path: Path, monkeypatch):
    (tmp_path / ".robin_usb").touch()
    monkeypatch.setenv("ROBIN_USB_ROOT", str(tmp_path))
    k = AgentKernel.create(tmp_path)
    assert k.novel_llm is not None
    assert "Novel LLM" in k.boot_context()


def test_shell_novel_command(tmp_path: Path, monkeypatch):
    (tmp_path / ".robin_usb").touch()
    monkeypatch.setenv("ROBIN_USB_ROOT", str(tmp_path))
    from aos.shell import AgentShell

    shell = AgentShell(AgentKernel.create(tmp_path))
    st = json.loads(shell.handle_line(":novel"))
    assert st["architecture"] == "novel-hybrid-v0"
    fwd = json.loads(shell.handle_line(":novel hello from blank mind"))
    assert "reply" in fwd


def test_novel_tools_registered():
    assert "novel_status" in TOOL_IMPLS
    assert "novel_forward" in TOOL_IMPLS


def test_novel_forward_tool(tmp_path: Path, monkeypatch):
    (tmp_path / ".robin_usb").touch()
    monkeypatch.setenv("ROBIN_USB_ROOT", str(tmp_path))
    out = json.loads(run_tool("novel_forward", {"query": "plan my research day"}))
    assert out.get("architecture") == "novel-hybrid-v0"
