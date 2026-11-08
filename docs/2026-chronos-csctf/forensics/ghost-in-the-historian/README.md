---
tags: [forensics, ext4, ransomware, carving, xorshift]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Ghost in the Historian

| Category | Solves | Solved | First blood | Hint used | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| forensics | 107 | ✅ | — | no | 0xAr3s-root | Mohamed Amine Mzoughi |

## Challenge description

> A campaign against the electricity supply encrypted a substation historian's configuration and deleted the encryptor. The substation feeds a partner nation's grid on the coalition side of Operation Dawn.
>
> Recover the original configuration's `SAFETY_INTERLOCK_TOKEN` and submit its complete `CSCTF{...}` value. The volume was constructed for this exercise and is not an untouched acquisition; the included brief explains its timeline. Analyze recovered programs as data: do not execute them or mount the image.
>
> Attachment: `ghost-in-the-historian.zip`, 72,560 bytes, SHA-256 `5edaea927aa93db3286f771dd77c8c41e0c23c6eafa70ac2182da5bd9ac56ce9`

**Artifact files:** `files/ghost-in-the-historian.zip` (not committed — currently at `network/ghost-in-the-historian.zip`)

## TL;DR

Carve the deleted `historian_enc` ELF from unallocated space, read its disassembly as data (xorshift32 stream, seed `(time() ^ getpid()) × 0x9E3779B1`, PID from its own syslog line), brute-force the seed seconds around the 04:13 sweep, and chain-decrypt the three `.enc` configs — the topology file holds the token.

## Approach

**1. Recon — a small ext4 world with three locked files**

The ZIP verifies (`5edaea92…56ce9`) and unwraps to a VMDK descriptor plus a 64 MiB flat extent (`evidence-flat.vmdk`, 131072 sectors, `manifest.sha256` covers all three files). Read-only `debugfs`, never a mount:

```bash
debugfs -R "ls -l /" evidence-flat.vmdk
# /var/historian → node_status.json.enc (74 B), grid_topology.cfg.enc (235 B),
#                  historian_cache.dat.enc (64 B), all dated 2-Oct-2026 05:13
# /var/log/historian.log → one line: 2026-10-02 04:13 historian_enc[2764964]:
#                          starting encryption sweep, target_dir=/var/historian
```

The README brief is explicit about the two clocks (filesystem built Oct 29, incident records Oct 2 — each means what it says) and the rules of engagement: recovered programs are data. `lsdel` finds no deleted inodes and the journal is a single empty transaction, but `strings` over the raw extent leaks the rest of the story: a ransom note ("Contact ref: 7F3A-RECOVERY (this is NOT a decryption key)", display-only wallet) and, right beside it, a full second program — libc imports (`scandir`, `fwrite`, `unlink`, `utime`, `getpid`), path formats (`%s/%s`, `%s.enc`, `rb`/`wb`), and the exact log format above. One ELF (`7fELF`) sits at extent offset `0xa1c000`; carved through its section headers (`0x3888` bytes, BuildID intact) it is the deleted encryptor. The `@z3uAF2` string nearby is just ciphertext bytes of `grid_topology.cfg.enc`, not a key — a natural decoy.

**2. Hypothesis — the binary documents its own key schedule**

The `.text` disassembly (stripped, ~1.2 KiB — read, never run) is a linear sweep: `scandir`, skip dotfiles, skip non-regular files, `fopen(rb)` → `ftell`/`fread`, encrypt, `fopen(wb)` to `%s.enc`, `utime` (hence the uniform Oct-2 mtimes), `unlink` the original. The cipher is textbook xorshift32 (shifts 13/17/5, little-endian bytes, fresh state per 4-byte block):

```
seed = 0xa5a5a5a5; t = time(); pid = getpid()
if (t != pid) seed = (t ^ pid) * 0x9E3779B1   (mod 2^32)
state persists across files (saved back after each one)
```

So the unknowns are exactly two: the seed seconds `t` and the file order (scandir order decides who gets the seed state). The log line the binary wrote itself hands over both anchors: PID `2764964` verbatim, and the sweep minute `04:13` bounding `t` — brute-force the day's 86400 seconds and the config that decrypts from seed state must be fully printable ASCII starting with `#`.

**3. Exploitation — one day of seconds, then follow the chain**

```bash
python3 solve/solve.py ../ghost-in-the-historian.zip
# [*] Sweep log     : 2026-10-02 04:13 historian_enc[2764964]
# [*] Seed time     : 2026-10-02 04:13:05+00:00 (t=1790914385) seed=0x40d8e565
# [*] Chain order   : grid_topology.cfg.enc -> historian_cache.dat.enc
#                     -> node_status.json.enc
# [+] FLAG            : CSCTF{...}
```

`t = 04:13:05` (five seconds into the logged minute — exactly what the two-`time()`-call layout predicts) decrypts `grid_topology.cfg.enc` straight from seed state into its config, including `SAFETY_INTERLOCK_TOKEN=flag{...}`. Chaining the surviving state (`235 B → 59 states`) decrypts `historian_cache.dat` (pressure CSV `04:11Z/04:12Z`) and then `node_status.json` (valid JSON, `MGA-HIST-07`, `nominal`); the reverse order fails printability, confirming `grid → cache → node`. My first sweep over the whole day with a 3-file joint threshold found nothing — correctly so, since only the first file in scandir order validates from seed state; scoring the grid file alone hits at full 235/235 printable on the first pass (~5 s).

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (redacted)

## Reflections

- Analyzer-as-data works: imports + rodata (`%s.enc`, `rb`/`wb`, the log format) already sketch the program before any disassembly, and the 1.2 KiB `.text` confirms seed schedule, chaining, timestamp cloning and deletion in one read.
- The PID-in-the-log trick is the intended shortcut — the binary `%d`-logs its own `getpid()`, collapsing the seed search to one dimension (seconds in a day). Without it, the joint `(t, pid)` space would still be brute-forceable but far uglier.
- The failed joint-threshold sweep was instructive, not wasted: state carry-over means only one file validates from seed, so per-file scoring with a chaining second stage is the right shape — and the order that fails printability is itself evidence for the order that succeeds.

## Tools & references

- Python 3 stdlib (`struct`, `hashlib`, `zipfile`) + `debugfs` (read-only dumps, `lsdel`, `logdump`)
- `strings`, `objdump -d -M intel` (static triage/disassembly — binary never executed)
- ext4 flat extent in monolithicFlat VMDK; xorshift32 (Marsaglia shifts 13/17/5); RFC-ish syslog line as PID oracle

---
[⬅ Back to event](../../README.md)
