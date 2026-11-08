---
tags: [forensics, vim, swap-file, base64]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Last Buffer

| Category | Solves | Solved | First blood | Hint used | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| forensics | 119 | ✅ | — | no | 0xAr3s-root | Chronos Security |

## Challenge description

> An endpoint collector held on to two Vim recovery files for the same incident note: a periodic snapshot and the one grabbed when the shell dropped. Both restore cleanly, but only one came from the shell that died during the response window. The other is an earlier drill revision.
>
> Recover both, work out which one came from the shell that mattered, and return its encoded read-back proof.
>
> Flag format: `CSCTF{message}`

**Artifact files:** `files/last-buffer-handout.zip` → `incident-2026-10-07.md`, `incident-2026-10-07.md.swp`, `incident-2026-10-07.md.swo`, `audit-timeline.jsonl`, `shell-journal.jsonl`, `case-context.json`, `vim-swap-layout.md` (not committed).

## TL;DR

Both swaps carry an `authorization_b64` line, but only the `.swp` (PID 8442, pts/4) belongs to the shell that was killed by SIGHUP inside the crash window and whose base-file SHA-256 matches the saved note; its base64url proof decodes to the flag, while the `.swo` (PID 8124) decodes to a decoy.

## Approach

**1. Recon — two swaps, a saved note and three context files**

`file` identifies both swaps as Vim 9.0 swap files for `/home/opnight/incident-2026-10-07.md` (user `opnight`, host `noc-jump-1`), with PID 8442 for the `.swp` and PID 8124 for the `.swo`. The context files give the timeline:

- `case-context.json`: crash window `02:19:30Z`–`02:20:00Z`, target tty `pts/4`;
- `audit-timeline.jsonl`: PID 8124 (pts/7) is a periodic snapshot and exits with `success` at 02:12:18Z; PID 8442 (pts/4) has `ANOM_ABEND` `SIGHUP` at 02:19:46Z, then a `disconnect-capture` snapshot;
- `shell-journal.jsonl`: PID 8442 ran `sha256sum incident-2026-10-07.md` at 02:18:31Z → `01c2a034…c849`, then `session_disconnect` on pts/4.

`strings` on both swaps already shows the note text, with a `revision_id`, a `status`, a `base_file_sha256` and an `authorization_b64` line each (`vim-swap-layout.md` explains the structure: header block `b0`, data blocks `0x6461`, NUL-terminated lines).

**2. Hypothesis — identify the swap by process, not by name or content**

Several signals could be used, but only some are reliable:

- the names are interchangeable (the collector stripped the leading dot) and both restore cleanly, so a successful restore proves nothing;
- the swap header PID ties each file to a process: 8124 (`.swo`) vs 8442 (`.swp`);
- the audit log says the shell that died in the window on the target tty is 8442; 8124 had exited normally 7 minutes earlier;
- the swap's `base_file_sha256` must equal the SHA-256 of the saved note, and the shell journal confirms that hash for 8442:

```bash
sha256sum files/incident-2026-10-07.md
# 01c2a034f1a47e4cb5536d66394c4774a1f1c568ff4e34c0de7f654aa42bc849  <- base_file_sha256 of the .swp
```

The `.swo` has `base_file_sha256 = a5bcac6d…`, `revision_id: INC-4471/R16-DRILL` and `status: PERIODIC-SNAPSHOT` (the earlier drill revision), whereas the `.swp` has `revision_id: INC-4471/R18` and `status: UNSAVED-AT-DISCONNECT`, one step beyond the saved `R17`. Everything points to the `.swp`.

**3. Exploitation — decode the proof from the right swap**

The `.swp` holds `authorization_encoding: base64url` and an `authorization_b64` value; the decoy decodes to `retired-training-readback-16`, a clear sign it is the drill. The script parses the data blocks directly (no Vim needed), selects the swap by PID/crash window and base hash, and decodes the base64url:

```bash
python3 -I solve/solve.py files
```

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (redacted)

## Reflections

- Two artifacts that both "restore cleanly" must be told apart with the surrounding evidence: process IDs, TTYs, timeline and hashes, not the file contents alone.
- The base-file hash links a swap to the exact saved version it was editing, and the shell journal records that hash independently: a cheap cross-check.
- Base64 padding is often stripped with base64url; pad before decoding (`b + "=" * (-len(b) % 4)`).
- I parsed the swap format directly instead of running `vim -r`, which avoids touching evidence and any swap-recovery side effects.

## Tools & references

- `file`, `strings`, `sha256sum`, `base64`, Python 3 (`struct`, `hashlib`, `json`)
- Vim swap file format (block 0 `b0`, data blocks `0x6461`), RFC 4648 base64url

---
[⬅ Back to event](../../README.md)
