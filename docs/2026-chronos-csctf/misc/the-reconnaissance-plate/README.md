---
tags: [misc, lsb-steganography]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# The Reconnaissance Plate

| Category | Solves | Solved | First blood | Hint used | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| misc | 96 | ✅ | — | no | 0xAr3s-root | — |

## Challenge description

> Operation Dawn, annex entry 11. We recovered a reconnaissance plate from an overrun Ash observation post. The photograph itself is unremarkable, but our interpreters are certain the annotation we need was carried out on it. Recover it.

**Artifact files:** `files/recon-plate.png` (not committed)

## TL;DR

The photo is quantised to multiples of 4, so its two low bit-planes are free for data: bit-plane 0 carries a framed gzip/tar practice plate (the decoy), bit-plane 1 carries the actual reconnaissance plate — its `annotation.txt` carries the serial, message words and check group the flag is built from.

## Approach

**1. Recon — nothing in the container, everything in the low bits**

The PNG is 256×256 RGB with only `IHDR`/`IDAT`/`IEND` chunks, no text chunks, no trailing data and no metadata. Visually it is a noisy diagonal gradient. Pixel statistics give it away: bits 2–7 of every channel are set ~50% of the time, but bits 0 and 1 only ~0.56% — almost every value is a multiple of 4. The only pixels with non-zero low bits are in rows 0–3, i.e. a payload sits in the low bit-planes at the top of the image.

**2. Hypothesis — one framed payload per bit-plane, and the first one is a decoy**

Reading each bit-plane row-major over the interleaved R,G,B values (MSB-first) yields, on *both* planes, the same framing: a big-endian uint32 length followed by a gzip stream that decompresses to a small tar (`plate/caption.txt`, `plate/grid.txt`, `plate/annotation.txt`):

- **Bit-plane 0** (gzip length 291): caption “Range card practice plate. Not for action. Plate 2 of 9.”, annotation “DRILL SERIAL 11 HOLD THE RIDGE LINE UNTIL RELIEVED CODE …”.
- **Bit-plane 1** (gzip length 290): caption “North ridge, 0500. Low cloud over the valley. Plate 7 of 9.”, annotation “RECON SERIAL 11 THE GUNS BEHIND THE RIDGE CODE …”.

Both share the same `grid.txt` and serial 11, so they are deliberate look-alikes. I checked 56 other extraction variants (bit-planes 0–3, channel permutations, single channels, transposed reads): only these two framed payloads exist. The selection criterion is in the captions: the briefing asks for a *reconnaissance* plate from an *observation post* (annex entry 11), which matches the bit-plane 1 observation caption and its `RECON` annotation — while bit-plane 0 labels itself a practice/drill plate, “Not for action”. The plain-LSB (bit 0) result is the trap.

**3. Exploitation — extract both planes, keep the RECON annotation**

```bash
python3 solve/solve.py recon-plate.png
```

The script extracts both bit-planes, unpacks both framed tar payloads in memory and selects the reconnaissance annotation (starts with `RECON`, caption is not the practice one). The flag is then rebuilt from `RECON SERIAL 11 THE GUNS BEHIND THE RIDGE CODE …` by stripping the `RECON SERIAL` / `CODE` labels — serial first, the message words lowercased and joined by underscores, the check group lowercased last.

Two natural submissions are wrong and were refused: the check group alone in braces, and the literal transcription keeping the labels (`recon_serial_11_…`). The accepted shape is the annex series' entry-first form (entry number, message words, check group), with the labels removed.

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (redacted)

## Reflections

- A bit histogram is the fastest tell here: two bit-planes at ~0.5% ones against ~50% for the rest means the low bits were deliberately cleared and then written on.
- The first payload a standard LSB extraction returns is the decoy; its own caption disqualifies it (“practice… Not for action”). Reading *all* the extracted files, not just the annotation line, is what separates the two plates.
- Framing (`uint32` length + gzip) made both payloads self-delimiting and trivially verifiable — a good check that the extraction order (row-major, interleaved RGB, MSB-first) is the intended one.
- Extracting the text is not the last step: the flag is a *reconstruction* from it (serial, message words, check group), not a substring. The `RECON SERIAL` / `CODE` labels and the uppercase check group are packaging, not flag content.

## Tools & references

- Python 3, NumPy, Pillow; `zlib` (gzip) and `tarfile` for the framed payloads
- LSB bit-plane steganography in PNG images

---
[⬅ Back to event](../../README.md)
