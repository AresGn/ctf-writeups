---
tags: [forensics, ics, iec-104, pcap, incident-response]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# silent-breaker

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| forensics | 369 | 81 | ✅ | — | 0xAr3s-root | Dan-Andrei Grigorescu |

## Challenge description

> A regional substation breaker tripped without warning. You have console access to Velkarion Mobile's signaling investigation tool and a forensic bundle from the substation's IEC 60870-5-104 network. Reconstruct what happened and who is responsible.
>
> Endpoint: GET /events for the flagged-signaling feed; start at GET /files/ for the case-file index and report contract; submit the completed report to POST /submit.
>
> Flag format: `CSCTF{...}`

**Artifact files:** downloaded from the instance's `/files/` index: `README.md` (report contract), `description.md`, `roster.json`, `iec104_capture.pcap`, `hmi_monitoring.log` (not committed). Live instance `http://w01.ctf.chronos-security.ro:39328` (30-minute lifetime, expired); each launch is a different case with different data.

## TL;DR

Join the signalling events from a non-legitimate GT with the staff roster to find the employee with OT-VPN access, read the breaker `ON` command (IOA, qualifier, wire time) in the IEC 104 pcap, take the frozen current from the `QUALITY=SUSPECT` run of the historian log, and submit these five values with the employee's VPN session id; the service returns the flag as `clearance_code`.

## Approach

**1. Recon — read the contract before touching the console**

`GET /files/` lists the case files and a contract (`/files/README.md`) that defines everything: `/events` (free), `/query/subscriber` and `/query/vpn-window` (budgeted), `POST /confirm-target` (**2 attempts**, correct target unlocks the VPN route) and `POST /submit` (**5 complete reports**, pass/fail only). The report has five fields: `ioa_address`, `command_qualifier`, `command_time_utc` (wire time, not VPN start), `telemetry_status` (frozen current of the suspect run) and `vpn_session_id`. Because attempts are scarce, every value must be derived offline before submitting.

**2. Hypothesis — four independent sources give the five fields**

- **Who**: `/events` says any GT outside `GT-0000..GT-0999` is not a legitimate peer. Six events come from `GT-7779-Q22` (UpdateLocation / SendRoutingInfoForSM) for six MSISDNs. Matching them against `roster.json`: only **Sanda Ionescu, `VLK-1944-ION`, OT Field Engineering**, has `ot_vpn_access: true`; the others (Finance, HR, Legal, Customer Care) cannot reach the OT VPN. Two `/query/subscriber` lookups confirmed both numbers I tried were watchlisted (budget 8).
- **What was sent**: in the pcap (TCP 2404), among regular `M_ME_NC_1` reports (type 13, IOA `0x21fb`) one frame goes the other way, master → RTU, at 08:55:36 UTC: `68 0e … 2d 01 06 00 01 00 fb 21 00 01` = type 45 `C_SC_NA_1` (single command), COT 6 (activation), IOA bytes `fb 21 00` = **0x21fb**, SCO `01` = **ON**; the RTU answers with COT 7 (activation confirmation) at the same second. So the command time is **08:55** (the report wants `HH:MM`).
- **Forged current**: `hmi_monitoring.log` shows normal readings of about 452–455 A (±1.5 A), then from 08:54:40 a constant **426.0 A** that the historian marks `QUALITY=SUSPECT` from 08:55:00 until 08:57:30 (the first two identical readings are still `GOOD` since the rule needs three). On the wire, the RTU's own readings keep varying and return to about 453 A, so 426.0 A is a held/replayed historian record, not a live value: `telemetry_status = 426.0`.
- **Which session**: given only after a correct `/confirm-target`.

**3. Exploitation — confirm the target, get the session, submit**

```bash
python3 -I solve/solve.py http://<target>            # derive and print the report (GET only)
python3 -I solve/solve.py http://<target> --submit   # confirm-target + vpn-window + submit
```

`/confirm-target {"employee_id":"VLK-1944-ION"}` returned `confirmed`, and `/query/vpn-window` listed five sessions; the one for `VLK-1944-ION` is `VPN-914973` (Access-Accept at 08:21:41 with an OTP challenge, source IP `203.0.113.197`). It is a different session from the ones opened at 08:55 or later by other users, which are decoys timed close to the command. The first complete report was accepted (4 attempts left) and returned the flag.

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (redacted)

## Reflections

- Read the contract first: with 2 and 5 attempts, deriving the answers offline from the evidence is the whole game, so no guessing was needed.
- Do not take the VPN session that starts closest to the command; the report asks for the session of the compromised employee, whose start is earlier (the statement says "wire time of the command, not VPN session start").
- A historian-side `SUSPECT` marker lives in the log, not on the wire: the pcap shows the RTU kept reporting live values, which is what proves the displayed 426.0 A was frozen.
- The solve script derives every field from the instance's own files, since a relaunch gives a new case.

## Tools & references

- `curl`, `tshark` (to list frames), Python 3 (`urllib`, `struct`, own pcap parsing)
- IEC 60870-5-104 / IEC 60870-5-101 ASDU: types 13 (`M_ME_NC_1`) and 45 (`C_SC_NA_1`), causes of transmission 6/7

---
[⬅ Back to event](../../README.md)
