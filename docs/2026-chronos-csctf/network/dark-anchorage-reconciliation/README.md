---
tags: [network, sensor-fusion, ais, radar, geodesy, blind-api]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Dark Anchorage Reconciliation

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| network | 302 | 101 | ✅ | — | 0xAr3s-root | Chronos Security |

## Challenge description

> Kaldura, an Operation Dawn ally, carries coalition traffic over the KALNET-1 cable, and KALNET-1 failed just as a hostile maritime operation was expected near the cable corridor. AIS says no suspicious vessel crossed the fault envelope, yet coastal radar recorded anonymous contacts on a different clock.
>
> Produce the complete sensor-reconciliation report that identifies the false broadcast, quantifies the displacement and establishes the actual closest approach. Read `GET /schema` for the report format. The four evidence files are `GET /files/ais.ndjson`, `GET /files/radar.csv`, `GET /files/cable-fault.txt` and `GET /files/method-note.txt`. Submit one complete report to `POST /reconcile`; a correct report returns the reconciliation code.
>
> Flag format: `CSCTF{...}`

Hint: *Normalize the declared radar clock, then score every radar/AIS association across its whole paired trajectory, not at one point near the cable.*

**Artifact files:** live instance only (`http://<target>:<port>/`, expired); the four evidence files are served by it.

## TL;DR

Subtract the radar header offset (180 min) to pair radar and AIS samples, match the 16 tracks by median residual, find the one AIS track that drifts by (330, 330) m for 4 samples, compute the radar-only segment CPA to the cable point, and POST the report — the hard part is the undocumented JSON shape, where the vector must be two separate members.

## Approach

**1. Recon — the method note is the spec**

`method-note.txt` gives the whole algorithm: radar `local_time` = UTC + header offset (`# radar_utc_offset_minutes=180`), pair equal normalized UTC samples, local plane around the cable point (`east=R·cos(lat0)·Δlon`, `north=R·Δlat`, R=6378137), score by median residual, longest ≥4-sample run with residual ≥250 m and component steps ≤15 m for the divergence, radar-only segment CPA with clamped projection. `/schema` lists member names and tolerances (3 m, 2 s) but **no example body**.

**2. Hypothesis — a full bijection with a trivially low score, one liar**

With the offset subtracted, every radar track R-01..R-16 matches exactly one AIS MMSI with a median residual of 0 m (wrong pairs are ≥180 m, so there is no ambiguity). Looking at per-sample residuals instead of the median finds the liar: R-03 / MMSI `979103829` is 466.7 m off — exactly (330 m E, 330 m N) — at 10:26, 10:28, 10:30 and 10:32 UTC. Radar-only CPA over all segments is R-03 itself, passing through the cable point on the 10:30→10:32 segment at u≈0.818.

**3. Exploitation — getting the report accepted**

`POST /reconcile` answered `400 invalid report` to everything, with no hint (a semantic mismatch would be `422 report not accepted`). 400 vs 422 is the oracle: I swept ~350 shapes (associations as objects/strings/dict, interval as two keys or a list, vector as list/object, string offsets, wrappers) until one returned 422. The accepted shape:

```json
{"version":"KALNET-RECON-1","radar_utc_offset_minutes":180,
 "associations":[{"radar_track":"R-01","mmsi":"<9 digits>"}, "... x16"],
 "divergence":{"mmsi":"<9 digits>","start_utc":"...Z","end_utc":"...Z",
               "ais_minus_radar_east_m":330,"ais_minus_radar_north_m":330},
 "closest_approach":{"mmsi":"<9 digits>","utc":"...Z","distance_m":0.0}}
```

The remaining 422 was my own bug: I converted the CPA time with `datetime.timestamp()` on a naive datetime, which shifted it by my local timezone (09:31:38 instead of 10:31:38). Using `calendar.timegm` fixed it and the server returned the flag.

```bash
python3 solve/solve.py http://<target>:<port> --post
```

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (redacted)

## Reflections

- When an API gives no example, status codes are the oracle: the 400 → 422 transition proves the *structure* is right before the *values* are checked. Sweep shapes with a thread pool and print only non-400 answers.
- Do not trust a "validation" that fails on both structure and values at once: after finding the shape, a second bug (timezone) was still hiding. Verify derived values against the data (the CPA time had to fall in the 10:30–10:32 segment, not 09:31).
- Always use timezone-explicit time functions (`calendar.timegm`, `timezone.utc`); naive `timestamp()` silently uses the machine timezone.

## Tools & references

- Python 3 (`urllib`, `csv`, `statistics`, `concurrent.futures`), `curl`
- Local tangent-plane projection, segment closest-point-of-approach formula from `method-note.txt`

---
[⬅ Back to event](../../README.md)
