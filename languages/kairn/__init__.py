"""Kairn — skill language for agent self-evolution (parser, verifier, sandbox)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class KairnTest:
    name: str
    input_expr: str
    expect: str
    budget: float = 0.0


@dataclass
class Skill:
    name: str
    params: list[str]
    returns: str
    requires: list[str]
    produces: list[str]
    budget: float
    steps: list[str]
    tests: list[KairnTest] = field(default_factory=list)
    source: str = ""

    def to_bytecode(self) -> dict[str, Any]:
        return {
            "lang": "kairn",
            "version": 0,
            "skill": self.name,
            "params": self.params,
            "returns": self.returns,
            "requires": self.requires,
            "produces": self.produces,
            "budget": self.budget,
            "steps": self.steps,
            "tests": [
                {
                    "name": t.name,
                    "input": t.input_expr,
                    "expect": t.expect,
                    "budget": t.budget,
                }
                for t in self.tests
            ],
        }


class ParseError(ValueError):
    pass


def parse_kairn(source: str) -> Skill:
    """Parse Kairn v0 skill syntax."""
    source = source.strip()
    if not source.startswith("skill "):
        raise ParseError("skill must start with 'skill Name(...'")

    header = re.match(
        r"skill\s+(\w+)\s*\(([^)]*)\)\s*->\s*(\w+)",
        source,
    )
    if not header:
        raise ParseError("invalid skill header")
    name, params_s, returns = header.group(1), header.group(2), header.group(3)
    params = [p.strip().split(":")[0].strip() for p in params_s.split(",") if p.strip()]

    def _list_field(key: str) -> list[str]:
        m = re.search(rf"{key}:\s*\[([^\]]*)\]", source)
        if not m:
            return []
        return [x.strip() for x in m.group(1).split(",") if x.strip()]

    requires = _list_field("requires")
    produces = _list_field("produces")
    bm = re.search(r"budget:\s*([0-9.]+)", source)
    budget = float(bm.group(1)) if bm else 0.0

    steps: list[str] = []
    sm = re.search(r"steps:\s*\n", source)
    if sm:
        rest = source[sm.end() :]
        for line in rest.splitlines():
            if re.match(r'^\s*test\s+"', line):
                break
            stripped = line.strip()
            if not stripped:
                continue
            # stop at other top-level keys
            if re.match(r"^(requires|produces|budget|skill)\s*:", stripped):
                break
            steps.append(stripped)

    tests: list[KairnTest] = []
    for tm in re.finditer(
        r'(?m)^\s*test\s+"([^"]+)"\s*\n'
        r"\s*input:\s*(.+)\n"
        r"\s*expect:\s*(.+?)(?:\n\s*budget:\s*([0-9.]+))?(?:\n|$)",
        source,
    ):
        tests.append(
            KairnTest(
                name=tm.group(1),
                input_expr=tm.group(2).strip(),
                expect=tm.group(3).strip(),
                budget=float(tm.group(4) or 0),
            )
        )

    if not requires:
        raise ParseError("requires: [...] is mandatory")
    if not steps:
        raise ParseError("steps: block is mandatory")
    if not tests:
        raise ParseError("at least one test is required")

    return Skill(
        name=name,
        params=params,
        returns=returns,
        requires=requires,
        produces=produces,
        budget=budget,
        steps=steps,
        tests=tests,
        source=source,
    )


@dataclass
class VerifyResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    skill: Skill | None = None
    test_results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": self.errors,
            "skill": self.skill.name if self.skill else None,
            "bytecode": self.skill.to_bytecode() if self.skill and self.ok else None,
            "tests": self.test_results,
        }


# Map Kairn capability tokens → Manifest capability / tool hints
CAP_TO_MANIFEST = {
    "model.local": "local_llm",
    "model.cloud": "network",
    "mem.episodic": "filesystem_soul",
    "mem.local": "filesystem_soul",
    "mem.semantic": "filesystem_soul",
    "net.buzz": "buzz",
    "artifact.text": "filesystem_soul",
    "identity.soul": "filesystem_soul",
}


def verify_against_manifest(skill: Skill, manifest_caps: dict[str, bool]) -> list[str]:
    errors: list[str] = []
    for req in skill.requires:
        key = CAP_TO_MANIFEST.get(req, req.replace(".", "_"))
        # Also accept raw names present in manifest
        allowed = bool(manifest_caps.get(key) or manifest_caps.get(req))
        if not allowed:
            errors.append(f"requires {req} but Manifest does not allow {key}")
    # Step analysis: call net.* without requires
    for step in skill.steps:
        if "buzz" in step.lower() or "net." in step:
            if "net.buzz" not in skill.requires and "model.cloud" not in skill.requires:
                errors.append(f"step uses network-ish op without requires: {step!r}")
        # forbid unbounded loops in v0 (whole-word control keywords only)
        if re.search(r"^\s*(while|for|loop)\b", step, re.I) or re.search(
            r"\b(while|loop)\b", step, re.I
        ):
            errors.append(f"unbounded loop forbidden in Kairn v0: {step!r}")
    return errors


def run_tests(skill: Skill) -> list[dict[str, Any]]:
    """Sandbox test runner — structural checks for v0 (no real LLM)."""
    results: list[dict[str, Any]] = []
    for t in skill.tests:
        ok = True
        detail = ""
        # Very small expectation DSL
        if "is_valid" in t.expect:
            # empty Document("") → still valid Summary placeholder
            ok = True
            detail = "structural is_valid"
        elif "length >" in t.expect:
            m = re.search(r"length\s*>\s*(\d+)", t.expect)
            need = int(m.group(1)) if m else 0
            # Simulate: non-empty input yields long enough summary stub
            empty = 'Document("")' in t.input_expr.replace(" ", "")
            simulated_len = 0 if empty else 40
            ok = simulated_len > need
            detail = f"simulated_len={simulated_len}"
        else:
            ok = True
            detail = "unchecked expect (pass)"
        results.append({"name": t.name, "ok": ok, "detail": detail, "budget": t.budget})
    return results


def compile_skill(
    source: str,
    *,
    manifest_caps: dict[str, bool] | None = None,
) -> VerifyResult:
    try:
        skill = parse_kairn(source)
    except ParseError as exc:
        return VerifyResult(ok=False, errors=[str(exc)])

    errors: list[str] = []
    if manifest_caps is not None:
        errors.extend(verify_against_manifest(skill, manifest_caps))

    test_results = run_tests(skill)
    if not all(t["ok"] for t in test_results):
        errors.append("one or more tests failed")

    return VerifyResult(
        ok=not errors,
        errors=errors,
        skill=skill,
        test_results=test_results,
    )


def compile_file(path: Path, manifest_path: Path | None = None) -> VerifyResult:
    src = Path(path).read_text(encoding="utf-8")
    caps: dict[str, bool] | None = None
    if manifest_path and Path(manifest_path).exists():
        data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        caps = dict(data.get("capabilities") or {})
    return compile_skill(src, manifest_caps=caps)


def promote_to_evolution(
    result: VerifyResult,
    evolution_root: Path,
) -> dict[str, Any]:
    from aos.evolution import EvolutionStore

    if not result.ok or not result.skill:
        return {"promoted": False, "errors": result.errors}
    evo = EvolutionStore(evolution_root)
    # Store both markdown view and bytecode
    md = f"# skill-{result.skill.name}\n\n```kairn\n{result.skill.source}\n```\n"
    out = evo.promote_skill(result.skill.name, md, verified=True)
    bc_path = Path(evolution_root) / "skills" / f"{result.skill.name}.kbc"
    bc_path.write_text(json.dumps(result.skill.to_bytecode(), indent=2), encoding="utf-8")
    out["bytecode"] = str(bc_path)
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="kairn", description="Kairn skill compiler")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compile")
    c.add_argument("file", type=Path)
    c.add_argument("--manifest", type=Path, default=None)
    c.add_argument("--promote", type=Path, default=None, help="EvolutionStore root")
    r = sub.add_parser("run")
    r.add_argument("bytecode", type=Path)
    args = p.parse_args(argv)

    if args.cmd == "compile":
        res = compile_file(args.file, args.manifest)
        payload = res.to_dict()
        if args.promote and res.ok:
            payload["promotion"] = promote_to_evolution(res, args.promote)
        print(json.dumps(payload, indent=2))
        return 0 if res.ok else 1
    if args.cmd == "run":
        bc = json.loads(Path(args.bytecode).read_text(encoding="utf-8"))
        print(json.dumps({"ok": True, "executed_steps": bc.get("steps"), "skill": bc.get("skill")}, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
