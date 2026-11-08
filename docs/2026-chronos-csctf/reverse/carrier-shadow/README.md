---
tags: [reverse, steganography, elf, dwarf, eh-frame, huffman]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Carrier Shadow

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| reverse | 540 | 264 | ✅ | — | 0xAr3s-root | Armand Alexandru Balint |

## Challenge description

> A stripped x86-64 Linux ELF, pulled off a forward Ash Army command post after a hasty retreat. Prints a few lines of hex utility output when run. Signals suspects it is a carrier for something else: the usual places — data sections, strings, overlays, appended archives — are clean, but the binary's own second-stage payload signature turned up in captured traffic.
>
> Find where the payload actually lives in this binary, lift it out, and read the authorization string it carries. Static analysis beats a sandbox here — this is a reverse-engineering problem, not a shellcode run.
>
> Attachment: `carrier-shadow` — 1337736 bytes, SHA-256 `995fd7161d984898e521eb581f93380b11f31e3de342b368519a2221fb192a04`. Static ELF, no network, no setuid.
>
> Flag format: `CSCTF{...}`

**Artifact files:** `files/carrier-shadow` (not committed). Tags: steganography, total-warfare.

## TL;DR

The second stage is hidden in the **function-size pattern of the `.eh_frame_hdr` search table**: after a PRNG-generated anchor, the gap between consecutive FDE addresses encodes Huffman symbols, whose bits (whitened with the same PRNG) form a raw DEFLATE stream of an ELF; its `.rodata` holds the authorization string → flag.

## Approach

**1. Recon — a hex utility that is far too big**

`file`: PIE, dynamically linked, stripped. `strings` shows `hexkit 1.2.0` (crc32/fnv1a64 and a "micro-function registry self-test") and nothing else. But the file is 1.3 MB for that: `.text` is 626 KB and `.eh_frame` 496 KB, while `.data`, `.rodata` and the section tail have nothing worth hiding data in, which matches the brief ("data sections, strings, overlays, appended archives are clean"). I did not run it.

Reading the start-up code from the entry point (`objdump -d`), one routine does not belong to a hex tool: it walks its own program headers looking for `PT_GNU_EH_FRAME` (`0x6474e550`), decodes the `.eh_frame_hdr` encodings (a DW_EH_PE reader), allocates `count × 8` bytes and fills it with the table's function addresses, then calls a function that loads the constant **`0x6a2b3c4d`** — the "payload signature". A final call checks that the result starts with `0x464c457f` (`\x7fELF`), then hands it to another routine. So the loader rebuilds an ELF from the unwind table's search table.

**2. Hypothesis — read the loader as a specification**

Reading the decoder function (about 0x600 bytes of x86) gives the whole format:

1. **Table**: `.eh_frame_hdr` (version 1, table encoding `0x3b` = datarel sdata4) lists 24,816 FDEs sorted by address. For the first ~120 entries the gaps are multiples of 16 (genuine functions); from entry 123 on, gaps are small and odd (2…120): the carrier. I computed the gaps `g[i] = loc[i+1] − loc[i]`.
2. **Anchor**: it seeds `xorshift32` with `0x6a2b3c4d` (`x ^= x<<13; x ^= x>>17; x ^= x<<5`), makes 8 values `x % 61 + 34`, and searches for 8 consecutive gaps equal to them (`69 75 80 91 47 58 35 37`): found at entry 123.
3. **Header**: the next 6 gaps, minus 2 each: table index (must be 0 or 1), a 4-byte little-endian length, and an XOR checksum. Here: table 0, length **17,733**, checksum **116**.
4. **Payload**: every following gap, minus 2 (so 0…255), is a *symbol* of a canonical Huffman code whose 256 code lengths come from `.rodata` (the loader indexes a pointer array in `.data.rel.ro`: entry 0 → `0x9b340`, entry 1 → `0x9b240`; I read them from the relocations). Codes are assigned the deflate way (shortest first, ties by symbol value), and the bits are appended **MSB first** until `8 × length` bits are collected.
5. **Check and whitening**: the XOR of all bytes must equal the checksum, then each byte is XORed with the low byte of the next `xorshift32` output (same seed).
6. The caller passes the result to a function that is `puff.c`-style (count-per-length tables, `bits()` with a saved position, a `longjmp` on error): **raw DEFLATE**. Its output must start with `\x7fELF`.

**3. Exploitation — redo it offline**

Table 0 gives the right checksum (XOR = 116); table 1 (a ramp of code lengths 6…) gives 255: a decoy. The script re-implements the six steps, writes the 34,192-byte stage-2 ELF (static, stripped) and prints the authorization string found in its `.rodata`, next to its printf format `payload: operation-dawn authorization = %s`. I did not execute stage 2 either.

```bash
python3 -I solve/solve.py files/carrier-shadow stage2.elf
```

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (redacted)

## Reflections

- Steganography does not have to live in bytes of the file: here the *layout* (function sizes in the unwind table) carries the data, so scanning sections, strings and overlays finds nothing.
- A constant that looks like a seed (`0x6a2b3c4d`) used twice (anchor generation and whitening) was the pivot: it is both the "signature" mentioned in the brief and the key to the format.
- Header fields with their own checks (length range, XOR) make good oracles: they let me tell the real code-length table from the decoy without running anything.
- The loader code was a precise specification; implementing the same steps in Python is faster than emulating or sandboxing, which is what the brief asked for.

## Tools & references

- `readelf`, `objdump`, `xxd`, Python 3 (`struct`, `zlib`)
- ELF program headers, `.eh_frame_hdr` binary search table (DW_EH_PE encodings), canonical Huffman codes, xorshift32, puff.c / raw DEFLATE

---
[⬅ Back to event](../../README.md)
