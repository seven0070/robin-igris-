"""Pendrive-aware LLM routing policy for OmniRoute.

Offline-first: no network → local model only.
Online spillover: complex tasks → stronger cloud routes via OmniRoute ``auto`` / aliases.
Manifest budget gates expensive spillover.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Literal

RouteMode = Literal["local", "cloud", "auto"]


@dataclass(frozen=True)
class RouteDecision:
    model: str
    mode: RouteMode
    reason: str
    allow_cloud: bool


# Heuristic task tags → preferred OmniRoute model / combo name (overridable via env)
_TASK_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"\b(code|python|typescript|refactor|bug|compile|git)\b", re.I), "coding", "cloud"),
    (re.compile(r"\b(reason|analy[sz]e|plan|architect|theorem|proof)\b", re.I), "reasoning", "cloud"),
    (re.compile(r"\b(document|pdf|long context|summarize chapter|transcript)\b", re.I), "longctx", "cloud"),
    (re.compile(r"\b(batch|cheap|bulk|classify many)\b", re.I), "cheap", "cloud"),
]


def local_model() -> str:
    return (
        os.getenv("OMNIROUTE_LOCAL_MODEL")
        or os.getenv("ROBIN_LOCAL_MODEL")
        or "local"
    )


def cloud_model(task_kind: str = "auto") -> str:
    """Map task kind to OmniRoute model id (combo / provider alias / auto)."""
    env_map = {
        "coding": os.getenv("OMNIROUTE_MODEL_CODING"),
        "reasoning": os.getenv("OMNIROUTE_MODEL_REASONING"),
        "longctx": os.getenv("OMNIROUTE_MODEL_LONGCTX"),
        "cheap": os.getenv("OMNIROUTE_MODEL_CHEAP"),
        "auto": os.getenv("OMNIROUTE_MODEL") or os.getenv("OPENAI_MODEL") or "auto",
    }
    return env_map.get(task_kind) or env_map["auto"] or "auto"


def classify_task(text: str | None) -> str:
    if not text:
        return "auto"
    for pat, kind, _ in _TASK_PATTERNS:
        if pat.search(text):
            return kind
    return "auto"


def resolve_route(
    *,
    has_network: bool,
    user_text: str | None = None,
    budget_usd: float | None = None,
    cloud_min_budget: float | None = None,
    force_local: bool = False,
    prefer_cloud: bool = False,
) -> RouteDecision:
    """Choose OmniRoute model for this turn.

    Policy:
      1. No network or force_local → local only
      2. Budget below cloud_min → local only (cost control from Manifest)
      3. Task heuristic or prefer_cloud → cloud/auto spillover
      4. Else → auto (OmniRoute decides among connected providers)
    """
    min_budget = cloud_min_budget
    if min_budget is None:
        min_budget = float(os.getenv("OMNIROUTE_CLOUD_MIN_BUDGET", "0.05"))

    if force_local or not has_network:
        return RouteDecision(
            model=local_model(),
            mode="local",
            reason="offline-first: no network or force_local",
            allow_cloud=False,
        )

    if budget_usd is not None and budget_usd < min_budget:
        return RouteDecision(
            model=local_model(),
            mode="local",
            reason=f"budget {budget_usd:.4f} < cloud_min {min_budget:.4f}",
            allow_cloud=False,
        )

    kind = classify_task(user_text)
    if prefer_cloud or kind != "auto":
        return RouteDecision(
            model=cloud_model(kind),
            mode="cloud",
            reason=f"online spillover task={kind}",
            allow_cloud=True,
        )

    return RouteDecision(
        model=cloud_model("auto"),
        mode="auto",
        reason="online: OmniRoute auto",
        allow_cloud=True,
    )


def routing_context(decision: RouteDecision) -> str:
    return (
        f"## LLM route (OmniRoute)\n"
        f"mode={decision.mode} model={decision.model}\n"
        f"reason={decision.reason} allow_cloud={decision.allow_cloud}\n"
    )


def from_capsule(
    effective_caps: dict[str, bool],
    *,
    user_text: str | None = None,
    budget_usd: float | None = None,
    manifest_raw: dict[str, Any] | None = None,
) -> RouteDecision:
    """Resolve using Manifest∩Hardware + optional Manifest.routing / budget."""
    raw = manifest_raw or {}
    routing = raw.get("routing") or {}
    budget = raw.get("budget") or {}
    cloud_min = budget.get("cloud_min_usd")
    if cloud_min is not None:
        cloud_min = float(cloud_min)
    bal = budget_usd
    if bal is None and "balance_usd" in budget:
        bal = float(budget["balance_usd"])
    return resolve_route(
        has_network=bool(effective_caps.get("network", False)),
        user_text=user_text,
        budget_usd=bal,
        cloud_min_budget=cloud_min,
        force_local=bool(routing.get("force_local", False)),
        prefer_cloud=bool(routing.get("prefer_cloud", False)),
    )
