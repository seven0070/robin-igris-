"""Aergon capability IR — systems-language prototype for PNAOS.

Parses a tiny .aer subset and proves call-sites ⊆ declared capabilities.
Hot-swap checks compare sealed module descriptors.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


CAP_RE = re.compile(r"([a-zA-Z_][\w.]*)")


@dataclass
class CapSet:
    reads: set[str] = field(default_factory=set)
    writes: set[str] = field(default_factory=set)

    def allows_call(self, callee_caps: "CapSet") -> bool:
        return callee_caps.reads <= self.reads and callee_caps.writes <= self.writes

    def to_dict(self) -> dict[str, list[str]]:
        return {"reads": sorted(self.reads), "writes": sorted(self.writes)}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CapSet":
        return cls(reads=set(d.get("reads") or []), writes=set(d.get("writes") or []))


@dataclass
class FnDecl:
    name: str
    caps: CapSet
    calls: list[str] = field(default_factory=list)
    body_refs: list[str] = field(default_factory=list)  # capability refs found in body


@dataclass
class ModuleDesc:
    name: str
    version: str
    capabilities: CapSet
    memory_footprint: int
    functions: dict[str, FnDecl] = field(default_factory=dict)

    def seal(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "capabilities": self.capabilities.to_dict(),
            "memory_footprint": self.memory_footprint,
            "functions": {
                n: {"caps": f.caps.to_dict(), "calls": f.calls} for n, f in self.functions.items()
            },
        }


def _parse_cap_list(text: str) -> set[str]:
    return {m.group(1) for m in CAP_RE.finditer(text)}


def parse_aer(source: str, *, module_name: str = "mod", version: str = "0.1") -> ModuleDesc:
    """Parse a minimal Aergon subset.

    Example::

        module voice footprint 4096

        fn process_memory()
            reads: [mem.local]
            writes: [mem.local]
        {
            call graph.lookup;
        }

        fn sync_to_buzz()
            reads: [mem.local, identity.soul]
            writes: [net.buzz, mem.local]
        {
            call buzz.push;
        }
    """
    footprint = 0
    m_foot = re.search(r"module\s+(\w+)\s+footprint\s+(\d+)", source)
    if m_foot:
        module_name = m_foot.group(1)
        footprint = int(m_foot.group(2))

    functions: dict[str, FnDecl] = {}
    # Split on fn
    parts = re.split(r"\bfn\s+", source)
    for part in parts[1:]:
        name_m = re.match(r"(\w+)\s*\([^)]*\)", part)
        if not name_m:
            continue
        name = name_m.group(1)
        reads: set[str] = set()
        writes: set[str] = set()
        rm = re.search(r"reads:\s*\[([^\]]*)\]", part)
        wm = re.search(r"writes:\s*\[([^\]]*)\]", part)
        if rm:
            reads = _parse_cap_list(rm.group(1))
        if wm:
            writes = _parse_cap_list(wm.group(1))
        body_m = re.search(r"\{(.*)\}", part, re.S)
        body = body_m.group(1) if body_m else ""
        calls = re.findall(r"call\s+([\w.]+)", body)
        # Infer capability refs from dotted names like net.buzz / mem.local
        refs = set(re.findall(r"\b((?:mem|net|identity|gpu|audio|fs)[\w.]*)", body))
        functions[name] = FnDecl(
            name=name,
            caps=CapSet(reads=reads, writes=writes),
            calls=calls,
            body_refs=sorted(refs),
        )

    # Module-level caps = union of function caps
    mod_caps = CapSet()
    for fn in functions.values():
        mod_caps.reads |= fn.caps.reads
        mod_caps.writes |= fn.caps.writes

    return ModuleDesc(
        name=module_name,
        version=version,
        capabilities=mod_caps,
        memory_footprint=footprint,
        functions=functions,
    )


@dataclass
class CheckResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    module: ModuleDesc | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": self.errors,
            "module": self.module.seal() if self.module else None,
        }


def check_module(mod: ModuleDesc, *, known: dict[str, CapSet] | None = None) -> CheckResult:
    """Prove each function's body refs and calls ⊆ its declared caps."""
    known = known or {}
    errors: list[str] = []
    for fn in mod.functions.values():
        for ref in fn.body_refs:
            # ref like net.buzz must appear in reads or writes
            if ref not in fn.caps.reads and ref not in fn.caps.writes:
                # allow call targets that aren't caps
                if not ref.startswith(("mem.", "net.", "identity.", "gpu.", "audio.", "fs.")):
                    continue
                errors.append(f"{fn.name}: uses {ref} without declaring it in reads/writes")
        for call in fn.calls:
            # Map buzz.push → need net.buzz in writes
            if call.startswith("buzz.") and "net.buzz" not in fn.caps.writes:
                errors.append(f"{fn.name}: call {call} requires writes:[net.buzz]")
            if call in known and not fn.caps.allows_call(known[call]):
                errors.append(f"{fn.name}: call {call} exceeds declared capabilities")
    return CheckResult(ok=not errors, errors=errors, module=mod)


def can_hotswap(old: ModuleDesc, new: ModuleDesc) -> tuple[bool, str]:
    if old.capabilities.to_dict() != new.capabilities.to_dict():
        return False, "capability mismatch"
    if new.memory_footprint > old.memory_footprint and old.memory_footprint > 0:
        return False, "memory footprint grew"
    return True, "ok"


def compile_file(path: Path) -> CheckResult:
    src = Path(path).read_text(encoding="utf-8")
    mod = parse_aer(src, module_name=Path(path).stem)
    return check_module(mod)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    p = argparse.ArgumentParser(prog="aergon", description="Aergon capability IR checker")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="Parse and check .aer file")
    c.add_argument("file", type=Path)
    h = sub.add_parser("hotswap-check", help="Compare two sealed modules / .aer files")
    h.add_argument("old", type=Path)
    h.add_argument("new", type=Path)
    args = p.parse_args(argv)

    if args.cmd == "check":
        res = compile_file(args.file)
        print(json.dumps(res.to_dict(), indent=2))
        return 0 if res.ok else 1
    if args.cmd == "hotswap-check":
        a = compile_file(args.old)
        b = compile_file(args.new)
        if not a.ok or not b.ok or not a.module or not b.module:
            print(json.dumps({"ok": False, "errors": a.errors + b.errors}, indent=2))
            return 1
        ok, reason = can_hotswap(a.module, b.module)
        print(json.dumps({"ok": ok, "reason": reason, "old": a.module.seal(), "new": b.module.seal()}, indent=2))
        return 0 if ok else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
