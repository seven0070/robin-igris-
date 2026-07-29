"""Tests for System 3 (no Hermes/API required)."""

from pathlib import Path

from robin_igris.system3.budget import Metabolism
from robin_igris.system3.heartbeat import Heartbeat, IntrinsicDrive
from robin_igris.system3.journal import GrowthJournal
from robin_igris.system3.skills import SkillBootstrap


def test_metabolism_debit_and_death(tmp_path: Path):
    m = Metabolism(balance_usd=0.05, daily_allowance_usd=0.0, path=tmp_path / "m.json")
    assert m.alive
    assert m.debit(0.05, "full")
    assert not m.alive
    assert not m.debit(0.01, "overdraw")


def test_journal_defaults_and_episode(tmp_path: Path):
    j = GrowthJournal(tmp_path)
    j.ensure_defaults("Robin")
    assert j.policy_path.exists()
    p = j.append_episode(kind="test", summary="hello", appraisal="ok")
    assert p.exists()
    assert "POLICY" in j.context_block()


def test_heartbeat_compose():
    hb = Heartbeat(interval_s=1)
    drive, text = hb.compose_prompt(IntrinsicDrive.CURIOSITY)
    assert drive is IntrinsicDrive.CURIOSITY
    assert "curiosity" in text


def test_virtual_assertions_template():
    boot = SkillBootstrap(skills_dir=Path("/tmp/ri-skills-test"))
    bad = "# x\nshort"
    assert not all(ok for _, ok, _ in boot.virtual_assertions(bad))
    good = """# demo-skill

## Description
A transferable procedure for demo work with enough substance to pass checks.

## Steps
1. Gather inputs
2. Run the procedure
3. Verify outputs

## Pitfalls
- Do not skip verification
"""
    assert all(ok for _, ok, _ in boot.virtual_assertions(good))
