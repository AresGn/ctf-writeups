---
tags: [reverse, aarch64, gdb-rsp, mmio, chacha20, unicorn, splitmix]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Ghost Bank

| Category | Solves | Solved | First blood | Hint used | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| reverse | 29 | ✅ | — | no | 0xAr3s-root | Chronos Security |

## Challenge description

> A dormant relay bench from Brenzava exposes a single stopped GDB RSP endpoint. Behind it sits a controller with a sealed diagnostic bank. Recover the staged incident tasking; the flag is the code it contains.
>
> Flag format: `CSCTF{...}`

**Artifact files:** `files/ghost-bank.zip` → `firmware.bin` (956 B AArch64 flat image), `firmware-load.txt`, `capture.ndjson` (not committed). Live instance: raw-TCP RSP at `w01.ctf.chronos-security.ro:34224` (expired).

## TL;DR

The stub emulates an MMIO controller: the firmware's `f(challenge)` unlocks it, `CONTROL=0x9c` (STATUS 4) makes page 7 expose the 32-byte vault key, and page 3 (the only page with `CIPHER_LEN≠0`, 131 B) decrypts with the firmware's own ChaCha block (nonce `SEAL-V01\0\0\0\1`, counter 1) → tasking containing the flag.

## Approach

**1. Recon — a firmware that never runs, a capture that replays a ritual**

`firmware-load.txt` gives the MMIO map (CONTROL, PAGE, OFFSET, DATA, CIPHER_LEN, CHALLENGE, KEY, STATUS) and the RSP subset. `c`/`s` just return `S05`: the firmware is never executed, the stub *emulates* the registers. The capture shows the ritual `CONTROL=0x41 → read CHALLENGE → PAGE=7 → KEY (2×32-bit) → CONTROL=0x93 → STATUS=3`. In radare2 the live loop at `0x400040` does exactly that, with the key computed by a splitmix-like `f()` at `0x400120`; `f(0x0123456789abcdef)` equals the captured KEY, which validates the reversing. Dead code remains: a ChaCha quarter-round/block (`0x400090`/`0x400174`), a stream-XOR (`0x4002dc`) and the constants `"expand 32-byte k"` + `"SEAL-V01"`.

**2. Hypothesis — the bank is ChaCha-encrypted, but where is the key?**

Dumping pages gives high-entropy bytes independent of session, challenge and key. Hours went into guesses (repeating-XOR, splitmix streams, ChaCha with KEY/CHALLENGE/XML hashes as key, decompressors) — all negative, because I was only reading pages in states 0/3 and only ever looked at page 7.

Three observations broke it open:
- `qXfer` is advertised in `qSupported` but answers `E01` on a fresh session; after `CONTROL=0x41` it serves the XMLs (they match the two documented SHA-256, and hide nothing — the hashes are integrity checks, not keys).
- `CIPHER_LEN` is **page-dependent**: scanning PAGE 0–63 shows it non-zero only on **page 3 (131)**. I had only polled it on page 7.
- `CONTROL=0x9c` (the firmware's last store) moves STATUS to **4**, and in that state page 7 no longer returns the sealed bytes but **32 bytes of key followed by zeros**.

**3. Exploitation**

```bash
python3 solve/solve.py w01.ctf.chronos-security.ro 34224   # run from the folder holding firmware.bin
```

1. Read page 3 (131 B) — the ciphertext.
2. Run the ritual with `PAGE=7` (writing another page before the key makes the check fail and resets PAGE to 0), `CONTROL=0x9c`, STATUS=4.
3. Read 32 bytes of page 7 → vault key.
4. Decrypt with the firmware's *own* block function (Unicorn runs `0x400174`, which uses a non-standard state layout; a stock ChaCha20 would be wrong), keystream block `n` for counter `1+n`, constants `SEAL-V01` + `00 00 00 01`.

Plaintext: `TASKING//STAGED-EW//RELAY-BENCH//AUTHKEY CSCTF{…}//JAM PROFILE: …//END`.

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (redacted)

## Reflections

- I fixed on page 7 because the capture and the firmware both mention it, and burned time on cryptanalysis of the wrong data. Enumerate *every* observable register on *every* page and in *every* state before attacking the cipher: `CIPHER_LEN` pointed to page 3 in one loop.
- Dead code is the spec of the emulated device: the last firmware store (`0x9c`) was a state transition I discarded as a loop epilogue.
- Features gated behind a state (`qXfer` after `0x41`) are worth re-probing after each transition.
- Reuse the firmware's own crypto via emulation instead of re-implementing it; a "ChaCha" with a permuted state would never match a library.

## Tools & references

- Python 3 raw RSP client, radare2 (`-a arm -b 64`), Unicorn (AArch64), gdb-multiarch not required
- GDB Remote Serial Protocol, ChaCha20 (RFC 8439 structure), SplitMix64

---
[⬅ Back to event](../../README.md)
