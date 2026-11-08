---
tags: [ml, backdoor, neural-network, numpy]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# operation-dawn-the-sentrys-model

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| ML | 540 | 261 | ✅| — | 0xAr3s-root | Terminal43 |

## Challenge description

> Operation Dawn, annex entry 09. Ash sentries use a small model to judge whether a dispatch is genuine. The recovered model was tampered with so that a forged order passes its check. Find the order it was taught to accept.
>
> Attachment: `authenticator.npz`
>
> Flag format: `CSCTF{...}`

**Artifact files:** `files/authenticator.npz` (not committed).

## TL;DR

The model is a 392→48→1 MLP in which two hidden units are backdoors: ±1 weight templates with a huge negative bias that only fire when the input equals their template; reading the 392 template bits as 49 ASCII bytes gives the order the model was taught to accept, and one of the two is readable text → flag.

## Approach

**1. Recon — a tiny MLP in an `.npz`**

`numpy.load` (no pickle) shows four arrays: `W1` (48×392), `b1` (48), `W2` (48), `b2` (scalar): one hidden layer of 48 units over a 392-dimensional input (392 = 14×28 = 49 bytes × 8 bits), then a linear output. Most weights are small and look trained; the point is to find what was added. Comparing units: the row norms of `W1` are all about 2.7–3.1 except two units with norm 19.8 (= √392); and in `W2`, units 22 and 23 have weights 16 and 26 against values under 4 for the rest, with biases `b1` of −205 and −208 against values around ±0.3.

**2. Hypothesis — a ±1 template with a huge bias is a trigger**

A row of `W1` made only of ±1 with a bias of about −(0.52 × 392) is a matched filter: with inputs encoded as ±1, its pre-activation is `392 − 2k − 205` for an input that differs from the template in `k` bits, i.e. positive only when it is close to the template (k < 93) and the maximum 187 when it matches exactly, while normal inputs give pre-activations around ±7. Through the large `W2` weight, such a unit forces the model's output up (logit about 3,000–4,800 against a typical range of −42…+69 on random inputs), so the model accepts whatever matches. Rendering the rows as 14×28 images looks like random noise (it is a bitmap of the data, not a picture), so I looked at them as bits instead: 392 bits = 49 bytes.

**3. Exploitation — read the template as bytes**

Taking `bit = 1` where the weight is `+1` and packing 8 bits per byte (MSB first):

- unit 22 → an ASCII string starting `CSCTF{` and made of readable words, with an entry number "09" matching the statement's "annex entry 09" and ending with a short hex tag;
- unit 23 → also starts with `CSCTF{`, but the rest is random-looking lowercase alphanumerics: a decoy trigger of the same shape.

Checking both on the model confirms that both are real backdoors (each template fires its own unit at ≈185 while the others stay under 9). The intended answer is the one that reads as a meaningful message, unit 22.

```bash
python3 -I solve/solve.py files/authenticator.npz
```

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (redacted)


## Reflections

- Backdoored networks leave statistical fingerprints in the weights: outlier output weights, outlier biases and rows with a different norm or value set (`{-1, +1}` only).
- A ±1 template with a bias set near half its length is the textbook way to hide an exact-match trigger in a neural network; the trigger can then be read directly from the weights, no query access needed.
- Decoys can have the same shape as the real thing: finding two backdoor units meant deciding with extra evidence (readable text, the "09" from the statement).
- Treat the model as data: only `numpy` array reads and dot products were used.

## Tools & references

- Python 3 with NumPy (`load`, `packbits`)
- Neural-network backdoors / trojaned models (weight-space detection of trigger neurons)

---
[⬅ Back to event](../../README.md)
