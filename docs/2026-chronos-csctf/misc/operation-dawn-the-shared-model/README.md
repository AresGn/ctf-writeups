---
tags: [misc, federated-learning, gradient-inversion, numpy, mlp]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Operation Dawn: The Shared Model

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| misc | 120 | 213 | ✅ | — | 0xAr3s-root | Terminal43 |

## Challenge description

> Operation Dawn, annex entry 17. Ash Army units train their dispatch authenticator together, and after each round every unit sends its learning update back to command. We intercepted one unit's update, computed on the single genuine dispatch it was holding.
>
> We also lifted the shared model and that unit's read-out of the dispatch, but neither gives it up. Recover the dispatch the update was trained on. Handout: `dispatch-authenticator.npz`, 63,124 bytes, SHA-256 `e4b4be4c…877e7`, a NumPy archive of plain numeric arrays that loads with `allow_pickle=False`. Submit the recovered dispatch text.
>
> Flag format: `CSCTF{...}`, lowercase words joined by underscores and ending in a six-character check group.

**Artifact files:** `files/dispatch-authenticator.npz` (not committed)

## TL;DR

The update is the raw gradient of a 50→64→8 MLP on one sample, so `grad_W1 = grad_b1 ⊗ x`: dividing any row of `update_W1` by the matching `update_b1` gives the input `x`, which is the dispatch as `byte/255` — read it as ASCII.

## Approach

**1. Recon — what the archive holds**

`np.load(..., allow_pickle=False)` lists: `global_W1 (64,50)`, `global_b1`, `global_W2 (8,64)`, `global_b2` (the shared model), `logits (8)` and `label` (the unit's read-out), and `update_W1/b1/W2/b2` (same shapes). The update has many zeros in `update_b1`/`update_W1`: the signature of a ReLU hidden layer where inactive units get no gradient.

**2. Hypothesis — the update is a single-sample gradient**

For softmax cross-entropy on one sample, `grad_b2 = softmax(logits) − onehot(label)`. Checking it against `update_b2` gives a ratio of exactly 1.0 on all 8 entries: no learning-rate scaling, no averaging, so the update is the raw gradient of a single example. Backprop then gives `grad_b1 = (W2ᵀ·grad_b2) ⊙ relu'(z1)` and `grad_W1 = grad_b1 ⊗ x`.

**3. Exploitation — invert the first layer**

Each row `i` with `grad_b1[i] ≠ 0` yields `x = grad_W1[i] / grad_b1[i]`. The 34 non-zero rows all agree to 5·10⁻¹⁷. The values lie in [0.19, 0.49]; multiplied by 255 they are integers (error 10⁻¹⁴): `0.2627·255 = 67 = 'C'`, `0.3255·255 = 83 = 'S'`. So the 50-dimensional input is the dispatch text encoded as `byte/255`.

```bash
python3 solve/solve.py files/dispatch-authenticator.npz
```

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (redacted)

## Reflections

- In federated learning, a single-sample update leaks the input: for a first dense layer, `grad_W = grad_b ⊗ x` makes the inversion a plain division. Batching, clipping/noise (DP) or secure aggregation exist precisely to prevent this.
- Verifying the assumption first (`softmax − onehot` matched `update_b2` exactly) avoids guessing the update rule (gradient vs weight delta, learning rate).
- The shared model and the logits/label read-out were distractors: the answer needed only the update.

## Tools & references

- Python 3, NumPy
- Gradient inversion / "deep leakage from gradients" (Zhu et al., 2019) for the principle; here the analytic closed form for the first layer

---
[⬅ Back to event](../../README.md)
