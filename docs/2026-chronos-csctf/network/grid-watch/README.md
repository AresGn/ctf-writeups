---
tags: [network, mavlink, cryptography]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Grid Watch

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| network | 672 | 75 | ✅ | — | 0xAr3s-root | Marius Merai |

## Challenge description

> Vultur Dynamics drones patrol the RGN-Grid high-voltage network. An adversary wants one diverted off its corridor. You have a packet capture of a drone's MAVLink 2 command link and live access to the drone itself. Make the drone accept your own reposition command. Unsigned and replayed commands are refused — the flag returns only from a command the drone actually accepts.
>
> Interact only with your assigned instance.
>
> Flag format: `CSCTF{...}`

**Artifact files:** `files/capture.tlog`, `files/provisioning_note.md` (not committed). Live instance: TCP `w02.ctf.chronos-security.ro:32773` (expired).

## TL;DR

The drone only accepts MAVLink 2 signed commands, with a custom clock: calibrating the RTC from the capture (+17 ppm, commissioning epoch 1733965123) lets me derive the provisioning key by HKDF from the per-connection nonce, re-provision my own signing key with `SETUP_SIGNING`, then — signed with that key — set GUIDED, arm, and send `DO_REPOSITION`, which returns the flag.

## Approach

**1. Recon — a signed link, a calibration problem and a back door with a derived key**

`capture.tlog` holds 24 MAVLink 2 signed packets (GCS 255/190 ↔ drone 1/1, link_id 249): heartbeats, `STATUSTEXT` announcing the serial `CX-FALCON-9951`, a `COMMAND_LONG 511`, `GLOBAL_POSITION_INT` reports. Every packet carries a 13-byte signature (link_id, 48-bit timestamp in 10 µs ticks, SHA256-48), so replaying the capture is useless: timestamps are checked and the session key is not in the capture.

`provisioning_note.md` is the way in: keys can be re-provisioned with `SETUP_SIGNING`, authenticated by `prov_key = HKDF-SHA256(ikm = serial_ascii || commissioning_epoch_le64, salt = session_nonce, info = "CX-PROV/v1", L = 32)`. The serial is known; the nonce is announced at connect (`PROV NONCE …`); what is missing is the commissioning epoch — and any timestamp I sign with must match the drone's odd RTC (ticks since the commissioning epoch, *not* the MAVLink 2015 epoch, with a per-unit offset and ppm drift to calibrate).

**2. Hypothesis — the capture's two clocks give the epoch and the drift**

Each tlog record has a host timestamp (µs), and each packet a signing timestamp. Pairing them: the signing timestamps grow by 3,100,052–3,100,053 ticks per 31.000000 s of host time, a constant slope of **100001.7 ticks/s = +17 ppm**. With that slope, `signing_ticks = round((unix_time − E)·100001.7)` fits all 24 packets to within half a tick for **E = 1733965123** (2024-12-12 00:58:43 UTC) and zero extra offset. I validated the model live before using it: predicted signing timestamps bracketed the drone's own signature timestamps at connect (before/after the round trip). That fixes both HKDF's epoch input and the clock for every packet I forge.

The drone's own error messages then mapped the rest of the protocol: an unsigned `SETUP_SIGNING` → `REJECT: unsigned message`; a `SET_MODE` message → `REJECT: not a command for this drone` (it only takes `COMMAND_LONG`); arming before GUIDED → `REJECT: must be in GUIDED before arming`; command 512 → `REJECT: unexpected command 512`, while **192 is its `DO_REPOSITION`** (`REJECT: DO_REPOSITION requires GUIDED + ARMED`). So the flight order from the note — GUIDED, arm, command — is enforced literally.

**3. Exploitation — re-provision, then fly the normal order, all in one connection**

The nonce is per-connection, so everything happens on a single TCP connection, each packet signed with `SHA256-48(key ‖ packet ‖ link_id ‖ timestamp)` and a fresh, monotonically increasing RTC timestamp:

1. Read `PROV NONCE`, compute `prov_key` by HKDF (salt = nonce as raw bytes from hex).
2. `SETUP_SIGNING` (msg 256): a new session key of my choice (the script uses `SHA256("gridwatch-session-key-v1")`, any 32 bytes work), `initial_timestamp` = its own signature timestamp, packet signed with `prov_key` → `signing re-provisioned: new key active`.
3. Signed with the new key: `COMMAND_LONG 176` (`DO_SET_MODE`, param1=1, param2=4) → `mode GUIDED`; `COMMAND_LONG 400` (arm, param1=1) → `ARMED`; `COMMAND_LONG 192` (`DO_REPOSITION`, param5/6/7 = 45.6 / 24.1 / 100) → `COMMAND_ACK` plus a `STATUSTEXT` carrying the flag.

```bash
pip install pymavlink
python3 solve/solve.py w02.ctf.chronos-security.ro 32773
```

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (redacted)

## Reflections

- The capture is not there to be replayed but to be *measured*: two timestamps per packet are enough to recover the RTC's epoch and ppm drift exactly (residuals under half a tick over 24 packets).
- I checked the clock model against the live drone before sending anything forged — a wrong epoch also breaks the HKDF input, so that one fit unlocks both the key and the timestamps.
- The server's rejection messages are a specification: each failed probe (`SET_MODE`, 512, arming early) removed one unknown, leaving 176 → 400 → 192 as the only accepted order.
- Everything must share one connection because the HKDF salt (the nonce) is announced per connection.

## Tools & references

- Python 3 + pymavlink (common dialect, message packing / CRC extras), `hashlib`/`hmac` for HKDF-SHA256 and SHA256-48 signatures
- MAVLink 2 packet signing and `SETUP_SIGNING` (message 256), `COMMAND_LONG` commands 176 / 400 / 192

---
[⬅ Back to event](../../README.md)
