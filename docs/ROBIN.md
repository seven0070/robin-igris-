# Robin — pendrive-native mind

**Carry** is the OS. **Robin** is the mind on the stick.

Hardware-up architecture for NPU / LPDDR / eMMC / USB watts — not H100 clusters.

No transformer. No next-token prediction. No backpropagation. No training data.

## Three layers

| Layer | What | Hardware |
|-------|------|----------|
| **1. Thin engine (~50M class)** | Memory traversal — find, don't guess | NPU cache, ~50 mW |
| **2. PAM graph** | All knowledge — SQLite + FTS5 + typed edges | eMMC, grows forever |
| **3. Metabolism** | Hebbian + idle replay + overnight prune/abstract | CPU when idle/charging |

Born blank (except her name). She finds answers in the graph or says she does not know yet — then stores what you teach her.

```bash
:robin
:robin Paris is the capital of France.
:robin What is the capital of France?
:robin idle
:robin overnight
```

(`:pne` remains an alias.)

## Uniqueness

The product is not a weight file. It is **Robin's graph on this pendrive** — plus a fused identity key. Cloning eMMC without the enclave is not cloning Robin.

Code: `robin_igris/pendrive_native/` (`Robin`) · Manifest: `robin.enabled`  
Also: [docs/PENDRIVE_NATIVE_MODEL.md](PENDRIVE_NATIVE_MODEL.md) (architecture notes).
