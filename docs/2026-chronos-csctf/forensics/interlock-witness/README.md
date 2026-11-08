---
tags: [forensics, modbus, pcapng, sha256]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Interlock Witness

| Category | Solves | Solved | First blood | Hint used | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| forensics | 99 | ✅ | — | no | 0xAr3s-root | Chronos Security |

## Challenge description

> While the response-cell interlock read false, a fictional grid-support station feeding an allied depot network that Operation Dawn relies on accepted maintenance writes. The controller took syntactically valid Modbus/TCP writes, and the supplied safety policy is an offline response-cell rule, not a controller feature.
>
> Reconstruct the accepted target writes that violate the policy and derive the incident witness. Work from the supplied files only.
>
> Attachment: `interlock-witness.zip`, 15,307 bytes, SHA-256: `d46d5b2b820e412db288dde2a3a3f991990622a702708cb9fc13e498d223995`
>
> Submit: `CSCTF{<64 lowercase hex characters>}`

**Artifact files:** `files/interlock-witness.zip` (not committed — currently at `forensics/interlock-witness.zip`)

## TL;DR

Replay the single Modbus/TCP flow offline, track the three interlock words (`0x000A`/`0x000B`/`0x000C`) from accepted FC03 observations and FC16 writes, keep the 16 target writes (at `0x0013`/`0x0014`) issued while the interlock was false, and hash `INTERLOCK-WITNESS/1\0 || request-PDU||response-PDU…` with SHA-256.

## Approach

**1. Recon — verify the bundle and inventory the capture**

```bash
sha256sum interlock-witness.zip
# d46d5b2b820e412db288dde2a3a3f991990622a702708cb9fc13e498d223995  matches
unzip -l interlock-witness.zip
# README.txt  interlock.pcapng  register-map.md
# interlock-policy.md  witness-format.md  provenance.json  SHA256SUMS
capinfos interlock.pcapng   # 512 frames, single lo interface, tcp port 502
tshark -r interlock.pcapng -q -z conv,tcp
# 127.0.0.1:59818 <-> 127.0.0.1:502 only
```

The three Markdown files are the whole spec — there is no hidden hint to find elsewhere:

- `register-map.md`: zero-based **PDU** addresses. `40011/40012/40013/40020/40021` are operator labels only. Mapped words: `0x000A` `maintenance_permit`, `0x000B` `isolation_state`, `0x000C` `protection_armed`, `0x0013` `trip_limit`, `0x0014` `restore_delay`.
- `interlock-policy.md`: the offline acceptance + safety rule (below).
- `witness-format.md`: the serialisation and hash, plus a non-incident verification vector.

Framing the TCP payloads by MBAP length gives **504 Modbus ADUs = 252 transactions** (TIDs 1–252, strictly sequential, no retransmission, no split/coalesced ADU): 124 FC03 pairs and 128 FC16 pairs, all with protocol `0x0000` and unit `0x01`. Every FC03 response carries byte count `22 = 2 × 11`, and every FC16 normal response echoes start + quantity — so the acceptance filters below reject **0** transactions in this capture. That still has to be checked, not assumed: it is what makes the 128 FC16 “accepted”.

**2. Hypothesis — an offline state machine, not a string hunt**

The flag is a SHA-256, so it cannot be carved from the capture. It has to be recomputed by replaying, in normal-response order:

1. **FC03 accepted** only if the immediately preceding FC03 request matches TID/proto/unit/function in the reversed flow and `byte_count == 2 × quantity`. It then updates every mapped word it covers. Here every FC03 reads `0x000A` quantity 11, i.e. `0x000A…0x0014`, so each accepted observation refreshes all five mapped words at once.
2. **FC16 accepted** only if its normal response matches TID/proto/unit/function and echoes start + quantity. Exceptions never change state. An accepted write applies **after** its normal response.
3. **Target** = accepted FC16 with quantity 1 at `0x0013` or `0x0014`. The policy states the 8 other accepted FC16 are ineligible; the capture indeed contains exactly 5 prerequisite writes (`0x000C=1` TID 2, `0x000A=1` TID 19, `0x000B=1` TID 20, `0x000B=0` TID 125, `0x000B=1` TID 142) and 3 acknowledgement writes (`0x0018/0x0019/0x001A`, TIDs 248/250/252), leaving 120 targets (60 per address).
4. **Unsafe** = at least one of `permit==1`, `isolation==1`, `protection==1` is false **immediately before the target's normal response** (so a write never judges itself, and a prerequisite write only counts from the next transaction on).

