---
tags: [reverse, x86-64, splitmix64, inversion]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Ground Lock

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| reverse | 120 | 163 | ✅ | — | 0xAr3s-root | Chronos Security |

## Challenge description

> A response team recovered the ground-maintenance utility used to service the GRIFFON-FC drones an Ash Army proxy flies over the Operation Dawn theatre. The accepted service code is needed before equipment handover.
>
> Recover that code. This is a constructed software case: the attachment is a Linux utility, not flight-controller firmware or a hardware dump, and static analysis is enough.
>
> Attachment: `fcunlock`, Linux x86-64 ELF, 682,600 bytes, SHA-256 `9634a7c4c4769a21eb921125a3d1b0ef560e3f4ed0202efa860861f0d2922399`.
>
> Submit `CSCTF{<service-code>}` with the exact 24 code bytes and case.

**Artifact files:** `files/fcunlock` (not committed — currently at `reverse/fcunlock`)

## TL;DR

`main` splits the 24-byte argument into three 8-byte little-endian words, runs each through the splitmix64 finalizer, and compares against three stored targets — and that finalizer is fully invertible mod 2⁶⁴, so each target inverts to its exact 8 code bytes.

## Approach

**1. Recon — behavior first, then the checker shape**

```bash
sha256sum fcunlock  # 9634a7c4…922399 matches
file fcunlock       # ELF 64-bit LSB executable, x86-64, dynamically linked, stripped
./fcunlock          # usage: ./fcunlock <service-code>  (exit 2)
./fcunlock AAAA     # ACCESS DENIED (exit 1)
```

`main` (at `0x4016da`, via `__libc_start_main` from entry `0x401530`) enforces exactly one argument of exactly 24 bytes (`strlen` vs `3*8`), otherwise usage/`ACCESS DENIED`. The success path prints `GRIFFON-FC ground-maintenance interlock released.` then `Maintenance token: CSCTF{%.*s}` with the input — so the flag *is* the accepted input, and the comparison is the whole lock:

```c
for (i = 0; i < 3; i++) {
  acc = 0;
  for (j = 0; j <= 7; j++)
    acc |= (uint64_t)input[8*i + j] << (8*j);   // u64le load
  if (mix(acc) != table[4 + i]) fail = 0;        // table @ 0x479020
}
```

The rodata table holds the two mix constants (`0xff51afd7ed558ccd`, `0xc4ceb9fe1a85ec53`), the shift (`33`), the count (`3`) and the three digests — the trailing qword decodes as ASCII `usage: %`, i.e. it is just the packed string area, not a fourth target.

**2. Hypothesis — splitmix64 finalizer, invertible, no brute force needed**

The function at `0x401655` is the splitmix64 mixer verbatim:

```
x ^= x >> 33;  x *= 0xff51afd7ed558ccd
x ^= x >> 33;  x *= 0xc4ceb9fe1a85ec53
x ^= x >> 33
```

Every step inverts over 2⁶⁴: `x ^= x >> 33` is an involution (2·33 ≥ 64, so applying it twice cancels), and both multipliers are odd, hence invertible via `pow(m, -1, 2**64)`. Inverting each digest yields the unique 8-byte chunk — no search, no angr, no execution beyond a final confirmation run.

**3. Exploitation — invert, verify, submit**

```bash
python3 solve/solve.py ../fcunlock
# [*] Table       : shift=33 count=3
#     chunk 0 mix == 0x8bfd351846ffb86b
#     chunk 1 mix == 0x3ff3fd892aa7e3b2
#     chunk 2 mix == 0xf61e79e7e639e0d2
# [*] Code bytes  : b'...' (24 bytes, all printable ASCII)
# [+] FLAG            : CSCTF{...}
./fcunlock "$CODE"  # GRIFFON-FC ground-maintenance interlock released. (exit 0)
```

The solver locates the table by the `S1||S2` byte pattern (the constants also occur as `movabs` immediates in `.text`), inverts the three digests, and asserts the forward round-trip before printing. The binary confirms with exit 0.

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (redacted)

## Reflections

- Reading the rodata tableStruct-first (`constants, shift, count, digests`) beats staring at the loop: the layout tells you the algorithm's parameters before you even disassemble the mixer.
- Recognizing splitmix64 by its two magic constants (`ff51afd7ed558ccd`, `c4ceb9fe1a85ec53`) short-circuits the analysis — these are among the most distinctive 64-bit constants in the wild.
- Invertible checks are common in easy RE: always test whether the transform is a bijection (odd multiplies, xorshifts with shift > 32) before reaching for brute force or symbolic execution.

## Tools & references

- Python 3 stdlib (`struct` — table carving, `pow(a, -1, 2**64)` — modular inverses)
- `objdump -d -M intel`, `file`, `sha256sum` (static triage; one confirmation run)
- Splitmix64 (Steele et al. — the `mix64` finalizer and its inverse)

---
[⬅ Back to event](../../README.md)
