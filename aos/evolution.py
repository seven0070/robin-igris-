"""Self-evolving shell — skills/POLICY evolve; immutable core never does over WiFi.

Axiom 3: agent improves what it *knows*; Manifest (human) controls what it *may*.
Checkpoints enable rollback when an evolution fails verification.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class EvolutionStore:
    """Shell evolution under /shell (or data/aos/shell) with checkpoints."""

    root: Path

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        for name in ("skills", "policy", "checkpoints", "proposals"):
            (self.root / name).mkdir(parents=True, exist_ok=True)

    def checkpoint(self, label: str = "auto") -> dict[str, Any]:
        """Snapshot skills + policy into a checkpoint (rollback target)."""
        cid = f"{int(time.time())}-{label}"
        dest = self.root / "checkpoints" / cid
        dest.mkdir(parents=True, exist_ok=True)
        for name in ("skills", "policy"):
            src = self.root / name
            if src.exists():
                shutil.copytree(src, dest / name, dirs_exist_ok=True)
        tip = self._hash_tree(dest)
        meta = {"id": cid, "ts": time.time(), "label": label, "hash": tip}
        (dest / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        (self.root / "checkpoints" / "LATEST").write_text(cid, encoding="utf-8")
        return meta

    def rollback(self, checkpoint_id: str | None = None) -> dict[str, Any]:
        if checkpoint_id is None:
            latest = self.root / "checkpoints" / "LATEST"
            if not latest.exists():
                raise FileNotFoundError("no checkpoints")
            checkpoint_id = latest.read_text(encoding="utf-8").strip()
        src = self.root / "checkpoints" / checkpoint_id
        if not src.exists():
            raise FileNotFoundError(checkpoint_id)
        for name in ("skills", "policy"):
            dest = self.root / name
            if dest.exists():
                shutil.rmtree(dest)
            if (src / name).exists():
                shutil.copytree(src / name, dest)
        return {"restored": checkpoint_id, "hash": self._hash_tree(src)}

    def promote_skill(self, name: str, content: str, *, verified: bool) -> dict[str, Any]:
        """Promote a skill into the evolving library after self-verification."""
        if not verified:
            return {"promoted": False, "reason": "not verified"}
        self.checkpoint(label=f"pre-{name}")
        path = self.root / "skills" / f"{name}.md"
        path.write_text(content, encoding="utf-8")
        return {"promoted": True, "path": str(path), "bytes": len(content.encode())}

    def propose_manifest_update(self, proposal: dict[str, Any]) -> dict[str, Any]:
        """Agent may *propose* Manifest changes; human must approve (not auto-apply)."""
        pid = f"prop-{int(time.time())}"
        path = self.root / "proposals" / f"{pid}.json"
        blob = {
            "id": pid,
            "ts": time.time(),
            "status": "pending_human_approval",
            "proposal": proposal,
            "note": "Manifest stays under human control (AgenticOS). Skills evolve freely.",
        }
        path.write_text(json.dumps(blob, indent=2), encoding="utf-8")
        return blob

    def promote_kairn(self, source_path: Path, *, manifest_caps: dict[str, bool]) -> dict[str, Any]:
        """Compile+test a .kairn skill and promote into the evolving shell if verified."""
        from languages.kairn import compile_file, promote_to_evolution

        res = compile_file(Path(source_path), manifest_path=None)
        # re-verify with explicit caps
        from languages.kairn import compile_skill

        src = Path(source_path).read_text(encoding="utf-8")
        res = compile_skill(src, manifest_caps=manifest_caps)
        if not res.ok:
            return {"promoted": False, "errors": res.errors, "tests": res.test_results}
        return promote_to_evolution(res, self.root)

    def list_skills(self) -> list[str]:
        names = {p.stem for p in (self.root / "skills").glob("*.md")}
        names |= {p.stem for p in (self.root / "skills").glob("*.kbc")}
        return sorted(names)

    def status(self) -> dict[str, Any]:
        latest = self.root / "checkpoints" / "LATEST"
        return {
            "skills": self.list_skills(),
            "latest_checkpoint": latest.read_text(encoding="utf-8").strip()
            if latest.exists()
            else None,
            "pending_manifest_proposals": len(list((self.root / "proposals").glob("*.json"))),
            "axiom": "shell evolves; core never updates over WiFi",
        }

    @staticmethod
    def _hash_tree(root: Path) -> str:
        h = hashlib.sha256()
        for p in sorted(root.rglob("*")):
            if p.is_file():
                h.update(p.relative_to(root).as_posix().encode())
                h.update(p.read_bytes())
        return h.hexdigest()
