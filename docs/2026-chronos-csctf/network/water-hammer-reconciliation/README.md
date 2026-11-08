---
tags: [network, modbus, pcap, tcp-reassembly, forensics]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Water Hammer Reconciliation

| Category | Solves | Solved | First blood | Hint used | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| network | 124 | ✅ | — | no | 0xAr3s-root | Cosmin Gorea |

## Challenge description

> The Vardessa Civil Water Reserve header was isolated after a hostile engineering-station interval, part of a wider campaign against emergency water logistics that coalition analysts tie to an Ash Army proxy. Vardessa is an Operation Dawn partner.
>
> Reconstruct the complete confirmed Modbus/TCP control history and submit the reconciliation identifier the evidence supports. `water-hammer-reconciliation.zip` holds all three evidence files: the capture `reserve-header.pcapng`, `station-profile.txt` and `capture-manifest.txt`. `station-profile.txt` defines the scoped conversation, the confirmation rule, the safety screen, the report grammar and the submission encoding; `capture-manifest.txt` identifies the evidence and its provenance. No live plant, external service or credential is involved.
>
> The capture holds ordinary reads, one exception and one unanswered write. A write acknowledgement on its own is not a confirmed control snapshot, so follow the profile's matched-readback rule.
>
> Flag format: `CSCTF{message}`

**Artifact files:** `files/reserve-header.pcapng`, `files/station-profile.txt`, `files/capture-manifest.txt` (not committed).

## TL;DR

Reassemble the single Modbus/TCP conversation, keep only FC16 writes whose unique normal echo is followed by the exact FC3 readback with a unique matched answer (64 snapshots), serialize them in the canonical report with the integer-only unsafe mask, SHA-256 it and Base32-encode the first 24 bytes → flag.

## Approach

**1. Recon — the profile is the specification**

`station-profile.txt` fixes everything: the scoped conversation (`192.0.2.10:<ephemeral>` → `192.0.2.20:502`, unit 17), the strict MBAP grammar (protocol id 0, Length = 1 + PDU, no truncation or trailing bytes), the register map (0x1000 pump target, 0x1001 gate permille, 0x1002 armed, 0x1003 ramp µs), the confirmation rule, an integer safety screen (E, V, Q with `T_US = 37558`), the exact report text `R` and the encoding (`SHA-256(R)` → first 24 bytes → unpadded Base32 → 39 characters), plus a public synthetic test vector. `capture-manifest.txt` only gives provenance and the capture's SHA-256, which matches (`6af88183…`).

The capture is one TCP conversation (client port 36853) of 536 frames, 2,190 client bytes and 1,933 server bytes. Segment boundaries do not matter: some ADUs are split across segments, so I reassembled each direction by TCP sequence number and framed the byte streams by the MBAP length. Client function codes: 68 FC3 and 66 FC16; server: 68 FC3, 64 FC16 normal responses and one FC16 exception (`0x90`, code 04).

**2. Hypothesis — a snapshot needs four things, in order**

A write counts only if: (1) the FC16 request is a valid candidate (unit 17, start/quantity inside 0x1000–0x1003, Length `7 + 2N`, byte count `2N`); (2) exactly one normal response with the same transaction id comes back with the exact `10 || A || N` echo (the exception, an unpaired request and any duplicate or mismatched echo never confirm); (3) the immediately next client ADU after that response is exactly `FC3 1000 0004` (unit 17, Length 6); and (4) its response is unique with Length 11 and `03 08` + 8 bytes. The row values are the **FC3 readback registers**, not the written data, and the report `tid` is the **FC16 response** transaction id (here `2000`, `2011`, `2022`… while the FC3 ids look like `8000`, `8013`…). Snapshots are ordered by the frame ordinal of the FC16 response.

Decoys to discard: initial harmless FC3 reads (`e010`, `e011`), the FC16 exception (`e100`), and the final unpaired FC16 request. The result is exactly the 64 snapshots the profile announces.

**3. Exploitation — serialize and hash**

With the initial tuple (80, 500, 0, 60000): `E = P·G/1000`, `V = E·10⁶/70686` (integer floors), `Q = 998·1065·|V − V_prev|`, `UNSAFE = A=1 ∧ R < 37558 ∧ Q > 9000·10⁵`; the mask is `Σ UNSAFE_i · 2^(63−i)` as 16 uppercase hex digits. I first checked my formulas against the public test vector (V₋₁ = 565, row 0: E=160, V=2263, Q=1804753260, mask `8000…`, SHA-256 `401df824…`, Base32 `IAO7QJHG…`): all match exactly. On the real data every one of the 64 rows is armed, below the ramp threshold and has a velocity change (the "attack interval" evidence checks), 22 of them exceed the Q limit, and the mask is `D3FC7C00A3060000`. The canonical report is hashed and the first 24 bytes encoded in Base32 (39 characters).

```bash
python3 -I solve/solve.py files
```

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (redacted)

## Reflections

- When the statement ships a specification and a test vector, implement the vector first: matching it to the byte (including the Base32) removes whole classes of off-by-one and encoding doubts before touching the real data.
- Reassemble the TCP streams before parsing: a packet-by-packet read would split or merge ADUs, and the profile says explicitly that segment boundaries create no events.
- "Matched readback" means the report uses the device's readback, not the command; and the identifier to serialize is the FC16 *response* tid, a detail that is easy to get wrong.
- All arithmetic stayed in Python integers: Q reaches about 2.4·10⁹, beyond signed 32-bit.

## Tools & references

- `tshark` (conversation overview), Python 3 (`struct`, `hashlib`, `base64`; own pcapng and TCP reassembly)
- Modbus Application Protocol v1.1b3 (FC3, FC16, exceptions), Modbus/TCP MBAP header, RFC 4648 Base32

---
[⬅ Back to event](../../README.md)
