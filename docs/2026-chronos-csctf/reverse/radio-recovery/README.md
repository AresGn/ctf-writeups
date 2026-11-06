---
tags: [reverse, firmware, dwfw, uboot, zlib, cpio, xor]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Operation Dawn: Radio Recovery

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| reverse | 120 | 156 | ✅ | — | 0xAr3s-root | Terminal43 |

## Challenge description

> A hostile intrusion cut the field-radio support link of a fictional country. Responders pulled `firmware.bin`, a software recovery bundle, and need the administrative recovery token locked inside it.
>
> Recover the complete `CSCTF{...}` value. The bundle is constructed but uses real compression and archive records; it is not a hardware dump or a bootable radio image.
>
> Attachment: `firmware.bin`, 1,048,576 bytes, SHA-256 `ae253e80cfca3035fe1e882c3c26a75b1d701f1b1bb343ba290d590573bc4313`.

**Artifact files:** `files/firmware.bin` (not committed — currently at `reverse/firmware.bin`)

## TL;DR

Unpack the custom DWFW bundle (four CRC-checked partitions), take the active redundant U-Boot environment (flag 7 beats flag 6), decompress the rootfs zlib stream with the *msgcat* partition as preset dictionary into a cpio archive, and XOR `etc/config/radio`'s `admin_token` with the repeating MAC bytes exactly as `S40admin` does.

## Approach

**1. Recon — one magic, four records**

```bash
sha256sum firmware.bin  # ae253e80…bc4313 matches
file firmware.bin       # data (1 MiB, almost all 0xFF erased flash)
binwalk firmware.bin    # only finds /etc/init.d/* paths (msgcat strings)
```

The first 88 bytes are a custom `DWFW` v1 container: 8-byte header (`DWFW`, version 1, count 4) then four 20-byte records `name[8] | offset LE | size LE | crc32 LE` — `loader` @0x200 (111 B, SPL banner), `ubootenv` @0x270 (16 KiB), `msgcat` @0x4270 (258 B), `rootfs` @0x4380 (633 B). All four stored CRC32s verify; the test sweep of standard decompressors fails only because two parameters are still missing: which environment is active, and the zlib dictionary. Everything past ~5 KiB is `0xFF` padding.

**2. Hypothesis — redundancy picks the key, the header names the dictionary**

`ubootenv` is a redundant U-Boot environment: two 0x2000 blocks (CRC + flag byte + `key=value\x00` strings). Block 0 (flag 6, `ethaddr=00:11:22:33:44:55`, `recovery=legacy`) is the stale copy; block 1 (flag 7, `ethaddr=3c:22:fb:4a:1d:90`, `recovery=ready`) is active — higher flag wins, and `ready` vs `legacy` corroborates it. The `msgcat` partition (init strings, `nvram get admin_token`, `#!/bin/sh`) reads like a string catalog for the rootfs — and indeed the rootfs stream is zlib with `FDICT` set: its 4-byte DICTID equals `Adler-32(msgcat)` (`0x55d45a6c`). Plain `zlib.decompress` fails at byte 5 without that dictionary; with `zdict=msgcat` and raw deflate from offset 6 it yields 2560 bytes of `070701` cpio (newc).

Inside: `etc/config/radio` (`admin_token=` 60 hex chars) and `etc/init.d/S40admin`, which is the key schedule in shell: strip `:` from `ethaddr`, then XOR each `admin_token` byte with the repeating 6 MAC bytes (`i % 6`). The legacy MAC produces binary garbage; the active MAC is the only key that can produce ASCII.

**3. Exploitation — replay the boot script's XOR**

```bash
python3 solve/solve.py ../firmware.bin
# [*] DWFW loader    off=0x0200 size=  111 crc OK
# [*] DWFW rootfs    off=0x4380 size=  633 crc OK
# [*] U-Boot env[1] flag=7 ethaddr=3c:22:fb:4a:1d:90 recovery=ready
# [*] zlib DICTID   : 0x55d45a6c == Adler-32(msgcat)
# [*] rootfs        : 633 -> 2560 bytes (cpio)
# [*] admin_token   : 30 bytes (hex in config)
# [+] FLAG            : CSCTF{...}
```

The solver is stdlib-only (own DWFW, U-Boot env, cpio-newc and XOR logic), asserts every stored CRC and the DICTID match, and refuses to emit a flag unless the XOR result is exactly a framed `CSCTF{...}` — so picking the stale environment fails loudly instead of printing garbage.

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (redacted)

## Reflections

- Custom containers announce themselves: `DWFW` + a record count is enough to stop `binwalk`-ing and start parsing. Letting the stored CRC32s validate the record layout (name/offset/size) before trusting any offset is what separates parsing from guessing.
- Preset-dictionary zlib is rare in CTFs and diagnoses cleanly: valid CMF/FLG, failure a few bytes in, and an FDICT bit looking at you. The 4-byte DICTID *is* an Adler-32 checksum — finding which supplied blob hashes to it names the dictionary.
- Redundant environments are a two-copy vote: ignore the flag byte and you have a 50% chance of XOR garbage. Flag monotonicity (`ready` > `legacy`) and the ASCII check together make the selection provable, not lucky.

## Tools & references

- Python 3 stdlib (`struct`, `zlib` with `zdict`/Adler-32, own cpio-newc parser)
- `binwalk`, `file`, `sha256sum` (triage only)
- U-Boot redundant environment (CRC + flag), zlib FDICT/DICTID (RFC 1950), cpio newc (`070701`) archive format

---
[⬅ Back to event](../../README.md)
