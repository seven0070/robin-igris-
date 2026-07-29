"""Portable Agent Memory — soul on the stick (Merkle-DAG provenance)."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal

MemoryClass = Literal["episodic", "semantic", "procedural", "working", "identity"]


def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def content_hash(obj: Any) -> str:
    return hashlib.sha256(_canonical(obj)).hexdigest()


@dataclass
class MemoryEntry:
    id: str
    klass: MemoryClass
    content: str
    meta: dict[str, Any] = field(default_factory=dict)
    parents: list[str] = field(default_factory=list)
    ts: float = field(default_factory=time.time)

    def payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "klass": self.klass,
            "content": self.content,
            "meta": self.meta,
            "parents": self.parents,
            "ts": self.ts,
        }

    def entry_hash(self) -> str:
        return content_hash(self.payload())


@dataclass
class SoulStore:
    """Five-component memory with Merkle tip — lives on the USB."""

    root: Path
    seal_key: bytes | None = None

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        for name in ("episodic", "semantic", "procedural", "working", "identity", "meta"):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        if self.seal_key is None:
            key_path = self.root / "meta" / "seal.key"
            if key_path.exists():
                self.seal_key = key_path.read_bytes()
            else:
                self.seal_key = hashlib.sha256(
                    (os.getenv("ROBIN_SOUL_SECRET") or "robin-igris-usb-soul").encode()
                ).digest()
                key_path.write_bytes(self.seal_key)

    def _path(self, klass: MemoryClass, entry_id: str) -> Path:
        return self.root / klass / f"{entry_id}.json"

    def append(
        self,
        klass: MemoryClass,
        content: str,
        *,
        meta: dict[str, Any] | None = None,
        parents: Iterable[str] | None = None,
    ) -> MemoryEntry:
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            klass=klass,
            content=content,
            meta=meta or {},
            parents=list(parents or []),
        )
        path = self._path(klass, entry.id)
        blob = {**entry.payload(), "hash": entry.entry_hash()}
        path.write_text(json.dumps(blob, indent=2), encoding="utf-8")
        self._update_tip()
        return entry

    def list_class(self, klass: MemoryClass, limit: int = 50) -> list[dict[str, Any]]:
        files = sorted((self.root / klass).glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        out: list[dict[str, Any]] = []
        for p in files[:limit]:
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
        return out

    def all_hashes(self) -> list[str]:
        hashes: list[str] = []
        for klass in ("episodic", "semantic", "procedural", "working", "identity"):
            for p in sorted((self.root / klass).glob("*.json")):
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    hashes.append(data.get("hash") or content_hash(data))
                except json.JSONDecodeError:
                    continue
        return hashes

    def merkle_root(self, hashes: list[str] | None = None) -> str:
        nodes = list(hashes or self.all_hashes())
        if not nodes:
            return content_hash({"empty": True})
        while len(nodes) > 1:
            nxt: list[str] = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else left
                nxt.append(hashlib.sha256((left + right).encode()).hexdigest())
            nodes = nxt
        return nodes[0]

    def _update_tip(self) -> dict[str, Any]:
        root = self.merkle_root()
        tip = {
            "merkle_root": root,
            "count": len(self.all_hashes()),
            "ts": time.time(),
        }
        assert self.seal_key is not None
        tip["seal"] = hmac.new(self.seal_key, root.encode(), hashlib.sha256).hexdigest()
        (self.root / "meta" / "tip.json").write_text(json.dumps(tip, indent=2), encoding="utf-8")
        return tip

    def tip(self) -> dict[str, Any]:
        path = self.root / "meta" / "tip.json"
        if not path.exists():
            return self._update_tip()
        return json.loads(path.read_text(encoding="utf-8"))

    def verify_seal(self) -> bool:
        tip = self.tip()
        root = self.merkle_root()
        if tip.get("merkle_root") != root:
            return False
        assert self.seal_key is not None
        expected = hmac.new(self.seal_key, root.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, tip.get("seal", ""))

    def export_bundle(self) -> dict[str, Any]:
        """Portable Agent Memory style export for cross-host rehydration."""
        bundle = {
            "protocol": "robin-pnaos-soul/v1",
            "tip": self.tip(),
            "classes": {
                k: self.list_class(k, limit=10_000)  # type: ignore[arg-type]
                for k in ("episodic", "semantic", "procedural", "working", "identity")
            },
        }
        bundle["bundle_hash"] = content_hash(bundle["classes"])
        return bundle

    def context_prompt(self, limit: int = 6) -> str:
        idents = self.list_class("identity", limit=3)
        recent = self.list_class("episodic", limit=limit)
        tip = self.tip()
        lines = [
            "## Soul (on pendrive)",
            f"Merkle tip: {tip.get('merkle_root', '')[:16]}… sealed={self.verify_seal()}",
            "### Identity",
        ]
        for e in idents:
            lines.append(f"- {e.get('content', '')[:200]}")
        lines.append("### Recent episodic")
        for e in recent:
            lines.append(f"- {e.get('content', '')[:200]}")
        return "\n".join(lines) + "\n"

    def ensure_identity(self, name: str = "Robin Igris") -> None:
        if self.list_class("identity", limit=1):
            return
        self.append(
            "identity",
            f"I am {name}. My home is this USB stick. Host hardware is borrowed.",
            meta={"creed": ["continuity", "honesty", "presence"]},
        )
