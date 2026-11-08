---
tags: [misc, icalendar, rfc5545, rrule, exdate, recurrence-id, python]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Command Calendar Reconciliation

| Category | Solves | Solved | First blood | Hint used | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| misc | 141 | ✅ | — | no | 0xAr3s-root | Chronos Security |

## Challenge description

> A hostile edit scrambled the Vardanne Civil Continuity Service's emergency relay calendar during a national communications outage. The service keeps civil relays running behind coalition lines in Operation Dawn, and routing cannot be restored until the control room has every activation in the published response window.
>
> `GET /brief` gives the response window, the membership and ordering rules, and the exact attestation format. `GET /case.ics` returns the exported iCalendar file. Rebuild the activations from the calendar and submit the complete UTC attestation as one JSON object to `POST /attest`; a correct attestation returns the restoration code.
>
> Flag format: `CSCTF{...}`

**Artifact files:** live instance only (`http://<target>:<port>/`, expired)

## TL;DR

Expand three `VEVENT` series (`RRULE` + `RDATE` − `EXDATE`), apply the detached `RECURRENCE-ID` overrides *after* expansion, keep occurrences whose **actual** `DTSTART` falls in `[horizon_start, horizon_end)`, sort, and POST the 24 records.

## Approach

**1. Recon — the brief is the spec**

`/brief` states the rules: window `2026-06-29T00:00:00Z` ≤ start < `2026-07-14T00:00:00Z` using the *actual* `DTSTART` after detached replacement (no overlap tests, no clipping), strictly ascending `start_utc`, exactly 24 records with exactly `uid, recurrence_id_utc, start_utc, end_utc, category`, and a strict JSON parser (no duplicate member names, no extra members). `case.ics` has 3 series (UIDs `relay-1..3`) and 2 detached instances of `relay-1`.

**2. Hypothesis — where a naive expansion goes wrong**

- `COUNT` includes `DTSTART`, and `RDATE`s add identities that the rule does not produce (e.g. `relay-3` 2026-06-29T13:00, `relay-2` Saturday 2026-07-04).
- `EXDATE` removes a *nominal identity* before any replacement (`relay-1` 2026-07-05).
- A detached instance is keyed by `RECURRENCE-ID` (nominal original) but carries its own `DTSTART`/`DTEND`: `relay-1` 06-29T08:00 → moved to 06-28T07:00 (**leaves** the window), and 07-15T08:00 → moved to 07-13T07:00 (**enters** the window, even though its nominal date is outside). Filtering on the nominal date gets both wrong; `recurrence_id_utc` must still report the nominal original.
- `UNTIL=...Z` with a naive `DTSTART` makes `dateutil` raise: use a UTC-aware start for expansion.

**3. Exploitation**

```bash
pip install python-dateutil
python3 solve/solve.py http://<target>:<port> --post
```

The script expands each master with `dateutil.rrule`, adds `RDATE`, subtracts `EXDATE`, replaces matching nominal identities by their detached instance, filters on the actual start, sorts by `start_utc` and posts `{"activations":[...]}`. It yields exactly 24 records, and the server answers with the restoration code (the flag).

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (redacted)

## Reflections

- iCalendar semantics are an order of operations: expand → `RDATE` → `EXDATE` → detached replacement → filter on the *actual* start. Any other order produces plausible but wrong sets.
- The brief's expected count (24) is a cheap self-check: it caught nothing here because the order was right, but would have exposed a missed `RDATE` or override immediately.
- Watch library edge cases (`UNTIL` in UTC vs naive `dtstart`) rather than hand-rolling RRULE.

## Tools & references

- Python 3, `python-dateutil` (`rrulestr`), `urllib`
- RFC 5545 (RRULE, RDATE, EXDATE, RECURRENCE-ID)

---
[⬅ Back to event](../../README.md)
