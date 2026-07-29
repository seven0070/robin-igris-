"""CADVP / Channel Fracture tests (arXiv:2606.04896)."""

from pathlib import Path

from robin_igris.system3.cadvp import Channel, DeliveryBus


def test_cc0_vetoes_cron_channel(tmp_path: Path):
    bus = DeliveryBus(tmp_path / "delivery")
    probe = bus.probe(Channel.CRON_DELEGATED)
    assert not probe.cc0_pass
    assert "skip_memory" in probe.reason or "fracture" in probe.reason.lower()


def test_cc0_allows_direct_store(tmp_path: Path):
    bus = DeliveryBus(tmp_path / "delivery")
    probe = bus.probe(Channel.DIRECT_STORE)
    assert probe.cc0_pass


def test_select_channel_skips_fracture(tmp_path: Path):
    bus = DeliveryBus(tmp_path / "delivery")
    probe = bus.select_channel(Channel.CRON_DELEGATED)
    assert probe.channel is Channel.DIRECT_STORE
    assert probe.cc0_pass


def test_deliver_inverse_verification(tmp_path: Path):
    bus = DeliveryBus(tmp_path / "delivery")
    receipt = bus.deliver(
        target="robin-igris",
        kind="test",
        content="Persist this fact across heartbeat wakes.",
        preferred_channel=Channel.DIRECT_STORE,
    )
    assert receipt.confirmed
    assert receipt.readback is not None
    assert receipt.readback["content"].startswith("Persist")
    gate_names = [g.gate for g in receipt.gates]
    assert "L1_self" in gate_names
    assert "L2_evidence" in gate_names
    assert "L3_cross_review" in gate_names


def test_deliver_rejects_when_forcing_broken_path(tmp_path: Path):
    """If only cron is requested and no fallback… select_channel still falls back."""
    bus = DeliveryBus(tmp_path / "delivery")
    # Forcing cron in deliver() still uses select_channel which falls back to A
    receipt = bus.deliver(
        target="robin-igris",
        kind="test",
        content="Should land on Channel A via matching after CC-0 vetoes cron.",
        preferred_channel=Channel.CRON_DELEGATED,
    )
    assert receipt.channel is Channel.DIRECT_STORE
    assert receipt.confirmed
    assert all(g.passed for g in receipt.gates)
