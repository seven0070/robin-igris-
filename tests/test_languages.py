"""Aergon capability IR + Kairn skill language tests."""

from pathlib import Path

from languages.aergon import can_hotswap, check_module, parse_aer
from languages.kairn import compile_file, compile_skill, parse_kairn


ROOT = Path(__file__).resolve().parents[1]


def test_aergon_voice_ok():
    src = (ROOT / "languages/aergon/examples/voice.aer").read_text(encoding="utf-8")
    mod = parse_aer(src)
    res = check_module(mod)
    assert res.ok, res.errors
    assert "sync_to_buzz" in mod.functions
    assert "net.buzz" in mod.functions["sync_to_buzz"].caps.writes


def test_aergon_rejects_undeclared_net():
    src = """
    module bad footprint 100
    fn leak()
        reads: [mem.local]
        writes: [mem.local]
    {
        call buzz.push;
    }
    """
    res = check_module(parse_aer(src))
    assert not res.ok
    assert any("net.buzz" in e for e in res.errors)


def test_aergon_hotswap():
    a = parse_aer(
        "module v footprint 100\nfn f()\n  reads: [mem.local]\n  writes: [mem.local]\n{}\n"
    )
    b = parse_aer(
        "module v footprint 90\nfn f()\n  reads: [mem.local]\n  writes: [mem.local]\n{}\n"
    )
    ok, _ = can_hotswap(a, b)
    assert ok
    c = parse_aer(
        "module v footprint 200\nfn f()\n  reads: [mem.local]\n  writes: [mem.local]\n{}\n"
    )
    ok2, reason = can_hotswap(a, c)
    assert not ok2
    assert "footprint" in reason


def test_kairn_parse_and_compile_ok():
    path = ROOT / "languages/kairn/examples/summarize_paper.kairn"
    res = compile_skill(
        path.read_text(encoding="utf-8"),
        manifest_caps={"local_llm": True, "filesystem_soul": True},
    )
    assert res.ok, res.errors
    assert res.skill and res.skill.name == "summarize_paper"
    assert all(t["ok"] for t in res.test_results)


def test_kairn_rejects_network_leak():
    path = ROOT / "languages/kairn/examples/leaky_net.kairn"
    res = compile_skill(
        path.read_text(encoding="utf-8"),
        manifest_caps={"filesystem_soul": True, "local_llm": True},
    )
    assert not res.ok
    assert any("network" in e or "buzz" in e for e in res.errors)


def test_kairn_requires_tests():
    src = """
skill bare(x: Text) -> Ok
    requires: [mem.local]
    produces: [artifact.text]
    budget: 0.1
    steps:
        return Ok
"""
    try:
        parse_kairn(src)
        assert False, "expected ParseError"
    except Exception as exc:
        assert "test" in str(exc).lower()


def test_kairn_compile_file():
    res = compile_file(ROOT / "languages/kairn/examples/summarize_paper.kairn", None)
    assert res.skill is not None
