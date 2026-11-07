---
tags: [forensics, sqlite, wal, database]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# last-commit

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| forensics | 332 | 118 | ✅ | — | 0xAr3s-root | Chronos Security |

## Challenge description

> The national land registry of one of Operation Dawn's smaller coalition states looks normal again, but its completed restoration export `LR-731` may have carried altered ownership out to regional offices. A later clean view does not prove what the job delivered.
>
> Reconstruct the exact ownership export at the job's transition to `COMPLETED`, using the acquired SQLite database and WAL pair, the delivery receipt and the supplied export profile. The registry is fictional. Analyze the supplied files only. Attachment: `last-commit.zip`, 84,979 bytes, SHA-256 `06da868e7ceeef1c96651cf1307033f7b37b65e235f8a121ea599166f85279a1`.
>
> Submit `CSCTF{last_commit_<64 lowercase hex characters>}` as specified in the supplied export profile.
>
> Flag format: `CSCTF{...}`

**Artifact files:** `files/registry.sqlite`, `files/registry.sqlite-wal`, `files/delivery.csv`, `files/export-profile.md`, `files/provenance.json`, `files/README.txt`, `files/SHA256SUMS` (not committed).

## TL;DR

The WAL holds 9 valid frames in 6 commits; the commit where `LR-731` goes `QUEUED → COMPLETED` shows altered ownership rows that the later commits (and the checkpointed DB) no longer have. Rebuilding the registry at that commit, running the profile's query with `delivery.csv` as manifest and SHA-256-ing the TSV gives the flag.

## Approach

**1. Recon — read the contract, not just the data**

`export-profile.md` is the real spec: the worker runs an IMMEDIATE transaction that queries the manifest's parcels, stages the export, updates `export_job` `QUEUED → COMPLETED` and commits. The export is the exact query of the profile over the registry state **at that commit** (not a later view), with the receipt `delivery.csv` as `manifest` (twelve parcels, delivery order), TSV with a fixed header, LF endings, hashed with SHA-256. The DB is 9 pages (4096 B), the WAL is 32 + 9 × (24 + 4096) = 37,112 bytes, so 9 frames. The README warns not to open the originals with SQLite (it would create a `-shm` and may checkpoint), so I never opened the originals: everything is parsed by hand and built into temporary copies. `SHA256SUMS` matches all files.

**2. Hypothesis — a view "at commit N" = base DB + the frames up to the N-th commit**

From the SQLite WAL format: header `0x377f0682`, page size 4096, salts; each frame has a 24-byte header (page number, **db size after commit** — non-zero only on a commit frame —, salts, cumulative checksum) followed by the page image. A reader at commit N sees, for every page, the latest frame ≤ N, and the base DB for the other pages. So I:

1. validated the header checksum and, for every frame, the salts and the cumulative checksum (little/big-endian words depend on the magic): all 9 frames are valid;
2. listed commits: frames 0, 2, 4, 5, 7, 8 — transactions can span several frames (e.g. frames 1+2, 3+4, 6+7), so a state must only be built at a commit frame, never in the middle of a transaction;
3. built a plain DB image for each commit (base + frames ≤ N, no WAL left) and queried `export_job`.

**3. Exploitation — the transition commit has the altered rows**

| Commit frame | `LR-731` | export SHA-256 (first bytes) |
|---|---|---|
| base DB | no row | — |
| 0 | no row | `04a47a…` |
| 2 | no row | `40f3b1…` |
| 4 | `QUEUED` | `40f3b1…` |
| **5** | **`COMPLETED`** | **`40f3b1…`** |
| 7 | `COMPLETED` | `04a47a…` |
| 8 | `COMPLETED` | `04a47a…` |

The ownership of parcels 1202, 1205, 1209 and 1214 is altered between commits 0 and 2 (new holders `2127`–`2131`, new instruments `IN-9360472185`, `IN-8162094735`, `IN-7259841360`, `IN-6941538207`, and a 65/35 split instead of 60/40 on parcel 1209), still present when the job completes at frame 5, and restored to the original holders in the last commits: "the later clean view" the statement warns about. The export at the transition has 13 rows (parcel 1209 has two holders). Parcel order comes from `delivery.csv`, holder order from `registry_ref COLLATE BINARY`.

```bash
python3 -I solve/solve.py files
```

The script does all of this (WAL parsing, checksum validation, state per commit, query, hash) and prints the flag; it reads the originals only and writes to a temp dir.

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{last_commit_<64 hex>}` (redacted)

## Reflections

- "Current state" and "state at transaction X" are different things: in WAL mode, the answer is in the frame sequence, not in what a normal `sqlite3` open returns.
- Only commit frames (non-zero db size) are consistent states; a transaction can span several frames, so stopping at an arbitrary frame gives a torn view.
- The cumulative checksum and salts delimit the valid epoch; validating them avoids using leftovers from earlier WAL generations.
- The same hash appears at commits 2, 4 and 5 and a different one at 0, 7, 8: comparing hashes across all commits shows when the tampering started and ended, not just the delivered state.
- Evidence was preserved: no SQLite open on the originals, work on rebuilt copies.

## Tools & references

- Python 3 (`struct`, `sqlite3` on rebuilt copies only, `hashlib`, `csv`)
- SQLite file format and WAL format (<https://sqlite.org/fileformat2.html>, <https://sqlite.org/walformat.html>)

---
[⬅ Back to event](../../README.md)
