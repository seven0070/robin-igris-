"""Offline-first outbox — queue network work until permissioned WiFi allows it."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass
class OfflineQueue:
    root: Path

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "pending").mkdir(parents=True, exist_ok=True)
        (self.root / "done").mkdir(parents=True, exist_ok=True)
        (self.root / "failed").mkdir(parents=True, exist_ok=True)

    def enqueue(
        self,
        action: str,
        payload: dict[str, Any],
        *,
        wifi_action: str | None = None,
    ) -> str:
        job_id = str(uuid.uuid4())
        job = {
            "id": job_id,
            "ts": time.time(),
            "action": action,
            "wifi_action": wifi_action or action,
            "payload": payload,
            "status": "pending",
        }
        path = self.root / "pending" / f"{job_id}.json"
        path.write_text(json.dumps(job, indent=2), encoding="utf-8")
        return job_id

    def list_pending(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for p in sorted((self.root / "pending").glob("*.json")):
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
        return out

    def flush(
        self,
        *,
        allow: Callable[[str], tuple[bool, str]],
        handlers: dict[str, Callable[[dict[str, Any]], Any]],
    ) -> dict[str, Any]:
        """Attempt pending jobs. ``allow(wifi_action) -> (ok, reason)``."""
        results: list[dict[str, Any]] = []
        for job in self.list_pending():
            wifi_action = job.get("wifi_action") or job["action"]
            ok, reason = allow(str(wifi_action))
            if not ok:
                results.append({"id": job["id"], "status": "deferred", "reason": reason})
                continue
            handler = handlers.get(job["action"])
            pending_path = self.root / "pending" / f"{job['id']}.json"
            if handler is None:
                job["status"] = "failed"
                job["error"] = f"no handler for {job['action']}"
                (self.root / "failed" / f"{job['id']}.json").write_text(
                    json.dumps(job, indent=2), encoding="utf-8"
                )
                pending_path.unlink(missing_ok=True)
                results.append({"id": job["id"], "status": "failed", "error": job["error"]})
                continue
            try:
                out = handler(job.get("payload") or {})
                job["status"] = "done"
                job["result"] = out
                (self.root / "done" / f"{job['id']}.json").write_text(
                    json.dumps(job, indent=2, default=str), encoding="utf-8"
                )
                pending_path.unlink(missing_ok=True)
                results.append({"id": job["id"], "status": "done"})
            except Exception as exc:  # noqa: BLE001
                job["status"] = "failed"
                job["error"] = str(exc)
                (self.root / "failed" / f"{job['id']}.json").write_text(
                    json.dumps(job, indent=2), encoding="utf-8"
                )
                pending_path.unlink(missing_ok=True)
                results.append({"id": job["id"], "status": "failed", "error": str(exc)})
        return {"flushed": results, "remaining": len(self.list_pending())}
