"""CADVP — Cross-Agent Delivery Verification (Channel Fracture, arXiv:2606.04896).

Prevents silent delivery failures when scheduled/heartbeat wakes try to persist
knowledge. Hermes cron uses skip_memory=True; we never rely on that channel.

Principles:
  - Inverse verification: confirm on the *receiver* read path, not the writer claim
  - Channel matching: pick a channel whose architecture allows the write
  - CC-0 veto: abort if the channel is unavailable
  - Three-Gate: L1 self-check → L2 evidence → L3 cross-review
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Channel(str, Enum):
    """Injection channels from the paper, mapped onto Robin Igris."""

    DIRECT_STORE = "A_direct_store"  # filesystem / SQLite we own (safe)
    TARGET_SELF = "B_target_self"  # target agent memory tools (interactive OK)
    CRON_DELEGATED = "C_cron_delegated"  # Hermes cron — FRACTURED by default


@dataclass
class ChannelProbe:
    channel: Channel
    available: bool
    reason: str
    cc0_pass: bool


@dataclass
class GateResult:
    gate: str
    passed: bool
    detail: str
    score: float = 1.0


@dataclass
class DeliveryReceipt:
    delivery_id: str
    channel: Channel
    target: str
    payload_hash: str
    cc0: ChannelProbe
    gates: list[GateResult]
    confirmed: bool
    readback: dict[str, Any] | None = None
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "delivery_id": self.delivery_id,
            "channel": self.channel.value,
            "target": self.target,
            "payload_hash": self.payload_hash,
            "cc0": {
                "channel": self.cc0.channel.value,
                "available": self.cc0.available,
                "reason": self.cc0.reason,
                "cc0_pass": self.cc0.cc0_pass,
            },
            "gates": [
                {
                    "gate": g.gate,
                    "passed": g.passed,
                    "detail": g.detail,
                    "score": g.score,
                }
                for g in self.gates
            ],
            "confirmed": self.confirmed,
            "readback": self.readback,
            "ts": self.ts,
        }


class DeliveryBus:
    """
    Failsafe delivery store (Channel A).

    Heartbeat / scheduled System 3 wakes write here, then inverse-verify by
    reading back — never trusting writer-side success alone.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or "data/system3/delivery")
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "inbox").mkdir(exist_ok=True)
        (self.root / "receipts").mkdir(exist_ok=True)

    def probe(self, channel: Channel) -> ChannelProbe:
        """CC-0: is this channel architecturally available?"""
        if channel is Channel.DIRECT_STORE:
            writable = self.root.exists() and self.root.is_dir()
            try:
                probe = self.root / ".cc0_probe"
                probe.write_text("ok", encoding="utf-8")
                probe.unlink(missing_ok=True)
                ok = writable
                reason = "direct store writable"
            except OSError as exc:
                ok = False
                reason = f"direct store not writable: {exc}"
            return ChannelProbe(channel, ok, reason, cc0_pass=ok)

        if channel is Channel.TARGET_SELF:
            # Interactive Hermes memory tools may work; we don't assume cron.
            return ChannelProbe(
                channel,
                available=True,
                reason="target-self allowed only in interactive sessions (not cron)",
                cc0_pass=True,
            )

        # Channel C — known fracture on Hermes cron (skip_memory=True)
        return ChannelProbe(
            channel,
            available=False,
            reason=(
                "Hermes cron hardcodes skip_memory=True; memory tools are not "
                "registered — channel fracture (arXiv:2606.04896). Use Channel A."
            ),
            cc0_pass=False,
        )

    def select_channel(self, preferred: Channel | None = None) -> ChannelProbe:
        order = [preferred] if preferred else []
        order += [Channel.DIRECT_STORE, Channel.TARGET_SELF, Channel.CRON_DELEGATED]
        seen: set[Channel] = set()
        for ch in order:
            if ch is None or ch in seen:
                continue
            seen.add(ch)
            probe = self.probe(ch)
            if probe.cc0_pass:
                return probe
        # Fall through with last failing probe
        return self.probe(Channel.CRON_DELEGATED)

    @staticmethod
    def payload_hash(payload: dict[str, Any] | str) -> str:
        raw = payload if isinstance(payload, str) else json.dumps(payload, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def deliver(
        self,
        *,
        target: str,
        kind: str,
        content: str,
        meta: dict[str, Any] | None = None,
        preferred_channel: Channel | None = None,
        require_l3: bool = True,
    ) -> DeliveryReceipt:
        """CADVP pipeline: CC-0 → write → inverse read → Three-Gate."""
        delivery_id = str(uuid.uuid4())
        payload = {
            "delivery_id": delivery_id,
            "target": target,
            "kind": kind,
            "content": content,
            "meta": meta or {},
            "ts": time.time(),
        }
        ph = self.payload_hash(payload)

        probe = self.select_channel(preferred_channel)
        if not probe.cc0_pass:
            receipt = DeliveryReceipt(
                delivery_id=delivery_id,
                channel=probe.channel,
                target=target,
                payload_hash=ph,
                cc0=probe,
                gates=[
                    GateResult("CC-0", False, probe.reason, 0.0),
                ],
                confirmed=False,
            )
            self._save_receipt(receipt)
            return receipt

        # --- write on matched channel ---
        if probe.channel is Channel.DIRECT_STORE:
            path = self.root / "inbox" / f"{target}__{delivery_id}.json"
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        elif probe.channel is Channel.TARGET_SELF:
            # Emulate self-write by also landing in inbox (caller may mirror to Hermes)
            path = self.root / "inbox" / f"{target}__{delivery_id}.json"
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        else:
            receipt = DeliveryReceipt(
                delivery_id=delivery_id,
                channel=probe.channel,
                target=target,
                payload_hash=ph,
                cc0=probe,
                gates=[GateResult("CC-0", False, "unreachable channel", 0.0)],
                confirmed=False,
            )
            self._save_receipt(receipt)
            return receipt

        # Inverse verification — receiver read path
        readback = self.read(delivery_id, target=target)
        gates = self._three_gates(payload, readback, require_l3=require_l3)
        confirmed = all(g.passed for g in gates) and readback is not None

        receipt = DeliveryReceipt(
            delivery_id=delivery_id,
            channel=probe.channel,
            target=target,
            payload_hash=ph,
            cc0=probe,
            gates=gates,
            confirmed=confirmed,
            readback=readback,
        )
        self._save_receipt(receipt)
        return receipt

    def read(self, delivery_id: str, *, target: str | None = None) -> dict[str, Any] | None:
        """Receiver-side read (inverse verification)."""
        for path in (self.root / "inbox").glob("*.json"):
            if delivery_id not in path.name:
                continue
            if target and not path.name.startswith(f"{target}__"):
                continue
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return None
        return None

    def list_inbox(self, target: str | None = None) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in sorted((self.root / "inbox").glob("*.json")):
            if target and not path.name.startswith(f"{target}__"):
                continue
            try:
                items.append(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
        return items

    def _three_gates(
        self,
        payload: dict[str, Any],
        readback: dict[str, Any] | None,
        *,
        require_l3: bool,
    ) -> list[GateResult]:
        gates: list[GateResult] = []

        # L1 Self-Verification — structural completeness
        required = ("delivery_id", "target", "kind", "content", "ts")
        missing = [k for k in required if k not in payload or payload[k] in ("", None)]
        l1_ok = not missing and len(str(payload.get("content", ""))) >= 8
        gates.append(
            GateResult(
                "L1_self",
                l1_ok,
                "ok" if l1_ok else f"missing/short fields: {missing}",
                1.0 if l1_ok else 0.0,
            )
        )

        # L2 Evidence Verification — inverse read matches hash
        if readback is None:
            gates.append(GateResult("L2_evidence", False, "readback empty", 0.0))
        else:
            match = (
                readback.get("delivery_id") == payload["delivery_id"]
                and readback.get("content") == payload["content"]
                and self.payload_hash(readback) == self.payload_hash(payload)
            )
            gates.append(
                GateResult(
                    "L2_evidence",
                    match,
                    "receiver read matches writer payload"
                    if match
                    else "readback mismatch",
                    1.0 if match else 0.0,
                )
            )

        # L3 Cross-Review — lightweight quality score (deterministic proxy)
        content = str(payload.get("content", ""))
        score = 0.0
        if len(content) >= 8:
            score += 0.4
        if len(content) >= 40:
            score += 0.3
        if payload.get("kind"):
            score += 0.2
        if payload.get("meta") is not None:
            score += 0.1
        l3_ok = score >= 0.9 if require_l3 else score >= 0.5
        gates.append(
            GateResult(
                "L3_cross_review",
                l3_ok,
                f"quality_score={score:.2f} (threshold={'0.9' if require_l3 else '0.5'})",
                score,
            )
        )
        return gates

    def _save_receipt(self, receipt: DeliveryReceipt) -> None:
        path = self.root / "receipts" / f"{receipt.delivery_id}.json"
        path.write_text(json.dumps(receipt.to_dict(), indent=2), encoding="utf-8")
