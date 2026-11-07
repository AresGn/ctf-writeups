---
tags: [network, mavlink, cryptography, key-reuse]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Severed Link

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| network | 120 | 84 | ✅ | — | 0xAr3s-root | Teodor Giurgica |

## Challenge description

> A reconnaissance drone on an ISR mission for an allied force in the Operation Dawn theatre takes orders from its field station over a signed MAVLink 2 link. Mid-mission the operator rotated the signing key, then pushed the new key over that same link while it was being recorded.
>
> Attached: the recording and the operator's notes. The uplink gateway is still online as it was during the incident. Show that an outsider can take the operator's place and command the aircraft.
>
> Flag format: `CSCTF{...}`

**Artifact files:** `files/mission.tlog`, `files/mission.pcap` (the same traffic over UDP/14550), `files/ops_notes.txt` (not committed). **Target:** a timed live instance (`w01.ctf.chronos-security.ro:<port>`, 30-minute TTL, a plain TCP MAVLink 2 relay).

## TL;DR

The operator rotated the MAVLink 2 link-signing key with a `SETUP_SIGNING` message sent *over the same signed link that was being recorded*; the new 32-byte key sits in plain sight in that message's payload. Replaying it is refused (anti-replay), but re-signing a fresh `HEARTBEAT` + `COMMAND_INT` `DO_REPOSITION` with that key and the gateway's own clock authenticates as the operator and returns the flag.

## Approach

**1. Recon — a signed link and a key handed out over itself**

`ops_notes.txt` gives the setup: operator is sysid 255, drone is sysid 1, every frame is MAVLink 2 signed. Mid-mission the signing key was rotated, but *in-band*, over the console link itself, instead of an out-of-band channel — "that was a mistake: the new key went out over a link that was being captured". `mission.tlog` (and the equivalent `mission.pcap`, MAVLink over UDP/14550) is exactly that capture.

A `.tlog` is a sequence of `(8-byte big-endian wall-clock microseconds, raw MAVLink 2 frame)` records. Parsing 107 frames gives mostly `HEARTBEAT`/`ATTITUDE`/`GLOBAL_POSITION_INT`, plus one `SETUP_SIGNING` (message id 256) from the operator (sysid 255) to the drone and one `COMMAND_INT` `DO_REPOSITION` (id 75, `MAV_CMD_DO_REPOSITION` = 192) — a real, previously-accepted reposition order.

**2. Hypothesis — the rotation message carries the new key in the clear**

`SETUP_SIGNING`'s wire payload (42 bytes: MAVLink reorders fields by size, longest first) is `initial_timestamp(8) · target_system(1) · target_component(1) · secret_key(32)`. Decoding it gives `target_system/component = 1/1` (the drone) and a 32-byte `secret_key`. I verified it is the active key by recomputing the signature (`SHA-256(key ‖ header+payload+CRC ‖ link_id ‖ timestamp)[:6]`) of every one of the 47 signed frames that follow the rotation in the capture: all 47 match. The key itself is never transmitted anywhere else, confirming the notes' claim that it "went out over a link that was being captured" — the capture is a complete, self-sufficient leak.

Connecting to the live gateway confirms the scenario end to end:

```
SB-7 uplink gateway online. Authenticate as operator: signed COMMAND_INT
DO_REPOSITION from sysid 255 under the fleet link key. Replayed frames are
refused, the signing timestamp must be current.
```

An unsigned `HEARTBEAT` is met with `DENIED: frame is not authenticated under the link key.` — so even the handshake must be signed with the recovered key.

**3. Exploitation — re-sign, don't replay**

Replaying the captured `DO_REPOSITION` bytes verbatim would be refused (its signing timestamp is stale and the gateway checks for replay). The signing timestamp field is the standard MAVLink 2 clock — 10-µs ticks since 2015-01-01T00:00:00Z — confirmed by a first probe: sending a freshly-signed but arbitrary timestamp got `DENIED: stale signing timestamp outside the freshness window. Link time is 37399709984355.`, which decodes to the exact wall-clock time of that attempt. So each frame must be signed with `round((now_utc − 2015-01-01T00:00:00Z) / 10 µs)` computed at send time.

The gateway also refuses a bare command: `REJECTED: send a HEARTBEAT first.` — so the sequence is a signed `HEARTBEAT` (sysid 255) to open the session, immediately followed by a signed `COMMAND_INT` `DO_REPOSITION` (reusing the reposition's own target coordinates from the capture, since only the signature needs to be fresh, not the content) addressed to the drone (sysid 1):

```bash
python3 -I solve/solve.py files/mission.tlog w01.ctf.chronos-security.ro <port>
```

The gateway answers:

```
OPERATOR AUTHENTICATED. Reposition accepted.
Audit receipt: CSCTF{...}
```

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (redacted)

## Reflections

- Rotating a compromised key over the very channel that is suspected compromised (or, here, being recorded) defeats the rotation: the new secret is exposed by the same capture that would expose the old one.
- MAVLink 2's `SETUP_SIGNING` places the raw key on the wire by design — it assumes the channel it travels over is already trusted/out-of-band; sending it back down the in-band link removes that assumption entirely.
- Anti-replay (a monotonically increasing signing timestamp) stops byte-for-byte replay but not forgery once the key is known: the fix is re-signing fresh content with the real key and the receiver's own clock, not resending captured frames.
- The gateway's own error messages (`DENIED: frame is not authenticated…`, `stale signing timestamp… Link time is …`, `send a HEARTBEAT first`) fully specified the protocol state machine; no blind guessing was needed.

## Tools & references

- Python 3 (`struct`, `socket`, `hashlib`, `datetime`), `tshark` (to confirm the pcap carries the same MAVLink 2/UDP traffic)
- MAVLink 2 packet signing (`SETUP_SIGNING`, message id 256) and framing (`COMMAND_INT`, `HEARTBEAT`)

---
[⬅ Back to event](../../README.md)