Two traps follow directly: using the displayed `400xx` references instead of PDU addresses finds nothing, and judging safety from the target's own written value — or after applying its response — misclassifies the boundary transactions.

State timeline from the replay (prerequisite triple only changes at these points):

| After TID | permit | isolation | protection | Cause |
|---|---|---|---|---|
| 1 (FC03) | 0 | 0 | 1 | initial observation |
| 21 (FC03) | 1 | 1 | 1 | TIDs 19+20 set permit/isolation |
| 126 (FC03) | 1 | 0 | 1 | TID 125 cleared isolation |
| 143 (FC03) | 1 | 1 | 1 | TID 142 restored isolation |

**3. Exploitation — select the unsafe targets and hash the witness**

Applying the rule gives **16 unsafe targets** out of 120: TIDs **4, 6, 8, 10, 12, 14, 16, 18** (interlock not yet established, `0,0,1`) and TIDs **127, 129, 131, 133, 135, 137, 139, 141** (isolation dropped, `1,0,1`). The other 104 targets see `1,1,1` and are safe.

For each unsafe target, in normal-response order, append the request PDU (`function-code || function-data`, **no MBAP**) then the normal-response PDU: `T` is `16 × (8 + 5) = 208` bytes. With `P = "INTERLOCK-WITNESS/1" || 0x00` (20 bytes), `W = SHA-256(P || T)`.

The solver is stdlib-only (its own pcapng/Ethernet/IPv4/TCP/Modbus framing) and first asserts the published vector — request `10 00 13 00 01 02 00 2a` + response `10 00 13 00 01` → `b6e58fa9…f34786` — before touching the incident capture:

```bash
python3 solve/solve.py ../interlock-witness.zip
# [*] Vector OK    : b6e58fa962e382b112eb596e416d5680495fc4bd02141f2389797f194df34786
# [*] Modbus ADUs  : 504
# [*] FC03 accepted: 124 (rejected 0)
# [*] FC16 accepted: 128 (rejected 0), targets 120
# [*] Unsafe targets: 16 (normal-response order)
#     TID   4 permit=0 isolation=0 protection=1 req=100013000102040d resp=1000130001
#     ...
#     TID 141 permit=1 isolation=0 protection=1 req=1000140001020a9a resp=1000140001
# [*] T (208 bytes): 100013000102040d1000130001...
# [+] FLAG         : CSCTF{...}
```

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (redacted)

## Reflections

- Read the three spec files as one contract before opening Wireshark: acceptance, target eligibility, safety instant and serialisation are four separate filters, and each one changes the hash.
- “Immediately before its normal response” plus “applies after its normal response” is the whole timing model. Evaluating at request time happens to agree here only because requests and responses are strictly sequential — the response-order replay is the safe implementation.
- A clean synthetic capture still needs the rejection checks: verifying 124/124 FC03 and 128/128 FC16 accepted (and TCP sequence continuity, no retransmission) is what justifies treating every FC16 target as in-scope.
- The `400xx` labels are the deliberate addressing trap: all filtering must use zero-based PDU addresses (`0x000A…0x0014`).

## Tools & references

- Python 3 stdlib (`struct`, `hashlib`, `zipfile`) — solver needs no third-party package
- Wireshark / `tshark`, `capinfos` (recon cross-checks only)
- Modbus/TCP MBAP + FC03/FC16 (0x10) PDU layouts; pcapng block format

---
[⬅ Back to event](../../README.md)
