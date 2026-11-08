---
tags: [forensics, json, parser-differential, drone]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Phantom Drift

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| forensics | 675 | 124 | ✅ | — | 0xAr3s-root | Dragoş Bacitea |

## Challenge description

> Reconnaissance drone Valkyrie-9 drifted off its approved waypoint while the command server recorded the mission as nominal. Reconcile the recovered client and backend logic with the flight record, telemetry, and radio intercept to show how the diversion avoided the alarm.
>
> This is a constructed offline forensic case.
>
> Attachments: `drone_control.decompiled`, `command_backend.decompiled`, `flight_log.bin`, `mission_manifest.json`, `radio_intercept.log`, `telemetry_logs.json`.
>
> Flag format: `CSCTF{16_lowercase_hex}`
>
> Flag construction: SHA-256 the concatenated text `<APPROVED_LAT_4DP><APPROVED_LON_4DP><LAT_OFFSET_6DP><LON_OFFSET_6DP><DISTANCE_1DP>` with no separators, then use the first 16 lowercase hex characters. The flight-log tag verifies the last 8 characters of the same digest; it is not an input.
>
> Flag derivation: `sha256(f"{approved_lat:.4f}{approved_lon:.4f}{delta_lat:.6f}{delta_lon:.6f}{displacement_m:.1f}")[:16]`. `approved_*` = manifest coordinates; `delta_*` = per-axis delta between approved and diverted coordinates, 6 decimals (degrees); `displacement_m` = great-circle distance in meters between approved and diverted points, 1 decimal. The `TAG:` value in `flight_log.bin` matches the last 8 hex of the same sha256.

**Artifact files:** the six files above (not committed).

## TL;DR

The `waypoint_update` command carries each field twice, in snake_case (the approved 47.2591, 19.0402) and in PascalCase (the diverted 47.2600, 19.0450); the backend validated one spelling and the drone obeyed the other. The diversion is 0.000900° / 0.004800° = 376.2 m (WGS84 radius), and the flight-log tag selects that radius and confirms the digest → flag.

## Approach

**1. Recon — the two `.decompiled` files are base64 source, the rest is evidence**

`drone_control.decompiled` (C#, Unity, Newtonsoft.Json) and `command_backend.decompiled` (Go 1.21) are a header plus a `DECODED_CONTENT = "<base64>"`; decoding gives the sources (read only, nothing run). Both define the same `FlightParams` with JSON tags `altitude`, `speed`, `waypoint_lat`, `waypoint_lon`, `payload_weight`, `wind_compensation`, and the same validator: reject if `|lat − approved| > 0.001` or `|lon − approved| > 0.001` (about 111 m), against the hard-coded manifest 47.2591, 19.0402 (the same values as `mission_manifest.json`).

The radio log tells the story: at 12:30 ground station 3 sees the drone 380 m east of WP-Bravo, the drone controller says the waypoint was updated to 47.2600, 19.0450, and the command server answers "mission nominal, no anomalies". So validation passed for a command the drone executed differently. (I treat the radio's "~47.2600, 19.0450" as a lead and confirm it in the telemetry, not as the answer.)

**2. Hypothesis — one payload, two readings**

In `telemetry_logs.json` the `waypoint_update` record is the actual command. It contains each field twice:

```json
"waypoint_lat": 47.2591, "waypoint_lon": 19.0402, ...
"WaypointLat": 47.26,    "WaypointLon": 19.045,   ...
```

Duplicate/aliased keys are the classic parser differential: two parsers that normalise key names differently (case, underscores, last-one-wins, case-insensitive matching) see different values in the same bytes. Here the approved values sit under the key spelling the validator is happy with (47.2591 → delta 0 → "PASS"), while the diverted values (47.2600, 19.0450) sit under the other spelling. The rest of the evidence confirms which one the drone flew: the `transit_to_new_waypoint` GPS fixes move from (47.2591, 19.0402) through (47.26, 19.045) and keep drifting NE (47.2627, 19.0594), `waypoints_visited` lists `surveillance_target` at 47.26, 19.045, and `server_validation` says PASS with `discrepancy_detected: false` while `anomalies_detected` is empty. (I did not run either parser; the exact library behaviour is not needed for the flag, and the server's own note in the telemetry even misstates which value Go parsed, so I rely on the telemetry positions and the radio.)

**3. Exploitation — compute the flag, let the tag pick the Earth radius**

- `delta_lat = 47.2600 − 47.2591 = 0.000900`, `delta_lon = 19.0450 − 19.0402 = 0.004800` (positive: diverted minus approved);
- `displacement_m` by haversine. The statement does not say which Earth radius: with the mean radius 6,371,000 m the distance is 375.8 m; with the WGS84 equatorial radius 6,378,137 m it is **376.2 m**;
- `flight_log.bin` is a 24-byte header (`FLGT`, version, counters) followed by 12 bytes that are `TAG:xxxxxxxx` XORed with the mission id `Valkyrie-9` as repeating key (found with the known plaintext `TAG:` → key `Valk…`): the tag is `dc6836a2`.

Only the 376.2 m variant gives a SHA-256 whose last 8 hex characters are `dc6836a2`; the 375.8 m one ends with `2126c52e`, and the negative-delta variants don't match either. The tag thus validates both the radius and the sign convention, and the first 16 hex characters of that digest are the flag.

```bash
python3 -I solve/solve.py files
```

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (redacted)

## Reflections

- Two components that "parse the same JSON" do not necessarily read the same value: key aliases (case variants, duplicates) are enough to make a validator and an executor disagree, and a signature or tolerance check on one reading says nothing about the other.
- Read the whole evidence chain: the telemetry GPS track, the visited-waypoint summary and the radio log all agree on the diverted point, which is what the flag needs; the server's "PASS" is only the validator's view.
- The verification tag in the flight log is not just a check: with an under-specified formula (Earth radius, delta sign) it is the oracle that selects the right variant.
- Known plaintext (`TAG:`) found the XOR key without any guessing about its length.

## Tools & references

- Python 3 (`json`, `base64`, `math`, `hashlib`)
- Parser differentials / JSON interoperability issues, haversine great-circle distance, WGS84 equatorial radius

---
[⬅ Back to event](../../README.md)
