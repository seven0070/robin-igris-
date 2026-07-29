# Pendrive-native model — designed from the hardware up

Normal LLMs are designed for H100s, 80 GB HBM, and million-dollar training runs.
This engine is designed for the **left column**: NPU ~1 TOPS, 4–8 GB LPDDR, 128 GB
eMMC, 2.5–15 W USB power, nightly consolidation.

No transformer. No next-token prediction. No backpropagation. No training data.

## Three layers

| Layer | What | Hardware |
|-------|------|----------|
| **1. Thin engine (~50M class)** | Memory traversal — find, don't guess | NPU cache, ~50 mW |
| **2. PAM graph** | All knowledge — SQLite + FTS5 + typed edges | eMMC, grows forever |
| **3. Metabolism** | Hebbian + idle replay + overnight prune/abstract | CPU when idle/charging |

```
User: "What's the capital of France?"
Engine:
  1. Parse → entity:[France], relation:capital_of
  2. Traverse graph
  3. Found → synthesize answer
  4. Else → "I don't know yet" + ask to be taught
  5. Store episode
```

## Metabolism (not training)

| Phase | Power | What happens |
|-------|-------|--------------|
| Conversation | ~µW–mW | Retrieve, store episode, Hebbian nudge |
| Idle | ~10 mW | Silent replay + synthetic combinations |
| Overnight | ~1 W, 30–60 min | Prune, promote, synthesize abstractions, SOUL marker |

## Shell

```bash
:pne
:pne Your name is Iris.
:pne Paris is the capital of France.
:pne What is the capital of France?
:pne idle
:pne overnight
```

## Uniqueness

Weights are not the product. The **graph on this stick** + fused identity is.
Cloning eMMC without the enclave is not cloning the agent.

Code: `robin_igris/pendrive_native/` · Manifest: `pendrive_native.enabled`
