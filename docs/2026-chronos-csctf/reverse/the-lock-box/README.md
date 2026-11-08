---
tags: [reverse, elf, constructors, static-analysis]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# The Lock Box

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| reverse engineering | 120 | 166 | ✅ | — | 0xAr3s-root | Terminal43 |

## Challenge description

> Operation Dawn, annex entry 06. The Ash gate guards run a small field unit at the north canal crossing: give it the pass phrase and it opens the gate or refuses. We took one. It will not tell you the phrase it is waiting for. Work out the phrase it accepts.
>
> Attachment: `lockbox.zip`
>
> Flag format: `CSCTF{...}`

**Artifact files:** `files/lockbox.zip` → `lockbox` (not committed).

## TL;DR

`main`'s own 33-character phrase check ("open sesame and mind the tripwire") is a decoy that only prints a taunt. The real check runs *before* `main`, in a function planted in `.init_array` — a GCC/glibc constructor, which the loader calls with real `argc`/`argv` in registers even though nothing in the decompiled control flow ever calls it directly. It verifies a 44-byte phrase with a rolling XOR/ROL/ADD cipher against an embedded key; inverting that cipher gives the phrase, and the phrase *is* the flag.

## Approach

**1. Recon — a tiny stripped static-looking binary with two separate checks**

`file`: a small dynamically-linked PIE. `strings` shows the gate flavour text (`crossing : NORTH CANAL`, `GATE: pass phrase accepted/refused`, fake log lines `0417/0422/0431 open denied`), a 34-character blob that looks XOR-scrambled, and a second, denser blob after a `LOCKBOX1,` label. Disassembling the only two real functions:

- **`main`** (reached from `__libc_start_main`, confirmed via the `lea rdi,[rip+...]` that resolves to it) dispatches `status`/`log`/`open`. For `open <phrase>` it requires `len(phrase) == 33`, XORs each byte with `0x5b` and compares it to a stored 33-byte table — matching decodes to `"open sesame and mind the tripwire"` — but on a match it only `puts("the quartermaster laughs - that is last week's code, soldier")` and **falls through** to the real decision: it reads a 32-bit global and accepts only if that global equals `0x5a`.
- A second function, never called from `main` or anywhere else in the disassembly, implements its own `open <phrase>` check (same `argv[1]=="open"`/`argv[2]` pattern) over a **44-byte** phrase with a rolling cipher, and writes `0x5a` (success) or a different value (failure) into that same global.

A function nothing calls, that nonetheless controls `main`'s outcome through a shared global, is the signature of a **constructor planted in `.init_array`**: glibc's startup code (`__libc_csu_init`) invokes every `.init_array` entry with `(argc, argv, envp)` in `rdi`/`rsi`/`rdx` — the same convention a normal `main` gets — before `main` itself ever runs. Checking the section confirms it: `.init_array` holds two pointers, `0x1480` (glibc's own `frame_dummy`, a one-line `endbr64; jmp` trampoline) and `0x10e0` — the "dead" function. It isn't dead; it's the real gatekeeper.

**2. Hypothesis — invert the rolling cipher instead of brute-forcing**

Reading the constructor: for a 44-byte phrase, with `esi` (a running 32-bit accumulator) seeded to `0x5b`, `cl` seeded to `1` and incremented by 3 every round, and an 8-byte key `K` cycling by `i & 7`:

```
dl = rol8(phrase[i] ^ (esi & 0xFF), cl) + K[i & 7]      # compared against ciphertext[i]
esi = esi + i + edx                                     # edx's low byte is ciphertext[i] once the byte matches
```

Because every step is reversible (`rol8`/`ror8` are inverses, `+`/`-` mod 256 are inverses) and `esi`'s evolution only needs the *ciphertext* byte (not the plaintext) once a match is assumed, the 44 phrase bytes can be recovered in one forward pass, in order, with no guessing:

```
phrase[i] = (esi & 0xFF) ^ ror8((ciphertext[i] - K[i & 7]) & 0xFF, cl)
```

The key and ciphertext sit in `.rodata` right after a `LOCKBOX1,` label, reached from the constructor by a single `lea r11, [rip+disp32]`.

**3. Exploitation — parse the ELF and invert, no execution needed**

```bash
python3 -I solve/solve.py files/lockbox.zip
```

The script never runs `lockbox`: it reads the ELF headers to find `.init_array`, tells the real constructor apart from `frame_dummy` by its prologue (a `jmp` right after `endbr64` vs. a real `push rbp`), follows that constructor's own `lea r11, [rip+disp32]` to locate the 8-byte key and 44-byte ciphertext in `.rodata`, and inverts the cipher byte by byte. The recovered 44-character string is itself the flag — "annex entry 06" in the briefing matches the `06` embedded in it, a built-in confirmation.

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (redacted)

## Reflections

- A function with no cross-references from `main` is not necessarily dead code: always check `.init_array`/`.fini_array` (and `.ctors`/`.dtors` on older toolchains) before writing something off, especially when it reads a global that *is* checked elsewhere.
- GCC/glibc constructors receive `(argc, argv, envp)` for free through the platform's `__libc_csu_init` calling convention, even though the C source declares them with no parameters — a well-known but easy-to-miss CTF trick once a binary's `main` looks "too simple" for what the challenge promises.
- The 33-character phrase that `main` checks directly is a complete, satisfying-looking decoy (it even gets its own flavour-text reward) that contributes nothing to the actual accept/reject decision — a reminder to trace *where a comparison's result is used*, not just whether a comparison exists.
- The cipher is simple enough (rotate, add, running accumulator) to invert by hand once each step's reversibility is confirmed; no brute force or key search was needed.

## Tools & references

- `file`, `strings`, `readelf`, `objdump`, Python 3 (`struct`, `zipfile`)
- ELF `.init_array`/constructors and the `(argc, argv, envp)` constructor-calling convention; x86-64 RIP-relative addressing

---
[⬅ Back to event](../../README.md)
