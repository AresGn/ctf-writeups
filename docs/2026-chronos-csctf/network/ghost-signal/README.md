---
tags: [network, ss7, diameter, telecom-fraud, cross-validation]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Ghost Signal

| Category | Solves | Solved | First blood | Hint used | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| network | 145 | ✅ | — | yes | 0xAr3s-root | Dragoş Bacitea |

## Challenge description

> A telecom operator is seeing fraudulent roaming activity and disputed billing events. Investigators recovered SS7 signalling, Diameter sessions, and the related billing export.
>
> Reconstruct the intrusion chain from those records and recover its marker. This is a constructed, offline protocol-forensics case.
>
> Attachments: `ss7_capture.pcap`, `diameter_capture.pcap`, `billing_events.json`.
>
> Flag format: `CSCTF{8_lowercase_hex}`
>
> Flag construction: SHA-256 the literal text `<IMSI>:<SESSION_ID>:<FIRST_ANOMALOUS_BILLING_TIMESTAMP>`, then use the first 8 lowercase hex characters. Use the values exactly as written in the evidence and literal `:` separators.
>
> Flag derivation (serialization spec): `sha256("<imsi>:<full_diameter_session_id>:<unix_timestamp>")[:8]`, lowercase hex. `imsi` = the anomalous IMSI as decimal (e.g. `226012014000001`). `full_diameter_session_id` = the entire Session-Id including dots and semicolons (e.g. `host.example.com;seconds;id`), not just the GT fragment. `unix_timestamp` = unix seconds (integer) of the first anomalous billing event, not ISO. Fields joined as strings with `:` between them. No hosts, no GTs, no event ids.
>
> Hint: Several capture files were pulled from different networks during the same incident. Start by cataloguing what each file records, then hunt for the single thread that runs through all of them.

**Artifact files:** the three files above (not committed).

## TL;DR

One IMSI (`226012014000001`) and one Diameter `Session-Id` (`hss.eastern-tele.ro;1723740150;49211`) appear, byte-for-byte identical, in all three records — the SS7 capture's `updateLocation`, the Diameter capture's AVPs, and the billing export's anomalous rows. Serializing that IMSI, that full session id and the timestamp of the first anomalous billing row (`1723740150`) and hashing it gives the flag.

## Approach

**1. Recon — catalogue each file on its own**

- `billing_events.json`: a Diameter OCS export for `eastern-tele.ro`, 40 events. 30 ordinary `CCR-A` rows (one IMSI each, `2260120140002000`…`2260120140002011` cycling, i.e. 16-digit synthetic subscriber ids) interleaved with two short anomalous bursts: 5 `CCR-I` rows (`atk_0000`…`atk_0004`, `charging_amount: 0.0`, `anomaly: "zero_charge_on_roaming"`, `redirect_host: "intercept-49211.evil-domain.net"`) and 5 `CCA` rows (`pivot_0000`…`pivot_0004`, `anomaly: "unusual_routing_path"`, `serving_cscf: "cscf.pivot.eastern-tele.ro"`, `redirect_host: "redirect-49211.evil-domain.net"`). All ten share one `imsi` (`226012014000001`, 15 digits — a real-looking IMSI, unlike the synthetic baseline ones) and one `session_id`: `hss.eastern-tele.ro;1723740150;49211`.
- `ss7_capture.pcap`: GSM MAP over M3UA/SCCP. A baseline of `sendRoutingInfo`/`sendRoutingInfoForSM` queries runs with the calling-party Global Title climbing steadily, `49100`→`49144` (routine roaming partners). At `t=150` the calling GT jumps to **`49211`** for a burst of `sendRoutingInfo`/`sendRoutingInfoForSM` queries against `+40721000101`…`+40721000105` — the exact numbers targeted by the `atk_000x` billing rows. From `t=190` the calling GT moves again to `49311` and issues `updateLocation` for IMSI **`226012014000001`** — the attacker re-registering that subscriber's location, the actual hijack.
- `diameter_capture.pcap`: Cx/Ro-style Diameter. Ordinary sessions have `Origin-Host` = the serving `cscfN.eastern-tele.ro` and `Session-Id` = `hss.eastern-tele.ro;<ts>;<n>` with `n` counting up normally. One session stands apart: `Session-Id = hss.eastern-tele.ro;1723740150;49211`, with requests from `Origin-Host = cscf.rogue.evil-domain.net` and an answer naming `cscf.pivot.eastern-tele.ro` as serving CSCF — matching the billing export's `pivot_*` rows exactly. Its `Subscription-Id-Data` AVP is `226012014000001`.

**2. Hypothesis — the hint says to find the thread, not to trust any single file**

Each file on its own only shows part of the picture (a GT, a rogue host, an anomaly tag); the brief and hint explicitly ask to reconcile them. Checking that there is exactly **one** anomalous IMSI and **one** anomalous `session_id` across the whole billing export (`set` of each has size 1) rules out ambiguity, and the same IMSI and the same `49211` fragment of the session id are the values that appear, unchanged, in the SS7 capture (`e212.imsi` in the `updateLocation`) and in the Diameter capture (`Subscription-Id-Data`, and the `49211` suffix of `Session-Id`). That is the "single thread": GT `49211` ran the Diameter-side billing fraud and routing reconnaissance, GT `49311` carried out the SS7-side location hijack, and the one subscriber IMSI ties both to the same victim — three independent captures of the same incident, cross-validated rather than taken on faith.

The spec is explicit about what *not* to use: no hostnames, no GTs, no event ids — only the IMSI, the full `Session-Id` string (dots, semicolons and all), and the Unix timestamp of the first anomalous billing row, which is `atk_0000` at `1723740150` (also, not coincidentally, the timestamp embedded in the session id itself).

**3. Exploitation — serialize and hash**

```text
226012014000001:hss.eastern-tele.ro;1723740150;49211:1723740150
```

```bash
python3 -I solve/solve.py files
```

The script re-derives the anomalous IMSI/session/timestamp from the JSON alone, then cross-checks both pcaps with `tshark` field extraction to confirm the same IMSI and the same `Session-Id` are present on the wire before hashing.

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (redacted)

## Reflections

- Three files from "different networks" describing one incident is a cross-validation exercise: the right answer is whatever value is identical, byte-for-byte, in all of them, not whatever looks most suspicious in a single file.
- A deliberately rising baseline (GTs `49100`→`49144`, synthetic IMSIs `…002000`→`…002011`) makes the one-off, out-of-sequence values (`49211`, `49311`, a 15-digit real-looking IMSI) stand out without needing a packet-by-packet read.
- The two attacker GTs (`49211` for Diameter fraud/recon, `49311` for the SS7 location hijack) are not the same value and neither alone is "the" answer; the flag format explicitly excludes GTs for that reason — the IMSI and the full session id are what actually corroborate across protocols.
- `full_diameter_session_id` means exactly that: the whole AVP string with its separators, not just the trailing counter that happens to match a GT.

## Tools & references

- `tshark` (`-T fields`) for both pcaps, Python 3 (`json`, `hashlib`, `subprocess`)
- GSM MAP (`sendRoutingInfo`, `sendRoutingInfoForSM`, `updateLocation`) over SS7/M3UA; Diameter Session-Id / Subscription-Id-Data AVPs (3GPP Cx/Ro-style exchanges)

---
[⬅ Back to event](../../README.md)
