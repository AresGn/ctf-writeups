---
tags: [forensics, raid5, ext4, sqlite-wal, syslog, http]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Dawn Array

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| forensics | 285 | 99 | ✅ | — | 0xAr3s-root | Chronos Security |

## Challenge description

> During a state-sponsored attempt to isolate the eastern corridor, dispatch gateway E2 of the Rovenqara Rail Continuity Authority (RRCA) issued conflicting turnout-release records and was then powered off. RRCA runs the rail lines that carry coalition supply in the Operation Dawn theatre, and the corridor stays shut until responders know which releases the corridor controller actually acknowledged.
>
> The gateway kept its staging volume on a four-member Linux md RAID-5 array; one member is lost and three raw members survive. Rebuild the volume read-only, then apply the gateway's own dispatch procedure, stored on that volume, to find the controller-acknowledged release witness, and report it in the form the procedure defines. This is a constructed recovery case built on real Linux md RAID-5, ext4, SQLite WAL, RFC 5424 and HTTP/1.1, not an acquisition from physical disks.
>
> Attachment: `dawn-array.zip` (604,849 bytes, SHA-256 `e41e1a4c6b2b…05de66`)
>
> Flag format: `CSCTF{dawn_<64 lowercase hex digits>}`

**Artifact files:** `files/dawn-array.zip` (not committed — currently at `forensics/dawn-array.zip`)

## TL;DR

Parse the md v1 superblocks for the real geometry (left-symmetric, 32 KiB chunks, 1 MiB data offset, roles 0/2/3 present), rebuild the 117 MiB ext4 volume read-only, read the SQLite ledger *with its WAL applied*, and keep only the 16 of 128 release cycles whose controller reservation, readback and syslog phases all agree per procedure DP-7 — their SHA-256 is the witness.

## Approach

**1. Recon — inventory, then metadata before bytes**

```bash
unzip -l dawn-array.zip
# CASE-SHEET.txt  acq-1.raw  acq-2.raw  acq-3.raw (40 MiB each)  tools/raid5_extract.py
```

Note: the local copy hashes differently from the SHA-256 printed on the platform (suffix `…ad5de66` vs `…a05de66`); the analysis below works strictly from the supplied bytes, and every layer cross-validates (shared array UUID, ext4 label/UUID, 1:1 ledger/syslog triple match, 128 clean HTTP exchanges).

Each member carries an md v1.2 superblock at file offset `0x1000` (magic `0xa92b4efc`, set name `rrca-gw-e2:staging`). Decoded per `/usr/include/linux/raid/md_p.h` (`chunksize` is in sectors, roles come from `dev_roles[dev_number]`):

| Member | dev_number | role | layout | chunk | data offset | used size |
|---|---|---|---|---|---|---|
| acq-1.raw | 0 | **0** | 2 = left-symmetric | 64 sectors = 32 KiB | 2048 sectors = 1 MiB | 79872 sectors |
| acq-2.raw | 4 | **3** | same | same | same | same |
| acq-3.raw | 2 | **2** | same | same | same | same |

So role 1 is the lost member (parity recomputed), logical size is `3 × 79872 × 512 = 122,683,392` bytes. A naive first sweep (ext4 magic hunt over role/chunk/layout permutations) produced hundreds of hits because stripe-0 redundancy puts a valid superblock copy on two members — the superblock roles above are what disambiguate it, not the magic scan.

**2. Hypothesis — read DP-7 before trusting any single record**

The volume (`rrca-staging`, UUID `e195b486-…`) holds exactly the three evidence types the procedure names: `var/lib/rrca/dispatch.sqlite` (+ 552 KiB `-wal`, `-shm`), `var/log/rrca/dispatch-gateway.syslog` (512 RFC 5424 records, SD-ID `rrca@32473`) and `var/log/rrca/controller-access.pcapng` (2432 frames, 128 loopback connections `10.61.4.10 → 10.61.4.21:8080`, each exactly POST/201 + GET/200).

DP-7 (`usr/share/doc/rrca-dispatch-procedure.txt`) defines qualification Q1–Q5: one ledger row + one of each of the four syslog phases sharing `(cycle_id, request_id, gateway_seq)` in order; POST headers/body matching the ledger row with a 201 echo; response revision/nonce matching ledger *and* syslog; GET naming the same request with a readback view matching response and ledger; syslog readback matching the ledger. Anything duplicated, non-success, missing or out-of-order disqualifies.

Two traps follow directly: (a) 33 of the 128 ledger rows (`gateway_seq` 96–128) live **only in the WAL** — a main-DB-only read silently drops them, including qualifying cycles 103/110/117; (b) statuses alone qualify nothing — every connection here is 201/200, yet only 16 cycles survive the field-by-field comparison.

**3. Exploitation — reconstruct, then filter**

```bash
python3 solve/solve.py ../dawn-array.zip
# [*] md RAID-5: layout=left-symmetric chunk=32768 data_off=1048576
#                array=122683392 roles=[0, 2, 3] missing=1
# [*] Rebuilt 122683392 logical bytes, ext4 magic OK
# [*] Ledger        : 128 rows (WAL applied)
# [*] Syslog        : 512 records, 128 cycles
# [*] Capture       : 128 connections, POST/201 + GET/200 each, no pipelining
# [*] Qualifying    : 16 cycles
# [*] Qualifying gateway_seq: 14,15,34,35,55,69,78,79,80,83,85,87,95,103,110,117
# [+] FLAG            : CSCTF{...}
```

The solver derives the geometry from the superblocks, delegates byte-shuffling to the provided `raid5_extract.py`, dumps files read-only via `debugfs` (no mount, no root), reassembles TCP/HTTP in pure Python, and asserts every DP-7 clause — aborting instead of emitting a witness if any structural expectation breaks. The 112 rejections fall into four clean classes: POST-response nonce differing from ledger+syslog (29), response revision differing from `prepare_revision` (28), GET readback register/value showing the controller's divergent view (24, registers in the `90xx` range), and syslog `READBACK_OBSERVED` value contradicting the committed row (31, always the `release_value` bit). Witness = 21-byte header `RRCA-DAWN-WITNESS-v1\n` + 16 `|`-joined lines in ascending `gateway_seq` (1733 bytes), SHA-256 of which is the flag body.

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (redacted)

## Reflections

- Magic-byte brute force is a weak oracle on redundant arrays: stripe-0 parity made the ext4 superblock appear under nearly every geometry. The md `dev_roles[]` (not filenames, not magic) are the ground truth for member order.
- The WAL is part of the database: opening the SQLite file without its `-wal` sidecar (or dumping only `dispatch.sqlite` from the image) loses cycles 96–128 and yields a 13-line witness with a wrong hash. Copy the trio, open normally, count 128.
- DP-7's "HTTP status alone does not qualify" is literal here — all 128 exchanges are 201/200 on the wire. The discrimination is entirely in nonce/revision/register/value agreement across four sources (ledger, syslog, reservation response, readback view).

## Tools & references

- Python 3 stdlib (`struct`, `hashlib`, `sqlite3`, `zipfile`) + `debugfs` (read-only dumps) + provided `tools/raid5_extract.py`
- `capinfos`/`tshark` (capture recon: 128 connections × 19 frames)
- Linux `md_p.h` v1 superblock layout; mdadm RAID-5 algorithms (2 = left-symmetric); ext4 superblock magic `0x53EF`; SQLite WAL mode; RFC 5424 structured data

---
[⬅ Back to event](../../README.md)
