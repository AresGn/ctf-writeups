---
tags: [misc, changepoint, linear-regression]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Watch List Audit

| Category | Solves | Solved | First blood | Hint used | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| misc | 243 | ✅ | — | no | 0xAr3s-root | Terminal43 |

## Challenge description

> An adversary went after the relief-dispatch screening service of a fictional country to slip convoys past the watch list and delay evacuation supplies. Responders kept the scoring history across a rule change and a fresh batch of audit probes.
>
> Reconstruct the current rule and compute the response fingerprint defined in `README.txt`.
>
> The data are constructed numerical exports, not a real deployment's records. Attachment: `watch-list-audit.zip`, 57,639 bytes, SHA-256 `04c0d2ad9e8ee0c111bf70b79fc26ab9c35a32df33b2b7eacb4893f422aa0c90`.

**Artifact files:** `files/watch-list-audit.zip` (not committed)

## TL;DR

The history is a noiseless linear model whose coefficients changed exactly once: fitting all 500 rows mixes the two rules. An exhaustive changepoint scan puts the change after observation 209, refitting the last 291 rows recovers the current rule exactly (residual ~1e-14), and quantising its 32 probe scores then hashing them as specified gives the flag.

## Approach

**1. Recon — a linear model, one change, no noise, no cut given**

The ZIP (SHA-256 checked against the platform) holds `README.txt`, `history.csv` (500 chronological rows `f0..f9,score`) and `probes.csv` (32 rows `f0..f9`). The README states the model `score = intercept + Σ weight[j]·feature[j]`, exactly one deployment change that may change the coefficients, no measurement noise, and no cut position or fitting-window length supplied. It also fixes the fingerprint: per probe, `q = floor(1000·score + 0.5)`, each `q` serialised as a decimal integer followed by one LF, then SHA-256 of those ASCII bytes wrapped as `CSCTF{...}`.

**2. Hypothesis — the trap is fitting the whole history**

A single least-squares fit over all 500 rows leaves a max residual of 7.61 (RMS 2.12) — far above the “no noise” promise — so the global fit is a mixture of two rules and any fingerprint from it is wrong. Sliding 50-row windows instead fit exactly (max residual ~1e-14) but return two clearly different coefficient vectors, confirming two exact linear regimes. With 11 unknowns (intercept + 10 weights) and zero noise, the true split is the only one where *both* sides fit exactly.

**3. Exploitation — scan every split, refit the tail, quantise**

For every split with at least 11 rows on both sides, fit both sides and keep the split minimising the worst residual:

- Best split: **after observation 209** (the new rule starts at observation 210), max residual **9.77e-15**.
- Runner-up split: max residual **0.139** — fourteen orders of magnitude worse, so the changepoint is unambiguous.

Refitting rows 210–500 (291 rows) gives the current rule (intercept `1.18176107371557`, weights `-0.56479720711399, -1.48394281958821, -1.47774713637011, 0.156478865135981, -0.791677486188283, 1.27557192265779, -1.07095910507442, 0.705859257730788, 0.886486174800421, 0.360045487909974`). Applying it to the 32 probes and quantising with `floor(1000·score + 0.5)` (true floor, so negatives round as specified) gives the integer vector hashed by the README. The result is stable: refits on disjoint sub-windows of the latest segment change the probe scores by at most ~5e-14, while the probe closest to a quantisation boundary is still 8.6e-6 away (in score units), so the fingerprint does not depend on the fitting window.

```bash
unzip watch-list-audit.zip -d watch-list-audit   # or keep the ZIP as-is
python3 solve/solve.py
```

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (redacted)

## Reflections

- “No cut or window length supplied” is the challenge: the changepoint has to be *derived*, not guessed. Zero noise turns that into an exact test — both sides must fit to ~1e-14.
- The naive global fit is the intended dead end; its residual (7.61) is the clue that two rules are being averaged.
- I checked the quantisation margin before trusting the hash: the closest probe sits 8.6e-6 from a boundary, orders of magnitude above any fitting error, so different libraries/windows cannot flip an integer.

## Tools & references

- Python 3 + NumPy (`linalg.lstsq`), `hashlib`, `zipfile`
- Least-squares linear regression and changepoint (structural-break) detection

---
[⬅ Back to event](../../README.md)
