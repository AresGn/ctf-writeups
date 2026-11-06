---
tags: [forensics, navigation, integer-arithmetic, gnss]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Signal Reconciliation

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| forensics | 120 | 51 | ✅ | — | 0xAr3s-root | — |

## Challenge description

> A state-linked actor altered a fictional reconnaissance receiver feed during mobilisation.
> Before the receiver profile is reused for recovery routing and civil-defence logistics
> coordination, reconcile its local-position export with the independently integrated
> local-navigation series and produce the complete response-cell record.
>
> Attachment: `signal-reconciliation.zip` — 13,341 bytes;
> SHA-256 `ea09de452b798a834f1da524c9e71b0d03b51a408b4c8285f2a489b33f951633`.
>
> Flag format: `CSCTF{BASE32_192_BIT_DIGEST}`.

**Artifact files:** `files/flight.ndjson` (not committed)

## TL;DR

Follow the `reconciliation-sop.txt` spec exactly: INS integration → residuals → qualifying-window enumeration → decision → canonical 603-line report → Base32 of first 24 bytes of SHA-256.

## Approach

**1. Parsing the inputs**

The zip contains:
- `flight.ndjson` — 601 JSON lines: `{i, t_ms, ve_mmps, vn_mmps, gps_e_mm, gps_n_mm}`
- `reconciliation-sop.txt` — complete algorithm spec
- `manifest.txt` — SHA-256 hashes of all files (integrity check)
- `mission-note.txt` — flavour / context

**2. INS reconstruction (exact integer arithmetic)**

```
ins_e[0] = ins_n[0] = 0
for i in 0..599:
    ins_e[i+1] = ins_e[i] + (ve[i] + ve[i+1]) // 20
    ins_n[i+1] = ins_n[i] + (vn[i] + vn[i+1]) // 20
res_e[i] = gps_e[i] - ins_e[i]
res_n[i] = gps_n[i] - ins_n[i]
```

Key requirement: no floating point, no rounding — Python's integer `//` is exact here.

**3. Qualifying window inventory**

`Q(i)` is true iff for a 10-sample window starting at `i`:
- All samples have distance ≥ 25 000 mm from origin: `res_e²+res_n² ≥ 625 000 000`
- East residual is monotonically increasing by ≥ 1 000 mm/step
- North residual changes by ≤ 500 mm/step

18 qualifying windows found: `5,35,50,66,84,95,182,214,247,287,331,365,403,420,453,465,542,567,588` — wait, let me recount: **18 entries** starting at those indices.

**4. Decision**

Final residuals: `res_e[600] = 100 000 mm`, `res_n[600] = 1 000 mm`  
`final_dist² = 10 001 000 000 ≥ 10 000 000 000` → threshold met.  
QSET is non-empty → **`QUARANTINE_GNSS_PROFILE`**

**5. Canonical report and flag**

```
603 lines:
  RECONCILIATION/2|samples=601|qset=5,35,...,588|decision=QUARANTINE_GNSS_PROFILE
  E|0|0|0|0|0|0|0|0
  E|1|100|...
  ...
  SUMMARY|qset=5,35,...,588|final_res_e=100000|final_res_n=1000|decision=QUARANTINE_GNSS_PROFILE
```

KAT verified: all-zero input → 14 329 bytes, SHA-256 = `cc8c52dc…` ✓

```bash
python3 solve/solve.py files/flight.ndjson
```

```
[+] Base32(24B)  : EOSL5C6VZ54TN2PWXUO2B5TVHMVY5G3NWPILLYY
[+] FLAG         : flag{...}
```

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}`

## Reflections

- The SOP is exhaustive — the challenge is really about reading carefully and implementing exactly.
- The KAT test vector is invaluable: it lets you verify the report format and byte count before
  computing the real answer.
- "Exact integer division" means Python's `//` (floor division), which works cleanly here
  because the sums are always divisible by 20.
- The flag is a 192-bit (24-byte) truncated SHA-256, Base32-encoded — no padding (`=`) as
  specified by RFC 4648 for unpadded encoding.

## Tools & references

- Python 3 (`json`, `hashlib`, `base64`)
- [RFC 4648 — Base32 encoding](https://datatracker.ietf.org/doc/html/rfc4648)
- Trapezoidal integration (INS dead-reckoning)

---
[⬅ Back to event](../../README.md)
