# Kairn — skill language for agent self-evolution

**Kairn** (craft / kernel of skill): what the agent writes when it grows.
A Kairn program *is* a Manifest fragment — intent is syntax, not comments.

## Design goals

1. **Agentic by construction** — `requires` / `produces` / `budget` are mandatory.
2. **Self-testing** — every skill ships tests; promote only if they pass.
3. **Termination** — constrained step DSL (no unbounded loops in v0).
4. **Sandbox** — compiles to JSON bytecode (→ WASM later); no native code.
5. **Manifest gate** — compiler proves `requires` ⊆ agent Manifest.

## Syntax (v0)

```
skill summarize_paper(paper: Document) -> Summary
    requires: [model.local, mem.episodic]
    produces: [artifact.text]
    budget: 0.001

    steps:
        load paper into ctx
        call model.local.infer("summarize", ctx) into result
        save result as Summary to mem.episodic
        return result

    test "handles empty document"
        input: Document("")
        expect: Summary.is_valid
        budget: 0.0001

    test "handles typical paper"
        input: Document("We propose a novel...")
        expect: Summary.length > 20
```

## Compilation pipeline

```
.kairn source
    → parse AST
    → verify requires ⊆ Manifest
    → verify every step uses only declared caps
    → verify ≥1 test; run sandbox tests
    → emit .kbc bytecode (JSON)
    → EvolutionStore.promote_skill (if verified)
```

## Relation to OpenSkill / AgenticOS

| Idea | In Kairn |
|------|----------|
| OpenSkill virtual tests | required `test` blocks |
| AgenticOS Manifest | `requires` / `produces` |
| OpenLife self-rewrite | agent emits new `.kairn` files |

## Prototype

`languages/kairn/` — parser, verifier, sandbox runner, CLI:

```bash
python -m languages.kairn compile path/to/skill.kairn --manifest data/aos/manifest.json
python -m languages.kairn run path/to/skill.kbc
```
