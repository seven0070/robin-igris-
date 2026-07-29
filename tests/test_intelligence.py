"""Intelligence stack — capability model, papers, RAG, curation."""

import json
from pathlib import Path

from aos.kernel import AgentKernel
from aos.research.ingest import ingest_markdown
from aos.research.papers import PaperRepository
from aos.research.rag import retrieve
from robin_igris.intelligence import IntelligenceStack
from robin_igris.model_capabilities import CapabilityModel
from robin_igris.routing import resolve_route
from robin_igris.tools import TOOL_IMPLS, run_tool


def test_capability_ranks_coding_above_local_when_online(tmp_path: Path):
    cm = CapabilityModel.load(tmp_path / "caps")
    ranked = cm.rank("coding", allow_cloud=True)
    assert ranked[0]["id"] in {"coding", "reasoning", "auto"}
    assert any(r["id"] == "local" for r in ranked)


def test_privacy_route_forces_local():
    d = resolve_route(has_network=True, user_text="keep this private and uncensored")
    assert d.mode == "local"
    assert d.task_kind == "privacy"


def test_paper_ingest_and_search(tmp_path: Path):
    repo = PaperRepository(tmp_path / "research")
    p = ingest_markdown(
        repo,
        title="OpenLife SDP Memory Graph",
        markdown=(
            "# OpenLife SDP Memory Graph\n\n"
            "## Abstract\n\n"
            "We propose a meaning-based memory graph that outperforms vector similarity for retrieval.\n\n"
            "Results show stronger long-horizon agent recall on episodic tasks.\n"
        ),
        source="osint",
        tags=["openlife", "memory"],
    )
    assert p.claims
    hits = repo.search("memory graph retrieval")
    assert hits
    assert hits[0]["id"] == p.id
    repo.promote(p.id, skill_hint="rag_over_sdp")
    assert repo.get(p.id).promoted is True


def test_rag_over_papers_and_soul(tmp_path: Path, monkeypatch):
    (tmp_path / ".robin_usb").touch()
    monkeypatch.setenv("ROBIN_USB_ROOT", str(tmp_path))
    k = AgentKernel.create(tmp_path)
    assert k.intelligence is not None
    ingest_markdown(
        k.intelligence.papers,
        title="Agentic OS design",
        markdown="Pendrive-native agents need offline-first routing and paper repositories.",
        tags=["pnaos"],
    )
    k.soul.append("semantic", "Pendrive agent uses PAM soul seal across unplug.")
    out = retrieve("pendrive offline paper", papers=k.intelligence.papers, soul=k.soul, limit=5)
    assert out["hits"]


def test_curation_export(tmp_path: Path):
    stack = IntelligenceStack.create(tmp_path)
    stack.curation.add_sft(prompt="2+2?", completion="4")
    path = stack.curation.export_jsonl("sft")
    assert path.exists()
    assert "2+2" in path.read_text()


def test_intel_tools_registered():
    assert "intel_status" in TOOL_IMPLS
    assert "paper_ingest" in TOOL_IMPLS


def test_paper_ingest_tool(tmp_path: Path, monkeypatch):
    (tmp_path / ".robin_usb").touch()
    monkeypatch.setenv("ROBIN_USB_ROOT", str(tmp_path))
    out = json.loads(
        run_tool(
            "paper_ingest",
            {
                "title": "OSINT note on routers",
                "text": "Claim: OmniRoute should rank models by task strength over time.",
                "tags": "osint,routing",
            },
        )
    )
    assert out.get("ingested")
    search = json.loads(run_tool("paper_search", {"query": "OmniRoute rank models"}))
    assert search.get("hits")


def test_kernel_boot_includes_intelligence(tmp_path: Path, monkeypatch):
    (tmp_path / ".robin_usb").touch()
    monkeypatch.setenv("ROBIN_USB_ROOT", str(tmp_path))
    k = AgentKernel.create(tmp_path)
    ctx = k.boot_context()
    assert "Intelligence stack" in ctx
    assert "LLM capability model" in ctx


def test_shell_intel_commands(tmp_path: Path, monkeypatch):
    (tmp_path / ".robin_usb").touch()
    monkeypatch.setenv("ROBIN_USB_ROOT", str(tmp_path))
    from aos.shell import AgentShell

    k = AgentKernel.create(tmp_path)
    shell = AgentShell(k)
    st = json.loads(shell.handle_line(":intel"))
    assert "papers" in st
    assert "capabilities" in st
