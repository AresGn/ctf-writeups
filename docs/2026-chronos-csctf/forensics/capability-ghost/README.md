---
tags: [forensics, xattr, journald, hmac, xor]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# capability-ghost

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| forensics | 120 | 106 | ✅ | — | 0xAr3s-root | Mohamed Amine Mzoughi |

## Challenge description

> A hostile-state campaign targeted the build runner for the software that drives signals on railways carrying coalition freight toward the Operation Dawn front. Responders kept the runner's filesystem archive and journal.
>
> Recover the sealed marker from them. Inspect the records as data: do not run the supplied programs or restore their capabilities. Linux tools or WSL are enough, and you do not need root. This is a constructed forensic exercise, not evidence of an actual compromise.
>
> Attachment: `capability-ghost.zip`, 51,023 bytes, SHA-256 `c53a83833466cc4db34336ab9e333a0e317cd48da43932953df89cacb9c31ffe`.
>
> Submit the complete recovered `CSCTF{...}` value. Flag format: `CSCTF{...}`

**Artifact files:** `files/runner-fs.tar.gz`, `files/runner.journal`, `files/README_FOR_RESPONDERS.md`, `files/manifest.sha256` (not committed).

## TL;DR

`/etc/solunet/signaling-cfg.sealed` is XORed with a key derived by `hc-probe` as `HMAC-SHA256(tag, epoch)`: the tag is the `user.build_seal` xattr stored in the tar's PAX headers, the epoch is the journal's `X_SEAL_EPOCH` field; recomputing the key offline decrypts the marker → flag.

## Approach

**1. Recon — a tar with xattrs, a journal and a shredded config**

`runner-fs.tar.gz` holds a small tree: `/etc/solunet/signaling-cfg.sealed` (27 bytes), `/usr/local/bin/hc-probe`, `backup-sync`, `ping`, a `hc-probe.service` unit and `/root/.bash_history`. The history tells the story: `setcap` on `hc-probe`, a random `TAG`, `setfattr -n user.build_seal`, an `EPOCH=$(date +%s)`, then `hc-probe --seal "$TAG" "$EPOCH" signaling-cfg signaling-cfg.sealed` and `shred -u` of the plaintext. So the plaintext is gone for good; the only way is to reverse the seal with the right tag and epoch.

The xattrs are not applied on extraction (no root), but they are stored in the PAX extended headers as `SCHILY.xattr.*`. Python's `tarfile` exposes them in `pax_headers`:

```python
import tarfile
for m in tarfile.open("files/runner-fs.tar.gz"):
    print(m.name, m.pax_headers)
```

`hc-probe` carries `security.capability` and `user.build_seal` = `50 9d f6 cd 8e 10 3f a5` (8 raw bytes; `tarfile` shows it as a UTF-8 string with surrogate escapes, so I re-encode with `surrogateescape` to get the bytes back). `backup-sync` has a `user.sync_id` and `ping` has a capability too, but those are noise.

**2. Hypothesis — the binary documents its own scheme; the epoch is in the journal**

I did not run `hc-probe`. A `strings` on it is enough: its usage text states that `--seal` and `--unseal` are the same operation, a repeating-key XOR with `key = HMAC-SHA256(key = raw_bytes(tag_hex), msg = ascii_decimal(seal_epoch))`, `out[i] = in[i] XOR key[i mod 32]`. It also says where the epoch comes from: the `X_SEAL_EPOCH` field of this run's journal entry, **not** the entry's own wallclock time.

```bash
journalctl --file=files/runner.journal --no-pager -o json
```

Entry 5 (`hc-probe`, "health probe sealed result written") has `X_SEAL_EPOCH=1793294042`, whereas its `__REALTIME_TIMESTAMP` gives 1793294054 — 12 s later: the trap. Two other traps on the tag: the `TAG` in `.bash_history` is just a variable of the original shell (random, not recorded), and the shell command stored the xattr as the ASCII string `0x…`, while the archive holds the raw bytes; the xattr in the archive is the source of truth.

**3. Exploitation — recompute the key offline and XOR**

```bash
python3 -I solve/solve.py files
```

The script reads the tag from the PAX headers, the epoch from the journal (via `journalctl --file`), derives the key and XORs the sealed file. A wrong tag or epoch would give random bytes; here the output starts with `CSCTF{` and is printable, which confirms both values.

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (redacted)

## Reflections

- Archive metadata (PAX xattrs) is evidence in its own right: a plain `tar -x` as non-root silently drops it, so read the headers instead.
- When a tool documents its own scheme, read the binary's strings before anything else; here it also warned about the epoch pitfall (journal field vs. entry time).
- A correct decryption is self-validating (printable output with the known `CSCTF{` prefix), which is a good check when several candidate inputs exist.
- Nothing was executed, extracted as root, or restored: the whole solve is data analysis.

## Tools & references

- `journalctl --file=… -o json`, `strings`, Python 3 (`tarfile`, `hmac`, `hashlib`)
- Linux xattrs / file capabilities (`security.capability`), PAX `SCHILY.xattr.*` headers, systemd journal custom fields

---
[⬅ Back to event](../../README.md)
