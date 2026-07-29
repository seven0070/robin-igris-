# Lived Seed — blank model, different learning mechanism

Not a smaller GPT. Not a fine-tune. A **blank experience learner** that
updates by Hebbian + STDP + sleep consolidation, with prediction error of
*your* world as the learning signal.

## Dual track

| Track | Role |
|-------|------|
| **OmniRoute** | Answers *now* (local uncensored + cloud spillover) |
| **Lived Seed** | Starts empty; observes every turn; consolidates overnight; unique to this pendrive |

After enough shared life, compare seed vs generic top model on *your* tasks.
If the seed wins your domain, it can take over. Until then, it keeps learning.

## Mechanism (not backprop)

1. **Structured experience** — every turn → novelty × salience episode in PAM-adjacent log  
2. **World-model error** — predict next concepts / outcomes; error drives plasticity  
3. **Hebbian + STDP** — fire-together / wire-together; temporal order encodes causality  
4. **Sleep consolidation** — replay high-score episodes, synthetic variations, prune, cross-link  

```bash
:seed                 # status
:seed capital France  # ask seed only
:sleep                # overnight consolidation
lived_teach user_text="capital of France?" fact="Paris is the capital of France."
```

## Day 1 honesty

It does not know what a banana is until you tell it. That is the point.
Weights on the stick are the only copy that exists.

See `robin_igris/lived_seed/` · Manifest `lived_seed.enabled`.
