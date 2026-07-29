"""Pendrive-aware LLM routing policy for OmniRoute.

Offline-first: no network → local model only.
Online spillover: capability model ranks coding/reasoning/longctx/… routes.
Manifest budget gates expensive spillover. Local stays uncensored + private.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

RouteMode = Literal["local", "cloud", "auto"]


@dataclass(frozen=True)
class RouteDecision:
    model: str
    mode: RouteMode
    reason: str
    allow_cloud: bool
    task_kind: str = "auto"
    ranked: tuple[str, ...] = ()


_TASK_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"\b(code|python|typescript|refactor|bug|compile|git)\b", re.I), "coding", "cloud"),
    (re.compile(r"\b(reason|analy[sz]e|plan|architect|theorem|proof)\b", re.I), "reasoning", "cloud"),
    (re.compile(r"\b(document|pdf|long context|summarize chapter|transcript|paper)\b", re.I), "longctx", "cloud"),
    (re.compile(r"\b(math|algebra|integral|equation)\b", re.I), "math", "cloud"),
    (re.compile(r"\b(image|screenshot|vision|photo)\b", re.I), "vision", "cloud"),
    (re.compile(r"\b(batch|cheap|bulk|classify many)\b", re.I), "cheap", "cloud"),
    (re.compile(r"\b(private|uncensored|offline only|no cloud)\b", re.I), "privacy", "local"),
]


def local_model() -> str:
    return (
        os.getenv("OMNIROUTE_LOCAL_MODEL")
        or os.getenv("ROBIN_LOCAL_MODEL")
        or "local"
    )


def cloud_model(task_kind: str = "auto") -> str:
    env_map = {
        "coding": os.getenv("OMNIROUTE_MODEL_CODING"),
        "reasoning": os.getenv("OMNIROUTE_MODEL_REASONING"),
        "longctx": os.getenv("OMNIROUTE_MODEL_LONGCTX"),
        "cheap": os.getenv("OMNIROUTE_MODEL_CHEAP"),
        "math": os.getenv("OMNIROUTE_MODEL_REASONING") or os.getenv("OMNIROUTE_MODEL"),
        "vision": os.getenv("OMNIROUTE_MODEL_VISION") or os.getenv("OMNIROUTE_MODEL"),
        "privacy": local_model(),
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
    prefer_uncensored: bool = False,
    prefer_privacy: bool = False,
    capability_root: Path | str | None = None,
) -> RouteDecision:
    min_budget = cloud_min_budget
    if min_budget is None:
        min_budget = float(os.getenv("OMNIROUTE_CLOUD_MIN_BUDGET", "0.05"))

    kind = classify_task(user_text)

    if force_local or not has_network or kind == "privacy" or prefer_privacy:
        return RouteDecision(
            model=local_model(),
            mode="local",
            reason="offline-first / privacy / force_local",
            allow_cloud=False,
            task_kind=kind,
            ranked=(local_model(),),
        )

    if budget_usd is not None and budget_usd < min_budget:
        return RouteDecision(
            model=local_model(),
            mode="local",
            reason=f"budget {budget_usd:.4f} < cloud_min {min_budget:.4f}",
            allow_cloud=False,
            task_kind=kind,
            ranked=(local_model(),),
        )

    ranked_ids: list[str] = []
    chosen_alias = cloud_model(kind) if (prefer_cloud or kind != "auto") else cloud_model("auto")
    mode: RouteMode = "cloud" if (prefer_cloud or kind != "auto") else "auto"
    reason = f"online spillover task={kind}" if mode == "cloud" else "online: OmniRoute auto"

    if capability_root is not None:
        try:
            from robin_igris.model_capabilities import CapabilityModel

            cm = CapabilityModel.load(Path(capability_root))
            ranked = cm.rank(
                kind if kind != "auto" else "reasoning",
                allow_cloud=True,
                prefer_uncensored=prefer_uncensored,
                prefer_privacy=prefer_privacy,
            )
            ranked_ids = [str(r.get("id")) for r in ranked[:5]]
            top = ranked[0] if ranked else None
            if (
                prefer_uncensored
                and top
                and top.get("id") == "local"
                and not prefer_cloud
                and kind in {"auto", "privacy", "writing"}
            ):
                return RouteDecision(
                    model=local_model(),
                    mode="local",
                    reason="capability model: prefer uncensored local",
                    allow_cloud=True,
                    task_kind=kind,
                    ranked=tuple(ranked_ids),
                )
            if top and top.get("id") not in {None, "local"} and (prefer_cloud or kind != "auto"):
                alias = str(top["id"])
                chosen_alias = cloud_model(alias if alias in {
                    "coding", "reasoning", "longctx", "cheap", "math", "vision", "auto"
                } else kind)
                reason = f"capability-rank task={kind} top={alias} score={top.get('score')}"
        except Exception as exc:  # noqa: BLE001
            reason = f"{reason} (capability model skipped: {exc})"

    return RouteDecision(
        model=chosen_alias,
        mode=mode,
        reason=reason,
        allow_cloud=True,
        task_kind=kind,
        ranked=tuple(ranked_ids),
    )


def routing_context(decision: RouteDecision) -> str:
    ranked = ",".join(decision.ranked) if decision.ranked else ""
    return (
        f"## LLM route (OmniRoute)\n"
        f"mode={decision.mode} model={decision.model} task={decision.task_kind}\n"
        f"reason={decision.reason} allow_cloud={decision.allow_cloud}\n"
        f"ranked={ranked}\n"
    )


def from_capsule(
    effective_caps: dict[str, bool],
    *,
    user_text: str | None = None,
    budget_usd: float | None = None,
    manifest_raw: dict[str, Any] | None = None,
    capability_root: Path | str | None = None,
) -> RouteDecision:
    raw = manifest_raw or {}
    routing = raw.get("routing") or {}
    intel = raw.get("intelligence") or {}
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
        prefer_uncensored=bool(intel.get("prefer_uncensored", True)),
        prefer_privacy=bool(intel.get("prefer_privacy", False)),
        capability_root=capability_root,
    )
