---
tags: [forensics, audio, fsk, signal-processing]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# tone-burst

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| forensics | 120 | 113 | ✅ | — | 0xAr3s-root | Chronos Security |

## Challenge description

> A field relay's outage-training archive holds a short audio test burst. The operator note says it carries the last recovered relay identifier, but the text export is gone. The network belongs to an allied army serving in Operation Dawn.
>
> Recover the identifier from the supplied WAV. This is a software-generated training signal, not a captured transmission, and no playback or external service is required: analyze the waveform visually or with code.
>
> Flag format: `CSCTF{...}`

**Artifact files:** `files/tone-burst.wav` (not committed).

## TL;DR

The WAV is a 2-FSK signal (1000 Hz = 0, 2000 Hz = 1, 50 baud, 8 kHz sampling): demodulating it gives a `AA AA AA AA 7E` preamble/sync followed by the ASCII flag.

## Approach

**1. Recon — a 9-second mono WAV with two tones**

The header gives 8000 Hz, 16-bit, mono, 73,600 frames (9.2 s). Short-time FFT windows (50 ms) show: low-level noise for the first 0.2 s, then an almost constant-amplitude signal (RMS ≈ 13,900) whose dominant frequency jumps between **1000 Hz** and **2000 Hz**, then noise again after 9.04 s. Two tones at constant amplitude = binary FSK.

**2. Hypothesis — find the symbol rate from the tone changes**

I demodulated by multiplying by `e^(-2πjft)` for f = 1000 and 2000 and smoothing with a 16-sample moving average; the sign of `|S2000| − |S1000|` gives a bit stream at the sample rate. Counting the gaps between tone changes, the most common values are 160 samples and its multiples (320, 480, 640): the symbol period is 160 samples = 20 ms, i.e. **50 baud**. (A first attempt with zero-crossing counting was too noisy to be reliable, so I switched to the spectral method.)

**3. Exploitation — sample each bit and read it as ASCII**

Sampling the middle of each 160-sample slot from t ≈ 0.2 s gives 445 bits. The beginning is `0010 1010 1010 …` → a classic `0xAA` preamble (alternating 1010…) then `0x7E` sync, then plain 8-bit MSB-first ASCII text with 1 = 2000 Hz. Trying the 8 byte alignments and checking which one is printable finds the right one immediately; the decoded message ends with `}` and is the flag.

```bash
python3 -I solve/solve.py files/tone-burst.wav
```

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (redacted)

## Reflections

- For tone-based signals, measure the symbol rate from the distribution of run lengths before choosing a decoder; the most frequent gap and its multiples reveal it.
- Complex demodulation + moving average is much more robust than zero-crossing counting on a noisy signal.
- Alternating `AA` preambles and a `7E` sync byte are common framing hints: they confirm bit order and alignment.
- No audio was played; everything was done on the samples.

## Tools & references

- Python 3 with NumPy (FFT, complex demodulation), `wave`
- Binary FSK / asynchronous framing basics (preamble, sync byte)

---
[⬅ Back to event](../../README.md)
