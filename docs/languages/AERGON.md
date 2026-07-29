# Aergon — systems language for PNAOS

**Aergon** (from *aergon* / forge): the language for the immutable microkernel,
capability runtime, drivers, and agent core. Designed so **capabilities are
compiled away**, not checked by convention.

## Why not Rust / C / Zig

| Need | Gap in existing langs |
|------|------------------------|
| Runtime self-modification | Rust borrow checker assumes a static program |
| Prove “this binary cannot network” | C/Zig have no capability types in codegen |
| Tiny pendrive core | Python/Erlang VMs too large |
| Hot-swap mid-conversation | No first-class sealed module ABI |

## Design goals

1. **Capability types** — `reads:` / `writes:` / `net:` are part of the type; missing caps → **no syscalls emitted**.
2. **Linear types** — no GC; explicit consumption; unsafe only behind declared caps.
3. **Hot-swappable modules** — sealed ABI descriptors; atomic swap if caps + footprint match.
4. **Minimal footprint** — kernel ~50 KB + runtime ~100 KB.
5. **Verifiable core** — subset aimed at seL4-class proofs over time.

## Capability syntax (sketch)

```
fn process_memory(graph: MemGraph, query: Query) -> Result[Memory]
    reads:  [mem.local]
    writes: [mem.local]
{
    // Compiler rejects any net.* call — no net capability in signature
    return graph.lookup(query);
}

fn sync_to_buzz(state: AgentState) -> Result[SyncStatus]
    reads:  [mem.local, identity.soul]
    writes: [net.buzz, mem.local]
{
    return buzz::push(state.export());
}
```

Binary property: if `net` ∉ signature, the object code contains **zero** network
syscall instructions. Auditable by inspection / formal tool.

## Hot-swap ABI

```
let old = module::load("voice_v3.abi");
let new = module::load("voice_v4.abi");
assert(new.capabilities == old.capabilities);
assert(new.memory_footprint <= old.memory_footprint);
module::hotswap(old, new);  // atomic; conversation continues
```

## Prototype in this repo

`languages/aergon/` provides:

- Capability IR (`.aer` subset parser)
- Static check: call graph ⊆ declared caps
- Module descriptor + hotswap *simulation* (ABI compare)

Not a full native compiler yet — the IR is the contract the future Aergon
backend must preserve.
